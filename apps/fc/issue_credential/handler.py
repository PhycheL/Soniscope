"""FC function issue-credential — STS single-file credential issuance.

Uses the FC shared module for authentication, validation, and safe logging.
"""

from __future__ import annotations

import sys
import os

# Ensure the shared module in the parent directory is importable.
_FC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _FC_ROOT not in sys.path:
    sys.path.insert(0, _FC_ROOT)

from shared.auth import safe_handler  # noqa: E402


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
    """Business logic stub — full STS issuance arrives in US-007."""
    # For now, return a placeholder; the shared auth and validation already ran.
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"status":"ok","message":"issue-credential placeholder"}',
    }
