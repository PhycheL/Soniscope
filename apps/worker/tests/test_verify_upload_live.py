"""verify_upload_live 单测（US-010）：纯断言、编排 SKIP/FAIL、P95、泄漏检测、报告。

全程注入 FakeProbes，不触网。
"""

from __future__ import annotations

import re
from collections.abc import Callable

import pytest

from soniscope_worker.verify_prep import ProbeError
from soniscope_worker.verify_upload_live import (
    FAKE_CODE,
    MISMATCH_BODY_SIZE,
    VERIFIED_BODY,
    LiveResult,
    VerifyLiveOptions,
    VerifyResponse,
    all_passed,
    assert_auth_failure,
    assert_object_not_found,
    assert_size_mismatch,
    assert_verified_true,
    format_report,
    make_fragment_id,
    run_checks,
    run_test_verify_upload,
)

_FID_RE = re.compile(r"^\d{8}T\d{6}_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$")


def _resp(status: int, body: dict[str, object], elapsed: float = 0.1) -> VerifyResponse:
    return VerifyResponse(status=status, body=body, elapsed_seconds=elapsed)


# ── 纯断言：assert_auth_failure ──────────────────────────────────────────────
@pytest.mark.parametrize("status", [400, 401])
def test_auth_failure_ok(status: int) -> None:
    r = assert_auth_failure(_resp(status, {"error": "INVALID_CODE"}), name="x")
    assert r.status == "PASS"


def test_auth_failure_wrong_status() -> None:
    r = assert_auth_failure(_resp(200, {"verified": False, "reason": "X"}), name="x")
    assert r.status == "FAIL"


def test_auth_failure_detects_object_info_leak() -> None:
    # 鉴权失败却返回对象信息字段 → 判 FAIL（AC#6）。
    r = assert_auth_failure(_resp(401, {"error": "INVALID_CODE", "size": 123}), name="x")
    assert r.status == "FAIL"
    assert "泄漏" in r.detail


def test_auth_failure_detects_verified_true_leak() -> None:
    r = assert_auth_failure(_resp(401, {"verified": True}), name="x")
    assert r.status == "FAIL"


# ── 纯断言：assert_verified_true ─────────────────────────────────────────────
def test_verified_true_ok() -> None:
    body = {"verified": True, "etag": "abc", "size": 40, "last_modified": "t"}
    r = assert_verified_true(_resp(200, body), expected_size=40, name="x")
    assert r.status == "PASS"


def test_verified_true_size_mismatch_fails() -> None:
    body = {"verified": True, "etag": "abc", "size": 99, "last_modified": "t"}
    r = assert_verified_true(_resp(200, body), expected_size=40, name="x")
    assert r.status == "FAIL"


def test_verified_true_missing_field_fails() -> None:
    body = {"verified": True, "size": 40, "last_modified": "t"}  # 缺 etag
    r = assert_verified_true(_resp(200, body), expected_size=40, name="x")
    assert r.status == "FAIL"


def test_verified_true_non_200_fails() -> None:
    r = assert_verified_true(_resp(401, {"error": "INVALID_CODE"}), expected_size=40, name="x")
    assert r.status == "FAIL"


# ── 纯断言：assert_object_not_found / assert_size_mismatch ───────────────────
def test_object_not_found_ok() -> None:
    body = {"verified": False, "reason": "OBJECT_NOT_FOUND"}
    assert assert_object_not_found(_resp(200, body), name="x").status == "PASS"


def test_object_not_found_wrong_reason_fails() -> None:
    body = {"verified": False, "reason": "SIZE_MISMATCH"}
    assert assert_object_not_found(_resp(200, body), name="x").status == "FAIL"


def test_size_mismatch_ok() -> None:
    body = {"verified": False, "reason": "SIZE_MISMATCH", "actual_size": 100}
    r = assert_size_mismatch(_resp(200, body), expected_actual_size=100, name="x")
    assert r.status == "PASS"


def test_size_mismatch_wrong_actual_fails() -> None:
    body = {"verified": False, "reason": "SIZE_MISMATCH", "actual_size": 50}
    r = assert_size_mismatch(_resp(200, body), expected_actual_size=100, name="x")
    assert r.status == "FAIL"


# ── make_fragment_id ─────────────────────────────────────────────────────────
def test_make_fragment_id_matches_regex() -> None:
    import datetime

    fid = make_fragment_id(datetime.datetime(2026, 5, 26, 14, 48, 0, tzinfo=datetime.UTC))
    assert _FID_RE.match(fid)


def test_make_fragment_id_unique_same_second() -> None:
    import datetime

    now = datetime.datetime(2026, 5, 26, 14, 48, 0, tzinfo=datetime.UTC)
    assert make_fragment_id(now) != make_fragment_id(now)


# ── FakeProbes ───────────────────────────────────────────────────────────────
class FakeProbes:
    """按 fragment_id 推断场景返回响应；记录上传 / 删除。"""

    def __init__(
        self,
        *,
        responses: dict[str, VerifyResponse] | None = None,
        default: VerifyResponse | None = None,
        unreachable: bool = False,
    ) -> None:
        self.responses = responses or {}
        self.default = default
        self.unreachable = unreachable
        self.uploaded: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self.calls: list[tuple[str, str, int]] = []

    def call_verify_upload(
        self, code: str, fragment_id: str, expected_size: int
    ) -> VerifyResponse:
        self.calls.append((code, fragment_id, expected_size))
        if self.unreachable:
            raise ProbeError("FC verify-upload 不可达")
        if code in self.responses:
            return self.responses[code]
        assert self.default is not None
        return self.default

    def upload_object(self, key: str, body: bytes) -> None:
        self.uploaded[key] = body

    def delete_object(self, key: str) -> None:
        self.deleted.append(key)


def _fixed_fid_factory() -> Callable[[], str]:
    seq = iter(
        f"20260526T14480{i}_dev01_01HZX3K8MN5PQR9TFB7AYWVCD{chr(65 + i)}" for i in range(9)
    )
    return lambda: next(seq)


# ── 编排：无 code → 仅伪造场景跑，其余 SKIP，exit 0 ──────────────────────────
def test_run_checks_no_codes_only_fake() -> None:
    probes = FakeProbes(responses={FAKE_CODE: _resp(401, {"error": "INVALID_CODE"})})
    results, latencies = run_checks(
        probes, VerifyLiveOptions(), fragment_id_factory=_fixed_fid_factory()
    )
    by_status = [r.status for r in results]
    assert by_status.count("PASS") == 1  # 仅伪造 code
    assert by_status.count("SKIP") == 3  # verified / not_found / mismatch
    assert len(latencies) == 1
    assert all_passed(results, latencies) is True


# ── 编排：全 code 全成功 ────────────────────────────────────────────────────
def test_run_checks_all_codes_pass() -> None:
    probes = FakeProbes(
        responses={
            FAKE_CODE: _resp(401, {"error": "INVALID_CODE"}),
            "cv": _resp(
                200,
                {"verified": True, "etag": "e", "size": len(VERIFIED_BODY), "last_modified": "t"},
            ),
            "cn": _resp(200, {"verified": False, "reason": "OBJECT_NOT_FOUND"}),
            "cm": _resp(
                200,
                {"verified": False, "reason": "SIZE_MISMATCH", "actual_size": MISMATCH_BODY_SIZE},
            ),
        }
    )
    opts = VerifyLiveOptions(verified_code="cv", not_found_code="cn", mismatch_code="cm")
    results, latencies = run_checks(probes, opts, fragment_id_factory=_fixed_fid_factory())
    assert all(r.status == "PASS" for r in results)
    assert len(latencies) == 4
    assert all_passed(results, latencies) is True
    # not_found 场景构造了「上传后删除」；verified / mismatch 场景做了清理删除。
    assert len(probes.deleted) == 3
    assert len(probes.uploaded) == 3


# ── 编排：verified 上传后清理删除该对象 ─────────────────────────────────────
def test_verified_cleans_up_object() -> None:
    probes = FakeProbes(
        responses={
            FAKE_CODE: _resp(401, {"error": "INVALID_CODE"}),
            "cv": _resp(
                200,
                {"verified": True, "etag": "e", "size": len(VERIFIED_BODY), "last_modified": "t"},
            ),
        },
        default=_resp(401, {"error": "INVALID_CODE"}),
    )
    opts = VerifyLiveOptions(verified_code="cv")
    run_checks(probes, opts, fragment_id_factory=_fixed_fid_factory())
    # verified 场景上传 1 个对象并清理（删除）。
    assert len(probes.uploaded) == 1
    assert len(probes.deleted) == 1
    assert probes.deleted[0] in probes.uploaded


# ── 编排：FC 不可达 → 该场景 FAIL ───────────────────────────────────────────
def test_run_checks_unreachable_fails() -> None:
    probes = FakeProbes(unreachable=True)
    results, latencies = run_checks(
        probes, VerifyLiveOptions(), fragment_id_factory=_fixed_fid_factory()
    )
    assert any(r.status == "FAIL" for r in results)
    assert all_passed(results, latencies) is False


# ── P95：超阈值 → all_passed False ──────────────────────────────────────────
def test_p95_threshold_blocks_pass() -> None:
    slow = _resp(401, {"error": "INVALID_CODE"}, elapsed=2.0)  # 2s > 1s 阈值
    probes = FakeProbes(responses={FAKE_CODE: slow})
    results, latencies = run_checks(
        probes, VerifyLiveOptions(), fragment_id_factory=_fixed_fid_factory()
    )
    assert all(not r.failed for r in results)  # 断言本身通过
    assert all_passed(results, latencies) is False  # 但 P95 超阈值


# ── 报告：不泄漏 + P95 行 + 末行 ────────────────────────────────────────────
def test_format_report_has_p95_and_no_secret() -> None:
    results = [LiveResult("场景", "PASS", "OK")]
    lines = format_report(results, [0.1, 0.2])
    text = "\n".join(lines)
    assert "P95" in text
    assert "✅ test-verify-upload 通过" in text
    assert "fc-logs FUNCTION=verify-upload" in text


def test_format_report_empty_latency_marks_fail() -> None:
    # 有断言通过但无任何真实调用（全 SKIP）时 P95 无样本 → 不达标。
    results = [LiveResult("场景", "SKIP", "no code")]
    assert all_passed(results, []) is False


# ── 顶层入口 ─────────────────────────────────────────────────────────────────
def test_run_test_verify_upload_exit_zero_skip_only() -> None:
    probes = FakeProbes(responses={FAKE_CODE: _resp(401, {"error": "INVALID_CODE"})})
    lines, code = run_test_verify_upload(VerifyLiveOptions(), probes=probes)
    assert code == 0
    assert any("test-verify-upload 通过" in ln for ln in lines)


def test_run_test_verify_upload_exit_one_on_fail() -> None:
    probes = FakeProbes(unreachable=True)
    lines, code = run_test_verify_upload(VerifyLiveOptions(), probes=probes)
    assert code == 1
    assert any("未通过" in ln for ln in lines)
