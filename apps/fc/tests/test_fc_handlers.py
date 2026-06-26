"""US-006 FC handler 集成测试：两个函数都导入并使用 fc_shared（AC#6）。

handler.py 不被 mypy 检查（两文件同名），故用 importlib 以唯一模块名动态加载，
验证存活探针、缺环境变量、鉴权失败与鉴权通过四条路径。
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
REQUIRED_ENV = {
    "OSS_BUCKET": "soniscope-audio",
    "OSS_REGION": "cn-beijing",
    "OSS_ENDPOINT": "oss-cn-beijing.aliyuncs.com",
    "WX_APPID": "wx3f973c7297728b0c",
    "WX_APP_SECRET": "shhh-secret",
    "OPENID_ALLOWLIST": "OID-allowed",
}

# (云端函数名, 代码目录, POST 必填业务字段)
HANDLERS = [
    ("issue-credential", "issue_credential", "size"),
    ("verify-upload", "verify_upload", "expected_size"),
]


def _load_handler(source_dir: str) -> ModuleType:
    path = FC_DIR / source_dir / "handler.py"
    spec = importlib.util.spec_from_file_location(f"fc_handler_{source_dir}", path)
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
    handler = mod.handler
    result = handler(environ, sink)
    body = b"".join(result)
    return sink.status, json.loads(body)


@pytest.mark.parametrize(("function", "source_dir", "_field"), HANDLERS)
def test_handler_imports_fc_shared(function: str, source_dir: str, _field: str) -> None:
    mod = _load_handler(source_dir)
    assert mod.fc_shared is fc_shared
    assert callable(mod.handler)


@pytest.mark.parametrize(("function", "source_dir", "_field"), HANDLERS)
def test_handler_get_is_health_probe(function: str, source_dir: str, _field: str) -> None:
    mod = _load_handler(source_dir)
    status, payload = _call(mod, _environ("GET"))
    assert status == "200 OK"
    assert payload["function"] == function
    assert payload["status"] == "ok"


@pytest.mark.parametrize(("function", "source_dir", "field"), HANDLERS)
def test_handler_missing_env_is_500(
    function: str, source_dir: str, field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in REQUIRED_ENV:
        monkeypatch.delenv(key, raising=False)
    mod = _load_handler(source_dir)
    body = json.dumps({"code": "c", "fragment_id": "f1", field: 100}).encode("utf-8")
    status, payload = _call(mod, _environ("POST", body))
    assert status == "500 Internal Server Error"
    assert payload["error"] == fc_shared.SERVER_MISCONFIGURED
    assert "WX_APPID" in payload["missing"]


@pytest.mark.parametrize(("function", "source_dir", "field"), HANDLERS)
def test_handler_invalid_body_is_400(
    function: str, source_dir: str, field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, val in REQUIRED_ENV.items():
        monkeypatch.setenv(key, val)
    mod = _load_handler(source_dir)
    status, payload = _call(mod, _environ("POST", b""))
    assert status == "400 Bad Request"
    assert payload["error"] == fc_shared.INVALID_REQUEST


@pytest.mark.parametrize(("function", "source_dir", "field"), HANDLERS)
def test_handler_not_in_allowlist_is_403(
    function: str, source_dir: str, field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = {**REQUIRED_ENV, "OPENID_ALLOWLIST": "someone-else"}
    for key, val in env.items():
        monkeypatch.setenv(key, val)

    def fake_code_to_openid(code: str, appid: str, secret: str, **_kw: Any) -> str:
        return "OID-allowed"

    monkeypatch.setattr(fc_shared.wechat, "code_to_openid", fake_code_to_openid)
    mod = _load_handler(source_dir)
    body = json.dumps({"code": "c", "fragment_id": "f1", field: 100}).encode("utf-8")
    status, payload = _call(mod, _environ("POST", body))
    assert status == "403 Forbidden"
    assert payload["error"] == fc_shared.OPENID_NOT_ALLOWED


@pytest.mark.parametrize(("function", "source_dir", "field"), HANDLERS)
def test_handler_authorized_path(
    function: str, source_dir: str, field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, val in REQUIRED_ENV.items():
        monkeypatch.setenv(key, val)

    def fake_code_to_openid(code: str, appid: str, secret: str, **_kw: Any) -> str:
        return "OID-allowed"

    monkeypatch.setattr(fc_shared.wechat, "code_to_openid", fake_code_to_openid)
    mod = _load_handler(source_dir)
    body = json.dumps({"code": "c", "fragment_id": "f1", field: 100}).encode("utf-8")
    status, payload = _call(mod, _environ("POST", body))
    assert status == "200 OK"
    assert payload["status"] == "authorized"
