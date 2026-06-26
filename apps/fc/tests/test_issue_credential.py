"""US-007 issue-credential handler 集成测试：STS 单 key 签发与安全反例。

handler.py 不被 mypy 检查（两 handler 同名），用 importlib 以唯一模块名动态加载；
STS 签发器通过 monkeypatch ``fc_shared.sts.get_issuer`` 注入假实现，不触网。
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import fc_shared

FC_DIR = Path(__file__).resolve().parents[1]  # apps/fc
FRAGMENT_ID = "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE"
OBJECT_KEY = "recordings/2026-05-26/20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav"

SHARED_ENV = {
    "OSS_BUCKET": "soniscope-audio",
    "OSS_REGION": "cn-beijing",
    "OSS_ENDPOINT": "oss-cn-beijing.aliyuncs.com",
    "WX_APPID": "wx3f973c7297728b0c",
    "WX_APP_SECRET": "shhh-secret",
    "OPENID_ALLOWLIST": "OID-allowed",
}
STS_ENV = {
    "RAM_ROLE_ARN": "acs:ram::1633875501759333:role/soniscope-uploader-role",
    "ALIYUN_AK_ID": "ak-id",
    "ALIYUN_AK_SECRET": "ak-secret",
}


def _load_handler() -> ModuleType:
    path = FC_DIR / "issue_credential" / "handler.py"
    spec = importlib.util.spec_from_file_location("fc_handler_issue_credential", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Sink:
    def __init__(self) -> None:
        self.status = ""

    def __call__(self, status: str, headers: list[tuple[str, str]]) -> Any:
        self.status = status
        return None


def _environ(method: str, body: bytes = b"") -> dict[str, Any]:
    return {
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }


def _call(mod: ModuleType, environ: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    sink = _Sink()
    body = b"".join(mod.handler(environ, sink))
    return sink.status, json.loads(body)


class _FakeIssuer:
    """记录入参的假 STS 签发器，返回固定临时凭证。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def assume_role(self, **kwargs: Any) -> fc_shared.StsCredential:
        self.calls.append(kwargs)
        return fc_shared.StsCredential(
            access_key_id="STS.fakeid",
            access_key_secret="fake-secret",
            security_token="fake-token",
            expiration="2026-05-26T15:03:00Z",
        )


def _allow_openid(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(code: str, appid: str, secret: str, **_kw: Any) -> str:
        return "OID-allowed"

    monkeypatch.setattr(fc_shared.wechat, "code_to_openid", fake)


def _set_full_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, val in {**SHARED_ENV, **STS_ENV}.items():
        monkeypatch.setenv(key, val)


def test_issue_success_returns_full_sts(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)
    fake = _FakeIssuer()
    monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: fake)
    mod = _load_handler()
    body = json.dumps({"code": "c", "fragment_id": FRAGMENT_ID, "size": 10_000_000}).encode()
    status, payload = _call(mod, _environ("POST", body))
    assert status == "200 OK"
    assert set(payload) == {
        "access_key_id",
        "access_key_secret",
        "security_token",
        "expiration",
        "bucket",
        "endpoint",
        "object_key",
    }
    assert payload["object_key"] == OBJECT_KEY
    assert payload["bucket"] == "soniscope-audio"
    assert payload["endpoint"] == "oss-cn-beijing.aliyuncs.com"


def test_issue_passes_single_key_policy_and_bounded_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)
    fake = _FakeIssuer()
    monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: fake)
    mod = _load_handler()
    body = json.dumps({"code": "c", "fragment_id": FRAGMENT_ID, "size": 100}).encode()
    _call(mod, _environ("POST", body))
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["duration_seconds"] <= 900
    resource = call["policy"]["Statement"][0]["Resource"][0]
    assert resource == f"acs:oss:*:*:soniscope-audio/{OBJECT_KEY}"
    assert "recordings/*" not in resource


def test_size_exceeded_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "52428800")
    _allow_openid(monkeypatch)
    fake = _FakeIssuer()
    monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: fake)
    mod = _load_handler()
    body = json.dumps({"code": "c", "fragment_id": FRAGMENT_ID, "size": 60_000_000}).encode()
    status, payload = _call(mod, _environ("POST", body))
    assert status == "400 Bad Request"
    assert payload["error"] == fc_shared.SIZE_EXCEEDED
    assert payload["limit_bytes"] == 52428800
    assert payload["actual_bytes"] == 60_000_000
    assert fake.calls == []  # 超限时不应签发


def test_invalid_fragment_id_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)
    monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: _FakeIssuer())
    mod = _load_handler()
    body = json.dumps({"code": "c", "fragment_id": "bogus", "size": 100}).encode()
    status, payload = _call(mod, _environ("POST", body))
    assert status == "400 Bad Request"
    assert payload["error"] == fc_shared.INVALID_REQUEST


def test_missing_sts_env_is_500(monkeypatch: pytest.MonkeyPatch) -> None:
    # 共享 env 齐全、openid 放行，但缺 RAM_ROLE_ARN 等 → 500 SERVER_MISCONFIGURED。
    for key, val in SHARED_ENV.items():
        monkeypatch.setenv(key, val)
    for key in STS_ENV:
        monkeypatch.delenv(key, raising=False)
    _allow_openid(monkeypatch)
    mod = _load_handler()
    body = json.dumps({"code": "c", "fragment_id": FRAGMENT_ID, "size": 100}).encode()
    status, payload = _call(mod, _environ("POST", body))
    assert status == "500 Internal Server Error"
    assert payload["error"] == fc_shared.SERVER_MISCONFIGURED
    assert "RAM_ROLE_ARN" in payload["missing"]


def test_forged_code_gets_no_sts(monkeypatch: pytest.MonkeyPatch) -> None:
    # 伪造 code：jscode2session 失败 → 401，绝不返回任何 STS 字段（AC#7）。
    _set_full_env(monkeypatch)

    def reject(code: str, appid: str, secret: str, **_kw: Any) -> str:
        raise fc_shared.FcHttpError(401, fc_shared.INVALID_CODE, message="bad code")

    monkeypatch.setattr(fc_shared.wechat, "code_to_openid", reject)
    fake = _FakeIssuer()
    monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: fake)
    mod = _load_handler()
    body = json.dumps({"code": "forged", "fragment_id": FRAGMENT_ID, "size": 100}).encode()
    status, payload = _call(mod, _environ("POST", body))
    assert status == "401 Unauthorized"
    assert payload["error"] == fc_shared.INVALID_CODE
    assert "access_key_id" not in payload
    assert "security_token" not in payload
    assert fake.calls == []


def test_missing_code_gets_no_sts(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    fake = _FakeIssuer()
    monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: fake)
    mod = _load_handler()
    body = json.dumps({"fragment_id": FRAGMENT_ID, "size": 100}).encode()
    status, payload = _call(mod, _environ("POST", body))
    assert status == "400 Bad Request"
    assert payload["error"] == fc_shared.INVALID_REQUEST
    assert "access_key_id" not in payload
    assert fake.calls == []


def test_issuer_failure_is_500_without_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)

    class _Boom:
        def assume_role(self, **kwargs: Any) -> fc_shared.StsCredential:
            raise RuntimeError("ak-secret leaked-here")  # 异常文本含敏感词

    monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: _Boom())
    mod = _load_handler()
    body = json.dumps({"code": "c", "fragment_id": FRAGMENT_ID, "size": 100}).encode()
    status, payload = _call(mod, _environ("POST", body))
    assert status == "500 Internal Server Error"
    assert payload == {"error": fc_shared.STS_ISSUE_FAILED}
    assert "ak-secret" not in json.dumps(payload)
