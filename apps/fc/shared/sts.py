"""FC shared STS — single-file AssumeRole credential issuance.

Uses stdlib only (urllib, hmac, hashlib) — same pattern as auth.py's
jscode2session.

The Aliyun STS AssumeRole REST API is called with HMAC-SHA1 signing (v1).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from urllib import parse as urlparse
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from .config import SharedConfig, read_shared_config
from .errors import (
    ERROR_INTERNAL,
    bad_request,
    internal_error,
)
from .logging import get_logger

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

STS_API_ENDPOINT = "sts.aliyuncs.com"
STS_MAX_DURATION_SECONDS = 900


def issue_sts_credential(
    fragment_id: str,
    size: int,
    config: SharedConfig | None = None,
) -> dict:
    """Issue a single-file STS credential for *fragment_id*.

    Args:
        fragment_id: The full fragment_id string.
        size: The file size in bytes (checked against MAX_UPLOAD_BYTES).
        config: Optional pre-loaded config; read from env if None.

    Returns:
        A dict ready to be serialised as the success JSON response body
        (see tech-spec §4.1).

    Raises:
        AuthError (via size check): 400 SIZE_EXCEEDED.
        RuntimeError: on STS API call failure (logged, then raised as 502).
    """
    if config is None:
        config = read_shared_config()

    # 1. Size check
    max_bytes_str = os.environ.get("MAX_UPLOAD_BYTES", "")
    max_bytes = int(max_bytes_str) if max_bytes_str else 52_428_800  # default 50 MB

    if size > max_bytes:
        raise _size_exceeded_error(size, max_bytes)

    # 2. Derive OSS object key from fragment_id
    object_key = _fragment_oss_key(fragment_id)

    # 3. Call STS AssumeRole
    logger = get_logger()
    logger.info(
        "sts_assume_role_request fragment_id=%s object_key=%s size=%d",
        fragment_id, object_key, size,
    )

    t0 = time.monotonic()
    try:
        result = _call_assume_role(object_key, config)
    except Exception as exc:
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.error(
            "sts_assume_role_failed fragment_id=%s elapsed_ms=%.1f err=%s",
            fragment_id, elapsed_ms, exc,
        )
        raise RuntimeError(f"STS AssumeRole failed: {exc}")

    elapsed_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "sts_assume_role_success fragment_id=%s elapsed_ms=%.1f",
        fragment_id, elapsed_ms,
    )

    return {
        "access_key_id": result["access_key_id"],
        "access_key_secret": result["access_key_secret"],
        "security_token": result["security_token"],
        "expiration": result["expiration"],
        "bucket": config.oss_bucket,
        "endpoint": config.oss_endpoint,
        "object_key": object_key,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fragment_oss_key(fragment_id: str) -> str:
    """Derive the OSS object key from a fragment_id.

    Format: ``recordings/<YYYY-MM-DD>/<fragment_id>.wav``
    The date prefix is parsed from the fragment_id's leading timestamp portion.
    """
    # fragment_id format: <YYYYMMDDTHHMMSS>_<deviceShortId>_<ulid>
    if "T" not in fragment_id:
        raise ValueError(f"Invalid fragment_id: no 'T' separator found: {fragment_id!r}")

    date_part = fragment_id.split("T")[0]
    if len(date_part) != 8:
        raise ValueError(
            f"Invalid fragment_id date portion: {date_part!r} (from {fragment_id!r})"
        )

    yyyy = date_part[0:4]
    mm = date_part[4:6]
    dd = date_part[6:8]
    date_str = f"{yyyy}-{mm}-{dd}"

    return f"recordings/{date_str}/{fragment_id}.wav"


def _build_sts_policy(object_key: str, bucket: str) -> dict:
    """Build a single-file STS policy allowing only ``oss:PutObject``.

    The Resource is **exact** — no wildcards.
    """
    return {
        "Version": "1",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["oss:PutObject"],
                "Resource": [
                    f"acs:oss:*:*:{bucket}/{object_key}"
                ],
            }
        ],
    }


def _call_assume_role(object_key: str, config: SharedConfig) -> dict:
    """Call the Aliyun STS AssumeRole REST API (HMAC-SHA1 v1 signing).

    Returns a dict with keys: access_key_id, access_key_secret,
    security_token, expiration (ISO 8601 string).
    """
    policy = _build_sts_policy(object_key, config.oss_bucket)
    policy_json = json.dumps(policy, separators=(",", ":"))

    params: dict[str, str] = {
        "Action": "AssumeRole",
        "Format": "JSON",
        "Version": "2015-04-01",
        "SignatureMethod": "HMAC-SHA1",
        "SignatureVersion": "1.0",
        "SignatureNonce": uuid.uuid4().hex,
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "RoleArn": config.ram_role_arn,
        "RoleSessionName": f"soniscope-upload-{_short_id()}",
        "DurationSeconds": str(STS_MAX_DURATION_SECONDS),
        "Policy": policy_json,
    }

    # Build query string sorted by parameter key
    sorted_keys = sorted(params.keys())
    canonical_qs = "&".join(
        f"{_pct_encode(k)}={_pct_encode(params[k])}" for k in sorted_keys
    )

    string_to_sign = f"GET&{_pct_encode('/')}&{_pct_encode(canonical_qs)}"

    # HMAC-SHA1 signing: key = AccessKeySecret&
    key = (config.aliyun_ak_secret + "&").encode("utf-8")
    signature = hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    sig_b64 = _base64_encode(signature)

    url = f"https://{STS_API_ENDPOINT}/?{canonical_qs}&Signature={_pct_encode(sig_b64)}"

    try:
        req = urllib_request.Request(url)
        with urllib_request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except HTTPError as exc:
        get_logger().error("sts_http_error status=%s body=%s", exc.code, _safe_read(exc))
        raise RuntimeError(f"STS HTTP {exc.code}")
    except URLError as exc:
        raise RuntimeError(f"STS network error: {exc.reason}")
    except json.JSONDecodeError:
        raise RuntimeError("Invalid JSON from STS")

    # Check for API-level errors
    if "Code" in data and data.get("Code") != "Success":
        code = data.get("Code", "Unknown")
        message = data.get("Message", "")
        raise RuntimeError(f"STS API error: {code} — {message}")

    credentials = data.get("Credentials", {})
    if not credentials:
        raise RuntimeError(f"STS response missing Credentials: {data}")

    return {
        "access_key_id": credentials["AccessKeyId"],
        "access_key_secret": credentials["AccessKeySecret"],
        "security_token": credentials["SecurityToken"],
        "expiration": credentials["Expiration"],
    }


def _size_exceeded_error(size: int, max_bytes: int) -> Exception:
    """Raise an AuthError for SIZE_EXCEEDED.

    We import AuthError lazily here to avoid circular imports (auth imports
    from config, sts is called from handlers that import auth).
    """
    from .auth import AuthError
    from .errors import ERROR_SIZE_EXCEEDED

    return AuthError(
        400,
        ERROR_SIZE_EXCEEDED,
        detail=f"Upload size {size} exceeds limit of {max_bytes}",
        extra={"limit_bytes": max_bytes, "actual_bytes": size},
    )


# ---------------------------------------------------------------------------
# Small stdlib helpers
# ---------------------------------------------------------------------------


def _pct_encode(s: str) -> str:
    """Percent-encode *s* per RFC 3986 (uppercase hex, unreserved not encoded)."""
    return urlparse.quote(s, safe="-_.~")


def _base64_encode(data: bytes) -> str:
    """Base64-encode *data* and return a str."""
    import base64
    return base64.b64encode(data).decode("ascii")


def _short_id() -> str:
    """Return a short random identifier for the STS session name."""
    return uuid.uuid4().hex[:8]


def _safe_read(error: HTTPError) -> str:
    """Safely read an HTTPError body as a string."""
    try:
        return error.read().decode("utf-8", errors="replace")[:500]
    except Exception:
        return "<unreadable>"
