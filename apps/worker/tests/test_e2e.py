"""US-030：E2E 完整性 / sha256 / 关键字段校验脚本单测。

在 ``tmp_path`` 下构造**真实** Fragment 目录（非 mock），覆盖三个 verify 脚本的通过 / 失败
路径、失败汇总（fragment_id + 字段路径）与非零退出。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from soniscope_worker.e2e import (
    REQUIRED_FILES,
    check_fields,
    check_integrity,
    check_sha256,
    discover_fragments,
    run_verify_e2e_fields,
    run_verify_e2e_integrity,
    run_verify_e2e_sha256,
)

# 合法 fragment_id：<YYYYMMDDTHHMMSS>_<deviceShortId>_<26 ULID>，日期前缀 2026-05-27。
FID1 = "20260527T140000_devm01_01HZX3K8MN5PQR9TFB7AYWVCDE"
FID2 = "20260527T140100_devm01_01HZX3K8MN5PQR9TFB7AYWVCDF"
DATE = "2026-05-27"

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def _base_manifest(
    fragment_id: str,
    *,
    original_format: str = "wav",
    audio_sha: str | None = _SHA_A,
    audio_size: int | None = 1000,
    orig_sha: str | None = _SHA_A,
    orig_size: int | None = 1000,
    verified_at: str | None = "2026-05-27T14:00:32+08:00",
    completed_at: str | None = "2026-05-27T14:01:12+08:00",
) -> dict[str, Any]:
    return {
        "fragment_id": fragment_id,
        "session_id": "01HZX3K8MN5PQR9TFB7AYWVCDE",
        "chunk_seq": 1,
        "chunk_total": None,
        "device_id": "devm01",
        "recorded_at": "2026-05-27T14:00:00+08:00",
        "duration_seconds": 24.0,
        "audio": {
            "format": "wav",
            "original_format": original_format,
            "size_bytes": audio_size,
            "sha256": audio_sha,
        },
        "upload": {
            "uploaded_at": "2026-05-27T14:00:30+08:00",
            "verified_at": verified_at,
            "verify_method": "fc-head-object",
            "original_sha256": orig_sha,
            "original_size_bytes": orig_size,
        },
        "transcription": {
            "started_at": "2026-05-27T14:01:00+08:00",
            "completed_at": completed_at,
            "elapsed_seconds": 12.3,
            "transcriber": "cloud-speech",
            "model": "m",
            "params_version": "v1",
            "provider": "aliyun-nls",
            "upload_mode": "oss-url",
        },
    }


def _make_fragment(
    fragments_root: Path,
    fragment_id: str,
    *,
    date: str = DATE,
    files: tuple[str, ...] = REQUIRED_FILES,
    manifest: dict[str, Any] | None = None,
    manifest_text: str | None = None,
) -> Path:
    """构造一个真实 Fragment 目录，写入指定产物文件。"""
    frag_dir = fragments_root / date / fragment_id
    frag_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        path = frag_dir / name
        if name == "manifest.json":
            if manifest_text is not None:
                path.write_text(manifest_text, encoding="utf-8")
            else:
                data = manifest if manifest is not None else _base_manifest(fragment_id)
                path.write_text(json.dumps(data), encoding="utf-8")
        elif name == ".done":
            path.write_bytes(b"")
        else:
            path.write_text("x", encoding="utf-8")
    return frag_dir


# ── discover_fragments ─────────────────────────────────────────────────────
def test_discover_empty_root(tmp_path: Path) -> None:
    assert discover_fragments(tmp_path / "missing") == []


def test_discover_filters_invalid_dir_names(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1)
    (root / DATE / "not-a-fragment").mkdir(parents=True)
    found = discover_fragments(root)
    assert [f.fragment_id for f in found] == [FID1]


def test_discover_by_date(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1, date=DATE)
    _make_fragment(root, FID2, date="2026-05-28")
    assert {f.fragment_id for f in discover_fragments(root, date=DATE)} == {FID1}
    assert {f.fragment_id for f in discover_fragments(root)} == {FID1, FID2}


# ── integrity ──────────────────────────────────────────────────────────────
def test_check_integrity_complete(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1)
    frag = discover_fragments(root)[0]
    assert check_integrity(frag).ok


def test_check_integrity_missing_file(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1, files=("audio.wav", "manifest.json"))
    frag = discover_fragments(root)[0]
    result = check_integrity(frag)
    assert not result.ok
    assert any("transcript.json" in p for p in result.problems)
    assert any(".done" in p for p in result.problems)


def test_run_integrity_pass_with_expected(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1)
    _make_fragment(root, FID2)
    lines, code = run_verify_e2e_integrity(fragments_root=root, date=DATE, expected=2)
    assert code == 0
    assert any("✅" in line for line in lines)


def test_run_integrity_count_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1)
    lines, code = run_verify_e2e_integrity(fragments_root=root, date=DATE, expected=100)
    assert code == 1
    assert any("不等于期望 100" in line for line in lines)


def test_run_integrity_incomplete_fragment(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1, files=("audio.wav",))
    lines, code = run_verify_e2e_integrity(fragments_root=root, date=DATE, expected=1)
    assert code == 1
    assert any(FID1 in line and "FAIL" in line for line in lines)


def test_run_integrity_expected_disabled(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1)
    lines, code = run_verify_e2e_integrity(fragments_root=root, expected=0)
    assert code == 0


# ── sha256（§3.3）──────────────────────────────────────────────────────────
def test_check_sha256_wav_passthrough_ok() -> None:
    m = _base_manifest(FID1, original_format="wav", audio_sha=_SHA_A, orig_sha=_SHA_A)
    assert check_sha256(m, FID1).ok


def test_check_sha256_wav_mismatch_fails() -> None:
    m = _base_manifest(FID1, original_format="wav", audio_sha=_SHA_A, orig_sha=_SHA_B)
    result = check_sha256(m, FID1)
    assert not result.ok
    assert any("audio.sha256 != upload.original_sha256" in p for p in result.problems)


def test_check_sha256_wav_size_mismatch_fails() -> None:
    m = _base_manifest(
        FID1, original_format="wav", audio_size=1000, orig_size=2000
    )
    result = check_sha256(m, FID1)
    assert not result.ok
    assert any("size_bytes" in p for p in result.problems)


def test_check_sha256_transcode_differing_ok() -> None:
    m = _base_manifest(
        FID1, original_format="m4a", audio_sha=_SHA_A, orig_sha=_SHA_B,
        audio_size=1000, orig_size=2000,
    )
    assert check_sha256(m, FID1).ok


def test_check_sha256_null_rejected() -> None:
    m = _base_manifest(FID1, original_format="m4a", audio_sha=None, orig_sha=_SHA_B)
    result = check_sha256(m, FID1)
    assert not result.ok
    assert any("audio.sha256 为空" in p for p in result.problems)


def test_run_sha256_pass(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1, manifest=_base_manifest(FID1))
    lines, code = run_verify_e2e_sha256(fragments_root=root, date=DATE)
    assert code == 0
    assert any("✅" in line for line in lines)


def test_run_sha256_corrupt_manifest_fails(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1, manifest_text="{ not json")
    lines, code = run_verify_e2e_sha256(fragments_root=root, date=DATE)
    assert code == 1
    assert any("解析失败" in line for line in lines)


# ── fields（AC#3）──────────────────────────────────────────────────────────
def test_check_fields_ok() -> None:
    assert check_fields(_base_manifest(FID1), FID1).ok


def test_check_fields_missing_verified_at() -> None:
    result = check_fields(_base_manifest(FID1, verified_at=None), FID1)
    assert not result.ok
    assert any("upload.verified_at 为空" in p for p in result.problems)


def test_check_fields_blank_completed_at() -> None:
    result = check_fields(_base_manifest(FID1, completed_at="  "), FID1)
    assert not result.ok
    assert any("transcription.completed_at 为空" in p for p in result.problems)


def test_run_fields_pass(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1)
    lines, code = run_verify_e2e_fields(fragments_root=root, date=DATE)
    assert code == 0


def test_run_fields_missing_manifest_fails(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1, files=("audio.wav", ".done"))
    lines, code = run_verify_e2e_fields(fragments_root=root, date=DATE)
    assert code == 1
    assert any("缺少 manifest.json" in line for line in lines)


def test_run_fields_reports_failed_fragment_id(tmp_path: Path) -> None:
    root = tmp_path / "fragments"
    _make_fragment(root, FID1, manifest=_base_manifest(FID1, completed_at=None))
    lines, code = run_verify_e2e_fields(fragments_root=root, date=DATE)
    assert code == 1
    assert any(FID1 in line for line in lines)
