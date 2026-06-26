"""issue-credential STS 单 object key 凭证签发（US-007，tech-spec §4.1 / §4.4）。

把可单测的纯逻辑（fragment_id → object_key 解析、单 key policy 构造、size 校验、
响应组装）与真实云调用（AssumeRole，lazy import 云 SDK）分离：

* 纯逻辑无 IO、直接单测，由 mypy strict + ruff + pytest 覆盖；
* AssumeRole 通过 ``StsIssuer`` Protocol 注入，单测用假实现，运行时用 ``RealStsIssuer``。

安全红线：STS policy Resource **精确等于** 单个 object key（无通配符），有效期 ≤ 900 秒，
只允许 ``oss:PutObject``。长期 AK 只在内部调用 AssumeRole，绝不进响应或日志。
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .errors import INVALID_REQUEST, SIZE_EXCEEDED, FcHttpError

# tech-spec §4.1：STS 有效期上限（秒），AssumeRole 最短亦为 900s。
STS_MAX_DURATION_SECONDS = 900
# AssumeRole 会话名（≤ 64 字符，仅字母 / 数字 / 少量符号）。
ROLE_SESSION_NAME = "soniscope-issue-credential"

# fragment_id 格式：<YYYYMMDDTHHMMSS>_<deviceShortId>_<26 字符 ULID>（AGENTS.md / tech-spec）。
_FRAGMENT_ID_RE = re.compile(
    r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})T\d{6}"
    r"_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$"
)


@dataclass(frozen=True)
class StsCredential:
    """AssumeRole 返回的临时凭证（仅签发响应需要的字段）。"""

    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration: str


def object_key_for(fragment_id: str) -> str:
    """由 fragment_id 解析日期前缀并构造 OSS object key（AC#2）。

    返回 ``recordings/<YYYY-MM-DD>/<fragment_id>.wav``；格式 / 日期非法抛 400。
    """
    match = _FRAGMENT_ID_RE.match(fragment_id)
    if match is None:
        raise FcHttpError(400, INVALID_REQUEST, message="invalid fragment_id format")
    year, month, day = match["year"], match["month"], match["day"]
    try:
        datetime(int(year), int(month), int(day))  # noqa: DTZ001 - 仅校验日期合法性
    except ValueError as exc:
        raise FcHttpError(400, INVALID_REQUEST, message="invalid fragment_id date") from exc
    return f"recordings/{year}-{month}-{day}/{fragment_id}.wav"


def single_key_policy(bucket: str, object_key: str) -> dict[str, object]:
    """构造仅允许 PutObject 到单个 object key 的 STS policy（tech-spec §4.4，无通配符）。"""
    return {
        "Version": "1",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["oss:PutObject"],
                "Resource": [f"acs:oss:*:*:{bucket}/{object_key}"],
            }
        ],
    }


def parse_size(value: object) -> int:
    """把请求体 size 解析为正整数；非整数 / 非正抛 400 INVALID_REQUEST。"""
    if isinstance(value, bool):  # bool 是 int 子类，显式拒绝
        raise FcHttpError(400, INVALID_REQUEST, message="size must be a positive integer")
    if isinstance(value, int):
        size = value
    elif isinstance(value, str) and value.strip().isdigit():
        size = int(value.strip())
    else:
        raise FcHttpError(400, INVALID_REQUEST, message="size must be a positive integer")
    if size <= 0:
        raise FcHttpError(400, INVALID_REQUEST, message="size must be a positive integer")
    return size


def check_size(size: int, max_upload_bytes: int) -> None:
    """size 超过上限时抛 400 SIZE_EXCEEDED（含 limit_bytes / actual_bytes，AC#3）。"""
    if size > max_upload_bytes:
        raise FcHttpError(
            400,
            SIZE_EXCEEDED,
            limit_bytes=max_upload_bytes,
            actual_bytes=size,
        )


def credential_response(
    cred: StsCredential, *, bucket: str, endpoint: str, object_key: str
) -> dict[str, object]:
    """组装 §4.1 成功响应（含 7 个字段，AC#6）。"""
    return {
        "access_key_id": cred.access_key_id,
        "access_key_secret": cred.access_key_secret,
        "security_token": cred.security_token,
        "expiration": cred.expiration,
        "bucket": bucket,
        "endpoint": endpoint,
        "object_key": object_key,
    }


class StsIssuer(Protocol):
    """AssumeRole 注入点：用部署 / 子账号凭证签发单 key STS（便于单测打桩）。"""

    def assume_role(
        self,
        *,
        ak_id: str,
        ak_secret: str,
        role_arn: str,
        region: str,
        policy: Mapping[str, object],
        duration_seconds: int,
        session_name: str,
    ) -> StsCredential: ...


def _import_sts() -> Any:
    from alibabacloud_sts20150401 import models as sts_models
    from alibabacloud_sts20150401.client import Client as StsClient
    from alibabacloud_tea_openapi import models as open_api_models

    return StsClient, sts_models, open_api_models


class RealStsIssuer:
    """真实 AssumeRole 实现（lazy import alibabacloud-sts20150401 + tea-openapi）。"""

    def assume_role(
        self,
        *,
        ak_id: str,
        ak_secret: str,
        role_arn: str,
        region: str,
        policy: Mapping[str, object],
        duration_seconds: int,
        session_name: str,
    ) -> StsCredential:
        sts_client_cls, sts_models, open_api_models = _import_sts()
        cfg = open_api_models.Config(access_key_id=ak_id, access_key_secret=ak_secret)
        cfg.endpoint = f"sts.{region}.aliyuncs.com"
        client = sts_client_cls(cfg)
        req = sts_models.AssumeRoleRequest(
            role_arn=role_arn,
            role_session_name=session_name,
            duration_seconds=duration_seconds,
            policy=json.dumps(dict(policy)),
        )
        cred = client.assume_role(req).body.credentials
        return StsCredential(
            access_key_id=str(cred.access_key_id),
            access_key_secret=str(cred.access_key_secret),
            security_token=str(cred.security_token),
            expiration=str(cred.expiration),
        )


def get_issuer() -> StsIssuer:
    """返回运行时 STS 签发器；单测通过 monkeypatch 本函数注入假实现。"""
    return RealStsIssuer()
