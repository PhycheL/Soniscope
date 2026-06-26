"""FC WSGI 请求解析与 JSON 响应工具（US-006）。

FC 3.0 Python Web 函数为标准 WSGI 入口。本模块提供：

* ``read_json_body`` —— 读取并解析请求体，非法 / 缺失 / 解析失败统一抛 400 ``INVALID_REQUEST``。
* ``require_fields`` —— 校验必填字段，缺失抛 400 ``INVALID_REQUEST``（列出缺失字段名）。
* ``json_response`` / ``error_response`` —— 渲染 JSON 响应。
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .errors import INVALID_REQUEST, FcHttpError

StartResponse = Callable[[str, list[tuple[str, str]]], Any]

_STATUS_LINES: dict[int, str] = {
    200: "200 OK",
    400: "400 Bad Request",
    401: "401 Unauthorized",
    403: "403 Forbidden",
    500: "500 Internal Server Error",
}


def status_line(code: int) -> str:
    """HTTP 状态码 → WSGI 状态行。"""
    return _STATUS_LINES.get(code, f"{code} Status")


def json_response(
    start_response: StartResponse, status_code: int, payload: Mapping[str, object]
) -> list[bytes]:
    """渲染 JSON 响应（UTF-8，含 Content-Length）。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        status_line(status_code),
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def error_response(start_response: StartResponse, err: FcHttpError) -> list[bytes]:
    """把 ``FcHttpError`` 渲染为对应状态码的 JSON 响应。"""
    return json_response(start_response, err.status, err.payload)


def read_json_body(environ: Mapping[str, Any]) -> dict[str, Any]:
    """从 WSGI environ 读取并解析 JSON 请求体（必须是 JSON 对象）。"""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    stream = environ.get("wsgi.input")
    raw: bytes = stream.read(length) if (stream is not None and length > 0) else b""
    if not raw:
        raise FcHttpError(400, INVALID_REQUEST, message="empty request body")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FcHttpError(400, INVALID_REQUEST, message="malformed JSON body") from exc
    if not isinstance(data, dict):
        raise FcHttpError(400, INVALID_REQUEST, message="request body must be a JSON object")
    return data


def require_fields(data: Mapping[str, Any], fields: Sequence[str]) -> None:
    """校验 ``fields`` 全部存在且非空（None / 空串视为缺失）；缺失抛 400。"""
    missing = [f for f in fields if f not in data or data[f] is None or data[f] == ""]
    if missing:
        raise FcHttpError(
            400, INVALID_REQUEST, message="missing required field(s)", missing=missing
        )
