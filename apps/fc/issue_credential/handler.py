"""FC function issue-credential — STS single-file credential issuance.

Uses the FC shared module for authentication, validation, and safe logging.
"""

from __future__ import annotations

import json
import os
import sys

# Ensure the shared module in the parent directory is importable.
_FC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _FC_ROOT not in sys.path:
    sys.path.insert(0, _FC_ROOT)

from shared.auth import AuthError, safe_handler  # noqa: E402
from shared.errors import ERROR_INTERNAL  # noqa: E402
from shared.logging import get_logger  # noqa: E402
from shared.sts import issue_sts_credential  # noqa: E402


def handler(event: dict, context: object) -> dict:
    """FC 3.0 Web function handler.

    Accepts POST with ``{code, fragment_id, size}``.
    Authenticates via wx.login → openid allowlist, then issues STS (US-007).
    """
    return safe_handler(
        event,
        _handle,
        required_fields=("code", "fragment_id", "size"),
    )


def _handle(data: dict, openid: str, t_start: float) -> dict:
    """Business logic: validate size, issue single-file STS credential.

    The shared ``safe_handler`` wrapper has already:
    - Parsed and validated the JSON body
    - Verified ``code``, ``fragment_id``, ``size`` are present
    - Authenticated via wx.login → openid allowlist
    """
    fragment_id = str(data["fragment_id"])
    size_val = data["size"]

    # Size must be a valid integer
    try:
        size = int(size_val)
    except (ValueError, TypeError):
        raise AuthError(400, "INVALID_SIZE", f"size must be an integer, got {size_val!r}")

    if size < 0:
        raise AuthError(400, "INVALID_SIZE", f"size must be non-negative, got {size}")

    try:
        result = issue_sts_credential(fragment_id, size)
    except RuntimeError as exc:
        get_logger().error(
            "sts_issuance_failed fragment_id=%s err=%s", fragment_id, exc
        )
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": ERROR_INTERNAL, "detail": "STS credential issuance failed"},
                ensure_ascii=False,
            ),
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result, ensure_ascii=False),
    }
