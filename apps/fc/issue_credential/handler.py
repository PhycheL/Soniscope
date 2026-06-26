"""FC 3.0 顶级 Web 函数 ``issue-credential``（US-006 接入 fc_shared 共享鉴权）。

本处理器复用 ``fc_shared`` 完成：JSON 请求校验、微信 code 换 openid、OPENID_ALLOWLIST
鉴权与脱敏结构化日志。真正的 **STS 单 object key 凭证签发** 逻辑在 US-007 实现——鉴权
通过后当前返回占位响应，US-007 把该分支替换为真实签发。

云端函数名为 kebab-case ``issue-credential``；代码目录用 snake_case ``issue_credential``。
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
    """WSGI 入口：GET 走存活探针；POST 走共享鉴权 +（US-007）STS 签发。"""
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    if method != "POST":
        # deploy-fc 存活验证用 GET，返回 200 健康响应。
        return fc_shared.json_response(
            start_response, 200, {"function": "issue-credential", "status": "ok"}
        )

    started = time.monotonic()
    try:
        env = fc_shared.load_env(os.environ)
        ctx = fc_shared.authorize_request(
            environ, env, extra_fields=("fragment_id", "size")
        )
    except fc_shared.FcConfigError as exc:
        fc_shared.log_event(
            "issue_credential_misconfigured",
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
            "issue_credential_denied",
            decision=exc.error_code,
            elapsed_ms=_elapsed_ms(started),
        )
        return fc_shared.error_response(start_response, exc)

    fc_shared.log_event(
        "issue_credential_authorized",
        openid_hash=ctx.openid_hash,
        fragment_id=ctx.body.get("fragment_id"),
        decision="AUTHORIZED",
        elapsed_ms=_elapsed_ms(started),
    )
    # STS 单 object key 凭证签发在 US-007 实现。
    return fc_shared.json_response(
        start_response, 200, {"status": "authorized", "note": "STS issuance lands in US-007"}
    )
