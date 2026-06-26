"""FC 3.0 顶级 Web 函数 ``issue-credential``（US-007 实现 STS 单 object key 签发）。

流程（tech-spec §4.1）：
1. 共享鉴权（fc_shared）：JSON 校验 → 微信 code 换 openid → OPENID_ALLOWLIST。
2. 由 fragment_id 解析 object key ``recordings/<YYYY-MM-DD>/<fragment_id>.wav``。
3. size 超过 MAX_UPLOAD_BYTES → 400 SIZE_EXCEEDED。
4. AssumeRole 签发仅允许 ``oss:PutObject`` 到该单 key、有效期 ≤ 900s 的 STS 凭证。

公网匿名 / 伪造 code 调用在第 1 步即 401/403，拿不到任何 STS（安全红线，AC#7）。
长期 AK 与 STS secret 绝不进日志（audit.is_sensitive 兜底）。

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
        ctx = fc_shared.authorize_request(environ, env, extra_fields=("fragment_id", "size"))
        # 鉴权通过后再加载 STS 专属配置并做 size / object_key 校验。
        sts_env = fc_shared.load_sts_env(os.environ)
        size = fc_shared.parse_size(ctx.body.get("size"))
        fc_shared.check_size(size, sts_env.max_upload_bytes)
        object_key = fc_shared.object_key_for(str(ctx.body["fragment_id"]))
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

    try:
        issuer = fc_shared.sts.get_issuer()
        cred = issuer.assume_role(
            ak_id=sts_env.ak_id,
            ak_secret=sts_env.ak_secret,
            role_arn=sts_env.ram_role_arn,
            region=env.oss_region,
            policy=fc_shared.single_key_policy(env.oss_bucket, object_key),
            duration_seconds=fc_shared.STS_MAX_DURATION_SECONDS,
            session_name=fc_shared.sts.ROLE_SESSION_NAME,
        )
    except Exception as exc:  # noqa: BLE001 - 任何签发失败统一 500，不泄漏明文
        fc_shared.log_event(
            "issue_credential_sts_failed",
            openid_hash=ctx.openid_hash,
            object_key=object_key,
            decision=fc_shared.STS_ISSUE_FAILED,
            reason=type(exc).__name__,
            elapsed_ms=_elapsed_ms(started),
        )
        return fc_shared.json_response(
            start_response, 500, {"error": fc_shared.STS_ISSUE_FAILED}
        )

    fc_shared.log_event(
        "issue_credential_issued",
        openid_hash=ctx.openid_hash,
        fragment_id=ctx.body.get("fragment_id"),
        object_key=object_key,
        size=size,
        decision="ISSUED",
        elapsed_ms=_elapsed_ms(started),
    )
    return fc_shared.json_response(
        start_response,
        200,
        fc_shared.credential_response(
            cred, bucket=env.oss_bucket, endpoint=env.oss_endpoint, object_key=object_key
        ),
    )
