"""FC 3.0 顶级 Web 函数 ``verify-upload``（US-006 接入 fc_shared 共享鉴权）。

本处理器复用 ``fc_shared`` 完成：JSON 请求校验、微信 code 换 openid、OPENID_ALLOWLIST
鉴权与脱敏结构化日志，鉴权逻辑与 ``issue-credential`` 完全一致。真正的 **OSS HeadObject
上传确认** 逻辑在 US-009 实现——鉴权通过后当前返回占位响应，US-009 把该分支替换为真实校验。

云端函数名为 kebab-case ``verify-upload``；代码目录用 snake_case ``verify_upload``。
``fc_shared`` 由 ``make deploy-fc`` 打包脚本 vendoring 到函数包根目录
（见 ``soniscope_worker.fc_deploy.package_function``）。
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterable
from typing import Any

import fc_shared

StartResponse = Callable[[str, list[tuple[str, str]]], Any]


def _elapsed_ms(started: float) -> float:
    return round((time.monotonic() - started) * 1000, 1)


def handler(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
    """WSGI 入口：GET 走存活探针；POST 走共享鉴权 +（US-009）HeadObject 校验。"""
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    if method != "POST":
        # deploy-fc 存活验证用 GET，返回 200 健康响应。
        return fc_shared.json_response(
            start_response, 200, {"function": "verify-upload", "status": "ok"}
        )

    started = time.monotonic()
    try:
        env = fc_shared.load_env(os.environ)
        ctx = fc_shared.authorize_request(
            environ, env, extra_fields=("fragment_id", "expected_size")
        )
    except fc_shared.FcConfigError as exc:
        fc_shared.log_event(
            "verify_upload_misconfigured",
            decision=fc_shared.SERVER_MISCONFIGURED,
            missing=",".join(exc.missing),
            elapsed_ms=_elapsed_ms(started),
        )
        return fc_shared.json_response(
            start_response,
            500,
            {"error": fc_shared.SERVER_MISCONFIGURED, "missing": exc.missing},
        )
    except fc_shared.FcHttpError as exc:
        fc_shared.log_event(
            "verify_upload_denied",
            decision=exc.error_code,
            elapsed_ms=_elapsed_ms(started),
        )
        return fc_shared.error_response(start_response, exc)

    fc_shared.log_event(
        "verify_upload_authorized",
        openid_hash=ctx.openid_hash,
        fragment_id=ctx.body.get("fragment_id"),
        decision="AUTHORIZED",
        elapsed_ms=_elapsed_ms(started),
    )
    # OSS HeadObject 上传确认在 US-009 实现。
    return fc_shared.json_response(
        start_response, 200, {"status": "authorized", "note": "HeadObject verify lands in US-009"}
    )
