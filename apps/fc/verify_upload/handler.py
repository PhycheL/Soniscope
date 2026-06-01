"""FC function verify-upload — OSS HeadObject upload confirmation.

Uses the FC shared module for authentication, validation, and safe logging.
"""

from __future__ import annotations

import json
import os
import sys
import time

# Ensure the shared module in the parent directory is importable.
_FC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _FC_ROOT not in sys.path:
    sys.path.insert(0, _FC_ROOT)

from shared.auth import AuthError, safe_handler  # noqa: E402
from shared.errors import ERROR_INTERNAL  # noqa: E402
from shared.logging import get_logger  # noqa: E402
from shared.oss import head_object  # noqa: E402
from shared.sts import _fragment_oss_key  # noqa: E402


def handler(event: dict, context: object) -> dict:
    """FC 3.0 Web function handler.

    Accepts POST with ``{code, fragment_id, expected_size}``.
    Authenticates via wx.login → openid allowlist, then performs HeadObject (US-009).
    """
    return safe_handler(
        event,
        _handle,
        required_fields=("code", "fragment_id", "expected_size"),
    )


def _handle(data: dict, openid: str, t_start: float) -> dict:
    """Business logic: derive OSS key, HeadObject, respond with verification result.

    The shared ``safe_handler`` wrapper has already:
    - Parsed and validated the JSON body
    - Verified ``code``, ``fragment_id``, ``expected_size`` are present
    - Authenticated via wx.login → openid allowlist
    """
    fragment_id = str(data["fragment_id"])
    expected_size_val = data["expected_size"]

    # Validate expected_size is an integer
    try:
        expected_size = int(expected_size_val)
    except (ValueError, TypeError):
        raise AuthError(400, "INVALID_SIZE", f"expected_size must be an integer, got {expected_size_val!r}")

    if expected_size < 0:
        raise AuthError(400, "INVALID_SIZE", f"expected_size must be non-negative, got {expected_size}")

    # Derive OSS object key
    try:
        object_key = _fragment_oss_key(fragment_id)
    except ValueError as exc:
        raise AuthError(400, "INVALID_FRAGMENT_ID", str(exc))

    logger = get_logger()
    t_head_start = time.monotonic()

    try:
        result = head_object(object_key)
    except RuntimeError as exc:
        elapsed_ms = (time.monotonic() - t_head_start) * 1000
        logger.error(
            "verify_upload_head_failed fragment_id=%s object_key=%s elapsed_ms=%.1f err=%s",
            fragment_id, object_key, elapsed_ms, exc,
        )
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": ERROR_INTERNAL, "detail": "HeadObject verification failed"},
                ensure_ascii=False,
            ),
        }

    head_elapsed_ms = (time.monotonic() - t_head_start) * 1000
    total_elapsed_ms = (time.monotonic() - t_start) * 1000

    if not result.found:
        logger.info(
            "verify_upload_result fragment_id=%s verified=false reason=OBJECT_NOT_FOUND "
            "head_elapsed_ms=%.1f total_elapsed_ms=%.1f",
            fragment_id, head_elapsed_ms, total_elapsed_ms,
        )
        body: dict = {"verified": False, "reason": "OBJECT_NOT_FOUND"}
    elif result.content_length is not None and result.content_length != expected_size:
        logger.info(
            "verify_upload_result fragment_id=%s verified=false reason=SIZE_MISMATCH "
            "expected=%d actual=%d head_elapsed_ms=%.1f total_elapsed_ms=%.1f",
            fragment_id, expected_size, result.content_length,
            head_elapsed_ms, total_elapsed_ms,
        )
        body = {
            "verified": False,
            "reason": "SIZE_MISMATCH",
            "actual_size": result.content_length,
        }
    else:
        logger.info(
            "verify_upload_result fragment_id=%s verified=true size=%s etag=%s "
            "head_elapsed_ms=%.1f total_elapsed_ms=%.1f",
            fragment_id, result.content_length, result.etag,
            head_elapsed_ms, total_elapsed_ms,
        )
        body = {
            "verified": True,
            "etag": result.etag or "",
            "size": result.content_length,
            "last_modified": result.last_modified or "",
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
