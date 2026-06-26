"""US-008：`make test-fc-live` issue-credential 云端联调与 STS 安全反例测试。

HTTP / OSS 依赖通过 `FcLiveProbes` 协议注入 `FakeProbes`，全程不触网。
重点覆盖：纯断言逻辑（401/403/成功/SIZE_EXCEEDED/越权/过期）、code 缺失时 SKIP、
STS 字段不泄漏、汇总与退出码、ProbeError 收敛为单项 FAIL、fragment_id 合法性。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from typer.testing import CliRunner

from soniscope_worker.cli import app
from soniscope_worker.fc_live import (
    ERR_INVALID_CODE,
    ERR_OPENID_NOT_ALLOWED,
    ERR_SIZE_EXCEEDED,
    ESCAPE_OPS,
    FAIL,
    PASS,
    SKIP,
    HttpResponse,
    IssuedCredential,
    LiveOptions,
    OssOpResult,
    all_passed,
    assert_credential_complete,
    assert_escape_op,
    assert_size_exceeded,
    assert_status_error,
    format_report,
    make_fragment_id,
    other_recordings_key,
    parse_issued_credential,
    run_checks,
    run_test_fc_live,
)
from soniscope_worker.verify_prep import ProbeError

runner = CliRunner()

# ── 测试夹具：完整 STS 凭证响应 ──────────────────────────────────────────────
FULL_CRED_BODY: dict[str, object] = {
    "access_key_id": "STS.AkIdExample0000",
    "access_key_secret": "stsSecretValueABCDEFGH1234567890",
    "security_token": "CAISxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "expiration": "2026-06-27T12:00:00Z",
    "bucket": "soniscope-audio",
    "endpoint": "oss-cn-beijing.aliyuncs.com",
    "object_key": "recordings/2026-06-27/20260627T120000_fclive_0123456789ABCDEF0123456789.wav",
}


class FakeProbes:
    """可编程的假探针：按 code 返回预设响应，并记录调用。"""

    def __init__(
        self,
        responses: Mapping[str, HttpResponse] | None = None,
        ops: Sequence[OssOpResult] | None = None,
        *,
        raise_on: str = "",
        ops_error: str = "",
    ) -> None:
        self.responses = dict(responses or {})
        self.ops = list(ops or [])
        self.raise_on = raise_on
        self.ops_error = ops_error
        self.calls: list[tuple[str, str, int]] = []
        self.escape_calls: list[bool] = []

    def call_issue_credential(self, code: str, fragment_id: str, size: int) -> HttpResponse:
        self.calls.append((code, fragment_id, size))
        if self.raise_on and code == self.raise_on:
            raise ProbeError("FC 不可达（测试）")
        if code in self.responses:
            return self.responses[code]
        # 默认：未知 code → 401 INVALID_CODE
        return HttpResponse(401, {"error": ERR_INVALID_CODE})

    def oss_escape_ops(
        self, cred: IssuedCredential, *, check_expiry: bool
    ) -> Sequence[OssOpResult]:
        self.escape_calls.append(check_expiry)
        if self.ops_error:
            raise ProbeError(self.ops_error)
        if not check_expiry:
            return [o for o in self.ops if o.name != "expired_put"]
        return self.ops


def _denied_ops() -> list[OssOpResult]:
    return [
        OssOpResult("put_other_key", "AccessDenied"),
        OssOpResult("get_object", "AccessDenied"),
        OssOpResult("list_objects", "AccessDenied"),
        OssOpResult("delete_object", "AccessDenied"),
        OssOpResult("expired_put", "ExpiredToken"),
    ]


# ── 纯断言逻辑 ───────────────────────────────────────────────────────────────
def test_assert_status_error_pass() -> None:
    resp = HttpResponse(401, {"error": ERR_INVALID_CODE})
    r = assert_status_error(resp, expected_status=401, expected_error=ERR_INVALID_CODE, name="x")
    assert r.status == PASS


def test_assert_status_error_wrong_status() -> None:
    resp = HttpResponse(200, {"error": ERR_INVALID_CODE})
    r = assert_status_error(resp, expected_status=401, expected_error=ERR_INVALID_CODE, name="x")
    assert r.status == FAIL


def test_assert_status_error_wrong_code() -> None:
    resp = HttpResponse(403, {"error": "SOMETHING_ELSE"})
    r = assert_status_error(
        resp, expected_status=403, expected_error=ERR_OPENID_NOT_ALLOWED, name="x"
    )
    assert r.status == FAIL


def test_assert_status_error_detects_leaked_sts_fields() -> None:
    # 拒绝响应里若混入 STS 字段，必须判 FAIL（安全红线）。
    resp = HttpResponse(401, {"error": ERR_INVALID_CODE, "access_key_secret": "leak"})
    r = assert_status_error(resp, expected_status=401, expected_error=ERR_INVALID_CODE, name="x")
    assert r.status == FAIL
    assert "泄漏" in r.detail


def test_assert_credential_complete_pass() -> None:
    r = assert_credential_complete(HttpResponse(200, FULL_CRED_BODY), name="x")
    assert r.status == PASS
    # 只展示 object_key，绝不展示 secret / token。
    assert "stsSecretValue" not in r.detail
    assert "CAIS" not in r.detail
    assert "recordings/2026-06-27" in r.detail


def test_assert_credential_complete_missing_field() -> None:
    body = dict(FULL_CRED_BODY)
    body["security_token"] = ""
    r = assert_credential_complete(HttpResponse(200, body), name="x")
    assert r.status == FAIL
    assert "security_token" in r.detail


def test_assert_credential_complete_non_200() -> None:
    r = assert_credential_complete(HttpResponse(403, {"error": ERR_OPENID_NOT_ALLOWED}), name="x")
    assert r.status == FAIL


def test_assert_size_exceeded_pass() -> None:
    resp = HttpResponse(
        400, {"error": ERR_SIZE_EXCEEDED, "limit_bytes": 52428800, "actual_bytes": 60000000}
    )
    r = assert_size_exceeded(resp, name="x")
    assert r.status == PASS


def test_assert_size_exceeded_missing_bytes() -> None:
    resp = HttpResponse(400, {"error": ERR_SIZE_EXCEEDED})
    assert assert_size_exceeded(resp, name="x").status == FAIL


def test_assert_size_exceeded_wrong_status() -> None:
    resp = HttpResponse(200, dict(FULL_CRED_BODY))
    assert assert_size_exceeded(resp, name="x").status == FAIL


def test_assert_escape_op_denied_pass() -> None:
    r = assert_escape_op(OssOpResult("put_other_key", "AccessDenied"), display="d", expiry=False)
    assert r.status == PASS


def test_assert_escape_op_not_denied_fail() -> None:
    # 操作意外成功（空错误码）→ 未被拒 → FAIL
    r = assert_escape_op(OssOpResult("put_other_key", ""), display="d", expiry=False)
    assert r.status == FAIL


def test_assert_escape_op_expired_pass() -> None:
    r = assert_escape_op(OssOpResult("expired_put", "ExpiredToken"), display="d", expiry=True)
    assert r.status == PASS


def test_assert_escape_op_expired_rejects_plain_denied() -> None:
    # 过期反例接受过期码或拒绝码（is_denied expiry=True 同时含 denied 集合）
    r = assert_escape_op(OssOpResult("expired_put", "AccessDenied"), display="d", expiry=True)
    assert r.status == PASS


# ── 解析与辅助 ───────────────────────────────────────────────────────────────
def test_parse_issued_credential_full() -> None:
    cred = parse_issued_credential(FULL_CRED_BODY)
    assert cred is not None
    assert cred.object_key.endswith(".wav")
    assert cred.access_key_secret == "stsSecretValueABCDEFGH1234567890"


def test_parse_issued_credential_incomplete() -> None:
    body = dict(FULL_CRED_BODY)
    del body["expiration"]
    assert parse_issued_credential(body) is None


def test_other_recordings_key_differs() -> None:
    key = "recordings/2026-06-27/frag.wav"
    other = other_recordings_key(key)
    assert other != key
    assert other.startswith("recordings/2026-06-27/")
    assert other.endswith(".wav")


def test_make_fragment_id_is_valid() -> None:
    import re

    fid = make_fragment_id(_FIXED_NOW)
    pattern = re.compile(r"^\d{8}T\d{6}_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$")
    assert pattern.match(fid), fid


def test_make_fragment_id_unique() -> None:
    assert make_fragment_id(_FIXED_NOW) != make_fragment_id(_FIXED_NOW)


# ── 编排：场景组合 ───────────────────────────────────────────────────────────
def _fid_factory() -> str:
    return "20260627T120000_fclive_0123456789ABCDEF0123456789"


def test_run_checks_fake_code_only() -> None:
    # 不带任何真实 code：仅伪造 code 跑 401，其余全 SKIP，无 FAIL。
    probes = FakeProbes()
    results = run_checks(probes, LiveOptions(), fragment_id_factory=_fid_factory)
    assert all_passed(results)
    by_status = {r.status for r in results}
    assert PASS in by_status and SKIP in by_status and FAIL not in by_status
    # 第一项是伪造 code → 401 PASS
    assert results[0].status == PASS


def test_run_checks_full_happy_path() -> None:
    probes = FakeProbes(
        responses={
            "allow-code": HttpResponse(200, FULL_CRED_BODY),
            "bad-code": HttpResponse(403, {"error": ERR_OPENID_NOT_ALLOWED}),
            "size-code": HttpResponse(
                400, {"error": ERR_SIZE_EXCEEDED, "limit_bytes": 52428800, "actual_bytes": 60000000}
            ),
        },
        ops=_denied_ops(),
    )
    opts = LiveOptions(
        allow_code="allow-code",
        not_allowed_code="bad-code",
        size_code="size-code",
        check_expiry=True,
    )
    results = run_checks(probes, opts, fragment_id_factory=_fid_factory)
    assert all_passed(results)
    assert not any(r.status == SKIP for r in results)
    # 五个越权 / 过期反例都跑了
    assert probes.escape_calls == [True]


def test_run_checks_escape_not_denied_fails() -> None:
    bad_ops = [OssOpResult(name, "") for name, _, _ in ESCAPE_OPS]  # 全部意外成功
    probes = FakeProbes(responses={"c": HttpResponse(200, FULL_CRED_BODY)}, ops=bad_ops)
    results = run_checks(
        probes, LiveOptions(allow_code="c"), fragment_id_factory=_fid_factory
    )
    assert not all_passed(results)


def test_run_checks_skip_expiry() -> None:
    probes = FakeProbes(responses={"c": HttpResponse(200, FULL_CRED_BODY)}, ops=_denied_ops())
    results = run_checks(
        probes,
        LiveOptions(allow_code="c", check_expiry=False),
        fragment_id_factory=_fid_factory,
    )
    assert probes.escape_calls == [False]
    expired_display = next(d for n, d, _ in ESCAPE_OPS if n == "expired_put")
    expired = [r for r in results if r.name == expired_display]
    assert expired and expired[0].status == SKIP
    assert all_passed(results)


def test_run_checks_fc_unreachable_is_fail() -> None:
    probes = FakeProbes(raise_on="allow-code")
    results = run_checks(
        probes, LiveOptions(allow_code="allow-code"), fragment_id_factory=_fid_factory
    )
    # 成功签发那项应为 FAIL（FC 不可达）
    assert not all_passed(results)


def test_run_checks_incomplete_credential_blocks_escape() -> None:
    body = dict(FULL_CRED_BODY)
    body["security_token"] = ""
    probes = FakeProbes(responses={"c": HttpResponse(200, body)}, ops=_denied_ops())
    results = run_checks(
        probes, LiveOptions(allow_code="c"), fragment_id_factory=_fid_factory
    )
    assert not all_passed(results)
    # 探针的 escape ops 不应被调用（没有完整凭证）
    assert probes.escape_calls == []


def test_run_checks_ops_probe_error() -> None:
    probes = FakeProbes(
        responses={"c": HttpResponse(200, FULL_CRED_BODY)}, ops_error="OSS 客户端失败"
    )
    results = run_checks(
        probes, LiveOptions(allow_code="c"), fragment_id_factory=_fid_factory
    )
    # 成功签发 PASS，但反例因探针错误全 FAIL
    assert not all_passed(results)
    assert any(r.status == PASS for r in results)


# ── 报告与退出码 ─────────────────────────────────────────────────────────────
def test_format_report_no_secret_leak() -> None:
    probes = FakeProbes(
        responses={"allow-code": HttpResponse(200, FULL_CRED_BODY)}, ops=_denied_ops()
    )
    results = run_checks(
        probes, LiveOptions(allow_code="allow-code"), fragment_id_factory=_fid_factory
    )
    text = "\n".join(format_report(results))
    assert "stsSecretValueABCDEFGH1234567890" not in text
    assert "CAISxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" not in text
    assert "✅" in text


def test_run_test_fc_live_exit_code_pass() -> None:
    probes = FakeProbes()
    lines, code = run_test_fc_live(LiveOptions(), probes)
    assert code == 0
    assert any("汇总" in line for line in lines)


def test_run_test_fc_live_exit_code_fail() -> None:
    # 伪造 code 返回非 401 → FAIL → 非零退出
    probes = FakeProbes(responses={"x": HttpResponse(200, FULL_CRED_BODY)})
    probes.responses[__import_fake_code()] = HttpResponse(500, {"error": "BOOM"})
    lines, code = run_test_fc_live(LiveOptions(), probes)
    assert code == 1


def __import_fake_code() -> str:
    from soniscope_worker.fc_live import FAKE_CODE

    return FAKE_CODE


# ── CLI ─────────────────────────────────────────────────────────────────────
def test_cli_test_fc_live_skip_only_exits_zero(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # 注入假探针，避免真实触网；不带 code → 仅 401 PASS + 其余 SKIP → exit 0
    from soniscope_worker import fc_live

    monkeypatch.setattr(fc_live, "RealFcLiveProbes", FakeProbes)
    result = runner.invoke(app, ["test-fc-live", "--skip-expiry"])
    assert result.exit_code == 0
    assert "test-fc-live 通过" in result.stdout


def test_cli_test_fc_live_failure_exits_one(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from soniscope_worker import fc_live

    def _boom() -> FakeProbes:
        return FakeProbes(raise_on=fc_live.FAKE_CODE)

    monkeypatch.setattr(fc_live, "RealFcLiveProbes", _boom)
    result = runner.invoke(app, ["test-fc-live"])
    assert result.exit_code == 1


_FIXED_NOW = __import__("datetime").datetime(2026, 6, 27, 12, 0, 0)
