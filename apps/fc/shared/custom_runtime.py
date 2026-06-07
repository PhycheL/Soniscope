"""Small stdlib HTTP adapter for Alibaba Cloud FC custom runtime.

The deployed FC functions are configured with start command ``python3 app.py``.
This module lets the existing handler-style code run behind that command
without changing FC runtime, trigger, or environment-variable configuration.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlsplit

HandlerFn = Callable[[dict[str, Any], object | None], dict[str, Any]]


def serve(handler: HandlerFn) -> None:
    """Start a custom-runtime HTTP server for *handler*."""
    port = int(os.environ.get("FC_SERVER_PORT") or os.environ.get("PORT") or "9000")

    class FCRequestHandler(_FCRequestHandler):
        fc_handler = staticmethod(handler)

    server = ThreadingHTTPServer(("0.0.0.0", port), FCRequestHandler)
    server.serve_forever()


class _FCRequestHandler(BaseHTTPRequestHandler):
    """Translate an HTTP request into the repo's FC handler event shape."""

    fc_handler: HandlerFn
    server_version = "SoniScopeFC/1.0"

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch()

    def log_message(self, fmt: str, *args: object) -> None:
        # Keep stdout/stderr free of request bodies and secrets.
        return

    def _dispatch(self) -> None:
        body = self._read_body()
        parsed_path = urlsplit(self.path)
        event = {
            "path": parsed_path.path or "/",
            "httpMethod": self.command,
            "method": self.command,
            "headers": dict(self.headers.items()),
            "queryString": parsed_path.query,
            "body": body,
        }

        try:
            result = self.fc_handler(event, None)
        except Exception:
            result = {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "INTERNAL_ERROR"}),
            }

        status_code = int(result.get("statusCode", 200))
        headers = result.get("headers", {})
        response_body = _body_to_bytes(result.get("body", ""))

        self.send_response(status_code)
        sent_content_type = False
        if isinstance(headers, dict):
            for name, value in headers.items():
                lower_name = str(name).lower()
                if lower_name in {"content-length", "transfer-encoding"}:
                    continue
                if lower_name == "content-type":
                    sent_content_type = True
                self.send_header(str(name), str(value))
        if not sent_content_type:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def _read_body(self) -> str:
        content_length = self.headers.get("Content-Length", "")
        try:
            length = int(content_length) if content_length else 0
        except ValueError:
            length = 0
        if length <= 0:
            return ""
        return self.rfile.read(length).decode("utf-8")


def _body_to_bytes(body: object) -> bytes:
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
