"""FC 3.0 顶级 Web 函数 ``verify-upload``（US-009 实现 HeadObject 上传确认）。

流程（tech-spec §4.2）：
1. 共享鉴权（fc_shared）：JSON 校验 → 微信 code 换 openid → OPENID_ALLOWLIST，与
   ``issue-credential`` 完全一致。
2. 由 fragment_id 解析 object key ``recordings/<YYYY-MM-DD>/<fragment_id>.wav``。
3. 用 FC 子账号 AK 对该 key 执行 OSS HeadObject。
4. 按对象存在性与 Content-Length 返回 verified / OBJECT_NOT_FOUND / SIZE_MISMATCH。

HeadObject 只能校验对象存在性与大小（无法校验 sha256，sha256 由离线脚本负责）。
公网匿名 / 伪造 code 调用在第 1 步即 401/403，拿不到任何对象信息（安全红线）。

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
        # 鉴权通过后再加载 OSS 读凭证并解析 object key（invalid-body/allowlist 先返回）。
        verify_env = fc_shared.load_verify_env(os.environ)
        expected_size = fc_shared.parse_size(ctx.body.get("expected_size"))
        object_key = fc_shared.object_key_for(str(ctx.body["fragment_id"]))
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

    try:
        header = fc_shared.head.get_header()
        head = header.head_object(
            bucket=env.oss_bucket,
            region=env.oss_region,
            endpoint=env.oss_endpoint,
            ak_id=verify_env.ak_id,
            ak_secret=verify_env.ak_secret,
            object_key=object_key,
        )
    except Exception as exc:  # noqa: BLE001 - 任何 HeadObject 失败统一 500，不泄漏明文
        fc_shared.log_event(
            "verify_upload_head_failed",
            openid_hash=ctx.openid_hash,
            object_key=object_key,
            decision=fc_shared.HEAD_OBJECT_FAILED,
            reason=type(exc).__name__,
            elapsed_ms=_elapsed_ms(started),
        )
        return fc_shared.json_response(
            start_response, 500, {"error": fc_shared.HEAD_OBJECT_FAILED}
        )

    result = fc_shared.verify_upload_result(head, expected_size)
    fc_shared.log_event(
        "verify_upload_verified",
        openid_hash=ctx.openid_hash,
        fragment_id=ctx.body.get("fragment_id"),
        verified=result["verified"],
        reason=result.get("reason"),
        decision="VERIFIED" if result["verified"] else "NOT_VERIFIED",
        elapsed_ms=_elapsed_ms(started),
    )
    return fc_shared.json_response(start_response, 200, result)
