"""Worker 音频格式检测、WAV 直通与非 WAV 转码（US-022）。

下载完成（``inbox/<fragment_id>.part``）后的格式标准化步骤（tech-spec §5.1 / §3.3 / §3.5）：

1. 用 ``ffprobe`` 检测**真实**音频格式，不信任文件扩展名或 OSS object key 的 ``.wav`` 后缀。
2. 合规 WAV **直通**：原子 rename ``.part`` → ``fragments/<date>/<id>/audio.wav``；
   直通时 ``audio.sha256`` / ``audio.size_bytes`` 等于原始上传值（§3.3）。
3. 非 WAV 输入用 ``ffmpeg`` 转码：先写 ``inbox/<id>.wav.tmp``，再原子 rename → ``audio.wav``；
   ``audio.sha256`` 与 ``original_sha256`` 分别真实计算（通常不同，且都不为 null）。
4. 转码 / 探测失败时把原始文件留档到 ``inbox/failed/``，**不创建或污染** fragment 目录（§5.1）。

沿用「纯逻辑（无 IO，可直接单测）+ IO 用可注入 callable」分层：``standardize`` 默认用真实
``probe_media`` / ``ffmpeg_to_wav``，单测注入 fake 不触 ffmpeg/ffprobe。``make test-*`` 用真实
fixtures + ffmpeg/ffprobe 端到端验证。

本模块只做「``.part`` → ``audio.wav``」这一步；下载在 US-021（poller），manifest 落盘在 US-024，
完整流水线串联在 US-027。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from soniscope_worker.fixtures import FixtureError, MediaInfo, probe_media, sha256_of
from soniscope_worker.oss_admin import OssAdminError, object_key_for

AUDIO_FILENAME = "audio.wav"
WAV_TMP_SUFFIX = ".wav.tmp"


class AudioToolError(RuntimeError):
    """ffmpeg 转码失败或 ffmpeg 不可用（与 ffprobe 探测失败 FixtureError 区分）。"""


# ── 纯逻辑：格式判定 ───────────────────────────────────────────────────────
def is_wav(info: MediaInfo) -> bool:
    """ffprobe 探测结果是否为 WAV（容器名含 ``wav`` 或流编码为 ``pcm_*``）。

    与 :func:`fixtures.codec_matches` 的 wav 判定一致，不信任扩展名。
    """
    fmt = info.format_name.lower()
    codecs = [c.lower() for c in info.codec_names]
    return "wav" in fmt or any(c.startswith("pcm") for c in codecs)


def format_label(info: MediaInfo) -> str:
    """从 ffprobe 结果派生原始格式标签（仅在元数据未提供 original_format 时兜底）。"""
    if is_wav(info):
        return "wav"
    codecs = [c.lower() for c in info.codec_names]
    if "aac" in codecs:
        return "m4a"
    if codecs:
        return codecs[0]
    return info.format_name.lower().split(",")[0].strip()


# ── IO：ffmpeg 转码为 WAV ─────────────────────────────────────────────────
def ffmpeg_to_wav(src: Path, dest: Path) -> None:
    """用 ffmpeg 把任意输入转码为 16kHz 单声道 PCM WAV（ASR 友好的标准化目标）。

    ffmpeg 不可用抛 :class:`AudioToolError`；转码失败（损坏 / 不支持的输入）同样抛
    :class:`AudioToolError`，调用方据此留档到 ``inbox/failed/``。
    """
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                # 输出文件名为 ``<id>.wav.tmp``，扩展名 .tmp 无法让 ffmpeg 推断 muxer，
                # 必须显式指定 ``-f wav``。
                "-f",
                "wav",
                str(dest),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise AudioToolError(
            "未找到 ffmpeg，请先安装 ffmpeg（macOS：brew install ffmpeg）。"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise AudioToolError(f"ffmpeg 转码失败：{src.name}：{stderr[-500:]}") from exc


# ── 标准化结果 ─────────────────────────────────────────────────────────────
STATUS_PASSTHROUGH = "passthrough"
STATUS_TRANSCODED = "transcoded"
STATUS_FAILED = "failed"


@dataclass(frozen=True)
class StandardizeResult:
    """``.part`` → ``audio.wav`` 标准化结果。

    成功时 ``audio_format`` 固定为 ``"wav"``；``original_format`` 保留元数据声明值或探测结果。
    """

    fragment_id: str
    status: str  # passthrough / transcoded / failed
    audio_path: Path | None = None
    audio_format: str | None = None
    original_format: str | None = None
    audio_sha256: str | None = None
    audio_size_bytes: int | None = None
    original_sha256: str | None = None
    original_size_bytes: int | None = None
    failed_archive: Path | None = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status in (STATUS_PASSTHROUGH, STATUS_TRANSCODED)


def _archive_failed(part: Path, failed_root: Path, fragment_id: str) -> Path | None:
    """把失败的原始文件移到 ``inbox/failed/<fragment_id>.part`` 留档（不再重试）。"""
    failed_root.mkdir(parents=True, exist_ok=True)
    dest = failed_root / f"{fragment_id}.part"
    try:
        os.replace(part, dest)
        return dest
    except OSError:  # pragma: no cover - part 已不存在等罕见情况
        return None


def standardize(
    part: Path,
    *,
    fragment_id: str,
    fragments_root: Path,
    inbox_root: Path,
    failed_root: Path,
    original_format: str | None = None,
    log: Callable[[str], None] = lambda _msg: None,
    probe: Callable[[Path], MediaInfo] = probe_media,
    transcode: Callable[[Path, Path], None] = ffmpeg_to_wav,
) -> StandardizeResult:
    """把下载好的 ``.part`` 标准化为 ``fragments/<date>/<id>/audio.wav``（US-022）。

    - ffprobe 判定为 WAV → 直通（原子 rename，bytes 不变，sha256/size 与原始一致，§3.3）。
    - 非 WAV → ffmpeg 转码到 ``inbox/<id>.wav.tmp`` 后原子 rename（sha256 真实重算）。
    - 探测或转码失败 → 原始文件留档到 ``inbox/failed/``，不创建 fragment 目录（AC#7）。

    ``original_sha256`` / ``original_size_bytes`` 取下载得到的 ``.part`` 真实值（消费前计算），
    保证非 WAV 路径下两个 sha256 都不为 null（AC#6）。
    """
    try:
        date = object_key_for(fragment_id).split("/")[1]
    except OssAdminError as exc:
        return StandardizeResult(
            fragment_id=fragment_id, status=STATUS_FAILED, detail=f"非法 fragment_id：{exc}"
        )

    if not part.is_file():
        return StandardizeResult(
            fragment_id=fragment_id, status=STATUS_FAILED, detail=f"待标准化文件缺失：{part}"
        )

    # 原始（下载所得）字节的真实 sha256 / size —— 必须在 part 被 rename/转码消费前计算。
    original_sha256 = sha256_of(part)
    original_size_bytes = part.stat().st_size

    try:
        info = probe(part)
    except FixtureError as exc:
        archived = _archive_failed(part, failed_root, fragment_id)
        log(f"[audio] {fragment_id} 探测失败，留档到 {archived}：{exc}")
        return StandardizeResult(
            fragment_id=fragment_id,
            status=STATUS_FAILED,
            original_sha256=original_sha256,
            original_size_bytes=original_size_bytes,
            failed_archive=archived,
            detail=f"ffprobe 探测失败：{exc}",
        )

    fmt = (original_format or "").strip() or format_label(info)
    target_dir = fragments_root / date / fragment_id
    audio_path = target_dir / AUDIO_FILENAME

    if is_wav(info):
        # 直通：原子 rename .part → audio.wav，bytes 不变（AC#2/#5）。
        target_dir.mkdir(parents=True, exist_ok=True)
        os.replace(part, audio_path)
        log(f"[audio] {fragment_id} WAV 直通：{audio_path}")
        return StandardizeResult(
            fragment_id=fragment_id,
            status=STATUS_PASSTHROUGH,
            audio_path=audio_path,
            audio_format="wav",
            original_format=fmt,
            audio_sha256=original_sha256,  # 字节未变，等于原始 sha256（§3.3）
            audio_size_bytes=original_size_bytes,
            original_sha256=original_sha256,
            original_size_bytes=original_size_bytes,
        )

    # 非 WAV：ffmpeg 转码（AC#3）。先写 inbox/<id>.wav.tmp，再原子 rename。
    inbox_root.mkdir(parents=True, exist_ok=True)
    tmp = inbox_root / f"{fragment_id}{WAV_TMP_SUFFIX}"
    tmp.unlink(missing_ok=True)
    try:
        transcode(part, tmp)
    except AudioToolError as exc:
        tmp.unlink(missing_ok=True)
        archived = _archive_failed(part, failed_root, fragment_id)
        log(f"[audio] {fragment_id} 转码失败，留档到 {archived}：{exc}")
        return StandardizeResult(
            fragment_id=fragment_id,
            status=STATUS_FAILED,
            original_format=fmt,
            original_sha256=original_sha256,
            original_size_bytes=original_size_bytes,
            failed_archive=archived,
            detail=str(exc),
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, audio_path)
    part.unlink(missing_ok=True)  # 原始 .part 已被消费
    audio_sha256 = sha256_of(audio_path)
    audio_size_bytes = audio_path.stat().st_size
    log(f"[audio] {fragment_id} 转码为 WAV：{audio_path}（original_format={fmt}）")
    return StandardizeResult(
        fragment_id=fragment_id,
        status=STATUS_TRANSCODED,
        audio_path=audio_path,
        audio_format="wav",
        original_format=fmt,
        audio_sha256=audio_sha256,
        audio_size_bytes=audio_size_bytes,
        original_sha256=original_sha256,
        original_size_bytes=original_size_bytes,
    )


# ── make test-*：用真实 fixtures + ffmpeg/ffprobe 端到端验证 ────────────────
def _repo_root() -> Path:
    """仓库根目录（apps/worker/src/soniscope_worker/audio.py → parents[4]）。"""
    return Path(__file__).resolve().parents[4]


def _fixture_path(name: str) -> Path:
    return _repo_root() / "tests" / "audio" / name

# 各 test 用例的固定 fragment_id（合法格式，便于路径推导与人工核对）。
_PASSTHROUGH_FID = "20260527T120000_devp01_01HZX3K8MN5PQR9TFB7AYWVCDE"
_TRANSCODE_FID = "20260527T120100_devt01_01HZX3K8MN5PQR9TFB7AYWVCDF"
_FAIL_FID = "20260527T120200_devf01_01HZX3K8MN5PQR9TFB7AYWVCDG"


def _setup_workdir(base: Path) -> tuple[Path, Path, Path]:
    """在临时目录下建 inbox/ inbox/failed/ fragments/，返回三者路径。"""
    inbox = base / "inbox"
    failed = inbox / "failed"
    fragments = base / "fragments"
    for d in (inbox, failed, fragments):
        d.mkdir(parents=True, exist_ok=True)
    return inbox, failed, fragments


def run_test_wav_passthrough() -> tuple[list[str], int]:
    """make test-wav-passthrough：用 sample-20s.wav 验证直通（AC#8）。"""
    lines: list[str] = []
    src = _fixture_path("sample-20s.wav")
    if not src.is_file():
        lines.append(f"SKIP — 缺少 fixture：{src}（先跑 python3 scripts/fetch_test_fixtures.py）")
        return lines, 0
    with tempfile.TemporaryDirectory(prefix="soniscope-wav-passthrough-") as tmpdir:
        base = Path(tmpdir)
        inbox, failed, fragments = _setup_workdir(base)
        part = inbox / f"{_PASSTHROUGH_FID}.part"
        shutil.copy2(src, part)
        original_sha = sha256_of(part)
        result = standardize(
            part,
            fragment_id=_PASSTHROUGH_FID,
            fragments_root=fragments,
            inbox_root=inbox,
            failed_root=failed,
            original_format="wav",
            log=lines.append,
        )
        problems: list[str] = []
        if result.status != STATUS_PASSTHROUGH:
            problems.append(f"期望 passthrough，实际 {result.status}（{result.detail}）")
        if result.audio_path is None or not result.audio_path.is_file():
            problems.append("audio.wav 未生成")
        elif not is_wav(probe_media(result.audio_path)):
            problems.append("audio.wav 不被 ffprobe 识别为 WAV")
        if result.audio_format != "wav":
            problems.append(f"audio.format 应为 wav，实际 {result.audio_format}")
        if result.audio_sha256 != original_sha or result.original_sha256 != original_sha:
            problems.append("直通路径 audio.sha256 应等于 upload.original_sha256（§3.3）")
        if result.audio_size_bytes != result.original_size_bytes:
            problems.append("直通路径 audio.size_bytes 应等于 original_size_bytes")
        lines.append(f"original_sha256 = {original_sha[:16]}…")
        lines.append(f"audio.sha256    = {(result.audio_sha256 or '')[:16]}…")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ WAV 直通路径校验通过（audio.sha256 == upload.original_sha256）")
    return lines, 0


def run_test_audio_transcode_to_wav() -> tuple[list[str], int]:
    """make test-audio-transcode-to-wav：用 sample-20s.m4a 验证转码（AC#9）。"""
    lines: list[str] = []
    src = _fixture_path("sample-20s.m4a")
    if not src.is_file():
        lines.append(f"SKIP — 缺少 fixture：{src}（先跑 python3 scripts/fetch_test_fixtures.py）")
        return lines, 0
    with tempfile.TemporaryDirectory(prefix="soniscope-transcode-") as tmpdir:
        base = Path(tmpdir)
        inbox, failed, fragments = _setup_workdir(base)
        part = inbox / f"{_TRANSCODE_FID}.part"
        shutil.copy2(src, part)
        original_sha = sha256_of(part)
        try:
            result = standardize(
                part,
                fragment_id=_TRANSCODE_FID,
                fragments_root=fragments,
                inbox_root=inbox,
                failed_root=failed,
                original_format="m4a",
                log=lines.append,
            )
        except AudioToolError as exc:
            lines.append(f"SKIP — ffmpeg 不可用：{exc}")
            return lines, 0
        problems: list[str] = []
        if result.status != STATUS_TRANSCODED:
            problems.append(f"期望 transcoded，实际 {result.status}（{result.detail}）")
        if result.audio_path is None or not result.audio_path.is_file():
            problems.append("audio.wav 未生成")
        elif not is_wav(probe_media(result.audio_path)):
            problems.append("audio.wav 不被 ffprobe 识别为 WAV")
        if result.audio_format != "wav":
            problems.append(f"audio.format 应为 wav，实际 {result.audio_format}")
        if result.original_format != "m4a":
            problems.append(f"audio.original_format 应保留 m4a，实际 {result.original_format}")
        if not result.audio_sha256 or not result.original_sha256:
            problems.append("转码路径 audio.sha256 与 original_sha256 都不得为 null（§3.3）")
        elif result.audio_sha256 == result.original_sha256:
            problems.append("转码路径 audio.sha256 应不同于 original_sha256")
        if (inbox / f"{_TRANSCODE_FID}{WAV_TMP_SUFFIX}").exists():
            problems.append(".wav.tmp 残留未清理")
        lines.append(f"original_sha256(m4a) = {original_sha[:16]}…")
        lines.append(f"audio.sha256(wav)    = {(result.audio_sha256 or '')[:16]}…")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ 非 WAV → WAV 转码路径校验通过（audio.wav 可被 ffprobe 识别为 WAV）")
    return lines, 0


def run_test_transcode_fail() -> tuple[list[str], int]:
    """make test-transcode-fail：用损坏音频验证 inbox/failed/ 留档（AC#10）。"""
    lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="soniscope-transcode-fail-") as tmpdir:
        base = Path(tmpdir)
        inbox, failed, fragments = _setup_workdir(base)
        part = inbox / f"{_FAIL_FID}.part"
        # 损坏音频：随机字节，ffprobe / ffmpeg 都无法识别。
        part.write_bytes(b"NOT-A-REAL-AUDIO-FILE" * 64)
        result = standardize(
            part,
            fragment_id=_FAIL_FID,
            fragments_root=fragments,
            inbox_root=inbox,
            failed_root=failed,
            original_format="wav",
            log=lines.append,
        )
        problems: list[str] = []
        if result.status != STATUS_FAILED:
            problems.append(f"期望 failed，实际 {result.status}")
        archived = failed / f"{_FAIL_FID}.part"
        if not archived.is_file():
            problems.append(f"失败文件未留档到 inbox/failed/（{archived}）")
        if part.exists():
            problems.append("原始 .part 未从 inbox 移走")
        frag_dir = fragments / object_key_for(_FAIL_FID).split("/")[1] / _FAIL_FID
        if frag_dir.exists():
            problems.append(f"不应创建/污染 fragment 完成目录（{frag_dir}）")
        if (inbox / f"{_FAIL_FID}{WAV_TMP_SUFFIX}").exists():
            problems.append(".wav.tmp 残留未清理")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ 转码失败留档校验通过（inbox/failed/ 留档，未污染 fragments/）")
    return lines, 0
