"""ops 单测（US-029）：list-oss-objects / verify-no-stale / verify-oss-retention。

全程注入 Fake source + 临时目录，不触网；覆盖纯逻辑、退出码、红线 R-07 源码扫描、
日志扫描、OSS≥本地 数量校验与 secret 不泄漏。
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from soniscope_worker.ops import (
    OpsError,
    RetentionReport,
    count_local_fragments,
    count_oss_wav,
    date_listing_prefix,
    find_stale,
    format_list_objects,
    format_retention_report,
    format_stale_report,
    run_list_oss_objects,
    run_verify_no_stale,
    run_verify_oss_retention,
    scan_business_source_for_delete,
    scan_logs_for_delete,
    validate_date,
    wav_objects_for_date,
)
from soniscope_worker.poller import OssListing

VALID_FID = "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE"
VALID_FID2 = "20260526T144900_dev01_01HZX3K8MN5PQR9TFB7AYWVCDF"
DATE = "2026-05-26"
KEY1 = f"recordings/{DATE}/{VALID_FID}.wav"
KEY2 = f"recordings/{DATE}/{VALID_FID2}.wav"


class FakeSource:
    """记录调用的内存 OSS 只读数据源（list/head/download，无 delete）。"""

    def __init__(self, listings: list[OssListing] | None = None, fail: bool = False) -> None:
        self._listings = listings or []
        self._fail = fail
        self.list_calls = 0

    def list_recordings(self) -> list[OssListing]:
        self.list_calls += 1
        if self._fail:
            raise RuntimeError("boom-list")
        return list(self._listings)

    def head_metadata(self, object_key: str) -> Mapping[str, str]:  # pragma: no cover
        return {}

    def download(self, object_key: str, dest: Path) -> None:  # pragma: no cover
        raise NotImplementedError


# ── validate_date / list-oss-objects 纯逻辑 ─────────────────────────────────
def test_validate_date_ok() -> None:
    assert validate_date(DATE) == DATE


@pytest.mark.parametrize("bad", ["2026-5-26", "20260526", "2026/05/26", "garbage"])
def test_validate_date_bad_format(bad: str) -> None:
    with pytest.raises(OpsError, match="格式"):
        validate_date(bad)


def test_validate_date_invalid_day() -> None:
    with pytest.raises(OpsError, match="非法日期"):
        validate_date("2026-13-40")


def test_date_listing_prefix() -> None:
    assert date_listing_prefix(DATE) == f"recordings/{DATE}/"


def test_wav_objects_for_date_filters_and_sorts() -> None:
    listings = [
        OssListing(key=KEY2, size=200),
        OssListing(key=KEY1, size=100),
        OssListing(key=f"recordings/2026-05-27/{VALID_FID}.wav", size=300),  # 别的日期
        OssListing(key=f"recordings/{DATE}/notes.txt", size=10),  # 非 wav
    ]
    out = wav_objects_for_date(listings, DATE)
    assert [o.key for o in out] == [KEY1, KEY2]  # 按 key 排序、只剩当天 wav


def test_format_list_objects_with_count() -> None:
    lines = format_list_objects(DATE, [OssListing(key=KEY1, size=100)])
    joined = "\n".join(lines)
    assert KEY1 in joined
    assert "100 bytes" in joined
    assert "总数：1" in joined


def test_format_list_objects_empty() -> None:
    lines = format_list_objects(DATE, [])
    assert any("（无）" in ln for ln in lines)
    assert any("总数：0" in ln for ln in lines)


# ── run_list_oss_objects 入口 ───────────────────────────────────────────────
def test_run_list_oss_objects_ok() -> None:
    source = FakeSource([OssListing(key=KEY1, size=100), OssListing(key=KEY2, size=200)])
    lines, code = run_list_oss_objects(DATE, source=source)
    assert code == 0
    assert source.list_calls == 1
    assert any("总数：2" in ln for ln in lines)


def test_run_list_oss_objects_bad_date_no_io() -> None:
    source = FakeSource([OssListing(key=KEY1, size=100)])
    lines, code = run_list_oss_objects("bad", source=source)
    assert code == 1
    assert source.list_calls == 0
    assert any("FAIL" in ln for ln in lines)


def test_run_list_oss_objects_source_error_contained() -> None:
    source = FakeSource(fail=True)
    lines, code = run_list_oss_objects(DATE, source=source)
    assert code == 1
    assert any("FAIL" in ln for ln in lines)
    assert all("boom-list" not in ln for ln in lines)  # 只含类名，不泄漏明文


# ── verify-no-stale ─────────────────────────────────────────────────────────
def test_find_stale_clean(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    tmp = tmp_path / "tmp"
    inbox.mkdir()
    tmp.mkdir()
    report = find_stale(inbox, tmp)
    assert report.clean is True


def test_find_stale_detects_all_kinds(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    failed = inbox / "failed"
    tmp = tmp_path / "tmp"
    failed.mkdir(parents=True)
    tmp.mkdir()
    (inbox / f"{VALID_FID}.part").write_bytes(b"x")
    (inbox / f"{VALID_FID}.wav.tmp").write_bytes(b"x")
    (failed / f"{VALID_FID}.part").write_bytes(b"x")  # 留档：不计入
    (tmp / f"{VALID_FID}.transcript.json.tmp").write_bytes(b"x")
    report = find_stale(inbox, tmp)
    assert report.inbox_parts == [f"{VALID_FID}.part"]  # 顶层，不含 failed/
    assert report.inbox_wav_tmp == [f"{VALID_FID}.wav.tmp"]
    assert report.tmp_transcript_tmp == [f"{VALID_FID}.transcript.json.tmp"]
    assert report.clean is False


def test_find_stale_missing_dirs(tmp_path: Path) -> None:
    report = find_stale(tmp_path / "nope-inbox", tmp_path / "nope-tmp")
    assert report.clean is True


def test_format_stale_report_clean() -> None:
    lines, code = format_stale_report(find_stale(Path("/nonexistent-x"), Path("/nonexistent-y")))
    assert code == 0
    assert any("无残留" in ln for ln in lines)


def test_run_verify_no_stale_reports_residue(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    tmp = tmp_path / "tmp"
    inbox.mkdir()
    tmp.mkdir()
    (inbox / f"{VALID_FID}.part").write_bytes(b"x")
    lines, code = run_verify_no_stale(inbox_root=inbox, tmp_root=tmp)
    assert code == 1
    assert any(f"inbox/{VALID_FID}.part" in ln for ln in lines)


def test_run_verify_no_stale_clean(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    tmp = tmp_path / "tmp"
    inbox.mkdir()
    tmp.mkdir()
    lines, code = run_verify_no_stale(inbox_root=inbox, tmp_root=tmp)
    assert code == 0


# ── verify-oss-retention：counts ────────────────────────────────────────────
def test_count_oss_wav_skips_invalid_keys() -> None:
    listings = [
        OssListing(key=KEY1),
        OssListing(key=KEY2),
        OssListing(key="recordings/2026-05-26/not-a-fragment.wav"),  # 非法 fid
        OssListing(key="recordings/2026-05-26/notes.txt"),  # 非 wav
    ]
    assert count_oss_wav(listings) == 2


def test_count_local_fragments(tmp_path: Path) -> None:
    frags = tmp_path / "fragments"
    d = frags / DATE
    (d / VALID_FID).mkdir(parents=True)
    (d / VALID_FID / ".done").write_bytes(b"")
    (d / VALID_FID2).mkdir(parents=True)
    (d / VALID_FID2 / "audio.wav").write_bytes(b"x")
    (d / "empty-dir").mkdir()  # 无任何产物：不计入
    assert count_local_fragments(frags) == 2


def test_count_local_fragments_missing(tmp_path: Path) -> None:
    assert count_local_fragments(tmp_path / "nope") == 0


# ── verify-oss-retention：源码 / 日志删除扫描 ───────────────────────────────
def test_scan_business_source_no_delete_in_real_package() -> None:
    """真实 Worker 包业务源码（排除仅测试用模块）必须无 DeleteObject 调用（红线 R-07）。"""
    src_root = Path(__file__).resolve().parents[1] / "src" / "soniscope_worker"
    assert scan_business_source_for_delete(src_root) == []


def test_scan_business_source_detects_violation(tmp_path: Path) -> None:
    (tmp_path / "biz.py").write_text("client.delete_object(req)\n", encoding="utf-8")
    (tmp_path / "oss_admin.py").write_text("client.delete_object(req)\n", encoding="utf-8")  # 豁免
    hits = scan_business_source_for_delete(tmp_path)
    assert hits == ["biz.py:1"]


def test_scan_logs_for_delete(tmp_path: Path) -> None:
    log = tmp_path / "worker.log"
    log.write_text("ok line\nDeleteObject called here\nanother\n", encoding="utf-8")
    hits, scanned = scan_logs_for_delete([log, tmp_path / "missing.log"])
    assert hits == [f"{log}:2"]
    assert scanned == [str(log)]


def test_scan_logs_clean(tmp_path: Path) -> None:
    log = tmp_path / "worker.log"
    log.write_text("poll ok\ndownloaded fragment\n", encoding="utf-8")
    hits, scanned = scan_logs_for_delete([log])
    assert hits == []
    assert scanned == [str(log)]


# ── verify-oss-retention：报告渲染 ──────────────────────────────────────────
def test_format_retention_report_pass() -> None:
    report = RetentionReport(local_count=2, oss_count=3, log_files_scanned=["w.log"])
    lines, code = format_retention_report(report)
    assert code == 0
    joined = "\n".join(lines)
    assert "OSS 留存校验通过" in joined
    assert "≥" in joined


def test_format_retention_report_count_violation() -> None:
    report = RetentionReport(local_count=5, oss_count=3)
    lines, code = format_retention_report(report)
    assert code == 1
    assert any("少于本地" in ln for ln in lines)


def test_format_retention_report_source_violation() -> None:
    report = RetentionReport(local_count=1, oss_count=1, source_delete_hits=["biz.py:9"])
    lines, code = format_retention_report(report)
    assert code == 1
    assert any("biz.py:9" in ln for ln in lines)
    assert any("R-07" in ln for ln in lines)


def test_format_retention_report_log_violation() -> None:
    report = RetentionReport(
        local_count=1, oss_count=1, log_delete_hits=["w.log:2"], log_files_scanned=["w.log"]
    )
    lines, code = format_retention_report(report)
    assert code == 1
    assert any("w.log:2" in ln for ln in lines)


def test_format_retention_report_oss_skip_passes() -> None:
    report = RetentionReport(local_count=2, oss_count=None, oss_skip_reason="缺 config")
    lines, code = format_retention_report(report)
    assert code == 0  # OSS 不可用不致命
    assert any("SKIP" in ln for ln in lines)


# ── run_verify_oss_retention 编排 ───────────────────────────────────────────
def test_run_verify_oss_retention_ok(tmp_path: Path) -> None:
    frags = tmp_path / "fragments"
    (frags / DATE / VALID_FID).mkdir(parents=True)
    (frags / DATE / VALID_FID / ".done").write_bytes(b"")
    src = tmp_path / "src"
    src.mkdir()
    (src / "poller.py").write_text("# no delete here\n", encoding="utf-8")
    log = tmp_path / "worker.log"
    log.write_text("poll ok\n", encoding="utf-8")
    source = FakeSource([OssListing(key=KEY1), OssListing(key=KEY2)])
    lines, code = run_verify_oss_retention(
        source=source, fragments_root=frags, src_root=src, log_paths=[log]
    )
    assert code == 0
    assert any("OSS 留存校验通过" in ln for ln in lines)


def test_run_verify_oss_retention_oss_less_than_local(tmp_path: Path) -> None:
    frags = tmp_path / "fragments"
    for fid in (VALID_FID, VALID_FID2):
        (frags / DATE / fid).mkdir(parents=True)
        (frags / DATE / fid / ".done").write_bytes(b"")
    src = tmp_path / "src"
    src.mkdir()
    source = FakeSource([OssListing(key=KEY1)])  # OSS 只有 1 < 本地 2
    lines, code = run_verify_oss_retention(
        source=source, fragments_root=frags, src_root=src, log_paths=[]
    )
    assert code == 1
    assert any("少于本地" in ln for ln in lines)


def test_run_verify_oss_retention_oss_unreachable_skips(tmp_path: Path) -> None:
    frags = tmp_path / "fragments"
    src = tmp_path / "src"
    src.mkdir()
    source = FakeSource(fail=True)
    lines, code = run_verify_oss_retention(
        source=source, fragments_root=frags, src_root=src, log_paths=[]
    )
    assert code == 0  # OSS 不可达不致命
    assert any("SKIP" in ln for ln in lines)
    assert all("boom-list" not in ln for ln in lines)
