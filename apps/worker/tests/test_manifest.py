"""US-024：manifest.json schema 组装、transcript 落盘与 Fragment 完整性检查单测。

不触 ffmpeg/ffprobe/云端：build_manifest / transcript_json_from_result /
manifest_without_timestamps / write_fragment_outputs 均为纯逻辑或本地文件操作，
用内存构造的 StandardizeResult / ManifestDraft 驱动。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soniscope_worker.audio import STATUS_PASSTHROUGH, STATUS_TRANSCODED, StandardizeResult
from soniscope_worker.manifest import (
    TIMESTAMP_FIELD_PATHS,
    ManifestError,
    TranscriptionInfo,
    UploadInfo,
    build_manifest,
    device_id_of,
    manifest_without_timestamps,
    run_test_fragment_integrity,
    run_test_manifest_idempotent,
    transcript_json_from_result,
    write_fragment_outputs,
)
from soniscope_worker.poller import ManifestDraft

FID = "20260527T140000_devm01_01HZX3K8MN5PQR9TFB7AYWVCDE"
DATE = "2026-05-27"


def _draft(**overrides: object) -> ManifestDraft:
    base: dict[str, object] = {
        "fragment_id": FID,
        "session_id": "01HZX3K8MN5PQR9TFB7AYWVCDE",
        "chunk_seq": 1,
        "chunk_total": None,
        "recorded_at": "2026-05-27T14:00:00+08:00",
        "duration_seconds": 24.0,
        "original_format": "wav",
        "original_sha256": "abc123",
    }
    base.update(overrides)
    return ManifestDraft(**base)  # type: ignore[arg-type]


def _passthrough_std(**overrides: object) -> StandardizeResult:
    base: dict[str, object] = {
        "fragment_id": FID,
        "status": STATUS_PASSTHROUGH,
        "audio_path": Path("/x/audio.wav"),
        "audio_format": "wav",
        "original_format": "wav",
        "audio_sha256": "abc123",
        "audio_size_bytes": 1000,
        "original_sha256": "abc123",
        "original_size_bytes": 1000,
    }
    base.update(overrides)
    return StandardizeResult(**base)  # type: ignore[arg-type]


# ── device_id_of ──────────────────────────────────────────────────────────
def test_device_id_of_parses_middle_segment() -> None:
    assert device_id_of(FID) == "devm01"


def test_device_id_of_invalid_raises() -> None:
    with pytest.raises(ManifestError):
        device_id_of("not-a-fragment-id")


def test_device_id_of_invalid_date_raises() -> None:
    with pytest.raises(ManifestError):
        device_id_of("20261340T140000_devm01_01HZX3K8MN5PQR9TFB7AYWVCDE")


# ── build_manifest 字段来源 ───────────────────────────────────────────────
def test_build_manifest_top_level_fields() -> None:
    m = build_manifest(
        fragment_id=FID,
        draft=_draft(),
        std=_passthrough_std(),
        upload=UploadInfo(uploaded_at="t1", verified_at="t2"),
        transcription=TranscriptionInfo(model="M", params_version="v1", provider="aliyun-nls"),
    )
    for key in (
        "fragment_id", "session_id", "chunk_seq", "chunk_total",
        "device_id", "recorded_at", "duration_seconds",
        "audio", "upload", "transcription",
    ):
        assert key in m
    assert m["fragment_id"] == FID
    assert m["device_id"] == "devm01"
    assert m["session_id"] == "01HZX3K8MN5PQR9TFB7AYWVCDE"
    assert m["chunk_seq"] == 1
    assert m["chunk_total"] is None
    assert m["recorded_at"] == "2026-05-27T14:00:00+08:00"
    assert m["duration_seconds"] == 24.0


def test_build_manifest_audio_from_standardize() -> None:
    m = build_manifest(
        fragment_id=FID,
        draft=_draft(original_format="mp3"),
        std=_passthrough_std(audio_sha256="aud", audio_size_bytes=42),
        upload=UploadInfo(),
        transcription=TranscriptionInfo(),
    )
    assert m["audio"]["format"] == "wav"
    assert m["audio"]["original_format"] == "mp3"  # draft 优先（来自 OSS 元数据）
    assert m["audio"]["size_bytes"] == 42
    assert m["audio"]["sha256"] == "aud"


def test_build_manifest_original_format_falls_back_to_probe() -> None:
    # 元数据未提供 original_format 时用 StandardizeResult 探测结果兜底。
    m = build_manifest(
        fragment_id=FID,
        draft=_draft(original_format=None),
        std=_passthrough_std(original_format="m4a"),
        upload=UploadInfo(),
        transcription=TranscriptionInfo(),
    )
    assert m["audio"]["original_format"] == "m4a"


def test_build_manifest_upload_block() -> None:
    m = build_manifest(
        fragment_id=FID,
        draft=_draft(original_sha256="orig-sha"),
        std=_passthrough_std(original_size_bytes=2048),
        upload=UploadInfo(uploaded_at="u", verified_at="v"),
        transcription=TranscriptionInfo(),
    )
    up = m["upload"]
    assert up["uploaded_at"] == "u"
    assert up["verified_at"] == "v"
    assert up["verify_method"] == "fc-head-object"
    assert up["original_sha256"] == "orig-sha"  # 来自 x-oss-meta-sha256
    assert up["original_size_bytes"] == 2048  # OSS Content-Length / 下载字节数


def test_build_manifest_transcription_block() -> None:
    tr = TranscriptionInfo(
        started_at="s", completed_at="c", elapsed_seconds=12.3,
        transcriber="cloud-speech", model="M", params_version="v1",
        provider="aliyun-nls", upload_mode="oss-url",
    )
    m = build_manifest(
        fragment_id=FID, draft=_draft(), std=_passthrough_std(),
        upload=UploadInfo(), transcription=tr,
    )
    t = m["transcription"]
    assert t["started_at"] == "s"
    assert t["completed_at"] == "c"
    assert t["elapsed_seconds"] == 12.3
    assert t["transcriber"] == "cloud-speech"
    assert t["model"] == "M"
    assert t["params_version"] == "v1"
    assert t["provider"] == "aliyun-nls"
    assert t["upload_mode"] == "oss-url"


def test_build_manifest_sha_consistency_passthrough() -> None:
    # 直通：audio.sha256 == upload.original_sha256（§3.3）。
    m = build_manifest(
        fragment_id=FID,
        draft=_draft(original_sha256="same"),
        std=_passthrough_std(audio_sha256="same", audio_size_bytes=100, original_size_bytes=100),
        upload=UploadInfo(), transcription=TranscriptionInfo(),
    )
    assert m["audio"]["sha256"] == m["upload"]["original_sha256"] == "same"
    assert m["audio"]["size_bytes"] == m["upload"]["original_size_bytes"] == 100


def test_build_manifest_sha_consistency_transcoded() -> None:
    # 转码：两个 sha 真实计算、不同且非 null（§3.3）。
    m = build_manifest(
        fragment_id=FID,
        draft=_draft(original_sha256="orig", original_format="m4a"),
        std=StandardizeResult(
            fragment_id=FID, status=STATUS_TRANSCODED, audio_format="wav",
            original_format="m4a", audio_sha256="wav-sha", audio_size_bytes=500,
            original_sha256="orig", original_size_bytes=300,
        ),
        upload=UploadInfo(), transcription=TranscriptionInfo(),
    )
    assert m["audio"]["sha256"] == "wav-sha"
    assert m["upload"]["original_sha256"] == "orig"
    assert m["audio"]["sha256"] != m["upload"]["original_sha256"]
    assert m["audio"]["sha256"] and m["upload"]["original_sha256"]


# ── transcript_json_from_result ───────────────────────────────────────────
def test_transcript_json_excludes_duration() -> None:
    result = {
        "segments": [{"start": 0.0, "end": 1.0, "text": "你好"}],
        "language": "zh", "model": "M", "params_version": "v1",
        "provider": "aliyun-nls", "duration": 24.0,
    }
    tj = transcript_json_from_result(result)
    assert "duration" not in tj
    assert set(tj) == {"segments", "language", "model", "params_version", "provider"}
    assert tj["segments"] == [{"start": 0.0, "end": 1.0, "text": "你好"}]
    assert tj["language"] == "zh"


def test_transcript_json_handles_missing_segments() -> None:
    tj = transcript_json_from_result({"language": "zh"})
    assert tj["segments"] == []
    assert tj["model"] is None


# ── manifest_without_timestamps ───────────────────────────────────────────
def test_manifest_without_timestamps_strips_only_timestamps() -> None:
    m = build_manifest(
        fragment_id=FID, draft=_draft(),
        std=_passthrough_std(),
        upload=UploadInfo(uploaded_at="u", verified_at="v"),
        transcription=TranscriptionInfo(
            started_at="s", completed_at="c", elapsed_seconds=1.0, model="M",
        ),
    )
    stripped = manifest_without_timestamps(m)
    for section, field_name in TIMESTAMP_FIELD_PATHS:
        assert field_name not in stripped[section]
    # 非时间戳字段保留。
    assert stripped["recorded_at"] == m["recorded_at"]
    assert stripped["upload"]["original_sha256"] == m["upload"]["original_sha256"]
    assert stripped["transcription"]["model"] == "M"
    # 原 manifest 未被修改（深拷贝）。
    assert "uploaded_at" in m["upload"]


def test_manifest_without_timestamps_equal_across_timestamp_diffs() -> None:
    m1 = build_manifest(
        fragment_id=FID, draft=_draft(), std=_passthrough_std(),
        upload=UploadInfo(uploaded_at="t1"),
        transcription=TranscriptionInfo(started_at="a", elapsed_seconds=1.0, model="M"),
    )
    m2 = build_manifest(
        fragment_id=FID, draft=_draft(), std=_passthrough_std(),
        upload=UploadInfo(uploaded_at="t2"),
        transcription=TranscriptionInfo(started_at="b", elapsed_seconds=9.9, model="M"),
    )
    assert m1 != m2
    assert manifest_without_timestamps(m1) == manifest_without_timestamps(m2)


# ── write_fragment_outputs ────────────────────────────────────────────────
def test_write_fragment_outputs_five_products(tmp_path: Path) -> None:
    frag_dir = tmp_path / "fragments" / DATE / FID
    frag_dir.mkdir(parents=True)
    (frag_dir / "audio.wav").write_bytes(b"RIFFfake")  # 上游 standardize 落盘
    tmp_root = tmp_path / "tmp"
    manifest = build_manifest(
        fragment_id=FID, draft=_draft(), std=_passthrough_std(),
        upload=UploadInfo(), transcription=TranscriptionInfo(),
    )
    tj = {
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "甲"},
            {"start": 1.0, "end": 2.0, "text": "乙"},
        ],
        "language": "zh", "model": "M", "params_version": "v1", "provider": "p",
    }
    out = write_fragment_outputs(frag_dir, FID, manifest, tj, tmp_root=tmp_root)
    for p in (out.audio, out.manifest, out.transcript_json, out.transcript_txt, out.done_marker):
        assert p.is_file()
    # .done 0 字节。
    assert out.done_marker.stat().st_size == 0
    # transcript.txt 顺序拼接。
    assert out.transcript_txt.read_text(encoding="utf-8") == "甲乙"
    # manifest 可解析且字段一致。
    loaded = json.loads(out.manifest.read_text(encoding="utf-8"))
    assert loaded["fragment_id"] == FID
    # transcript.json 临时文件已清理。
    assert not (tmp_root / f"{FID}.transcript.json.tmp").exists()


# ── make test 入口（缺 fixture → SKIP exit 0；有 fixture → 真跑）────────────
def test_run_fragment_integrity_skip_without_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "soniscope_worker.manifest._fixture_path",
        lambda name: Path("/nonexistent") / name,
    )
    lines, code = run_test_fragment_integrity()
    assert code == 0
    assert any("SKIP" in line for line in lines)


def test_run_manifest_idempotent_skip_without_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "soniscope_worker.manifest._fixture_path",
        lambda name: Path("/nonexistent") / name,
    )
    lines, code = run_test_manifest_idempotent()
    assert code == 0
    assert any("SKIP" in line for line in lines)
