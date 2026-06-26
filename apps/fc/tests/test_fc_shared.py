"""US-006 FC 共享模块单测（注入式 fetch，全程不触网）。"""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

import fc_shared


# ── WSGI / start_response 测试替身 ───────────────────────────────────────────
def make_environ(body: bytes, *, method: str = "POST") -> dict[str, Any]:
    """构造含 wsgi.input 的最小 WSGI environ。"""
    return {
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }


class FakeStartResponse:
    """记录 status / headers 的 start_response 替身。"""

    def __init__(self) -> None:
        self.status: str = ""
        self.headers: list[tuple[str, str]] = []

    def __call__(self, status: str, headers: list[tuple[str, str]]) -> Any:
        self.status = status
        self.headers = headers
        return None


def _ok_fetch(_url: str) -> bytes:
    return json.dumps({"openid": "OID-allowed"}).encode("utf-8")


def _make_env(*, allowlist: str = "OID-allowed") -> fc_shared.FcEnv:
    return fc_shared.load_env(
        {
            "OSS_BUCKET": "soniscope-audio",
            "OSS_REGION": "cn-beijing",
            "OSS_ENDPOINT": "oss-cn-beijing.aliyuncs.com",
            "WX_APPID": "wx3f973c7297728b0c",
            "WX_APP_SECRET": "shhh-secret",
            "OPENID_ALLOWLIST": allowlist,
        }
    )


# ── errors ───────────────────────────────────────────────────────────────────
def test_fc_http_error_payload() -> None:
    err = fc_shared.FcHttpError(400, fc_shared.INVALID_REQUEST, message="bad", missing=["x"])
    assert err.status == 400
    assert err.payload == {"error": "INVALID_REQUEST", "missing": ["x"], "message": "bad"}


def test_fc_config_error_lists_missing_names_only() -> None:
    err = fc_shared.FcConfigError(["WX_APPID", "OSS_BUCKET"])
    assert err.missing == ["WX_APPID", "OSS_BUCKET"]
    assert "WX_APPID" in str(err) and "OSS_BUCKET" in str(err)


# ── http ─────────────────────────────────────────────────────────────────────
def test_read_json_body_valid() -> None:
    data = fc_shared.read_json_body(make_environ(b'{"a": 1}'))
    assert data == {"a": 1}


def test_read_json_body_empty_is_400() -> None:
    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.read_json_body(make_environ(b""))
    assert ei.value.status == 400
    assert ei.value.error_code == fc_shared.INVALID_REQUEST


def test_read_json_body_malformed_is_400() -> None:
    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.read_json_body(make_environ(b"{not json"))
    assert ei.value.status == 400


def test_read_json_body_non_object_is_400() -> None:
    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.read_json_body(make_environ(b"[1, 2, 3]"))
    assert ei.value.status == 400


def test_require_fields_missing() -> None:
    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.require_fields({"code": "c"}, ("code", "fragment_id", "size"))
    assert ei.value.status == 400
    assert ei.value.payload["missing"] == ["fragment_id", "size"]


def test_require_fields_empty_string_counts_as_missing() -> None:
    with pytest.raises(fc_shared.FcHttpError):
        fc_shared.require_fields({"code": ""}, ("code",))


def test_require_fields_zero_is_present() -> None:
    fc_shared.require_fields({"size": 0}, ("size",))  # 不抛异常


def test_json_response_sets_status_and_content_length() -> None:
    sr = FakeStartResponse()
    body = fc_shared.json_response(sr, 200, {"ok": True})
    assert sr.status == "200 OK"
    headers = dict(sr.headers)
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Content-Length"] == str(len(body[0]))
    assert json.loads(body[0]) == {"ok": True}


def test_error_response_uses_error_status() -> None:
    sr = FakeStartResponse()
    body = fc_shared.error_response(
        sr, fc_shared.FcHttpError(403, fc_shared.OPENID_NOT_ALLOWED)
    )
    assert sr.status == "403 Forbidden"
    assert json.loads(body[0]) == {"error": "OPENID_NOT_ALLOWED"}


# ── env ──────────────────────────────────────────────────────────────────────
def test_load_env_success() -> None:
    env = _make_env(allowlist="o1, o2 ,, o3")
    assert env.oss_bucket == "soniscope-audio"
    assert env.openid_allowlist == ("o1", "o2", "o3")


def test_load_env_missing_lists_all_at_once() -> None:
    with pytest.raises(fc_shared.FcConfigError) as ei:
        fc_shared.load_env({"OSS_BUCKET": "b"})
    assert set(ei.value.missing) == {
        "OSS_REGION",
        "OSS_ENDPOINT",
        "WX_APPID",
        "WX_APP_SECRET",
        "OPENID_ALLOWLIST",
    }


def test_parse_allowlist_strips_and_drops_empty() -> None:
    assert fc_shared.parse_allowlist(" a , ,b ,") == ("a", "b")


# ── wechat ───────────────────────────────────────────────────────────────────
def test_code_to_openid_success() -> None:
    openid = fc_shared.code_to_openid("c", "appid", "secret", fetch=_ok_fetch)
    assert openid == "OID-allowed"


def test_code_to_openid_errcode_is_401() -> None:
    def fetch(_url: str) -> bytes:
        return json.dumps({"errcode": 40029, "errmsg": "invalid code"}).encode("utf-8")

    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.code_to_openid("bad", "appid", "secret", fetch=fetch)
    assert ei.value.status == 401
    assert ei.value.error_code == fc_shared.INVALID_CODE


def test_code_to_openid_missing_openid_is_401() -> None:
    def fetch(_url: str) -> bytes:
        return json.dumps({"session_key": "x"}).encode("utf-8")

    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.code_to_openid("c", "appid", "secret", fetch=fetch)
    assert ei.value.status == 401


def test_code_to_openid_fetch_failure_is_401() -> None:
    def fetch(_url: str) -> bytes:
        raise OSError("network down")

    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.code_to_openid("c", "appid", "secret", fetch=fetch)
    assert ei.value.status == 401


# ── audit（脱敏日志）────────────────────────────────────────────────────────
def test_hash_openid_is_stable_and_not_plaintext() -> None:
    h = fc_shared.hash_openid("openid-123")
    assert h == fc_shared.hash_openid("openid-123")
    assert "openid-123" not in h
    assert len(h) == 16


def test_is_sensitive() -> None:
    assert fc_shared.is_sensitive("code")
    assert fc_shared.is_sensitive("access_key_secret")
    assert fc_shared.is_sensitive("security_token")
    assert fc_shared.is_sensitive("x-oss-meta-sha256") is False
    assert fc_shared.is_sensitive("fragment_id") is False


def test_log_event_redacts_secrets_and_omits_none() -> None:
    line = fc_shared.log_event(
        "issue_credential_authorized",
        openid_hash="abcd1234abcd1234",
        fragment_id="20260627T010101_dev01_01ABC",
        code="SECRET-CODE",
        session_key="SECRET-SK",
        access_key_secret="SECRET-AK",
        security_token="SECRET-TOKEN",
        decision="AUTHORIZED",
        elapsed_ms=12.3,
        nothing=None,
    )
    for leaked in ("SECRET-CODE", "SECRET-SK", "SECRET-AK", "SECRET-TOKEN"):
        assert leaked not in line
    assert "***REDACTED***" in line
    assert "openid_hash=abcd1234abcd1234" in line
    assert "fragment_id=20260627T010101_dev01_01ABC" in line
    assert "decision=AUTHORIZED" in line
    assert "nothing=" not in line


# ── auth（端到端编排）────────────────────────────────────────────────────────
def test_authorize_request_happy() -> None:
    body = json.dumps({"code": "c", "fragment_id": "f1", "size": 100}).encode("utf-8")
    ctx = fc_shared.authorize_request(
        make_environ(body), _make_env(), fetch=_ok_fetch, extra_fields=("fragment_id", "size")
    )
    assert ctx.openid == "OID-allowed"
    assert ctx.openid_hash == fc_shared.hash_openid("OID-allowed")
    assert ctx.body["fragment_id"] == "f1"


def test_authorize_request_missing_field_is_400() -> None:
    body = json.dumps({"code": "c"}).encode("utf-8")
    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.authorize_request(
            make_environ(body), _make_env(), fetch=_ok_fetch, extra_fields=("fragment_id",)
        )
    assert ei.value.status == 400


def test_authorize_request_bad_code_is_401() -> None:
    def fetch(_url: str) -> bytes:
        return json.dumps({"errcode": 40029}).encode("utf-8")

    body = json.dumps({"code": "bad", "fragment_id": "f1"}).encode("utf-8")
    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.authorize_request(
            make_environ(body), _make_env(), fetch=fetch, extra_fields=("fragment_id",)
        )
    assert ei.value.status == 401


def test_authorize_request_not_in_allowlist_is_403() -> None:
    body = json.dumps({"code": "c", "fragment_id": "f1"}).encode("utf-8")
    with pytest.raises(fc_shared.FcHttpError) as ei:
        fc_shared.authorize_request(
            make_environ(body),
            _make_env(allowlist="someone-else"),
            fetch=_ok_fetch,
            extra_fields=("fragment_id",),
        )
    assert ei.value.status == 403
    assert ei.value.error_code == fc_shared.OPENID_NOT_ALLOWED


def test_check_allowlist() -> None:
    fc_shared.check_allowlist("a", ("a", "b"))  # 不抛异常
    with pytest.raises(fc_shared.FcHttpError):
        fc_shared.check_allowlist("c", ("a", "b"))
