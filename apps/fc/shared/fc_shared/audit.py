"""FC 安全结构化日志（US-006，安全红线见 AGENTS.md）。

日志只允许记录 openid **哈希**、fragment_id、判定结果、耗时等非敏感字段；
``code`` / ``session_key`` / AK Secret / SecurityToken 等敏感字段一律脱敏，
防止调用方误把敏感值塞进日志。
"""

from __future__ import annotations

import hashlib
from typing import Any

# 显式敏感字段名（小写、连字符归一为下划线后比较）。
SENSITIVE_FIELD_NAMES = frozenset(
    {
        "code",
        "js_code",
        "session_key",
        "access_key_id",
        "access_key_secret",
        "security_token",
        "secret",
        "app_secret",
        "wx_app_secret",
        "appkey",
        "api_key",
        "password",
    }
)
# 子串匹配兜底：任意含这些片段的字段名都脱敏。
_SENSITIVE_SUBSTRINGS = ("secret", "token", "appkey", "api_key", "session_key", "password")
_REDACTED = "***REDACTED***"


def hash_openid(openid: str) -> str:
    """openid → 稳定哈希摘要（sha256 前 16 位），用于日志而不暴露完整 openid。"""
    return hashlib.sha256(openid.encode("utf-8")).hexdigest()[:16]


def is_sensitive(name: str) -> bool:
    """字段名是否应脱敏。"""
    low = name.lower().replace("-", "_")
    if low in SENSITIVE_FIELD_NAMES:
        return True
    return any(token in low for token in _SENSITIVE_SUBSTRINGS)


def log_event(event: str, **fields: Any) -> str:
    """渲染并打印一行结构化日志（敏感字段脱敏），返回该行文本便于断言。

    FC 运行时把 stdout 采集到日志服务；``None`` 字段省略，字段按名排序保证稳定。
    """
    parts = [f"event={event}"]
    for key in sorted(fields):
        value = fields[key]
        if value is None:
            continue
        rendered = _REDACTED if is_sensitive(key) else str(value)
        parts.append(f"{key}={rendered}")
    line = " ".join(parts)
    print(line, flush=True)  # FC 运行时通过 stdout 采集日志
    return line
