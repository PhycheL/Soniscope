"""FC shared error response builders.

Produces consistent JSON error responses with stable error codes.
"""

from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# Error codes — stable, documented strings consumed by the mini-program
# ---------------------------------------------------------------------------

ERROR_INVALID_JSON = "INVALID_JSON"
ERROR_MISSING_FIELD = "MISSING_FIELD"
ERROR_INVALID_CODE = "INVALID_CODE"
ERROR_OPENID_NOT_ALLOWED = "OPENID_NOT_ALLOWED"
ERROR_SIZE_EXCEEDED = "SIZE_EXCEEDED"
ERROR_INTERNAL = "INTERNAL_ERROR"

# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _error_response(status_code: int, body: dict) -> dict:
    """Build a standard FC HTTP response dict."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def bad_request(error: str, detail: str = "", **extra: object) -> dict:
    """400 — client error (bad JSON, missing field, invalid parameter)."""
    body: dict[str, object] = {"error": error}
    if detail:
        body["detail"] = detail
    body.update(extra)
    return _error_response(400, body)


def unauthorized(error: str = ERROR_INVALID_CODE) -> dict:
    """401 — authentication failure."""
    return _error_response(401, {"error": error})


def forbidden(error: str = ERROR_OPENID_NOT_ALLOWED) -> dict:
    """403 — openid not in allowlist."""
    return _error_response(403, {"error": error})


def internal_error() -> dict:
    """500 — internal server error (masked)."""
    return _error_response(500, {"error": ERROR_INTERNAL})
