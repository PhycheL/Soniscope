"""FC shared OSS — HeadObject verification using HMAC-SHA1 (v1) signing.

Uses stdlib only (urllib, hmac, hashlib, base64) — same pattern as sts.py.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time as _time
from email.utils import formatdate
from typing import NamedTuple
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from .config import SharedConfig, read_shared_config
from .logging import get_logger


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class HeadObjectResult(NamedTuple):
    """Immutable result of an OSS HeadObject call."""

    found: bool
    content_length: int | None
    etag: str | None
    last_modified: str | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def head_object(
    object_key: str,
    config: SharedConfig | None = None,
) -> HeadObjectResult:
    """Perform HeadObject on *object_key* in the configured OSS bucket.

    Uses HMAC-SHA1 v1 signing against the OSS REST API — no additional SDK
    dependency required at FC runtime.

    Args:
        object_key: The full OSS object key (e.g.
            ``recordings/2026-05-26/xxx.wav``).
        config: Optional pre-loaded config; read from env if ``None``.

    Returns:
        A :class:`HeadObjectResult`.

    Raises:
        RuntimeError: on network errors or non-404 HTTP errors.
    """
    if config is None:
        config = read_shared_config()

    logger = get_logger()

    # ── Build the OSS URL (virtual-hosted style) ──
    # https://<bucket>.<endpoint>/<object_key>
    url = f"https://{config.oss_bucket}.{config.oss_endpoint}/{object_key}"

    # ── Build the string to sign (OSS HMAC-SHA1 v1) ──
    # StringToSign = VERB + "\n" + Content-MD5 + "\n" + Content-Type + "\n"
    #               + Date + "\n" + CanonicalizedOSSHeaders
    #               + CanonicalizedResource
    date_str = formatdate(timeval=_time.time(), localtime=False, usegmt=True)
    canonicalized_resource = f"/{config.oss_bucket}/{object_key}"
    string_to_sign = (
        f"HEAD\n\n\n{date_str}\n{canonicalized_resource}"
    )

    signature = base64.b64encode(
        hmac.new(
            config.aliyun_oss_ak_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")

    auth_header = f"OSS {config.aliyun_oss_ak_id}:{signature}"

    logger.debug("oss_headobject_request object_key=%s", object_key)

    try:
        req = urllib_request.Request(url, method="HEAD")
        req.add_header("Date", date_str)
        req.add_header("Authorization", auth_header)

        with urllib_request.urlopen(req, timeout=10) as resp:
            content_length_raw = resp.headers.get("Content-Length")
            content_length: int | None = (
                int(content_length_raw) if content_length_raw is not None else None
            )
            etag = resp.headers.get("ETag", "").strip('"')
            last_modified = resp.headers.get("Last-Modified", "")

            logger.debug(
                "oss_headobject_success object_key=%s size=%s etag=%s",
                object_key, content_length, etag,
            )
            return HeadObjectResult(
                found=True,
                content_length=content_length,
                etag=etag,
                last_modified=last_modified,
            )

    except HTTPError as exc:
        if exc.code == 404:
            logger.info("oss_headobject_not_found object_key=%s", object_key)
            return HeadObjectResult(
                found=False,
                content_length=None,
                etag=None,
                last_modified=None,
            )
        # Other HTTP errors
        logger.error(
            "oss_headobject_http_error status=%s object_key=%s",
            exc.code, object_key,
        )
        raise RuntimeError(f"OSS HeadObject HTTP {exc.code}")

    except URLError as exc:
        logger.error(
            "oss_headobject_network_error object_key=%s err=%s",
            object_key, exc.reason,
        )
        raise RuntimeError(f"OSS HeadObject network error: {exc.reason}")
