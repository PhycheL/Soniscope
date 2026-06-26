"""US-009 verify-upload handler 集成测试：HeadObject 上传确认与鉴权安全反例。

handler.py 不被 mypy 检查（两 handler 同名），用 importlib 以唯一模块名动态加载；
HeadObject 执行器通过 monkeypatch ``fc_shared.head.get_header`` 注入假实现，不触网。
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
from fc_shared import head

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
VERIFY_ENV = {"ALIYUN_AK_ID": "ak-id", "ALIYUN_AK_SECRET": "ak-secret"}


def _load_handler() -> ModuleType:
    path = FC_DIR / "verify_upload" / "handler.py"
    spec = importlib.util.spec_from_file_location("fc_handler_verify_upload", path)
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


class _FakeHeader:
    """记录入参的假 HeadObject 执行器，返回预置的 ObjectHead（或抛异常）。"""

    def __init__(self, result: head.ObjectHead | None = None, *, boom: Exception | None = None):
        self.result = result
        self.boom = boom
        self.calls: list[dict[str, Any]] = []

    def head_object(self, **kwargs: Any) -> head.ObjectHead:
        self.calls.append(kwargs)
        if self.boom is not None:
            raise self.boom
        assert self.result is not None
        return self.result


def _allow_openid(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(code: str, appid: str, secret: str, **_kw: Any) -> str:
        return "OID-allowed"

    monkeypatch.setattr(fc_shared.wechat, "code_to_openid", fake)


def _set_full_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, val in {**SHARED_ENV, **VERIFY_ENV}.items():
        monkeypatch.setenv(key, val)


def _inject_header(monkeypatch: pytest.MonkeyPatch, fake: _FakeHeader) -> None:
    monkeypatch.setattr(fc_shared.head, "get_header", lambda: fake)


def _body(**extra: Any) -> bytes:
    payload = {"code": "c", "fragment_id": FRAGMENT_ID, "expected_size": 12345, **extra}
    return json.dumps(payload).encode()


def test_verified_true_when_object_present_and_size_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)
    fake = _FakeHeader(
        head.ObjectHead(exists=True, content_length=12345, etag='"E"', last_modified="LM")
    )
    _inject_header(monkeypatch, fake)
    mod = _load_handler()
    status, payload = _call(mod, _environ("POST", _body()))
    assert status == "200 OK"
    assert payload == {"verified": True, "etag": '"E"', "size": 12345, "last_modified": "LM"}
    # HeadObject 被以解析出的单 object key 调用。
    assert fake.calls[0]["object_key"] == OBJECT_KEY
    assert fake.calls[0]["bucket"] == "soniscope-audio"


def test_object_not_found_returns_verified_false(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)
    _inject_header(monkeypatch, _FakeHeader(head.ObjectHead(exists=False)))
    mod = _load_handler()
    status, payload = _call(mod, _environ("POST", _body()))
    assert status == "200 OK"
    assert payload == {"verified": False, "reason": fc_shared.OBJECT_NOT_FOUND}


def test_size_mismatch_returns_actual_size(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)
    _inject_header(
        monkeypatch, _FakeHeader(head.ObjectHead(exists=True, content_length=100))
    )
    mod = _load_handler()
    status, payload = _call(mod, _environ("POST", _body(expected_size=200)))
    assert status == "200 OK"
    assert payload == {
        "verified": False,
        "reason": fc_shared.SIZE_MISMATCH,
        "actual_size": 100,
    }


def test_invalid_fragment_id_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)
    fake = _FakeHeader(head.ObjectHead(exists=True, content_length=1))
    _inject_header(monkeypatch, fake)
    mod = _load_handler()
    status, payload = _call(mod, _environ("POST", _body(fragment_id="bogus")))
    assert status == "400 Bad Request"
    assert payload["error"] == fc_shared.INVALID_REQUEST
    assert fake.calls == []  # 非法 fragment_id 不应触达 HeadObject


def test_missing_verify_env_is_500(monkeypatch: pytest.MonkeyPatch) -> None:
    # 共享 env 齐全、openid 放行，但缺 ALIYUN_AK_* → 500 SERVER_MISCONFIGURED。
    for key, val in SHARED_ENV.items():
        monkeypatch.setenv(key, val)
    for key in VERIFY_ENV:
        monkeypatch.delenv(key, raising=False)
    _allow_openid(monkeypatch)
    mod = _load_handler()
    status, payload = _call(mod, _environ("POST", _body()))
    assert status == "500 Internal Server Error"
    assert payload["error"] == fc_shared.SERVER_MISCONFIGURED
    assert "ALIYUN_AK_SECRET" in payload["missing"]


def test_forged_code_gets_no_object_info(monkeypatch: pytest.MonkeyPatch) -> None:
    # 伪造 code → 401，绝不暴露对象存在性 / 大小（安全红线）。
    _set_full_env(monkeypatch)

    def reject(code: str, appid: str, secret: str, **_kw: Any) -> str:
        raise fc_shared.FcHttpError(401, fc_shared.INVALID_CODE, message="bad code")

    monkeypatch.setattr(fc_shared.wechat, "code_to_openid", reject)
    fake = _FakeHeader(head.ObjectHead(exists=True, content_length=12345))
    _inject_header(monkeypatch, fake)
    mod = _load_handler()
    status, payload = _call(mod, _environ("POST", _body()))
    assert status == "401 Unauthorized"
    assert payload["error"] == fc_shared.INVALID_CODE
    assert "verified" not in payload
    assert "size" not in payload
    assert fake.calls == []


def test_head_failure_is_500_without_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_env(monkeypatch)
    _allow_openid(monkeypatch)
    fake = _FakeHeader(boom=RuntimeError("ak-secret leaked-here"))
    _inject_header(monkeypatch, fake)
    mod = _load_handler()
    status, payload = _call(mod, _environ("POST", _body()))
    assert status == "500 Internal Server Error"
    assert payload == {"error": fc_shared.HEAD_OBJECT_FAILED}
    assert "ak-secret" not in json.dumps(payload)
