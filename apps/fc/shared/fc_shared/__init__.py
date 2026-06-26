"""FC 共享鉴权 / 请求校验 / 安全日志模块（US-006）。

``issue-credential`` 与 ``verify-upload`` 两个 FC 3.0 顶级 Web 函数复用本包，避免鉴权
与校验逻辑重复且不一致。FC 3.0 无 service 层级，本包不引用任何 FC 2.0 service 概念。

部署时本包由 ``make deploy-fc`` 打包脚本 vendoring 到每个函数包根目录
（见 ``soniscope_worker.fc_deploy.package_function``），使两个函数都能 ``import fc_shared``。
"""

from __future__ import annotations

from . import sts
from .audit import hash_openid, is_sensitive, log_event
from .auth import AuthContext, authorize_request, check_allowlist
from .env import (
    DEFAULT_MAX_UPLOAD_BYTES,
    DEFAULT_REQUIRED_VARS,
    ISSUE_CREDENTIAL_REQUIRED_VARS,
    FcEnv,
    StsEnv,
    load_env,
    load_sts_env,
    parse_allowlist,
)
from .errors import (
    INVALID_CODE,
    INVALID_REQUEST,
    OPENID_NOT_ALLOWED,
    SERVER_MISCONFIGURED,
    SIZE_EXCEEDED,
    STS_ISSUE_FAILED,
    FcConfigError,
    FcHttpError,
)
from .http import error_response, json_response, read_json_body, require_fields, status_line
from .sts import (
    STS_MAX_DURATION_SECONDS,
    StsCredential,
    StsIssuer,
    check_size,
    credential_response,
    get_issuer,
    object_key_for,
    parse_size,
    single_key_policy,
)
from .wechat import code_to_openid

__all__ = [
    "DEFAULT_MAX_UPLOAD_BYTES",
    "DEFAULT_REQUIRED_VARS",
    "INVALID_CODE",
    "INVALID_REQUEST",
    "ISSUE_CREDENTIAL_REQUIRED_VARS",
    "OPENID_NOT_ALLOWED",
    "SERVER_MISCONFIGURED",
    "SIZE_EXCEEDED",
    "STS_ISSUE_FAILED",
    "STS_MAX_DURATION_SECONDS",
    "AuthContext",
    "FcConfigError",
    "FcEnv",
    "FcHttpError",
    "StsCredential",
    "StsEnv",
    "StsIssuer",
    "authorize_request",
    "check_allowlist",
    "check_size",
    "code_to_openid",
    "credential_response",
    "error_response",
    "get_issuer",
    "hash_openid",
    "is_sensitive",
    "json_response",
    "load_env",
    "load_sts_env",
    "log_event",
    "object_key_for",
    "parse_allowlist",
    "parse_size",
    "read_json_body",
    "require_fields",
    "single_key_policy",
    "status_line",
    "sts",
]
