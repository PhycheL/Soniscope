"""FC shared logging — structured, safe, no secrets leaked.

Never logs: code, session_key, access_key_secret, security_token, or any AK Secret.
Always logs: openid hash, fragment_id, decision/result, elapsed time.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

_logger = logging.getLogger("soniscope.fc")
_logger.setLevel(logging.DEBUG)

# Ensure at least a StreamHandler exists for FC stdout capture.
if not _logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.DEBUG)
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _logger.addHandler(_h)


def get_logger() -> logging.Logger:
    """Return the shared FC logger instance."""
    return _logger


# ---------------------------------------------------------------------------
# Safe hashing / masking
# ---------------------------------------------------------------------------


def _hash_openid(openid: str) -> str:
    """Return a truncated SHA-256 hex for *openid* (first 12 chars)."""
    return hashlib.sha256(openid.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Structured log helpers
# ---------------------------------------------------------------------------


def log_auth_attempt(openid: str | None, fragment_id: str) -> None:
    """Log an authentication attempt (before we know the result)."""
    masked = _hash_openid(openid) if openid else "<none>"
    _logger.info(
        "auth_attempt openid_hash=%s fragment_id=%s", masked, fragment_id
    )


def log_auth_result(
    openid: str | None,
    fragment_id: str,
    allowed: bool,
    elapsed_ms: float,
) -> None:
    """Log the result of an authentication decision."""
    masked = _hash_openid(openid) if openid else "<none>"
    _logger.info(
        "auth_result openid_hash=%s fragment_id=%s allowed=%s elapsed_ms=%.1f",
        masked,
        fragment_id,
        str(allowed).lower(),
        elapsed_ms,
    )


def log_request(method: str, path: str, fragment_id: str) -> None:
    """Log an incoming request (no body, no secrets)."""
    _logger.info("request method=%s path=%s fragment_id=%s", method, path, fragment_id)


def log_response(status_code: int, fragment_id: str, elapsed_ms: float, reason: str = "") -> None:
    """Log the final response for a request."""
    extra = f" reason={reason}" if reason else ""
    _logger.info(
        "response status=%d fragment_id=%s elapsed_ms=%.1f%s",
        status_code,
        fragment_id,
        elapsed_ms,
        extra,
    )


def log_error(fragment_id: str, error_code: str, detail: str = "") -> None:
    """Log a handled error."""
    extra = f" detail={detail}" if detail else ""
    _logger.warning(
        "error fragment_id=%s error=%s%s",
        fragment_id,
        error_code,
        extra,
    )
