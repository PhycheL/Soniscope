"""FC shared authentication — wx.login code → openid + allowlist check.

This module is imported by both issue-credential and verify-upload.
It does NOT depend on any FC 2.0 service layer.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

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

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def authenticate(code: str, fragment_id: str, config: SharedConfig | None = None) -> str:
    """Exchange a wx.login *code* for an openid and verify it is in the allowlist.

    Args:
        code: The ``wx.login`` code from the mini-program.
        fragment_id: The fragment being operated on (for logging).
        config: Optional pre-loaded config; read from env if None.

    Returns:
        The verified openid string.

    Raises:
        AuthError: with HTTP status code and error code on failure.
    """
    if config is None:
        config = read_shared_config()

    t0 = time.monotonic()

    # 1. Exchange code for openid via jscode2session
    try:
        openid = _code_to_openid(code, config)
    except AuthError:
        raise
    except Exception as exc:
        get_logger().error("jscode2session_unexpected fragment_id=%s err=%s", fragment_id, exc)
        raise AuthError(401, ERROR_INVALID_CODE, str(exc))

    log_auth_attempt(openid, fragment_id)

    # 2. Check allowlist
    allowlist_raw = os.environ.get("OPENID_ALLOWLIST", "")
    allowed_openids = {o.strip() for o in allowlist_raw.split(",") if o.strip()}

    if not allowed_openids:
        get_logger().warning("OPENID_ALLOWLIST is empty — all requests will be rejected")

    allowed = openid in allowed_openids
    elapsed_ms = (time.monotonic() - t0) * 1000
    log_auth_result(openid, fragment_id, allowed, elapsed_ms)

    if not allowed:
        raise AuthError(403, ERROR_OPENID_NOT_ALLOWED)

    return openid


def parse_request_body(body: str) -> dict[str, Any]:
    """Parse and validate the incoming JSON request body.

    Returns the parsed body as a dict.

    Raises:
        AuthError: with 400 and the appropriate error code on failure.
    """
    if not body:
        raise AuthError(400, ERROR_INVALID_JSON, "Empty request body")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AuthError(400, ERROR_INVALID_JSON, str(exc))

    if not isinstance(data, dict):
        raise AuthError(400, ERROR_INVALID_JSON, "Body must be a JSON object")

    return data


def require_fields(data: dict[str, Any], *field_names: str) -> None:
    """Check that all *field_names* are present and non-empty in *data*.

    Raises:
        AuthError: with 400 and MISSING_FIELD if any field is missing.
    """
    missing = []
    for name in field_names:
        if name not in data:
            missing.append(name)
        elif data[name] is None or (isinstance(data[name], str) and not data[name].strip()):
            missing.append(name)

    if missing:
        raise AuthError(
            400,
            ERROR_MISSING_FIELD,
            f"Missing or empty fields: {', '.join(missing)}",
        )


class AuthError(Exception):
    """Controlled authentication / validation failure.

    Carries an HTTP status code, a stable error string, and optional
    extra fields that are merged into the JSON response body.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str = "",
        extra: dict[str, object] | None = None,
    ) -> None:
        super().__init__(error_code)
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        self.extra = extra or {}


def auth_error_to_response(exc: AuthError) -> dict:
    """Convert an AuthError into a standard FC HTTP response dict."""
    body: dict[str, object] = {"error": exc.error_code}
    if exc.detail:
        body["detail"] = exc.detail
    body.update(exc.extra)
    return {
        "statusCode": exc.status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def safe_handler(
    event: dict[str, Any],
    handler_fn: Any,
    *,
    required_fields: tuple[str, ...] = ("code", "fragment_id"),
) -> dict:
    """FC handler wrapper providing auth, parsing, logging, and error handling.

    This is the main entry point for both issue-credential and verify-upload
    handlers.  It:

    1. Parses and validates the JSON body.
    2. Checks required fields.
    3. Authenticates the caller (wx.login code → openid + allowlist).
    4. Calls *handler_fn*(parsed_body, openid, t_start).
    5. Catches AuthError and maps to HTTP responses.
    6. Catches unexpected exceptions and maps to 500.

    Args:
        event: The raw FC event dict.
        handler_fn: ``(data: dict, openid: str, t_start: float) -> dict``
        required_fields: Field names that must be present in the body.

    Returns:
        An FC-compatible HTTP response dict.
    """
    t_start = time.monotonic()
    path = event.get("path", "/")
    method = event.get("httpMethod", event.get("method", "POST"))
    body = event.get("body", "")

    # Pre-parse for fragment_id logging (best-effort, may be absent)
    try:
        pre_data = json.loads(body) if body else {}
        fragment_id = str(pre_data.get("fragment_id", "<unknown>"))
    except json.JSONDecodeError:
        fragment_id = "<unknown>"

    log_request(method, path, fragment_id)

    try:
        # 1. Parse body
        data = parse_request_body(body)

        # 2. Check required fields
        require_fields(data, *required_fields)

        # Update fragment_id from parsed data for logging
        fragment_id = str(data.get("fragment_id", fragment_id))

        # 3. Authenticate
        code = str(data["code"])
        openid = authenticate(code, fragment_id)

        # 4. Call business logic
        result = handler_fn(data, openid, t_start)

        elapsed_ms = (time.monotonic() - t_start) * 1000
        log_response(result.get("statusCode", 200), fragment_id, elapsed_ms)

        return result

    except AuthError as exc:
        elapsed_ms = (time.monotonic() - t_start) * 1000
        log_error(fragment_id, exc.error_code, exc.detail)
        log_response(exc.status_code, fragment_id, elapsed_ms, exc.error_code)
        return auth_error_to_response(exc)

    except Exception as exc:
        elapsed_ms = (time.monotonic() - t_start) * 1000
        log_error(fragment_id, ERROR_INTERNAL, str(exc))
        log_response(500, fragment_id, elapsed_ms, ERROR_INTERNAL)
        get_logger().exception("unhandled_exception fragment_id=%s", fragment_id)
        return internal_error()


# ---------------------------------------------------------------------------
# Internal: wx.login code → openid
# ---------------------------------------------------------------------------


def _code_to_openid(code: str, config: SharedConfig) -> str:
    """Call the WeChat jscode2session endpoint and return the openid.

    Uses urllib.request (stdlib, no extra FC dependency).
    """
    from urllib import request as urllib_request
    from urllib.error import HTTPError, URLError

    url = (
        f"https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={config.wx_appid}"
        f"&secret={config.wx_app_secret}"
        f"&js_code={code}"
        f"&grant_type=authorization_code"
    )

    try:
        req = urllib_request.Request(url)
        with urllib_request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except HTTPError as exc:
        raise AuthError(401, ERROR_INVALID_CODE, f"HTTP {exc.code}")
    except URLError as exc:
        raise AuthError(401, ERROR_INVALID_CODE, f"Network error: {exc.reason}")
    except json.JSONDecodeError:
        raise AuthError(401, ERROR_INVALID_CODE, "Invalid response from WeChat")

    # WeChat returns errcode on failure
    if "errcode" in data and data["errcode"] != 0:
        errcode = data.get("errcode", -1)
        errmsg = data.get("errmsg", "unknown")
        get_logger().warning(
            "jscode2session_failed errcode=%s errmsg=%s", errcode, errmsg
        )
        raise AuthError(401, ERROR_INVALID_CODE, f"WeChat error {errcode}: {errmsg}")

    openid = data.get("openid")
    if not openid:
        raise AuthError(401, ERROR_INVALID_CODE, "No openid in WeChat response")

    return openid
