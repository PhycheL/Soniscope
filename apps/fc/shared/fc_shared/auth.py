"""FC 共享鉴权编排（US-006，tech-spec §4.5）。

``authorize_request`` 把请求校验 → 微信 code 换 openid → OPENID_ALLOWLIST 鉴权
串成一步，供 ``issue-credential`` 与 ``verify-upload`` 复用：

* 请求体非法 / 字段缺失 → ``400 INVALID_REQUEST``
* code 换 openid 失败 → ``401 INVALID_CODE``
* openid 不在 allowlist → ``403 OPENID_NOT_ALLOWED``

子模块通过模块属性引用（``wechat.code_to_openid`` 等），便于单测打桩。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import audit, http, wechat
from .env import FcEnv
from .errors import OPENID_NOT_ALLOWED, FcHttpError


@dataclass(frozen=True)
class AuthContext:
    """鉴权通过后的上下文：openid、用于日志的 openid 哈希、已解析的请求体。"""

    openid: str
    openid_hash: str
    body: Mapping[str, Any]


def check_allowlist(openid: str, allowlist: Sequence[str]) -> None:
    """openid 不在 allowlist 时抛 ``403 OPENID_NOT_ALLOWED``。"""
    if openid not in allowlist:
        raise FcHttpError(403, OPENID_NOT_ALLOWED, message="openid not in allowlist")


def authorize_request(
    environ: Mapping[str, Any],
    env: FcEnv,
    *,
    fetch: wechat.Fetch | None = None,
    extra_fields: Sequence[str] = (),
) -> AuthContext:
    """解析请求体 → 校验必填字段（含 ``code``）→ 换 openid → allowlist 鉴权。"""
    body = http.read_json_body(environ)
    http.require_fields(body, ("code", *extra_fields))
    code = str(body["code"])
    openid = wechat.code_to_openid(code, env.wx_appid, env.wx_app_secret, fetch=fetch)
    check_allowlist(openid, env.openid_allowlist)
    return AuthContext(openid=openid, openid_hash=audit.hash_openid(openid), body=body)
