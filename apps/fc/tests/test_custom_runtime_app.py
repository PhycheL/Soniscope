"""Custom Runtime app.py entrypoint tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

FC_DIR = Path(__file__).resolve().parents[1]


class _Sink:
    def __init__(self) -> None:
        self.status = ""

    def __call__(self, status: str, headers: list[tuple[str, str]]) -> Any:
        self.status = status
        return None


def test_custom_runtime_app_delegates_to_handler(monkeypatch: Any) -> None:
    fake_handler_mod = ModuleType("handler")

    def fake_handler(environ: dict[str, Any], start_response: Any) -> list[bytes]:
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok:" + str(environ["REQUEST_METHOD"]).encode("ascii")]

    fake_handler_mod.handler = fake_handler  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "handler", fake_handler_mod)

    path = FC_DIR / "shared" / "app.py"
    spec = importlib.util.spec_from_file_location("fc_custom_runtime_app_test", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    sink = _Sink()
    body = b"".join(mod.application({"REQUEST_METHOD": "GET"}, sink))
    assert sink.status == "200 OK"
    assert body == b"ok:GET"


def test_custom_runtime_app_reads_fc_server_port(monkeypatch: Any) -> None:
    fake_handler_mod = ModuleType("handler")
    fake_handler_mod.handler = lambda _env, _start_response: []  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "handler", fake_handler_mod)
    monkeypatch.setenv("FC_SERVER_PORT", "9012")

    path = FC_DIR / "shared" / "app.py"
    spec = importlib.util.spec_from_file_location("fc_custom_runtime_app_port_test", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod._port() == 9012
