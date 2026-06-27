"""e2e_scenarios 单测（US-031）：E2E 崩溃恢复 / 显式重转 / 安全反例编排。

崩溃恢复与显式重转为自包含子场景（临时目录 + stub，不触网），直接跑真实编排断言全 PASS；
安全反例注入 Fake 探针（FC HTTP + STS PutObject），覆盖伪造 code 401、allowlist 外 403、
STS 越权 AccessDenied、FC 不可达 SKIP / FAIL、汇总退出码与不泄漏 AK Secret 明文。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from soniscope_worker.e2e_scenarios import (
    FAIL,
    PASS,
    SKIP,
    E2eSecurityOptions,
    ScenarioResult,
    format_e2e_report,
    run_test_e2e_crash_recovery,
    run_test_e2e_retranscribe,
    run_test_e2e_security,
)
from soniscope_worker.fc_live import (
    ERR_INVALID_CODE,
    ERR_OPENID_NOT_ALLOWED,
    FAKE_CODE,
    HttpResponse,
    IssuedCredential,
    OssOpResult,
)
from soniscope_worker.sts_escape import StsEscapeOptions
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


# ── Fake 探针 ────────────────────────────────────────────────────────────────
class FakeFcProbes:
    """注入式 FC HTTP 探针：按 code 返回预设响应或抛 ProbeError。"""

    def __init__(
        self, *, responses: Mapping[str, HttpResponse] | None = None, unreachable: bool = False
    ) -> None:
        self._responses = dict(responses or {})
        self._unreachable = unreachable
        self.calls: list[tuple[str, str, int]] = []

    def call_issue_credential(self, code: str, fragment_id: str, size: int) -> HttpResponse:
        self.calls.append((code, fragment_id, size))
        if self._unreachable:
            raise ProbeError("FC issue-credential 不可达：模拟")
        if code in self._responses:
            return self._responses[code]
        return HttpResponse(401, {"error": ERR_INVALID_CODE})

    # oss_escape_ops 不会被安全 E2E 用到（只用 call_issue_credential），保留以满足协议。
    def oss_escape_ops(
        self, cred: IssuedCredential, *, check_expiry: bool
    ) -> Sequence[OssOpResult]:
        raise AssertionError("安全 E2E 不应调用 oss_escape_ops")


class FakeStsProbes:
    """注入式 STS 签发 + OSS PutObject 探针。"""

    def __init__(self, *, error_code: str = "AccessDenied", mint_error: str = "") -> None:
        self._error_code = error_code
        self._mint_error = mint_error
        self.put_keys: list[str] = []

    def mint_single_key_credential(self, allowed_key: str, *, code: str) -> IssuedCredential:
        if self._mint_error:
            raise ProbeError(self._mint_error)
        return CRED

    def put_object(self, cred: IssuedCredential, key: str) -> str:
        self.put_keys.append(key)
        return self._error_code


# ── format_e2e_report ────────────────────────────────────────────────────────
def test_report_all_pass() -> None:
    lines, code = format_e2e_report("X", [ScenarioResult("a", PASS, "ok")])
    assert code == 0
    assert any("✅" in ln for ln in lines)


def test_report_fail_shows_repro() -> None:
    lines, code = format_e2e_report(
        "X", [ScenarioResult("a", FAIL, "boom", repro="make redo")]
    )
    assert code == 1
    joined = "\n".join(lines)
    assert "❌" in joined
    assert "复现：make redo" in joined


def test_report_skip_not_failure() -> None:
    lines, code = format_e2e_report("X", [ScenarioResult("a", SKIP, "no creds")])
    assert code == 0
    assert any("SKIP" in ln for ln in lines)


# ── 崩溃恢复 / 显式重转（自包含真实编排）─────────────────────────────────────
def test_e2e_crash_recovery_passes() -> None:
    lines, code = run_test_e2e_crash_recovery()
    assert code == 0, "\n".join(lines)
    # 3 个场景：下载中断 / 转码中断 / 转写中断。
    assert sum(1 for ln in lines if ln.startswith("[PASS]")) == 3
    assert any("transcript.json" in ln for ln in lines)


def test_e2e_retranscribe_passes() -> None:
    lines, code = run_test_e2e_retranscribe()
    assert code == 0, "\n".join(lines)
    assert sum(1 for ln in lines if ln.startswith("[PASS]")) == 2


# ── 安全反例 ─────────────────────────────────────────────────────────────────
def test_e2e_security_all_pass() -> None:
    fc = FakeFcProbes(
        responses={
            FAKE_CODE: HttpResponse(401, {"error": ERR_INVALID_CODE}),
            "real-not-allowed": HttpResponse(403, {"error": ERR_OPENID_NOT_ALLOWED}),
        }
    )
    sts = FakeStsProbes(error_code="AccessDenied")
    lines, code = run_test_e2e_security(
        E2eSecurityOptions(not_allowed_code="real-not-allowed"),
        fc_probes=fc,
        sts_probes=sts,
    )
    assert code == 0, "\n".join(lines)
    # 越权目标必须是「另一个」key。
    assert sts.put_keys and sts.put_keys[0] != ALLOWED_KEY


def test_e2e_security_skips_not_allowed_without_code() -> None:
    fc = FakeFcProbes()
    sts = FakeStsProbes(error_code="AccessDenied")
    lines, code = run_test_e2e_security(E2eSecurityOptions(), fc_probes=fc, sts_probes=sts)
    assert code == 0
    assert any(ln.startswith("[SKIP]") and "allowlist 外" in ln for ln in lines)


def test_e2e_security_fake_code_leaking_sts_fails() -> None:
    # 拒绝场景却泄漏 STS 字段 → 必须 FAIL（不返回 STS 红线，AC#4）。
    fc = FakeFcProbes(
        responses={FAKE_CODE: HttpResponse(401, {"error": ERR_INVALID_CODE, "access_key_id": "x"})}
    )
    sts = FakeStsProbes(error_code="AccessDenied")
    lines, code = run_test_e2e_security(E2eSecurityOptions(), fc_probes=fc, sts_probes=sts)
    assert code == 1, "\n".join(lines)


def test_e2e_security_escape_not_denied_fails() -> None:
    fc = FakeFcProbes(responses={FAKE_CODE: HttpResponse(401, {"error": ERR_INVALID_CODE})})
    sts = FakeStsProbes(error_code="")  # 越权意外成功（未被拒）
    _, code = run_test_e2e_security(E2eSecurityOptions(), fc_probes=fc, sts_probes=sts)
    assert code == 1


def test_e2e_security_fc_unreachable_skips() -> None:
    fc = FakeFcProbes(unreachable=True)
    sts = FakeStsProbes(error_code="AccessDenied")
    lines, code = run_test_e2e_security(E2eSecurityOptions(), fc_probes=fc, sts_probes=sts)
    # FC 不可达 → 该项 SKIP（不阻断），STS 反例仍 PASS → 整体 0。
    assert code == 0
    assert any(ln.startswith("[SKIP]") and "FC 不可达" in ln for ln in lines)


def test_e2e_security_no_secret_leak() -> None:
    fc = FakeFcProbes(responses={FAKE_CODE: HttpResponse(401, {"error": ERR_INVALID_CODE})})
    sts = FakeStsProbes(error_code="AccessDenied")
    lines, _ = run_test_e2e_security(
        E2eSecurityOptions(code="allow-code"), fc_probes=fc, sts_probes=sts
    )
    report = "\n".join(lines)
    assert "super-secret-do-not-log" not in report
    assert "security-token-do-not-log" not in report


def test_sts_escape_options_passthrough() -> None:
    # code 透传给 sts_escape（走 FC 真实签发链路时需要）。
    captured: dict[str, str] = {}

    class CapturingSts(FakeStsProbes):
        def mint_single_key_credential(
            self, allowed_key: str, *, code: str
        ) -> IssuedCredential:
            captured["code"] = code
            return super().mint_single_key_credential(allowed_key, code=code)

    fc = FakeFcProbes(responses={FAKE_CODE: HttpResponse(401, {"error": ERR_INVALID_CODE})})
    run_test_e2e_security(
        E2eSecurityOptions(code="allow-xyz"), fc_probes=fc, sts_probes=CapturingSts()
    )
    assert captured.get("code") == "allow-xyz"
    # 健全性：StsEscapeOptions 接受 code 字段。
    assert StsEscapeOptions(code="allow-xyz").code == "allow-xyz"
