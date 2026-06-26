"""微信 ``jscode2session`` 换 openid（US-006，tech-spec §4.5）。

任意失败（网络错误、非 0 errcode、缺 openid）统一映射为 ``401 INVALID_CODE``，
绝不向客户端或日志泄漏 ``code`` / ``secret`` / ``session_key``。
HTTP 拉取通过 ``fetch`` 注入，单测无需触网。
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from urllib.parse import urlencode

from .errors import INVALID_CODE, FcHttpError

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"

# 注入点：给定完整 URL 返回响应体字节。单测注入假实现。
Fetch = Callable[[str], bytes]


def _default_fetch(url: str) -> bytes:
    req = urllib.request.Request(url, method="GET")  # noqa: S310 - 固定 https 微信开放接口
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        return bytes(resp.read())


def code_to_openid(code: str, appid: str, secret: str, *, fetch: Fetch | None = None) -> str:
    """用 wx.login code 换 openid；失败抛 ``FcHttpError(401, INVALID_CODE)``。"""
    do_fetch = fetch or _default_fetch
    query = urlencode(
        {
            "appid": appid,
            "secret": secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    url = f"{JSCODE2SESSION_URL}?{query}"
    try:
        raw = do_fetch(url)
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001 - 任意失败统一 401，不泄漏 code / secret
        raise FcHttpError(401, INVALID_CODE, message="jscode2session request failed") from exc
    if not isinstance(data, dict):
        raise FcHttpError(401, INVALID_CODE, message="jscode2session returned malformed response")
    errcode = data.get("errcode", 0)
    openid = data.get("openid")
    if errcode not in (0, None) or not openid:
        raise FcHttpError(401, INVALID_CODE, message="jscode2session returned no openid")
    return str(openid)
