"""FC 共享鉴权 / 请求校验 / 安全日志模块（US-006）。

``issue-credential`` 与 ``verify-upload`` 两个 FC 3.0 顶级 Web 函数复用本包，避免鉴权
与校验逻辑重复且不一致。FC 3.0 无 service 层级，本包不引用任何 FC 2.0 service 概念。

部署时本包由 ``make deploy-fc`` 打包脚本 vendoring 到每个函数包根目录
（见 ``soniscope_worker.fc_deploy.package_function``），使两个函数都能 ``import fc_shared``。
"""

from __future__ import annotations

from .audit import hash_openid, is_sensitive, log_event
from .auth import AuthContext, authorize_request, check_allowlist
from .env import DEFAULT_REQUIRED_VARS, FcEnv, load_env, parse_allowlist
from .errors import (
    INVALID_CODE,
    INVALID_REQUEST,
    OPENID_NOT_ALLOWED,
    SERVER_MISCONFIGURED,
    FcConfigError,
    FcHttpError,
)
from .http import error_response, json_response, read_json_body, require_fields, status_line
from .wechat import code_to_openid

__all__ = [
    "DEFAULT_REQUIRED_VARS",
    "INVALID_CODE",
    "INVALID_REQUEST",
    "OPENID_NOT_ALLOWED",
    "SERVER_MISCONFIGURED",
    "AuthContext",
    "FcConfigError",
    "FcEnv",
    "FcHttpError",
    "authorize_request",
    "check_allowlist",
    "code_to_openid",
    "error_response",
    "hash_openid",
    "is_sensitive",
    "json_response",
    "load_env",
    "log_event",
    "parse_allowlist",
    "read_json_body",
    "require_fields",
    "status_line",
]
