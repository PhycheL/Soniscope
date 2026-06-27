"""Worker 轮询到落盘完整处理流水线（US-027，tech-spec §1.1 / §3.5 / §3.6 / §3.7）。

把前序 story 的各个单元串成一条幂等流水线：

1. **发现 / 下载 / 校验**（poller，US-021）：列举 OSS ``recordings/`` → 跳过已 ``.done`` 的
   Fragment（幂等）→ 下载到 ``inbox/<id>.part`` → sha256 校验 → 读 ``x-oss-meta-*`` 元数据。
2. **格式标准化**（audio，US-022）：``.part`` →（直通 / 转码）→ ``audio.wav``。
3. **manifest 初稿**（manifest，US-024）：组装 §3.3 manifest 并原子写 ``manifest.json``
   （``transcription.started_at`` 已填、``completed_at`` 待转写后回填）。
4. **转写**（transcriber/nls，US-025/026）：调用 :class:`Transcriber` → ``TranscriptResult``。
5. **transcript 落盘**：原子写 ``transcript.json``（经 ``tmp/`` 临时文件）+ ``transcript.txt``。
6. **manifest 终稿**：回填 ``transcription`` 四元组 + 计时，原子覆盖 ``manifest.json``。
7. **完成标记**：最后创建 0 字节 ``.done``（§3.5）。

**幂等 / 恢复**（AC#3/#4/#5）：正常轮询只看 ``.done``（存在即跳过，不下载/转码/转写）；
同一 object key 在一轮内重复出现只处理一次；中断重启后按硬盘真实文件状态继续——启动恢复扫描
（recovery，US-023）清理 ``inbox``/``tmp`` 中间态残留，并对「有 ``audio.wav`` 无 ``.done``」的
Fragment 直接重新转写补齐；缺 manifest 初稿的残留留待下一轮 OSS 轮询重下补全（对象永不删除）。

任一阶段失败都**不创建 ``.done``**，错误日志带 ``fragment_id`` 与失败阶段（AC#2）。

沿用「IO 用 :class:`OssSource` Protocol / :class:`Transcriber` 注入」分层：单测注入 fake 全程不
触网；``make test-*`` 用真实 fixtures + stub/真实转写器端到端验证。
"""

from __future__ import annotations

import json
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from soniscope_worker.audio import ffmpeg_to_wav, standardize
from soniscope_worker.config import TranscriberConfig
from soniscope_worker.fixtures import MediaInfo, probe_media
from soniscope_worker.locks import fragment_lock
from soniscope_worker.manifest import (
    TranscriptionInfo,
    UploadInfo,
    build_manifest,
    transcript_json_from_result,
)
from soniscope_worker.oss_admin import OssAdminError, object_key_for
from soniscope_worker.poller import (
    ManifestDraft,
    OssListing,
    OssSource,
    done_marker_path,
    plan_downloads,
    process_plan,
)
from soniscope_worker.recovery import (
    AUDIO_FILENAME,
    MANIFEST_FILENAME,
    TRANSCRIPT_JSON_FILENAME,
    TRANSCRIPT_TXT_FILENAME,
    FragmentState,
    atomic_write_json,
    atomic_write_text,
    create_done_marker,
    recover,
    transcript_txt_from_segments,
    write_transcript_json,
)
from soniscope_worker.transcriber import Transcriber, TranscriptResult

# 流水线阶段标识（失败时写入日志与 FragmentResult.stage）。
STAGE_DOWNLOAD = "download"
STAGE_STANDARDIZE = "standardize"
STAGE_MANIFEST_DRAFT = "manifest-draft"
STAGE_TRANSCRIBE = "transcribe"
STAGE_TRANSCRIPT = "transcript"
STAGE_MANIFEST_FINAL = "manifest-final"
STAGE_DONE = "done"

# FragmentResult.status 取值。
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


def _now_iso() -> str:
    """本地时区 ISO8601 时间戳（秒精度），供 transcription 时间戳使用。"""
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class FragmentResult:
    """单条 Fragment 处理结果。"""

    fragment_id: str
    status: str  # completed / failed / skipped
    stage: str  # 完成或失败时所处阶段
    fragment_dir: Path | None = None
    done_marker: Path | None = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == STATUS_COMPLETED


def _transcription_block(
    config: TranscriberConfig,
    result: TranscriptResult,
    *,
    started_at: str | None,
    completed_at: str | None,
    elapsed_seconds: float | None,
) -> dict[str, Any]:
    """构造 ``manifest.transcription`` 块（§3.3，与 build_manifest 字段一致）。

    ``transcriber`` / ``upload_mode`` 取自 config；``model`` / ``params_version`` /
    ``provider`` 取自真实转写结果。
    """
    return {
        "started_at": started_at,
        "completed_at": completed_at,
        "elapsed_seconds": elapsed_seconds,
        "transcriber": config.name,
        "model": result.model,
        "params_version": result.params_version,
        "provider": result.provider,
        "upload_mode": config.upload_mode,
    }


def _write_transcript_outputs(
    frag_dir: Path,
    fragment_id: str,
    result: TranscriptResult,
    *,
    tmp_root: Path,
) -> None:
    """原子写 ``transcript.json``（经 tmp）+ ``transcript.txt``（segments 派生，§3.4/§3.5）。"""
    result_dict = result.as_result_dict()
    write_transcript_json(
        frag_dir, fragment_id, transcript_json_from_result(result_dict), tmp_root=tmp_root
    )
    segments = result_dict.get("segments", [])
    txt = transcript_txt_from_segments(segments if isinstance(segments, list) else [])
    atomic_write_text(frag_dir / TRANSCRIPT_TXT_FILENAME, txt)


# ── 从下载好的 .part 跑完整一条 Fragment ────────────────────────────────────
def process_part(
    *,
    fragment_id: str,
    object_key: str,
    part: Path,
    draft: ManifestDraft,
    transcriber: Transcriber,
    config: TranscriberConfig,
    fragments_root: Path,
    inbox_root: Path,
    failed_root: Path,
    tmp_root: Path,
    now_iso: Callable[[], str] | None = None,
    monotonic: Callable[[], float] | None = None,
    probe: Callable[[Path], MediaInfo] = probe_media,
    transcode: Callable[[Path, Path], None] = ffmpeg_to_wav,
    log: Callable[[str], None] = lambda _msg: None,
) -> FragmentResult:
    """把下载好的 ``.part`` 跑完整流水线：标准化 → manifest 初稿 → 转写 → transcript → ``.done``。

    顺序严格按 AC#1：``audio.wav`` 标准化 → 写 manifest 初稿 → 调 Transcriber → 写
    transcript.json → 写 transcript.txt → 更新 manifest.transcription → 最后创建 ``.done``。
    任一阶段失败都不创建 ``.done``，返回 ``failed`` 并在日志标注失败阶段（AC#2）。
    """
    resolve_now = now_iso if now_iso is not None else _now_iso
    resolve_mono = monotonic if monotonic is not None else time.monotonic

    # 阶段 1：格式标准化（.part → audio.wav）。
    std = standardize(
        part,
        fragment_id=fragment_id,
        fragments_root=fragments_root,
        inbox_root=inbox_root,
        failed_root=failed_root,
        original_format=draft.original_format,
        log=log,
        probe=probe,
        transcode=transcode,
    )
    if not std.ok or std.audio_path is None:
        log(f"[pipeline] {fragment_id} 失败于阶段 {STAGE_STANDARDIZE}：{std.detail}")
        return FragmentResult(fragment_id, STATUS_FAILED, STAGE_STANDARDIZE, detail=std.detail)
    frag_dir = std.audio_path.parent
    manifest_path = frag_dir / MANIFEST_FILENAME

    # 阶段 2：manifest 初稿（transcription.started_at 已填、completed_at 待回填）。
    started_at = resolve_now()
    t0 = resolve_mono()
    draft_manifest = build_manifest(
        fragment_id=fragment_id,
        draft=draft,
        std=std,
        upload=UploadInfo(),
        transcription=TranscriptionInfo(
            started_at=started_at,
            transcriber=config.name,
            upload_mode=config.upload_mode,
        ),
    )
    try:
        atomic_write_json(manifest_path, draft_manifest)
    except OSError as exc:
        log(f"[pipeline] {fragment_id} 失败于阶段 {STAGE_MANIFEST_DRAFT}：{exc}")
        return FragmentResult(
            fragment_id, STATUS_FAILED, STAGE_MANIFEST_DRAFT, fragment_dir=frag_dir, detail=str(exc)
        )
    log(f"[pipeline] {fragment_id} manifest 初稿写入：{manifest_path}")

    # 阶段 3-6 在 fragment 粒度文件锁内执行（§3.7：与 retranscribe 互斥，绝不并发转同一条）。
    with fragment_lock(tmp_root, fragment_id):
        # 阶段 3：调用 Transcriber（云端 ASR）。
        try:
            result = transcriber.transcribe(fragment_id, std.audio_path, object_key)
        except Exception as exc:  # noqa: BLE001 - 转写失败不创建 .done，收敛为单项 failed（AC#2）
            log(
                f"[pipeline] {fragment_id} 失败于阶段 {STAGE_TRANSCRIBE}："
                f"{type(exc).__name__}: {exc}"
            )
            return FragmentResult(
                fragment_id,
                STATUS_FAILED,
                STAGE_TRANSCRIBE,
                fragment_dir=frag_dir,
                detail=f"{type(exc).__name__}: {exc}",
            )
        completed_at = resolve_now()
        elapsed = round(resolve_mono() - t0, 3)

        # 阶段 4：transcript.json + transcript.txt 落盘。
        try:
            _write_transcript_outputs(frag_dir, fragment_id, result, tmp_root=tmp_root)
        except OSError as exc:
            log(f"[pipeline] {fragment_id} 失败于阶段 {STAGE_TRANSCRIPT}：{exc}")
            return FragmentResult(
                fragment_id, STATUS_FAILED, STAGE_TRANSCRIPT, fragment_dir=frag_dir, detail=str(exc)
            )

        # 阶段 5：manifest 终稿（回填 transcription 四元组 + 计时）。
        final_manifest = build_manifest(
            fragment_id=fragment_id,
            draft=draft,
            std=std,
            upload=UploadInfo(),
            transcription=TranscriptionInfo(
                started_at=started_at,
                completed_at=completed_at,
                elapsed_seconds=elapsed,
                transcriber=config.name,
                model=result.model,
                params_version=result.params_version,
                provider=result.provider,
                upload_mode=config.upload_mode,
            ),
        )
        try:
            atomic_write_json(manifest_path, final_manifest)
        except OSError as exc:
            log(f"[pipeline] {fragment_id} 失败于阶段 {STAGE_MANIFEST_FINAL}：{exc}")
            return FragmentResult(
                fragment_id, STATUS_FAILED, STAGE_MANIFEST_FINAL,
                fragment_dir=frag_dir, detail=str(exc),
            )

        # 阶段 6：最后创建 .done（0 字节）。
        done = create_done_marker(frag_dir)
    log(f"[pipeline] {fragment_id} 处理完成：五产物齐全，.done 已创建（耗时 {elapsed}s）")
    return FragmentResult(
        fragment_id, STATUS_COMPLETED, STAGE_DONE, fragment_dir=frag_dir, done_marker=done
    )


# ── 启动恢复：对「有 audio.wav 无 .done」的 Fragment 重新转写补齐 ────────────
def process_pending(
    state: FragmentState,
    transcriber: Transcriber,
    *,
    config: TranscriberConfig,
    tmp_root: Path,
    now_iso: Callable[[], str] | None = None,
    monotonic: Callable[[], float] | None = None,
    log: Callable[[str], None] = lambda _msg: None,
) -> FragmentResult:
    """重新转写一个「转写未完」的 Fragment（§3.6 第三段，audio.wav 已就绪、无 .done）。

    读已有 manifest 初稿（含 OSS 元数据派生字段），转写现有 ``audio.wav``，回填
    ``transcription`` 并最后创建 ``.done``。缺 manifest 初稿（更早阶段崩溃）时跳过，
    留待下一轮 OSS 轮询重下补全（OSS 对象永不删除，AC#5）。
    """
    resolve_now = now_iso if now_iso is not None else _now_iso
    resolve_mono = monotonic if monotonic is not None else time.monotonic
    frag_dir = state.path
    fragment_id = state.fragment_id
    audio_path = frag_dir / AUDIO_FILENAME
    manifest_path = frag_dir / MANIFEST_FILENAME

    if not audio_path.is_file():  # 理论上 pending 必有 audio.wav，防御性处理
        return FragmentResult(
            fragment_id, STATUS_SKIPPED, STAGE_STANDARDIZE,
            fragment_dir=frag_dir, detail="无 audio.wav",
        )
    try:
        object_key = object_key_for(fragment_id)
    except OssAdminError as exc:
        log(f"[pipeline] {fragment_id} 非法 fragment_id，跳过恢复转写：{exc}")
        return FragmentResult(
            fragment_id, STATUS_SKIPPED, STAGE_STANDARDIZE, fragment_dir=frag_dir, detail=str(exc)
        )
    if not manifest_path.is_file():
        log(
            f"[pipeline] {fragment_id} 待转写但缺 manifest 初稿，留待 OSS 轮询重下补全"
        )
        return FragmentResult(
            fragment_id, STATUS_SKIPPED, STAGE_MANIFEST_DRAFT,
            fragment_dir=frag_dir, detail="缺 manifest 初稿",
        )
    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log(f"[pipeline] {fragment_id} manifest 初稿损坏，留待重下：{exc}")
        return FragmentResult(
            fragment_id, STATUS_SKIPPED, STAGE_MANIFEST_DRAFT,
            fragment_dir=frag_dir, detail=str(exc),
        )

    started_at = resolve_now()
    t0 = resolve_mono()
    # 恢复转写同样在 fragment 粒度文件锁内执行（§3.7：与 retranscribe 互斥）。
    with fragment_lock(tmp_root, fragment_id):
        try:
            result = transcriber.transcribe(fragment_id, audio_path, object_key)
        except Exception as exc:  # noqa: BLE001 - 恢复转写失败不创建 .done（AC#2）
            log(
                f"[pipeline] {fragment_id} 恢复转写失败于阶段 {STAGE_TRANSCRIBE}："
                f"{type(exc).__name__}: {exc}"
            )
            return FragmentResult(
                fragment_id,
                STATUS_FAILED,
                STAGE_TRANSCRIBE,
                fragment_dir=frag_dir,
                detail=f"{type(exc).__name__}: {exc}",
            )
        completed_at = resolve_now()
        elapsed = round(resolve_mono() - t0, 3)

        try:
            _write_transcript_outputs(frag_dir, fragment_id, result, tmp_root=tmp_root)
            manifest["transcription"] = _transcription_block(
                config, result,
                started_at=started_at, completed_at=completed_at, elapsed_seconds=elapsed,
            )
            atomic_write_json(manifest_path, manifest)
        except OSError as exc:
            log(f"[pipeline] {fragment_id} 恢复转写落盘失败：{exc}")
            return FragmentResult(
                fragment_id, STATUS_FAILED, STAGE_TRANSCRIPT, fragment_dir=frag_dir, detail=str(exc)
            )
        done = create_done_marker(frag_dir)
    log(f"[pipeline] {fragment_id} 恢复转写完成，.done 已补回（耗时 {elapsed}s）")
    return FragmentResult(
        fragment_id, STATUS_COMPLETED, STAGE_DONE, fragment_dir=frag_dir, done_marker=done
    )


# ── 一轮完整流水线（列举 → 跳过 .done → 下载校验 → 标准化转写落盘）──────────
def run_pipeline_once(
    source: OssSource,
    transcriber: Transcriber,
    *,
    config: TranscriberConfig,
    fragments_root: Path,
    inbox_root: Path,
    failed_root: Path,
    tmp_root: Path,
    now_iso: Callable[[], str] | None = None,
    monotonic: Callable[[], float] | None = None,
    probe: Callable[[Path], MediaInfo] = probe_media,
    transcode: Callable[[Path, Path], None] = ffmpeg_to_wav,
    log: Callable[[str], None] = lambda _msg: None,
) -> list[FragmentResult]:
    """执行一轮完整流水线：已 ``.done`` 的跳过（AC#3），新对象走 process_part。

    同一 object key 在一轮内重复出现只处理一次（AC#4：不产生重复 fragment 目录）。
    单条失败收敛为 ``failed`` 不影响整轮其它对象。
    """
    inbox_root.mkdir(parents=True, exist_ok=True)
    listings = source.list_recordings()
    plan = plan_downloads(
        listings,
        done_check=lambda fid, date: done_marker_path(fragments_root, date, fid).exists(),
    )
    log(
        f"[pipeline] 扫描 OSS 共 {len(listings)} 个对象：待处理 {len(plan.to_download)}，"
        f"跳过(.done) {len(plan.skipped_done)}，忽略 {len(plan.ignored_keys)}"
    )
    results: list[FragmentResult] = []
    seen: set[str] = set()
    for item in plan.to_download:
        if item.fragment_id in seen:  # 同 fragment 在一轮内只处理一次（AC#4）
            continue
        seen.add(item.fragment_id)
        outcome = process_plan(item, source, inbox_root=inbox_root, fragments_root=fragments_root)
        if outcome.status != "downloaded" or outcome.part_path is None or outcome.draft is None:
            log(
                f"[pipeline] {item.fragment_id} 下载/校验未通过（{outcome.status}），"
                f"本轮跳过等待重下：{outcome.detail}"
            )
            results.append(
                FragmentResult(
                    item.fragment_id, STATUS_FAILED, STAGE_DOWNLOAD, detail=outcome.detail
                )
            )
            continue
        results.append(
            process_part(
                fragment_id=item.fragment_id,
                object_key=item.object_key,
                part=outcome.part_path,
                draft=outcome.draft,
                transcriber=transcriber,
                config=config,
                fragments_root=fragments_root,
                inbox_root=inbox_root,
                failed_root=failed_root,
                tmp_root=tmp_root,
                now_iso=now_iso,
                monotonic=monotonic,
                probe=probe,
                transcode=transcode,
                log=log,
            )
        )
    return results


def run_pipeline_loop(
    source: OssSource,
    transcriber: Transcriber,
    interval_seconds: float,
    *,
    config: TranscriberConfig,
    fragments_root: Path,
    inbox_root: Path,
    failed_root: Path,
    tmp_root: Path,
    log: Callable[[str], None] = print,
    recover_first: bool = True,
    max_iterations: int | None = None,
    stop: Callable[[], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    now_iso: Callable[[], str] | None = None,
) -> int:
    """完整 Worker 主循环：启动恢复 → 周期性跑完整流水线；返回执行的扫描轮数。

    启动先做 §3.6 三段恢复扫描（清理 inbox/tmp 中间态残留），并对「转写未完」的 Fragment
    重新转写补齐 ``.done``；随后每隔 ``interval_seconds`` 跑一轮 :func:`run_pipeline_once`。
    单轮异常只记日志不杀死守护进程（下一轮重试）。``max_iterations`` / ``stop`` /
    ``sleep`` / ``monotonic`` 供测试与确定性单测注入。
    """
    if recover_first:
        report = recover(
            inbox_root=inbox_root, tmp_root=tmp_root, fragments_root=fragments_root, log=log
        )
        for state in report.pending:
            process_pending(
                state,
                transcriber,
                config=config,
                tmp_root=tmp_root,
                now_iso=now_iso,
                monotonic=monotonic,
                log=log,
            )
    iterations = 0
    while True:
        try:
            run_pipeline_once(
                source,
                transcriber,
                config=config,
                fragments_root=fragments_root,
                inbox_root=inbox_root,
                failed_root=failed_root,
                tmp_root=tmp_root,
                now_iso=now_iso,
                monotonic=monotonic,
                log=log,
            )
        except Exception as exc:  # noqa: BLE001 - 单轮失败不杀死守护进程
            log(f"[pipeline] 本轮处理失败（下一轮重试）：{type(exc).__name__}: {exc}")
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        if stop is not None and stop():
            break
        sleep(interval_seconds)
    return iterations


# ── make worker-run 真实主循环入口（供 poller.run_worker_run 委托）───────────
def run_worker_pipeline(log: Callable[[str], None] = print) -> None:
    """启动真实 Worker 完整流水线主循环（make worker-run）。

    读 config.yaml 的 OSS / poll / transcriber 段，构造 :class:`RealOssSource` 与真实
    Transcriber，无限轮询。config 缺失时打印诊断并返回。
    """
    from soniscope_worker.config import ConfigError, config_path, load_config
    from soniscope_worker.paths import fragments_dir, inbox_dir, inbox_failed_dir, tmp_dir
    from soniscope_worker.poller import RealOssSource
    from soniscope_worker.transcriber import create_transcriber

    try:
        cfg = load_config(config_path())
    except ConfigError as exc:
        log(f"[pipeline] 无法启动主流水线：{exc}")
        return
    interval = cfg.poll.interval_seconds
    log(
        f"[pipeline] Worker 主流水线启动，间隔 {interval}s，bucket={cfg.oss.bucket}，"
        f"transcriber={cfg.transcriber.name}"
    )
    source = RealOssSource(cfg)
    transcriber = create_transcriber(cfg.transcriber)
    run_pipeline_loop(
        source,
        transcriber,
        interval,
        config=cfg.transcriber,
        fragments_root=fragments_dir(),
        inbox_root=inbox_dir(),
        failed_root=inbox_failed_dir(),
        tmp_root=tmp_dir(),
        log=log,
    )


# ── make test-*：自包含 / 真实 fixtures 端到端验证 ──────────────────────────
def _repo_root() -> Path:
    """仓库根目录（apps/worker/src/soniscope_worker/pipeline.py → parents[4]）。"""
    return Path(__file__).resolve().parents[4]


def _fixture_path(name: str) -> Path:
    return _repo_root() / "tests" / "audio" / name


# 各 test 用例的固定 fragment_id（合法格式，便于路径推导与人工核对）。
_PIPELINE_FID = "20260527T160000_devp01_01HZX3K8MN5PQR9TFB7AYWVCDE"
_NOREDL_FID = "20260527T160100_devn01_01HZX3K8MN5PQR9TFB7AYWVCDF"
_TRANSCRIBE_FID = "20260527T160200_devt01_01HZX3K8MN5PQR9TFB7AYWVCDG"

# sample-20s.wav 的固定 OSS 用户自定义元数据（构造确定性 ManifestDraft；sha256 运行时回填）。
_SAMPLE_META: dict[str, str] = {
    "session-id": "01HZX3K8MN5PQR9TFB7AYWVCDE",
    "chunk-seq": "1",
    "chunk-total": "0",
    "recorded-at": "2026-05-27T16:00:00+08:00",
    "duration": "24",
    "original-format": "wav",
}

# §5.4 联调基线主干（sample-20s.wav）代表性词，用于宽松校验转写文本（与 nls 基线一致）。
_BASELINE_KEYWORDS = ("选择", "优先级")


class _StubTranscriber:
    """make test 用的确定性占位转写器（不触网；真实 NLS 由 make test-transcribe 覆盖）。"""

    name = "cloud-speech"

    def transcribe(
        self, fragment_id: str, audio_path: Path, oss_key: str
    ) -> TranscriptResult:
        from soniscope_worker.transcriber import Segment

        return TranscriptResult(
            segments=[
                Segment(0.0, 2.5, "今天天气不错"),
                Segment(2.5, 5.1, "我准备去公园跑步"),
            ],
            language="zh",
            model="stub",
            params_version="test",
            provider="stub",
            duration=24.0,
        )


class _FixtureSource:
    """make test 用的内存 OSS 数据源：把本地 fixture 当作单个 recordings 对象。

    ``fail_first_download`` 为真时第一次 download 写入部分字节后抛错（模拟 kill -9 下载中断），
    其余调用写完整字节。记录调用次数供 test-no-redownload 断言。
    """

    def __init__(
        self,
        object_key: str,
        body: bytes,
        meta: dict[str, str],
        *,
        fail_first_download: bool = False,
    ) -> None:
        self._key = object_key
        self._body = body
        self._meta = meta
        self._fail_first = fail_first_download
        self.download_calls: list[str] = []
        self.list_calls = 0

    def list_recordings(self) -> list[OssListing]:
        self.list_calls += 1
        return [OssListing(key=self._key, size=len(self._body))]

    def head_metadata(self, object_key: str) -> dict[str, str]:
        return dict(self._meta)

    def download(self, object_key: str, dest: Path) -> None:
        self.download_calls.append(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self._fail_first and len(self.download_calls) == 1:
            dest.write_bytes(self._body[: max(1, len(self._body) // 2)])  # 部分写入
            raise RuntimeError("模拟下载中断（kill -9）")
        dest.write_bytes(self._body)


def _stub_config() -> TranscriberConfig:
    """make test 用的最小 TranscriberConfig（占位字段，stub 转写器不真正使用 AK）。"""
    return TranscriberConfig.model_validate(
        {
            "name": "cloud-speech",
            "provider": "aliyun-nls",
            "model": "中文普通话（识音石 V1 - 端到端模型)",
            "params_version": "v1",
            "api_endpoint": "cn-beijing",
            "appkey": "stub-appkey-0000",
            "access_key_id": "stub-ak-id",
            "access_key_secret": "stub-ak-secret-0000",
            "upload_mode": "oss-url",
        }
    )


def _setup_runtime(base: Path) -> tuple[Path, Path, Path, Path]:
    """在临时目录下建 inbox/ inbox/failed/ fragments/ tmp/，返回四者路径。"""
    inbox = base / "inbox"
    failed = inbox / "failed"
    fragments = base / "fragments"
    tmp = base / "tmp"
    for d in (inbox, failed, fragments, tmp):
        d.mkdir(parents=True, exist_ok=True)
    return inbox, failed, fragments, tmp


def _sample_meta_with_sha(sha: str) -> dict[str, str]:
    meta = dict(_SAMPLE_META)
    meta["sha256"] = sha
    return meta


def _expected_products(frag_dir: Path) -> dict[str, Path]:
    return {
        AUDIO_FILENAME: frag_dir / AUDIO_FILENAME,
        MANIFEST_FILENAME: frag_dir / MANIFEST_FILENAME,
        TRANSCRIPT_JSON_FILENAME: frag_dir / TRANSCRIPT_JSON_FILENAME,
        TRANSCRIPT_TXT_FILENAME: frag_dir / TRANSCRIPT_TXT_FILENAME,
        ".done": frag_dir / ".done",
    }


def run_test_download_interrupt() -> tuple[list[str], int]:
    """make test-download-interrupt：下载中 kill -9 → 重启恢复后最终完成（AC#6）。

    自包含：用 sample-20s.wav fixture + stub 转写器。第一轮下载中断留下残留 ``.part``；
    重启恢复扫描清理 ``.part``；第二轮完整下载并跑通流水线，五产物齐全。
    """
    from soniscope_worker.fixtures import sha256_of

    lines: list[str] = []
    src = _fixture_path("sample-20s.wav")
    if not src.is_file():
        lines.append(f"SKIP — 缺少 fixture：{src}（先跑 python3 scripts/fetch_test_fixtures.py）")
        return lines, 0
    body = src.read_bytes()
    sha = sha256_of(src)
    object_key = object_key_for(_PIPELINE_FID)
    config = _stub_config()
    transcriber: Transcriber = _StubTranscriber()

    with tempfile.TemporaryDirectory(prefix="soniscope-download-interrupt-") as tmpdir:
        base = Path(tmpdir)
        inbox, failed, fragments, tmp = _setup_runtime(base)
        date = object_key.split("/")[1]
        frag_dir = fragments / date / _PIPELINE_FID

        # 第一轮：下载中断（kill -9），残留 .part，无 .done。
        src1 = _FixtureSource(
            object_key, body, _sample_meta_with_sha(sha), fail_first_download=True
        )
        run_pipeline_once(
            src1, transcriber, config=config, fragments_root=fragments,
            inbox_root=inbox, failed_root=failed, tmp_root=tmp, log=lines.append,
        )
        part = inbox / f"{_PIPELINE_FID}.part"
        problems: list[str] = []
        if not part.is_file():
            problems.append("下载中断后未见残留 .part（无法验证恢复路径）")
        if (frag_dir / ".done").exists():
            problems.append("下载中断后不应存在 .done")

        # 重启恢复扫描：清理 inbox 残留 .part。
        recover(inbox_root=inbox, tmp_root=tmp, fragments_root=fragments, log=lines.append)
        if part.exists():
            problems.append("恢复扫描后 .part 残留未清理")

        # 第二轮：完整下载并跑通流水线。
        src2 = _FixtureSource(object_key, body, _sample_meta_with_sha(sha))
        results = run_pipeline_once(
            src2, transcriber, config=config, fragments_root=fragments,
            inbox_root=inbox, failed_root=failed, tmp_root=tmp, log=lines.append,
        )
        if not results or not results[0].ok:
            problems.append(f"重启后流水线未完成：{results[0].detail if results else '无结果'}")
        for name, path in _expected_products(frag_dir).items():
            if not path.is_file():
                problems.append(f"缺少产物 {name}")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ 下载中断恢复校验通过（清理残留 .part 后重新下载并完成五产物）")
    return lines, 0


def run_test_no_redownload() -> tuple[list[str], int]:
    """make test-no-redownload：已 ``.done`` 的 Fragment 不会被重新下载（AC#7）。

    自包含：跑两轮流水线，断言第一轮下载并完成、第二轮因 ``.done`` 跳过，下载计数仍为 1。
    """
    from soniscope_worker.fixtures import sha256_of

    lines: list[str] = []
    src = _fixture_path("sample-20s.wav")
    if not src.is_file():
        lines.append(f"SKIP — 缺少 fixture：{src}（先跑 python3 scripts/fetch_test_fixtures.py）")
        return lines, 0
    body = src.read_bytes()
    sha = sha256_of(src)
    object_key = object_key_for(_NOREDL_FID)
    config = _stub_config()
    transcriber: Transcriber = _StubTranscriber()

    with tempfile.TemporaryDirectory(prefix="soniscope-no-redownload-") as tmpdir:
        base = Path(tmpdir)
        inbox, failed, fragments, tmp = _setup_runtime(base)
        source = _FixtureSource(object_key, body, _sample_meta_with_sha(sha))

        first = run_pipeline_once(
            source, transcriber, config=config, fragments_root=fragments,
            inbox_root=inbox, failed_root=failed, tmp_root=tmp, log=lines.append,
        )
        second = run_pipeline_once(
            source, transcriber, config=config, fragments_root=fragments,
            inbox_root=inbox, failed_root=failed, tmp_root=tmp, log=lines.append,
        )
        problems: list[str] = []
        if not first or not first[0].ok:
            problems.append("第一轮未完成该 Fragment")
        if second:
            problems.append(f"第二轮不应再处理已 .done 的 Fragment（实际处理 {len(second)} 条）")
        if len(source.download_calls) != 1:
            problems.append(
                f"已 .done Fragment 被重复下载：download 调用 "
                f"{len(source.download_calls)} 次（应为 1）"
            )
        lines.append(f"download 调用次数 = {len(source.download_calls)}（期望 1）")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ 幂等校验通过（已 .done Fragment 第二轮跳过，未重新下载）")
    return lines, 0


def run_test_transcribe() -> tuple[list[str], int]:
    """make test-transcribe：用 sample-20s.wav 跑完整 Worker 转写（真实 NLS，AC#8）。

    走完整流水线（标准化 → manifest → 真实 Transcriber → transcript → .done），断言五产物
    齐全且 ``transcript.txt`` 含 runbook §5.4 基线主干文字。缺 config / SDK / 网络 / ffprobe
    时优雅 SKIP（exit 0）；逻辑部分由 test_pipeline 单测用 stub 全覆盖。
    """
    from soniscope_worker.config import ConfigError, config_path, load_config
    from soniscope_worker.fixtures import FixtureError, sha256_of

    lines: list[str] = []
    src = _fixture_path("sample-20s.wav")
    if not src.is_file():
        lines.append(f"SKIP — 缺少 fixture：{src}（先跑 python3 scripts/fetch_test_fixtures.py）")
        return lines, 0
    try:
        cfg = load_config(config_path())
    except ConfigError as exc:
        lines.append(f"SKIP — 无法加载 config.yaml：{exc}")
        return lines, 0
    # 探测可用性（缺 ffprobe → SKIP，不误判为转写失败）。
    try:
        probe_media(src)
    except FixtureError as exc:
        lines.append(f"SKIP — ffprobe 不可用：{exc}")
        return lines, 0

    from soniscope_worker.transcriber import create_transcriber

    transcriber = create_transcriber(cfg.transcriber)
    body = src.read_bytes()
    sha = sha256_of(src)
    # oss_key 用 runbook 真实 sample 对象，使 oss-url 模式下 NLS 能拉取到音频。
    object_key = "sample/sample-20s.wav"

    with tempfile.TemporaryDirectory(prefix="soniscope-test-transcribe-") as tmpdir:
        base = Path(tmpdir)
        inbox, failed, fragments, tmp = _setup_runtime(base)
        part = inbox / f"{_TRANSCRIBE_FID}.part"
        part.write_bytes(body)
        draft_meta = _sample_meta_with_sha(sha)
        from soniscope_worker.poller import metadata_to_draft

        draft = metadata_to_draft(_TRANSCRIBE_FID, draft_meta)
        result = process_part(
            fragment_id=_TRANSCRIBE_FID,
            object_key=object_key,
            part=part,
            draft=draft,
            transcriber=transcriber,
            config=cfg.transcriber,
            fragments_root=fragments,
            inbox_root=inbox,
            failed_root=failed,
            tmp_root=tmp,
            log=lines.append,
        )
        if result.status == STATUS_FAILED and result.stage == STAGE_TRANSCRIBE:
            lines.append(
                f"SKIP — 真实 NLS 转写未完成（缺 SDK / 凭证 / 网络）：{result.detail}"
            )
            return lines, 0
        if not result.ok or result.fragment_dir is None:
            lines.append(f"FAIL — 流水线未完成（阶段 {result.stage}）：{result.detail}")
            return lines, 1
        frag_dir = result.fragment_dir
        problems: list[str] = []
        for name, path in _expected_products(frag_dir).items():
            if not path.is_file():
                problems.append(f"缺少产物 {name}")
        txt_path = frag_dir / TRANSCRIPT_TXT_FILENAME
        if txt_path.is_file():
            text = txt_path.read_text(encoding="utf-8")
            lines.append(f"transcript.txt：{text[:60]}{'…' if len(text) > 60 else ''}")
            if not any(kw in text for kw in _BASELINE_KEYWORDS):
                problems.append(
                    f"transcript.txt 主干与 §5.4 基线不符（期望含 {_BASELINE_KEYWORDS} 其一）"
                )
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ 完整 Worker 转写校验通过（五产物齐全，transcript.txt 含 §5.4 基线主干）")
    return lines, 0
