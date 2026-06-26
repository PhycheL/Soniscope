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

# tech-spec §4.0 / §4.1：issue-credential 额外依赖的 STS AssumeRole 运行时变量。
# verify-upload 不需要这些，故不放入共享 DEFAULT_REQUIRED_VARS。
ISSUE_CREDENTIAL_REQUIRED_VARS: tuple[str, ...] = (
    "RAM_ROLE_ARN",
    "ALIYUN_AK_ID",
    "ALIYUN_AK_SECRET",
)

# tech-spec §4.0：MAX_UPLOAD_BYTES 可选，缺失 / 非法时回退默认 50 MB。
DEFAULT_MAX_UPLOAD_BYTES = 52428800


@dataclass(frozen=True)
class FcEnv:
    """FC 运行时共享配置（不持有任何会被日志打印的字段；secret 仅供内部调用）。"""

    oss_bucket: str
    oss_region: str
    oss_endpoint: str
    wx_appid: str
    wx_app_secret: str
    openid_allowlist: tuple[str, ...]


@dataclass(frozen=True)
class StsEnv:
    """issue-credential 的 STS AssumeRole 运行时配置。

    ``ak_id`` / ``ak_secret`` 是 FC 子账号长期凭证，仅供内部调用 AssumeRole，
    绝不进日志（见 ``audit.is_sensitive`` 兜底）。
    """

    ram_role_arn: str
    ak_id: str
    ak_secret: str
    max_upload_bytes: int


def _parse_max_upload_bytes(raw: str) -> int:
    """解析 MAX_UPLOAD_BYTES；缺失 / 非正整数时回退默认值。"""
    text = raw.strip()
    if not text:
        return DEFAULT_MAX_UPLOAD_BYTES
    try:
        value = int(text)
    except ValueError:
        return DEFAULT_MAX_UPLOAD_BYTES
    return value if value > 0 else DEFAULT_MAX_UPLOAD_BYTES


def load_sts_env(
    source: Mapping[str, str] | None = None,
    *,
    required: Sequence[str] = ISSUE_CREDENTIAL_REQUIRED_VARS,
) -> StsEnv:
    """加载 issue-credential STS 专属环境变量；缺必填变量抛 FcConfigError。"""
    env = os.environ if source is None else source
    missing = [name for name in required if not str(env.get(name, "")).strip()]
    if missing:
        raise FcConfigError(missing)
    return StsEnv(
        ram_role_arn=str(env.get("RAM_ROLE_ARN", "")).strip(),
        ak_id=str(env.get("ALIYUN_AK_ID", "")).strip(),
        ak_secret=str(env.get("ALIYUN_AK_SECRET", "")).strip(),
        max_upload_bytes=_parse_max_upload_bytes(str(env.get("MAX_UPLOAD_BYTES", ""))),
    )


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
