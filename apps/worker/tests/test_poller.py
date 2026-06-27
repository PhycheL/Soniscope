"""US-021 Worker OSS 轮询 / HeadObject 元数据 / 安全下载 单元测试（全程不触网）。"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

import pytest

from soniscope_worker import poller
from soniscope_worker.config import SoniScopeConfig
from soniscope_worker.poller import (
    ManifestDraft,
    OssListing,
    PollIntervalOptions,
    PollPlan,
    check_scan_intervals,
    cleanup_parts,
    date_of,
    done_marker_path,
    fragment_id_from_key,
    metadata_to_draft,
    normalize_metadata,
    plan_downloads,
    poll_loop,
    poll_once,
    process_plan,
    run_test_poll_interval,
)

FID = "20260627T101500_dev01_0123456789ABCDEFGHJKMNPQRS"
KEY = "recordings/2026-06-27/20260627T101500_dev01_0123456789ABCDEFGHJKMNPQRS.wav"


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _full_meta(sha: str) -> dict[str, str]:
    return {
        "session-id": "SESSION01XYZ",
        "chunk-seq": "1",
        "chunk-total": "0",
        "recorded-at": "2026-06-27T10:15:00+08:00",
        "duration": "3.2",
        "original-format": "mp3",
        "sha256": sha,
    }


class FakeSource:
    """注入用 OSS 数据源：内存 dict（body + metadata），可计数与注入错误。"""

    def __init__(self, objects: Mapping[str, tuple[bytes, Mapping[str, str]]]) -> None:
        self._objects = dict(objects)
        self.download_calls: list[str] = []
        self.head_calls: list[str] = []
        self.list_calls = 0
        self.download_error: Exception | None = None

    def list_recordings(self) -> list[OssListing]:
        self.list_calls += 1
        return [OssListing(key=k, size=len(v[0])) for k, v in self._objects.items()]

    def head_metadata(self, object_key: str) -> Mapping[str, str]:
        self.head_calls.append(object_key)
        return dict(self._objects[object_key][1])

    def download(self, object_key: str, dest: Path) -> None:
        self.download_calls.append(object_key)
        if self.download_error is not None:
            raise self.download_error
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self._objects[object_key][0])


# ── fragment_id_from_key / date_of ─────────────────────────────────────────
def test_fragment_id_from_key_valid() -> None:
    assert fragment_id_from_key(KEY) == FID


def test_fragment_id_from_key_rejects_non_wav() -> None:
    assert fragment_id_from_key("recordings/2026-06-27/" + FID + ".m4a") is None


def test_fragment_id_from_key_rejects_wrong_prefix() -> None:
    assert fragment_id_from_key("uploads/2026-06-27/" + FID + ".wav") is None


def test_fragment_id_from_key_rejects_bad_id() -> None:
    assert fragment_id_from_key("recordings/2026-06-27/not-a-fragment.wav") is None


def test_fragment_id_from_key_rejects_date_mismatch() -> None:
    # 路径日期与 fragment_id 前缀不一致 → object_key_for 往返不等 → None
    assert fragment_id_from_key("recordings/2026-06-28/" + FID + ".wav") is None


def test_date_of() -> None:
    assert date_of(FID) == "2026-06-27"


# ── normalize_metadata / metadata_to_draft ─────────────────────────────────
def test_normalize_metadata_strips_prefix_and_lowercases() -> None:
    raw = {"X-Oss-Meta-Session-Id": "S1", "x-oss-meta-CHUNK-SEQ": "2"}
    out = normalize_metadata(raw)
    assert out == {"session-id": "S1", "chunk-seq": "2"}


def test_metadata_to_draft_full() -> None:
    draft = metadata_to_draft(FID, _full_meta("a" * 64))
    assert draft == ManifestDraft(
        fragment_id=FID,
        session_id="SESSION01XYZ",
        chunk_seq=1,
        chunk_total=None,  # "0" → None（§3.2）
        recorded_at="2026-06-27T10:15:00+08:00",
        duration_seconds=3.2,
        original_format="mp3",
        original_sha256="a" * 64,
    )


def test_metadata_to_draft_chunked_keeps_total() -> None:
    meta = _full_meta("b" * 64)
    meta["chunk-total"] = "3"
    meta["chunk-seq"] = "2"
    draft = metadata_to_draft(FID, meta)
    assert draft.chunk_total == 3
    assert draft.chunk_seq == 2


def test_metadata_to_draft_with_oss_prefix_keys() -> None:
    raw = {"x-oss-meta-sha256": "c" * 64, "x-oss-meta-duration": "10"}
    draft = metadata_to_draft(FID, raw)
    assert draft.original_sha256 == "c" * 64
    assert draft.duration_seconds == 10.0


def test_metadata_to_draft_missing_and_invalid_are_none() -> None:
    draft = metadata_to_draft(FID, {"chunk-seq": "x", "duration": "abc"})
    assert draft.session_id is None
    assert draft.chunk_seq is None
    assert draft.duration_seconds is None
    assert draft.original_sha256 is None


# ── plan_downloads ─────────────────────────────────────────────────────────
def test_plan_downloads_splits_done_new_ignored() -> None:
    other = "20260627T101600_dev01_0123456789ABCDEFGHJKMNPQRS"
    other_key = "recordings/2026-06-27/" + other + ".wav"
    listings = [
        OssListing(KEY, 100),
        OssListing(other_key, 200),
        OssListing("recordings/2026-06-27/garbage.txt", 5),
    ]
    plan = plan_downloads(listings, done_check=lambda fid, date: fid == FID)
    assert [p.fragment_id for p in plan.to_download] == [other]
    assert plan.skipped_done == [FID]
    assert plan.ignored_keys == ["recordings/2026-06-27/garbage.txt"]
    assert plan.to_download[0].object_key == other_key
    assert plan.to_download[0].size == 200


# ── process_plan ───────────────────────────────────────────────────────────
def test_process_plan_download_and_sha_match(tmp_path: Path) -> None:
    body = b"hello audio"
    source = FakeSource({KEY: (body, _full_meta(_sha(body)))})
    plan = PollPlan(FID, KEY, "2026-06-27", len(body))
    outcome = process_plan(
        plan, source, inbox_root=tmp_path / "inbox", fragments_root=tmp_path / "fragments"
    )
    assert outcome.status == "downloaded"
    assert outcome.sha256 == _sha(body)
    assert outcome.draft is not None and outcome.draft.original_format == "mp3"
    assert outcome.part_path is not None and outcome.part_path.exists()
    assert outcome.part_path.name == f"{FID}.part"
    assert source.head_calls == [KEY]


def test_process_plan_sha_mismatch_deletes_part(tmp_path: Path) -> None:
    body = b"hello audio"
    # 元数据里写一个不匹配的 sha256
    source = FakeSource({KEY: (body, _full_meta("d" * 64))})
    plan = PollPlan(FID, KEY, "2026-06-27", len(body))
    inbox = tmp_path / "inbox"
    outcome = process_plan(
        plan, source, inbox_root=inbox, fragments_root=tmp_path / "fragments"
    )
    assert outcome.status == "sha256_mismatch"
    assert not (inbox / f"{FID}.part").exists()  # .part 已删除等下一轮重下


def test_process_plan_download_error_is_caught(tmp_path: Path) -> None:
    source = FakeSource({KEY: (b"x", _full_meta(_sha(b"x")))})
    source.download_error = OSError("network down")
    plan = PollPlan(FID, KEY, "2026-06-27", 1)
    outcome = process_plan(
        plan, source, inbox_root=tmp_path / "inbox", fragments_root=tmp_path / "fragments"
    )
    assert outcome.status == "error"
    assert "network down" in outcome.detail


def test_process_plan_no_meta_sha_still_downloads(tmp_path: Path) -> None:
    body = b"no sha meta"
    source = FakeSource({KEY: (body, {"original-format": "wav"})})
    plan = PollPlan(FID, KEY, "2026-06-27", len(body))
    outcome = process_plan(
        plan, source, inbox_root=tmp_path / "inbox", fragments_root=tmp_path / "fragments"
    )
    assert outcome.status == "downloaded"


# ── cleanup_parts ──────────────────────────────────────────────────────────
def test_cleanup_parts_removes_residual(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / f"{FID}.part").write_bytes(b"partial")
    (inbox / "other.part").write_bytes(b"partial")
    (inbox / "keep.wav").write_bytes(b"keep")
    removed = cleanup_parts(inbox)
    assert set(removed) == {f"{FID}.part", "other.part"}
    assert not (inbox / f"{FID}.part").exists()
    assert (inbox / "keep.wav").exists()


def test_cleanup_parts_missing_inbox() -> None:
    assert cleanup_parts(Path("/nonexistent/inbox/xyz")) == []


# ── poll_once：跳过 .done，下载新对象 ──────────────────────────────────────
def test_poll_once_skips_done_fragment(tmp_path: Path) -> None:
    body = b"audio body"
    source = FakeSource({KEY: (body, _full_meta(_sha(body)))})
    fragments = tmp_path / "fragments"
    done = done_marker_path(fragments, "2026-06-27", FID)
    done.parent.mkdir(parents=True)
    done.write_bytes(b"")
    logs: list[str] = []
    result = poll_once(
        source, inbox_root=tmp_path / "inbox", fragments_root=fragments, log=logs.append
    )
    assert result.plan.skipped_done == [FID]
    assert source.download_calls == []  # .done → 不下载、不转写（AC#2）
    assert result.outcomes == []


def test_poll_once_downloads_new(tmp_path: Path) -> None:
    body = b"audio body"
    source = FakeSource({KEY: (body, _full_meta(_sha(body)))})
    logs: list[str] = []
    result = poll_once(
        source,
        inbox_root=tmp_path / "inbox",
        fragments_root=tmp_path / "fragments",
        log=logs.append,
    )
    assert source.download_calls == [KEY]
    assert [o.status for o in result.outcomes] == ["downloaded"]


# ── poll_loop：注入 sleep/monotonic，max_iterations，启动清理 .part ─────────
def test_poll_loop_runs_n_iterations_and_cleans_parts(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "stale.part").write_bytes(b"x")
    source = FakeSource({})
    sleeps: list[float] = []
    clock = [1000.0]

    def fake_sleep(s: float) -> None:
        sleeps.append(s)
        clock[0] += s

    stamps: list[float] = []
    iters = poll_loop(
        source,
        30.0,
        inbox_root=inbox,
        fragments_root=tmp_path / "fragments",
        log=lambda _m: None,
        max_iterations=3,
        sleep=fake_sleep,
        monotonic=lambda: clock[0],
        on_scan=stamps.append,
    )
    assert iters == 3
    assert source.list_calls == 3
    assert sleeps == [30.0, 30.0]  # 末轮不 sleep
    assert not (inbox / "stale.part").exists()  # 启动清理残留 .part（AC#6）
    ok, gaps = check_scan_intervals(stamps, 30.0)
    assert ok and gaps == [30.0, 30.0]


def test_poll_loop_survives_scan_error(tmp_path: Path) -> None:
    class BrokenSource:
        def list_recordings(self) -> list[OssListing]:
            raise ConnectionError("oss unreachable")

        def head_metadata(self, object_key: str) -> Mapping[str, str]:
            return {}

        def download(self, object_key: str, dest: Path) -> None:
            return None

    logs: list[str] = []
    iters = poll_loop(
        BrokenSource(),
        10.0,
        inbox_root=tmp_path / "inbox",
        fragments_root=tmp_path / "fragments",
        log=logs.append,
        max_iterations=2,
        sleep=lambda _s: None,
    )
    assert iters == 2  # 单轮失败不杀死循环，节奏保持
    assert any("本轮扫描失败" in ln for ln in logs)


def test_poll_loop_stop_callback(tmp_path: Path) -> None:
    source = FakeSource({})
    calls = [0]

    def stop() -> bool:
        calls[0] += 1
        return True

    iters = poll_loop(
        source,
        5.0,
        inbox_root=tmp_path / "inbox",
        fragments_root=tmp_path / "fragments",
        log=lambda _m: None,
        stop=stop,
        sleep=lambda _s: None,
    )
    assert iters == 1


# ── check_scan_intervals ───────────────────────────────────────────────────
def test_check_scan_intervals_within_tolerance() -> None:
    ok, gaps = check_scan_intervals([0.0, 30.2, 60.1], 30.0)
    assert ok
    assert gaps == [pytest.approx(30.2), pytest.approx(29.9)]


def test_check_scan_intervals_out_of_tolerance() -> None:
    ok, _ = check_scan_intervals([0.0, 40.0], 30.0)
    assert not ok


def test_check_scan_intervals_too_few() -> None:
    assert check_scan_intervals([1.0], 30.0) == (False, [])


# ── run_test_poll_interval ─────────────────────────────────────────────────
def _cfg(interval: int) -> SoniScopeConfig:
    return SoniScopeConfig.model_validate(
        {
            "oss": {
                "endpoint": "oss-cn-beijing.aliyuncs.com",
                "bucket": "soniscope-audio",
                "access_key_id": "ak-id",
                "access_key_secret": "ak-secret-value-1234",
            },
            "poll": {"interval_seconds": interval},
            "transcriber": {
                "name": "cloud-speech",
                "provider": "aliyun-nls",
                "model": "m",
                "params_version": "v1",
                "api_endpoint": "cn-beijing",
                "appkey": "appkey-value-1234",
                "access_key_id": "t-ak",
                "access_key_secret": "t-secret-value-1234",
                "upload_mode": "oss-url",
            },
        }
    )


def test_run_test_poll_interval_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
    clock = [0.0]

    def fake_sleep(s: float) -> None:
        clock[0] += s

    lines, code = run_test_poll_interval(
        PollIntervalOptions(expected_interval=30, iterations=3),
        source=FakeSource({}),
        cfg=_cfg(30),
        sleep=fake_sleep,
        monotonic=lambda: clock[0],
    )
    assert code == 0
    assert any("符合配置" in ln for ln in lines)


def test_run_test_poll_interval_expected_mismatch() -> None:
    lines, code = run_test_poll_interval(
        PollIntervalOptions(expected_interval=30, iterations=2),
        source=FakeSource({}),
        cfg=_cfg(60),
        sleep=lambda _s: None,
        monotonic=lambda: 0.0,
    )
    assert code == 1
    assert any("期望 poll.interval_seconds=30" in ln for ln in lines)


def test_run_test_poll_interval_skips_without_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))  # 无 config.yaml
    lines, code = run_test_poll_interval(PollIntervalOptions(expected_interval=30))
    assert code == 0
    assert any("SKIP" in ln for ln in lines)


# ── 安全红线：Worker 数据源协议绝不暴露删除能力 ───────────────────────────
def test_oss_source_has_no_delete_method() -> None:
    assert not hasattr(poller.RealOssSource, "delete_object")
    assert not hasattr(poller.RealOssSource, "delete")
    members = {n for n in dir(poller.OssSource) if not n.startswith("_")}
    assert members == {"list_recordings", "head_metadata", "download"}
