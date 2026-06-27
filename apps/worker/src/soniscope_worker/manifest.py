"""``manifest.json`` schema 组装、``transcript.*`` 落盘与 Fragment 完整性检查（US-024）。

每个 Fragment 目录下的 ``manifest.json`` 是该 Fragment 的**唯一权威状态来源**（tech-spec §3.3）。
本模块把三个来源的字段拼成符合 schema 的 manifest：

1. **从 fragment_id 解析**：``fragment_id`` / ``device_id``（fragment_id 中间段 deviceShortId）。
2. **从 OSS 用户自定义元数据**（``ManifestDraft``，见 poller.metadata_to_draft）：``session_id`` /
   ``chunk_seq`` / ``chunk_total`` / ``recorded_at`` / ``duration_seconds`` /
   ``audio.original_format`` / ``upload.original_sha256``。
3. **Worker 本地计算 / 流程填入**（``StandardizeResult`` + upload/transcription）：
   ``audio.sha256`` / ``audio.size_bytes`` / ``audio.format``（标准化后的最终 WAV，真实计算）、
   ``upload.original_size_bytes``（OSS Content-Length 或下载字节数）、``upload.*`` 时间戳、
   ``transcription.*``（转写四元组 + 计时）。

``transcript.json`` 结构为 ``segments`` / ``language`` / ``model`` / ``params_version`` /
``provider``（§3.4），**不落盘** ``TranscriptResult.duration``（时长已记录在
``manifest.duration_seconds``）；``transcript.txt`` 由 ``segments[].text`` 顺序拼接派生。

落盘遵循 §3.5 三段式协议（先临时 → 原子 rename → ``.done`` 最后、0 字节）：复用
:mod:`soniscope_worker.recovery` 的原子写入工具。本模块只做 manifest/transcript 组装与落盘，
完整流水线（下载 → 标准化 → 转写 → manifest → .done）在 US-027 串联。
"""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from soniscope_worker.audio import StandardizeResult, standardize
from soniscope_worker.fixtures import sha256_of
from soniscope_worker.oss_admin import OssAdminError, object_key_for
from soniscope_worker.poller import ManifestDraft, metadata_to_draft
from soniscope_worker.recovery import (
    AUDIO_FILENAME,
    DONE_MARKER,
    MANIFEST_FILENAME,
    TRANSCRIPT_JSON_FILENAME,
    TRANSCRIPT_TXT_FILENAME,
    atomic_write_json,
    atomic_write_text,
    create_done_marker,
    transcript_txt_from_segments,
    write_transcript_json,
)

VERIFY_METHOD = "fc-head-object"

# transcript.json 只保留这五个字段（§3.4），刻意排除内存态 TranscriptResult.duration。
_TRANSCRIPT_FIELDS = ("segments", "language", "model", "params_version", "provider")

# manifest 中随每次运行变化的时间戳 / 计时字段（make test-manifest-idempotent 比对时剔除）。
TIMESTAMP_FIELD_PATHS = (
    ("upload", "uploaded_at"),
    ("upload", "verified_at"),
    ("transcription", "started_at"),
    ("transcription", "completed_at"),
    ("transcription", "elapsed_seconds"),
)


class ManifestError(Exception):
    """manifest 组装错误（非法 fragment_id 等）。"""


# ── 纯逻辑：字段解析与组装 ─────────────────────────────────────────────────
def device_id_of(fragment_id: str) -> str:
    """从 ``fragment_id`` 解析 ``device_id``（中间段 deviceShortId，snake_case）。

    fragment_id 形如 ``<YYYYMMDDTHHMMSS>_<deviceShortId>_<26 ULID>``；先经
    :func:`object_key_for` 校验格式 / 日期合法，再取中间段。非法时抛 :class:`ManifestError`。
    """
    try:
        object_key_for(fragment_id)  # 校验格式与日期合法性
    except OssAdminError as exc:
        raise ManifestError(str(exc)) from exc
    return fragment_id.split("_")[1]


@dataclass(frozen=True)
class UploadInfo:
    """``manifest.upload`` 流程态字段（上传 / verify 时间戳由小程序回执映射）。"""

    uploaded_at: str | None = None
    verified_at: str | None = None
    verify_method: str = VERIFY_METHOD
    # original_sha256 / original_size_bytes 默认取 draft / StandardizeResult，可显式覆盖。


@dataclass(frozen=True)
class TranscriptionInfo:
    """``manifest.transcription`` 四元组 + 计时（§3.3 / §6.3）。"""

    started_at: str | None = None
    completed_at: str | None = None
    elapsed_seconds: float | None = None
    transcriber: str | None = None
    model: str | None = None
    params_version: str | None = None
    provider: str | None = None
    upload_mode: str | None = None


def build_manifest(
    *,
    fragment_id: str,
    draft: ManifestDraft,
    std: StandardizeResult,
    upload: UploadInfo,
    transcription: TranscriptionInfo,
) -> dict[str, Any]:
    """组装符合 tech-spec §3.3 schema 的 ``manifest.json`` 字典。

    字段来源（§3.3「字段来源」）：
    - ``fragment_id`` / ``device_id``：从 ``fragment_id`` 解析；
    - ``session_id`` / ``chunk_seq`` / ``chunk_total`` / ``recorded_at`` /
      ``duration_seconds`` / ``audio.original_format`` / ``upload.original_sha256``：来自 OSS
      用户自定义元数据（``draft``）；
    - ``audio.sha256`` / ``audio.size_bytes`` / ``audio.format``：Worker 本地计算
      （标准化后的最终 ``audio.wav``，来自 ``std``）；
    - ``upload.original_size_bytes``：OSS Content-Length / 下载字节数（``std`` 提供）；
    - ``upload.*`` 时间戳 / ``transcription.*``：Worker 在对应流程填入。
    """
    original_format: str | None
    if std.original_format and not draft.original_format:
        original_format = std.original_format
    else:
        original_format = draft.original_format
    return {
        "fragment_id": fragment_id,
        "session_id": draft.session_id,
        "chunk_seq": draft.chunk_seq,
        "chunk_total": draft.chunk_total,
        "device_id": device_id_of(fragment_id),
        "recorded_at": draft.recorded_at,
        "duration_seconds": draft.duration_seconds,
        "audio": {
            "format": std.audio_format,
            "original_format": original_format,
            "size_bytes": std.audio_size_bytes,
            "sha256": std.audio_sha256,
        },
        "upload": {
            "uploaded_at": upload.uploaded_at,
            "verified_at": upload.verified_at,
            "verify_method": upload.verify_method,
            "original_sha256": draft.original_sha256,
            "original_size_bytes": std.original_size_bytes,
        },
        "transcription": {
            "started_at": transcription.started_at,
            "completed_at": transcription.completed_at,
            "elapsed_seconds": transcription.elapsed_seconds,
            "transcriber": transcription.transcriber,
            "model": transcription.model,
            "params_version": transcription.params_version,
            "provider": transcription.provider,
            "upload_mode": transcription.upload_mode,
        },
    }


def transcript_json_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """从转写结果（含内存态 ``duration``）派生落盘用 ``transcript.json``（§3.4）。

    只保留 ``segments`` / ``language`` / ``model`` / ``params_version`` / ``provider``，
    **剔除 ``duration``**（时长已在 manifest.duration_seconds，不重复存储）。
    """
    out: dict[str, Any] = {}
    for key in _TRANSCRIPT_FIELDS:
        if key == "segments":
            segs = result.get("segments", [])
            out["segments"] = segs if isinstance(segs, list) else []
        else:
            out[key] = result.get(key)
    return out


def manifest_without_timestamps(manifest: dict[str, Any]) -> dict[str, Any]:
    """返回剔除时间戳 / 计时字段的 manifest 深拷贝（idempotent 比对用）。

    剔除 :data:`TIMESTAMP_FIELD_PATHS` 列出的字段（上传 / verify / 转写时间戳、
    elapsed_seconds），其余字段（含 recorded_at —— 来自固定元数据）保留。
    """
    clone = copy.deepcopy(manifest)
    for section, field_name in TIMESTAMP_FIELD_PATHS:
        sub = clone.get(section)
        if isinstance(sub, dict):
            sub.pop(field_name, None)
    return clone


# ── 落盘：manifest.json → transcript.json → transcript.txt → .done（§3.5）──
@dataclass(frozen=True)
class FragmentOutputs:
    """一条 Fragment 的五个产物路径。"""

    audio: Path
    manifest: Path
    transcript_json: Path
    transcript_txt: Path
    done_marker: Path


def write_fragment_outputs(
    fragment_dir: Path,
    fragment_id: str,
    manifest: dict[str, Any],
    transcript_json: dict[str, Any],
    *,
    tmp_root: Path,
) -> FragmentOutputs:
    """按 §3.5 三段式协议落盘 manifest / transcript，并最后创建 ``.done``。

    顺序：① 原子写 ``manifest.json``；② 原子写 ``transcript.json``（经
    ``tmp/<id>.transcript.json.tmp``）；③ 原子写 ``transcript.txt``（由 segments 派生）；
    ④ 最后创建 0 字节 ``.done``。``audio.wav`` 由上游 :func:`audio.standardize` 落盘，
    本函数只校验其存在以保证完整 Fragment。任一步失败都不会创建 ``.done``。
    """
    audio_path = fragment_dir / AUDIO_FILENAME
    manifest_path = fragment_dir / MANIFEST_FILENAME
    atomic_write_json(manifest_path, manifest)
    tj = write_transcript_json(fragment_dir, fragment_id, transcript_json, tmp_root=tmp_root)
    segments = transcript_json.get("segments", [])
    txt = transcript_txt_from_segments(segments if isinstance(segments, list) else [])
    tt = fragment_dir / TRANSCRIPT_TXT_FILENAME
    atomic_write_text(tt, txt)
    done = create_done_marker(fragment_dir)  # 最后创建
    return FragmentOutputs(
        audio=audio_path,
        manifest=manifest_path,
        transcript_json=tj,
        transcript_txt=tt,
        done_marker=done,
    )


# ── make test-*：用真实 fixtures + ffmpeg/ffprobe 端到端验证 ────────────────
def _repo_root() -> Path:
    """仓库根目录（apps/worker/src/soniscope_worker/manifest.py → parents[4]）。"""
    return Path(__file__).resolve().parents[4]


def _fixture_path(name: str) -> Path:
    return _repo_root() / "tests" / "audio" / name


_INTEGRITY_FID = "20260527T140000_devm01_01HZX3K8MN5PQR9TFB7AYWVCDE"

# sample-20s.wav 的固定 OSS 元数据（构造确定性 ManifestDraft）。
_FIXED_META = {
    "session-id": "01HZX3K8MN5PQR9TFB7AYWVCDE",
    "chunk-seq": "1",
    "chunk-total": "0",
    "recorded-at": "2026-05-27T14:00:00+08:00",
    "duration": "24",
    "original-format": "wav",
}

_FIXED_TRANSCRIPTION = TranscriptionInfo(
    transcriber="cloud-speech",
    model="中文普通话（识音石 V1 - 端到端模型)",
    params_version="v1",
    provider="aliyun-nls",
    upload_mode="oss-url",
)


def _stub_transcript_result() -> dict[str, Any]:
    """make test 用的确定性占位转写结果（含内存态 duration，落盘前剔除）。真实 NLS 在 US-026。"""
    return {
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "今天天气不错"},
            {"start": 2.5, "end": 5.1, "text": "我准备去公园跑步"},
        ],
        "language": "zh",
        "model": "中文普通话（识音石 V1 - 端到端模型)",
        "params_version": "v1",
        "provider": "aliyun-nls",
        "duration": 24.0,
    }


def _run_one_fragment(
    base: Path,
    fragment_id: str,
    src: Path,
    *,
    sha_meta: str,
    upload: UploadInfo,
    transcription: TranscriptionInfo,
) -> tuple[StandardizeResult, dict[str, Any], FragmentOutputs]:
    """在 ``base`` 临时运行时目录里跑「标准化 → 组装 manifest → 落盘五产物」一条。"""
    inbox = base / "inbox"
    failed = inbox / "failed"
    fragments = base / "fragments"
    tmp = base / "tmp"
    for d in (inbox, failed, fragments, tmp):
        d.mkdir(parents=True, exist_ok=True)

    part = inbox / f"{fragment_id}.part"
    shutil.copy2(src, part)
    std = standardize(
        part,
        fragment_id=fragment_id,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        original_format="wav",
    )
    raw_meta = dict(_FIXED_META)
    raw_meta["sha256"] = sha_meta
    draft = metadata_to_draft(fragment_id, raw_meta)
    manifest = build_manifest(
        fragment_id=fragment_id,
        draft=draft,
        std=std,
        upload=upload,
        transcription=transcription,
    )
    date = object_key_for(fragment_id).split("/")[1]
    frag_dir = fragments / date / fragment_id
    outputs = write_fragment_outputs(
        frag_dir,
        fragment_id,
        manifest,
        transcript_json_from_result(_stub_transcript_result()),
        tmp_root=tmp,
    )
    return std, manifest, outputs


def run_test_fragment_integrity() -> tuple[list[str], int]:
    """make test-fragment-integrity：跑完一条 Fragment 后五产物齐全（AC#7）。"""
    lines: list[str] = []
    src = _fixture_path("sample-20s.wav")
    if not src.is_file():
        lines.append(f"SKIP — 缺少 fixture：{src}（先跑 python3 scripts/fetch_test_fixtures.py）")
        return lines, 0
    with tempfile.TemporaryDirectory(prefix="soniscope-fragment-integrity-") as tmpdir:
        base = Path(tmpdir)
        sha_meta = sha256_of(src)  # 直通路径：original_sha256 == audio.sha256
        upload = UploadInfo(
            uploaded_at="2026-05-27T14:00:30+08:00",
            verified_at="2026-05-27T14:00:32+08:00",
        )
        _, manifest, outputs = _run_one_fragment(
            base, _INTEGRITY_FID, src, sha_meta=sha_meta,
            upload=upload, transcription=_FIXED_TRANSCRIPTION,
        )
        frag_dir = outputs.done_marker.parent
        problems: list[str] = []
        expected = {
            AUDIO_FILENAME: outputs.audio,
            MANIFEST_FILENAME: outputs.manifest,
            TRANSCRIPT_JSON_FILENAME: outputs.transcript_json,
            TRANSCRIPT_TXT_FILENAME: outputs.transcript_txt,
            DONE_MARKER: outputs.done_marker,
        }
        for name, path in expected.items():
            if not path.is_file():
                problems.append(f"缺少产物 {name}（{path}）")
        if outputs.done_marker.is_file() and outputs.done_marker.stat().st_size != 0:
            problems.append(".done 不是 0 字节空文件")
        # transcript.json 不含 duration（§3.4）。
        if outputs.transcript_json.is_file():
            tj = json.loads(outputs.transcript_json.read_text(encoding="utf-8"))
            if "duration" in tj:
                problems.append("transcript.json 不应含 duration 字段（§3.4）")
            if set(tj) != set(_TRANSCRIPT_FIELDS):
                problems.append(f"transcript.json 字段应恰为 {_TRANSCRIPT_FIELDS}")
        # transcript.txt == segments[].text 顺序拼接。
        if outputs.transcript_txt.is_file():
            txt = outputs.transcript_txt.read_text(encoding="utf-8")
            if txt != "今天天气不错我准备去公园跑步":
                problems.append(f"transcript.txt 派生不正确：{txt!r}")
        # manifest 顶层字段齐全（AC#1）。
        for key in (
            "fragment_id", "session_id", "chunk_seq", "chunk_total",
            "device_id", "recorded_at", "duration_seconds",
            "audio", "upload", "transcription",
        ):
            if key not in manifest:
                problems.append(f"manifest 缺少字段 {key}")
        if manifest.get("device_id") != "devm01":
            problems.append(f"device_id 解析错误：{manifest.get('device_id')}")
        lines.append(f"fragment 目录：{frag_dir}")
        lines.append(f"audio.sha256 = {(manifest['audio']['sha256'] or '')[:16]}…")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append(
        "✅ Fragment 完整性校验通过（audio.wav / manifest.json / transcript.json / "
        "transcript.txt / .done 五产物齐全）"
    )
    return lines, 0


def run_test_manifest_idempotent() -> tuple[list[str], int]:
    """make test-manifest-idempotent：同一 WAV 跑两次，除时间戳外 manifest 完全一致（AC#8）。"""
    lines: list[str] = []
    src = _fixture_path("sample-20s.wav")
    if not src.is_file():
        lines.append(f"SKIP — 缺少 fixture：{src}（先跑 python3 scripts/fetch_test_fixtures.py）")
        return lines, 0
    sha_meta = sha256_of(src)
    manifests: list[dict[str, Any]] = []
    # 两次运行刻意用不同的时间戳 / 计时，证明 idempotent 比对剔除这些字段后其余完全一致。
    run_params = [
        (
            UploadInfo(
                uploaded_at="2026-05-27T14:00:30+08:00",
                verified_at="2026-05-27T14:00:32+08:00",
            ),
            TranscriptionInfo(
                started_at="2026-05-27T14:01:00+08:00",
                completed_at="2026-05-27T14:01:12+08:00",
                elapsed_seconds=12.3,
                transcriber="cloud-speech",
                model="中文普通话（识音石 V1 - 端到端模型)",
                params_version="v1",
                provider="aliyun-nls",
                upload_mode="oss-url",
            ),
        ),
        (
            UploadInfo(
                uploaded_at="2026-06-01T09:00:30+08:00",
                verified_at="2026-06-01T09:00:35+08:00",
            ),
            TranscriptionInfo(
                started_at="2026-06-01T09:01:00+08:00",
                completed_at="2026-06-01T09:01:20+08:00",
                elapsed_seconds=20.7,
                transcriber="cloud-speech",
                model="中文普通话（识音石 V1 - 端到端模型)",
                params_version="v1",
                provider="aliyun-nls",
                upload_mode="oss-url",
            ),
        ),
    ]
    for upload, transcription in run_params:
        with tempfile.TemporaryDirectory(prefix="soniscope-manifest-idempotent-") as tmpdir:
            _, manifest, _ = _run_one_fragment(
                Path(tmpdir), _INTEGRITY_FID, src, sha_meta=sha_meta,
                upload=upload, transcription=transcription,
            )
            manifests.append(manifest)

    a = manifest_without_timestamps(manifests[0])
    b = manifest_without_timestamps(manifests[1])
    problems: list[str] = []
    if a != b:
        problems.append("剔除时间戳后两次 manifest 不一致")
        for key in sorted(set(a) | set(b)):
            if a.get(key) != b.get(key):
                problems.append(f"  字段 {key} 不一致：{a.get(key)!r} vs {b.get(key)!r}")
    # 验证两次的时间戳字段确实不同（否则比对剔除无意义）。
    if manifests[0]["upload"]["uploaded_at"] == manifests[1]["upload"]["uploaded_at"]:
        problems.append("两次运行时间戳应不同以验证剔除逻辑")
    lines.append(f"run1 uploaded_at = {manifests[0]['upload']['uploaded_at']}")
    lines.append(f"run2 uploaded_at = {manifests[1]['upload']['uploaded_at']}")
    lines.append(f"audio.sha256（两次相同）= {(a['audio']['sha256'] or '')[:16]}…")
    if problems:
        lines.extend(f"FAIL — {p}" for p in problems)
        return lines, 1
    lines.append("✅ manifest 幂等校验通过（除时间戳字段外两次运行完全一致）")
    return lines, 0
