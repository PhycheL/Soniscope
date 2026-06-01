"""FC shared module — authentication, validation, and safe logging.

Reusable by both ``issue-credential`` and ``verify-upload`` FC functions.
Does not depend on any FC 2.0 service layer.
"""

from __future__ import annotations

from .auth import (
    AuthError,
    authenticate,
    auth_error_to_response,
    parse_request_body,
    require_fields,
    safe_handler,
)
from .config import SharedConfig, read_shared_config
from .errors import (
    ERROR_INTERNAL,
    ERROR_INVALID_CODE,
    ERROR_INVALID_JSON,
    ERROR_MISSING_FIELD,
    ERROR_OPENID_NOT_ALLOWED,
    ERROR_SIZE_EXCEEDED,
    bad_request,
    forbidden,
    internal_error,
    unauthorized,
)
from .logging import get_logger, log_auth_attempt, log_auth_result, log_error, log_request, log_response

__all__ = [
    # auth
    "AuthError",
    "authenticate",
    "auth_error_to_response",
    "parse_request_body",
    "require_fields",
    "safe_handler",
    # config
    "SharedConfig",
    "read_shared_config",
    # errors
    "ERROR_INTERNAL",
    "ERROR_INVALID_CODE",
    "ERROR_INVALID_JSON",
    "ERROR_MISSING_FIELD",
    "ERROR_OPENID_NOT_ALLOWED",
    "ERROR_SIZE_EXCEEDED",
    "bad_request",
    "forbidden",
    "internal_error",
    "unauthorized",
    # logging
    "get_logger",
    "log_auth_attempt",
    "log_auth_result",
    "log_error",
    "log_request",
    "log_response",
]
