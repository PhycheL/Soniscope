#!/usr/bin/env python3
"""OSS object inspection helper — show-oss-object.

Reads details of a single OSS object given its FRAGMENT_ID, including object
existence, size, ETag, last_modified, and user-defined metadata (x-oss-meta-*).

Usage:
    python scripts/show_oss_object.py <FRAGMENT_ID>

Or via Makefile:
    make show-oss-object FRAGMENT_ID=<id>
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import sys
import time
from email.utils import formatdate
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


# ── Configuration ────────────────────────────────────────────────────────────

OSS_BUCKET = "soniscope-audio"
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"
OSS_REGION = "cn-beijing"


def _load_credentials() -> tuple[str, str]:
    """Load OSS credentials from environment (deploy AK)."""
    ak_id = os.environ.get("ALIYUN_AK_ID") or os.environ.get("ALIYUN_DEPLOY_AK_ID")
    ak_secret = os.environ.get("ALIYUN_AK_SECRET") or os.environ.get("ALIYUN_DEPLOY_AK_SECRET")
    if not ak_id or not ak_secret:
        print("❌ 请设置 ALIYUN_AK_ID / ALIYUN_AK_SECRET 或 ALIYUN_DEPLOY_AK_ID / ALIYUN_DEPLOY_AK_SECRET 环境变量")
        sys.exit(1)
    return ak_id, ak_secret


# ── Fragment ID → OSS Key ────────────────────────────────────────────────────


def fragment_to_date(fragment_id: str) -> str:
    """Extract YYYY-MM-DD from fragment_id's timestamp prefix."""
    if "T" not in fragment_id:
        raise ValueError(f"Invalid fragment_id: no 'T' separator found: {fragment_id!r}")
    date_part = fragment_id.split("T")[0]
    if len(date_part) != 8:
        raise ValueError(f"Invalid fragment_id date portion: {date_part!r}")
    yyyy = date_part[0:4]
    mm = date_part[4:6]
    dd = date_part[6:8]
    return f"{yyyy}-{mm}-{dd}"


def fragment_to_oss_key(fragment_id: str) -> str:
    """Derive OSS object key from fragment_id."""
    date = fragment_to_date(fragment_id)
    return f"recordings/{date}/{fragment_id}.wav"


# ── OSS API (HMAC-SHA1 v1 head-object) ──────────────────────────────────────


def oss_head_object(object_key: str, ak_id: str, ak_secret: str) -> dict:
    """Perform OSS HeadObject and return headers dict, or an empty dict on 404."""
    url = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{object_key}"

    date_str = formatdate(timeval=time.time(), localtime=False, usegmt=True)
    canonicalized_resource = f"/{OSS_BUCKET}/{object_key}"
    string_to_sign = f"HEAD\n\n\n{date_str}\n{canonicalized_resource}"

    signature = base64.b64encode(
        hmac.new(
            ak_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")

    auth_header = f"OSS {ak_id}:{signature}"

    try:
        req = urllib_request.Request(url, method="HEAD")
        req.add_header("Date", date_str)
        req.add_header("Authorization", auth_header)

        with urllib_request.urlopen(req, timeout=10) as resp:
            headers = {}
            for key in resp.headers:
                headers[key.lower()] = resp.headers[key]
            headers["_status"] = 200
            return headers

    except HTTPError as exc:
        if exc.code == 404:
            return {"_status": 404}
        print(f"❌ OSS HTTP error {exc.code} for {object_key}", file=sys.stderr)
        try:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            print(f"   Body: {body}", file=sys.stderr)
        except Exception:
            pass
        return {"_status": exc.code}
    except URLError as exc:
        print(f"❌ OSS network error: {exc.reason}", file=sys.stderr)
        return {"_status": -1}


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point — show OSS object details for a given fragment_id."""
    parser = argparse.ArgumentParser(
        description="展示 OSS 对象详情（对象存在性、size、etag、last_modified、用户自定义元数据）"
    )
    parser.add_argument("fragment_id", help="Fragment ID")
    args = parser.parse_args()

    fragment_id = args.fragment_id

    print(f"🔍 show-oss-object  FRAGMENT_ID={fragment_id}\n")

    # Derive OSS key
    try:
        object_key = fragment_to_oss_key(fragment_id)
    except ValueError as e:
        print(f"❌ 无法解析 fragment_id: {e}")
        sys.exit(1)

    print(f"   Object Key: {object_key}")

    # HeadObject
    ak_id, ak_secret = _load_credentials()
    headers = oss_head_object(object_key, ak_id, ak_secret)

    status = headers.get("_status", 0)

    if status == 404:
        print(f"\n📭 对象不存在 (404)")
        print(f"   {object_key}")
        sys.exit(0)

    if status != 200:
        print(f"\n❌ 查询失败 (HTTP {status})")
        sys.exit(1)

    # Object exists — display details
    content_length = headers.get("content-length", "—")
    etag = headers.get("etag", "—").strip('"')
    last_modified = headers.get("last-modified", "—")

    print(f"\n✅ 对象存在")
    print(f"   Size:          {content_length} bytes")
    print(f"   ETag:          {etag}")
    print(f"   Last-Modified: {last_modified}")

    # User-defined metadata (x-oss-meta-*)
    meta = {}
    for key, value in headers.items():
        if key.startswith("x-oss-meta-"):
            short_key = key[len("x-oss-meta-"):]
            meta[short_key] = value

    if meta:
        print(f"\n📋 用户自定义元数据 (x-oss-meta-*):")
        for mk in sorted(meta.keys()):
            print(f"   {mk}: {meta[mk]}")
    else:
        print(f"\n📋 无用户自定义元数据")


if __name__ == "__main__":
    main()
