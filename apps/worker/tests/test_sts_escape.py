"""sts_escape 单测（US-017 AC#8）：STS 单 key policy 越权写其他 key → AccessDenied。

FakeProbes 注入全程不触网；覆盖纯断言、被拒 / 未被拒、凭证缺失 SKIP、探针错误 FAIL、
越权目标为「另一个」key、报告不泄漏 AK Secret 明文、退出码。
"""

from __future__ import annotations

from soniscope_worker.fc_live import IssuedCredential
from soniscope_worker.sts_escape import (
    EscapeResult,
    StsEscapeOptions,
    all_passed,
    assert_escape_denied,
    format_report,
    run_checks,
    run_test_sts_escape,
)
from soniscope_worker.verify_prep import ProbeError

ALLOWED_KEY = "recordings/2026-06-27/20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav"

CRED = IssuedCredential(
    access_key_id="STS.id",
    access_key_secret="super-secret-do-not-log",
    security_token="security-token-do-not-log",
    expiration="2026-06-27T11:00:00Z",
    bucket="soniscope-audio",
    endpoint="oss-cn-beijing.aliyuncs.com",
    object_key=ALLOWED_KEY,
)


class FakeProbes:
    """注入式 STS 签发 + OSS PutObject 桩。"""

    def __init__(
        self,
        *,
        error_code: str = "AccessDenied",
        mint_error: str = "",
        put_raises: bool = False,
    ) -> None:
        self.error_code = error_code
        self.mint_error = mint_error
        self.put_raises = put_raises
        self.put_keys: list[str] = []

    def mint_single_key_credential(self, allowed_key: str, *, code: str) -> IssuedCredential:
        if self.mint_error:
            raise ProbeError(self.mint_error)
        return CRED

    def put_object(self, cred: IssuedCredential, key: str) -> str:
        self.put_keys.append(key)
        if self.put_raises:
            raise ProbeError("OSS STS 客户端初始化失败：RuntimeError")
        return self.error_code


# ── 纯断言 ───────────────────────────────────────────────────────────────────
def test_assert_escape_denied_access_denied() -> None:
    r = assert_escape_denied("AccessDenied", name="x")
    assert r.status == "PASS"
    assert "已被拒" in r.detail


def test_assert_escape_denied_unexpected_success() -> None:
    r = assert_escape_denied("", name="x")
    assert r.status == "FAIL"
    assert r.fix_hint


def test_assert_escape_denied_wrong_code() -> None:
    assert assert_escape_denied("SomeOtherError", name="x").status == "FAIL"


# ── run_checks ───────────────────────────────────────────────────────────────
def test_run_checks_denied_passes() -> None:
    probes = FakeProbes(error_code="AccessDenied")
    results = run_checks(probes, StsEscapeOptions(), allowed_key=ALLOWED_KEY)
    assert all_passed(results)
    # 越权目标必须是「另一个」key，不能等于允许的 key。
    assert probes.put_keys and probes.put_keys[0] != ALLOWED_KEY
    assert probes.put_keys[0].startswith("recordings/2026-06-27/")


def test_run_checks_not_denied_fails() -> None:
    probes = FakeProbes(error_code="")  # 意外成功（未被拒）
    results = run_checks(probes, StsEscapeOptions(), allowed_key=ALLOWED_KEY)
    assert not all_passed(results)
    assert results[0].status == "FAIL"


def test_run_checks_missing_credential_skips() -> None:
    probes = FakeProbes(mint_error="未提供部署凭证")
    results = run_checks(probes, StsEscapeOptions(), allowed_key=ALLOWED_KEY)
    assert results[0].status == "SKIP"
    assert all_passed(results)  # SKIP 不算失败
    assert probes.put_keys == []


def test_run_checks_probe_error_on_put_fails() -> None:
    probes = FakeProbes(put_raises=True)
    results = run_checks(probes, StsEscapeOptions(), allowed_key=ALLOWED_KEY)
    assert results[0].status == "FAIL"


# ── 报告 / 入口 ──────────────────────────────────────────────────────────────
def test_report_no_secret_leak() -> None:
    probes = FakeProbes(error_code="AccessDenied")
    results = run_checks(probes, StsEscapeOptions(), allowed_key=ALLOWED_KEY)
    report = "\n".join(format_report(results))
    assert "super-secret-do-not-log" not in report
    assert "security-token-do-not-log" not in report
    assert "✅" in report


def test_run_test_sts_escape_exit_codes() -> None:
    _, code_pass = run_test_sts_escape(StsEscapeOptions(), FakeProbes(error_code="AccessDenied"))
    assert code_pass == 0
    _, code_fail = run_test_sts_escape(StsEscapeOptions(), FakeProbes(error_code=""))
    assert code_fail == 1
    # SKIP（无凭证）不算失败，退出 0。
    _, code_skip = run_test_sts_escape(StsEscapeOptions(), FakeProbes(mint_error="缺凭证"))
    assert code_skip == 0


def test_default_results_nonempty() -> None:
    assert isinstance(run_checks(FakeProbes(), StsEscapeOptions())[0], EscapeResult)
