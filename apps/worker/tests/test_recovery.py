"""US-023 Worker 启动恢复扫描与原子写入工具 单元测试（全程不触系统工具/云端）。"""

from __future__ import annotations

import json
from pathlib import Path

from soniscope_worker.oss_admin import object_key_for
from soniscope_worker.recovery import (
    CASE_MISSING_DONE,
    CASE_STALE_PART,
    DONE_MARKER,
    PART_SUFFIX,
    TRANSCRIPT_TMP_SUFFIX,
    WAV_TMP_SUFFIX,
    atomic_write_json,
    atomic_write_text,
    classify_fragment_dir,
    create_done_marker,
    finalize_fragment,
    recover,
    recover_inbox,
    recover_tmp,
    run_simulate_worker_crash,
    run_test_crash_recovery,
    scan_fragments,
    transcript_tmp_path,
    transcript_txt_from_segments,
    write_transcript_json,
)

_FID = "20260527T130000_devc01_01HZX3K8MN5PQR9TFB7AYWVCDE"
_FID2 = "20260527T130100_devc01_01HZX3K8MN5PQR9TFB7AYWVCDF"
_DATE = object_key_for(_FID).split("/")[1]


def _mk_runtime(base: Path) -> tuple[Path, Path, Path]:
    inbox = base / "inbox"
    tmp = base / "tmp"
    fragments = base / "fragments"
    for d in (inbox, tmp, fragments):
        d.mkdir(parents=True, exist_ok=True)
    return inbox, tmp, fragments


# ── 原子写入工具 ───────────────────────────────────────────────────────────
def test_atomic_write_text_creates_file_no_tmp_residue(tmp_path: Path) -> None:
    dest = tmp_path / "sub" / "out.txt"
    atomic_write_text(dest, "你好world")
    assert dest.read_text(encoding="utf-8") == "你好world"
    # 不留临时文件
    assert [p.name for p in dest.parent.iterdir()] == ["out.txt"]


def test_atomic_write_json_roundtrip(tmp_path: Path) -> None:
    dest = tmp_path / "manifest.json"
    atomic_write_json(dest, {"fragment_id": _FID, "中文": 1})
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded == {"fragment_id": _FID, "中文": 1}


def test_write_transcript_json_uses_tmp_then_renames(tmp_path: Path) -> None:
    inbox, tmp, fragments = _mk_runtime(tmp_path)
    frag_dir = fragments / _DATE / _FID
    dest = write_transcript_json(frag_dir, _FID, {"segments": []}, tmp_root=tmp)
    assert dest == frag_dir / "transcript.json"
    assert dest.is_file()
    # 落盘后临时文件已被 rename 掉
    assert not transcript_tmp_path(tmp, _FID).exists()


def test_transcript_txt_from_segments_orders_and_concats() -> None:
    segs = [{"text": "甲"}, {"text": "乙"}, {"no_text": 1}, {"text": "丙"}]
    assert transcript_txt_from_segments(segs) == "甲乙丙"


def test_create_done_marker_is_zero_byte(tmp_path: Path) -> None:
    done = create_done_marker(tmp_path)
    assert done.name == DONE_MARKER
    assert done.is_file()
    assert done.stat().st_size == 0


def test_finalize_fragment_writes_all_and_done_last(tmp_path: Path) -> None:
    inbox, tmp, fragments = _mk_runtime(tmp_path)
    frag_dir = fragments / _DATE / _FID
    frag_dir.mkdir(parents=True, exist_ok=True)
    transcript = {"segments": [{"text": "abc"}, {"text": "def"}], "language": "zh"}
    result = finalize_fragment(frag_dir, _FID, transcript, tmp_root=tmp)
    assert result.transcript_json.is_file()
    assert result.transcript_txt.read_text(encoding="utf-8") == "abcdef"
    assert result.done_marker.is_file()
    assert result.done_marker.stat().st_size == 0
    assert not transcript_tmp_path(tmp, _FID).exists()


# ── 恢复扫描：inbox / tmp ──────────────────────────────────────────────────
def test_recover_inbox_removes_part_and_wav_tmp(tmp_path: Path) -> None:
    inbox, _, _ = _mk_runtime(tmp_path)
    (inbox / f"{_FID}{PART_SUFFIX}").write_bytes(b"x")
    (inbox / f"{_FID}{WAV_TMP_SUFFIX}").write_bytes(b"y")
    (inbox / "keep.txt").write_bytes(b"z")
    parts, wav_tmps = recover_inbox(inbox)
    assert parts == [f"{_FID}{PART_SUFFIX}"]
    assert wav_tmps == [f"{_FID}{WAV_TMP_SUFFIX}"]
    assert (inbox / "keep.txt").exists()
    assert not (inbox / f"{_FID}{PART_SUFFIX}").exists()
    assert not (inbox / f"{_FID}{WAV_TMP_SUFFIX}").exists()


def test_recover_inbox_missing_dir_safe(tmp_path: Path) -> None:
    parts, wav_tmps = recover_inbox(tmp_path / "nope")
    assert parts == []
    assert wav_tmps == []


def test_recover_tmp_removes_transcript_tmp(tmp_path: Path) -> None:
    _, tmp, _ = _mk_runtime(tmp_path)
    transcript_tmp_path(tmp, _FID).write_text("partial", encoding="utf-8")
    (tmp / "other.tmp").write_text("keep", encoding="utf-8")
    removed = recover_tmp(tmp)
    assert removed == [f"{_FID}{TRANSCRIPT_TMP_SUFFIX}"]
    assert (tmp / "other.tmp").exists()


# ── 恢复扫描：fragments 分类 ───────────────────────────────────────────────
def test_classify_fragment_dir_done(tmp_path: Path) -> None:
    frag = tmp_path / _DATE / _FID
    frag.mkdir(parents=True)
    (frag / "audio.wav").write_bytes(b"a")
    (frag / DONE_MARKER).write_bytes(b"")
    state = classify_fragment_dir(_DATE, frag)
    assert state is not None and state.status == "done"


def test_classify_fragment_dir_pending(tmp_path: Path) -> None:
    frag = tmp_path / _DATE / _FID
    frag.mkdir(parents=True)
    (frag / "audio.wav").write_bytes(b"a")
    state = classify_fragment_dir(_DATE, frag)
    assert state is not None and state.status == "pending"


def test_classify_fragment_dir_empty(tmp_path: Path) -> None:
    frag = tmp_path / _DATE / _FID
    frag.mkdir(parents=True)
    state = classify_fragment_dir(_DATE, frag)
    assert state is not None and state.status == "empty"


def test_classify_fragment_dir_illegal_id(tmp_path: Path) -> None:
    frag = tmp_path / _DATE / "not-a-valid-id"
    frag.mkdir(parents=True)
    assert classify_fragment_dir(_DATE, frag) is None


def test_classify_fragment_dir_date_mismatch(tmp_path: Path) -> None:
    wrong_date = "2099-01-01"
    frag = tmp_path / wrong_date / _FID
    frag.mkdir(parents=True)
    # fragment_id 前缀日期 != 目录日期 → 忽略
    assert classify_fragment_dir(wrong_date, frag) is None


def test_scan_fragments_classifies_all(tmp_path: Path) -> None:
    _, _, fragments = _mk_runtime(tmp_path)
    d1 = fragments / _DATE / _FID
    d1.mkdir(parents=True)
    (d1 / "audio.wav").write_bytes(b"a")
    (d1 / DONE_MARKER).write_bytes(b"")
    d2 = fragments / _DATE / _FID2
    d2.mkdir(parents=True)
    (d2 / "audio.wav").write_bytes(b"a")  # pending
    states = scan_fragments(fragments)
    by_id = {s.fragment_id: s.status for s in states}
    assert by_id == {_FID: "done", _FID2: "pending"}


def test_scan_fragments_missing_root(tmp_path: Path) -> None:
    assert scan_fragments(tmp_path / "nope") == []


# ── recover 编排 ───────────────────────────────────────────────────────────
def test_recover_cleans_and_classifies(tmp_path: Path) -> None:
    inbox, tmp, fragments = _mk_runtime(tmp_path)
    (inbox / f"{_FID}{PART_SUFFIX}").write_bytes(b"x")
    (inbox / f"{_FID}{WAV_TMP_SUFFIX}").write_bytes(b"y")
    transcript_tmp_path(tmp, _FID).write_text("p", encoding="utf-8")
    frag = fragments / _DATE / _FID
    frag.mkdir(parents=True)
    (frag / "audio.wav").write_bytes(b"a")  # pending
    report = recover(inbox_root=inbox, tmp_root=tmp, fragments_root=fragments)
    assert report.removed_parts == [f"{_FID}{PART_SUFFIX}"]
    assert report.removed_wav_tmps == [f"{_FID}{WAV_TMP_SUFFIX}"]
    assert report.removed_transcript_tmps == [f"{_FID}{TRANSCRIPT_TMP_SUFFIX}"]
    assert [s.fragment_id for s in report.pending] == [_FID]
    assert report.done == []
    assert "转写未完 1" in report.summary()


def test_recover_remove_empty_dirs(tmp_path: Path) -> None:
    inbox, tmp, fragments = _mk_runtime(tmp_path)
    empty = fragments / _DATE / _FID
    empty.mkdir(parents=True)  # 无 audio.wav → empty
    report = recover(
        inbox_root=inbox, tmp_root=tmp, fragments_root=fragments, remove_empty_dirs=True
    )
    assert [s.fragment_id for s in report.empty] == [_FID]
    assert not empty.exists()


def test_recover_empty_dir_ignored_by_default(tmp_path: Path) -> None:
    inbox, tmp, fragments = _mk_runtime(tmp_path)
    empty = fragments / _DATE / _FID
    empty.mkdir(parents=True)
    report = recover(inbox_root=inbox, tmp_root=tmp, fragments_root=fragments)
    assert [s.fragment_id for s in report.empty] == [_FID]
    assert empty.exists()  # 默认只忽略不删


# ── make test-crash-recovery ───────────────────────────────────────────────
def test_run_test_crash_recovery_passes() -> None:
    lines, code = run_test_crash_recovery()
    assert code == 0, "\n".join(lines)
    assert any("崩溃恢复校验通过" in line for line in lines)


# ── make simulate-worker-crash ─────────────────────────────────────────────
def test_simulate_unknown_case() -> None:
    lines, code = run_simulate_worker_crash("bogus", _FID)
    assert code == 1
    assert any("未知 CASE" in line for line in lines)


def test_simulate_missing_fragment_id() -> None:
    lines, code = run_simulate_worker_crash(CASE_MISSING_DONE, "")
    assert code == 1
    assert any("FRAGMENT_ID" in line for line in lines)


def test_simulate_illegal_fragment_id() -> None:
    lines, code = run_simulate_worker_crash(CASE_STALE_PART, "bad-id")
    assert code == 1
    assert any("非法 fragment_id" in line for line in lines)


def test_simulate_missing_done_deletes_marker(tmp_path: Path) -> None:
    inbox, _, fragments = _mk_runtime(tmp_path)
    frag = fragments / _DATE / _FID
    frag.mkdir(parents=True)
    (frag / "audio.wav").write_bytes(b"a")
    (frag / DONE_MARKER).write_bytes(b"")
    lines, code = run_simulate_worker_crash(
        CASE_MISSING_DONE, _FID, inbox_root=inbox, fragments_root=fragments
    )
    assert code == 0
    assert not (frag / DONE_MARKER).exists()
    assert any("已删除 .done" in line for line in lines)
    assert any("重新转写补回 .done" in line for line in lines)


def test_simulate_missing_done_no_fragment_dir(tmp_path: Path) -> None:
    inbox, _, fragments = _mk_runtime(tmp_path)
    lines, code = run_simulate_worker_crash(
        CASE_MISSING_DONE, _FID, inbox_root=inbox, fragments_root=fragments
    )
    assert code == 1
    assert any("找不到 fragment 目录" in line for line in lines)


def test_simulate_stale_part_creates_residual(tmp_path: Path) -> None:
    inbox, _, fragments = _mk_runtime(tmp_path)
    lines, code = run_simulate_worker_crash(
        CASE_STALE_PART, _FID, inbox_root=inbox, fragments_root=fragments
    )
    assert code == 0
    part = inbox / f"{_FID}{PART_SUFFIX}"
    assert part.is_file()
    assert any("已生成残留 .part" in line for line in lines)
    # 残留可被恢复扫描清理
    parts, _ = recover_inbox(inbox)
    assert parts == [f"{_FID}{PART_SUFFIX}"]
