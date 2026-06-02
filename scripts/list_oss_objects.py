#!/usr/bin/env python3
"""List OSS objects for a given date — ``make list-oss-objects``.

Lists all ``.wav`` objects under ``recordings/<YYYY-MM-DD>/`` in the
soniscope-audio bucket and outputs the total count.

Usage::

    python scripts/list_oss_objects.py <YYYY-MM-DD>

Or via Makefile::

    make list-oss-objects DATE=<YYYY-MM-DD>

Required environment variables:
    ALIYUN_AK_ID or ALIYUN_DEPLOY_AK_ID: Aliyun AccessKey ID
    ALIYUN_AK_SECRET or ALIYUN_DEPLOY_AK_SECRET: Aliyun AccessKey Secret
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import sys
import time as time_mod
from email.utils import formatdate
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

# ── Constants ─────────────────────────────────────────────────────────────────

OSS_BUCKET = "soniscope-audio"
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"


def _load_credentials() -> tuple[str, str]:
    """Load OSS credentials from environment."""
    ak_id = os.environ.get("ALIYUN_AK_ID") or os.environ.get("ALIYUN_DEPLOY_AK_ID")
    ak_secret = os.environ.get("ALIYUN_AK_SECRET") or os.environ.get(
        "ALIYUN_DEPLOY_AK_SECRET"
    )
    if not ak_id or not ak_secret:
        print(
            "❌ 请设置 ALIYUN_AK_ID / ALIYUN_AK_SECRET 或 "
            "ALIYUN_DEPLOY_AK_ID / ALIYUN_DEPLOY_AK_SECRET 环境变量"
        )
        sys.exit(1)
    return ak_id, ak_secret


def _validate_date(date_str: str) -> str:
    """Validate and normalize date string as YYYY-MM-DD."""
    import re

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        print(f"❌ 无效日期格式: {date_str!r}，期望格式: YYYY-MM-DD")
        sys.exit(1)
    return date_str


# ── OSS ListObjects (HMAC-SHA1 v1) ──────────────────────────────────────────


def oss_list_objects(
    prefix: str, ak_id: str, ak_secret: str
) -> tuple[list[str], str | None]:
    """List objects under *prefix* in the OSS bucket.

    Uses HMAC-SHA1 v1 signature against the OSS REST API (GET with query
    parameters).  Handles pagination via ``NextMarker`` / ``IsTruncated``.

    Returns (object_keys, error_message).  error_message is None on success.
    """
    url_base = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/"
    all_keys: list[str] = []
    marker: str | None = None

    while True:
        # Build query string
        params = f"?prefix={urllib_request.quote(prefix, safe='')}&max-keys=1000"
        if marker:
            params += f"&marker={urllib_request.quote(marker, safe='')}"

        url = f"{url_base}{params}"

        date_str = formatdate(timeval=time_mod.time(), localtime=False, usegmt=True)
        canonicalized_resource = f"/{OSS_BUCKET}/"

        string_to_sign = f"GET\n\n\n{date_str}\n{canonicalized_resource}"

        signature = base64.b64encode(
            hmac.new(
                ak_secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("ascii")

        auth_header = f"OSS {ak_id}:{signature}"

        try:
            req = urllib_request.Request(url, method="GET")
            req.add_header("Date", date_str)
            req.add_header("Authorization", auth_header)

            with urllib_request.urlopen(req, timeout=30) as resp:
                body = resp.read()

        except HTTPError as exc:
            body_content = ""
            try:
                body_content = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            return [], f"HTTP {exc.code}: {exc.reason} — {body_content}"
        except URLError as exc:
            return [], f"Network error: {exc.reason}"

        # Parse XML body
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as exc:
            return [], f"XML parse error: {exc}"

        # Collect keys from <Contents><Key> elements
        ns = ""  # OSS ListObjectsResult has no default namespace
        for contents in root.findall("Contents"):
            key_el = contents.find("Key")
            if key_el is not None and key_el.text:
                all_keys.append(key_el.text)

        # Check if truncated
        is_truncated_el = root.find("IsTruncated")
        is_truncated = (
            is_truncated_el is not None and is_truncated_el.text == "true"
        )

        if not is_truncated:
            break

        next_marker_el = root.find("NextMarker")
        if next_marker_el is not None and next_marker_el.text:
            marker = next_marker_el.text
        elif all_keys:
            marker = all_keys[-1]
        else:
            break

    return all_keys, None


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="列出指定日期的 OSS 对象（recordings/<date>/ 前缀）并输出总数"
    )
    parser.add_argument("date", help="日期，格式 YYYY-MM-DD")
    args = parser.parse_args()

    date = _validate_date(args.date)
    prefix = f"recordings/{date}/"

    print(f"📋 list-oss-objects  DATE={date}")
    print(f"   Prefix: {prefix}\n")

    ak_id, ak_secret = _load_credentials()
    keys, error = oss_list_objects(prefix, ak_id, ak_secret)

    if error is not None:
        print(f"❌ 查询失败: {error}")
        sys.exit(1)

    # Filter to .wav files only
    wav_keys = [k for k in keys if k.endswith(".wav")]
    non_wav = [k for k in keys if not k.endswith(".wav")]

    if wav_keys:
        print(f"✅ 找到 {len(wav_keys)} 个 .wav 对象：")
        for k in sorted(wav_keys):
            print(f"   {k}")
    else:
        print(f"📭 未找到 .wav 对象（前缀 {prefix}）")

    if non_wav:
        print(f"\n⚠️  另外 {len(non_wav)} 个非 .wav 对象：")
        for k in sorted(non_wav):
            print(f"   {k}")

    print(f"\n总计: {len(wav_keys)} 个 .wav 对象")
    if non_wav:
        print(f"      ({len(keys)} 个对象含非 .wav)")


if __name__ == "__main__":
    main()
