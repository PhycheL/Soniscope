"""FC 运行时环境变量加载（US-006，权威定义见 tech-spec §4.0）。

两个函数共享同一套运行时配置；缺失必填变量时一次性列出所有缺失变量**名**
（绝不打印变量值），由调用方映射为明确的启动 / 请求错误。
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .errors import FcConfigError

# tech-spec §4.0：两个 FC 函数共享的必填运行时环境变量。
DEFAULT_REQUIRED_VARS: tuple[str, ...] = (
    "OSS_BUCKET",
    "OSS_REGION",
    "OSS_ENDPOINT",
    "WX_APPID",
    "WX_APP_SECRET",
    "OPENID_ALLOWLIST",
)


@dataclass(frozen=True)
class FcEnv:
    """FC 运行时共享配置（不持有任何会被日志打印的字段；secret 仅供内部调用）。"""

    oss_bucket: str
    oss_region: str
    oss_endpoint: str
    wx_appid: str
    wx_app_secret: str
    openid_allowlist: tuple[str, ...]


def parse_allowlist(value: str) -> tuple[str, ...]:
    """逗号分隔的 OPENID_ALLOWLIST → 去空白、去空项的元组。"""
    return tuple(part.strip() for part in value.split(",") if part.strip())


def load_env(
    source: Mapping[str, str] | None = None,
    *,
    required: Sequence[str] = DEFAULT_REQUIRED_VARS,
) -> FcEnv:
    """从 ``source``（默认 ``os.environ``）加载 FcEnv；缺必填变量抛 FcConfigError。"""
    env = os.environ if source is None else source
    missing = [name for name in required if not str(env.get(name, "")).strip()]
    if missing:
        raise FcConfigError(missing)
    return FcEnv(
        oss_bucket=str(env.get("OSS_BUCKET", "")).strip(),
        oss_region=str(env.get("OSS_REGION", "")).strip(),
        oss_endpoint=str(env.get("OSS_ENDPOINT", "")).strip(),
        wx_appid=str(env.get("WX_APPID", "")).strip(),
        wx_app_secret=str(env.get("WX_APP_SECRET", "")).strip(),
        openid_allowlist=parse_allowlist(str(env.get("OPENID_ALLOWLIST", ""))),
    )
