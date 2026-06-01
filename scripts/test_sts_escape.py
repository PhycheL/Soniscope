#!/usr/bin/env python3
"""STS escape verification — verifies that STS temporary credentials are
scoped to a single OSS object key and cannot be used for other actions.

Tests:
- PutObject to a different object key → AccessDenied
- GetObject on any key → AccessDenied
- ListObjects → AccessDenied
- DeleteObject → AccessDenied

Usage:
    python scripts/test_sts_escape.py <ACCESS_KEY_ID> <ACCESS_KEY_SECRET> <SECURITY_TOKEN> <EXPECTED_OBJECT_KEY>

Or via Makefile:
    make test-sts-escape
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import sys
import time
from email.utils import formatdate
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


OSS_BUCKET = "soniscope-audio"
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"


# ── OSS Signing Helpers ──────────────────────────────────────────────────────


def _oss_put_object(
    object_key: str,
    data: bytes,
    ak_id: str,
    ak_secret: str,
    security_token: str,
) -> tuple[int, str]:
    """Attempt PutObject to a specific OSS key using STS credentials.

    Returns (status_code, body_text).
    """
    url = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{object_key}"
    date_str = formatdate(timeval=time.time(), localtime=False, usegmt=True)
    content_type = "application/octet-stream"
    content_md5 = ""  # optional

    canonicalized_resource = f"/{OSS_BUCKET}/{object_key}"
    string_to_sign = f"PUT\n{content_md5}\n{content_type}\n{date_str}\n{canonicalized_resource}"

    signature = base64.b64encode(
        hmac.new(
            ak_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")

    auth_header = f"OSS {ak_id}:{signature}"

    try:
        req = urllib_request.Request(url, data=data, method="PUT")
        req.add_header("Date", date_str)
        req.add_header("Authorization", auth_header)
        req.add_header("Content-Type", content_type)
        req.add_header("x-oss-security-token", security_token)

        with urllib_request.urlopen(req, timeout=15) as resp:
            return resp.status, ""
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
        except Exception:
            pass
        return exc.code, body
    except URLError as exc:
        return -1, f"Network error: {exc.reason}"


def _oss_get_object(
    object_key: str,
    ak_id: str,
    ak_secret: str,
    security_token: str,
) -> tuple[int, str]:
    """Attempt GetObject from OSS using STS credentials."""
    url = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{object_key}"
    date_str = formatdate(timeval=time.time(), localtime=False, usegmt=True)
    canonicalized_resource = f"/{OSS_BUCKET}/{object_key}"
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
        req.add_header("x-oss-security-token", security_token)

        with urllib_request.urlopen(req, timeout=15) as resp:
            return resp.status, ""
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
        except Exception:
            pass
        return exc.code, body
    except URLError as exc:
        return -1, f"Network error: {exc.reason}"


def _oss_list_objects(
    ak_id: str,
    ak_secret: str,
    security_token: str,
) -> tuple[int, str]:
    """Attempt ListObjects on the bucket using STS credentials."""
    url = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/"
    date_str = formatdate(timeval=time.time(), localtime=False, usegmt=True)
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
        req.add_header("x-oss-security-token", security_token)

        with urllib_request.urlopen(req, timeout=15) as resp:
            return resp.status, ""
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
        except Exception:
            pass
        return exc.code, body
    except URLError as exc:
        return -1, f"Network error: {exc.reason}"


def _oss_delete_object(
    object_key: str,
    ak_id: str,
    ak_secret: str,
    security_token: str,
) -> tuple[int, str]:
    """Attempt DeleteObject using STS credentials."""
    url = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{object_key}"
    date_str = formatdate(timeval=time.time(), localtime=False, usegmt=True)
    canonicalized_resource = f"/{OSS_BUCKET}/{object_key}"
    string_to_sign = f"DELETE\n\n\n{date_str}\n{canonicalized_resource}"

    signature = base64.b64encode(
        hmac.new(
            ak_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")

    auth_header = f"OSS {ak_id}:{signature}"

    try:
        req = urllib_request.Request(url, method="DELETE")
        req.add_header("Date", date_str)
        req.add_header("Authorization", auth_header)
        req.add_header("x-oss-security-token", security_token)

        with urllib_request.urlopen(req, timeout=15) as resp:
            return resp.status, ""
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
        except Exception:
            pass
        return exc.code, body
    except URLError as exc:
        return -1, f"Network error: {exc.reason}"


# ── Test Runner ──────────────────────────────────────────────────────────────


def _check_access_denied(status_code: int, body: str) -> bool:
    """Check if the response indicates AccessDenied."""
    if status_code == 403:
        return True
    if "AccessDenied" in body:
        return True
    if "Access Denied" in body:
        return True
    return False


def main() -> None:
    """Run the STS escape verification test suite."""
    parser = argparse.ArgumentParser(
        description="STS 越权验证 — 验证临时凭证不能用于非授权操作"
    )
    parser.add_argument("access_key_id", help="STS AccessKeyId")
    parser.add_argument("access_key_secret", help="STS AccessKeySecret")
    parser.add_argument("security_token", help="STS SecurityToken")
    parser.add_argument("object_key", help="授权上传的 object key")
    args = parser.parse_args()

    ak_id = args.access_key_id
    ak_secret = args.access_key_secret
    token = args.security_token
    expected_key = args.object_key

    print("🧪 STS 越权验证")
    print(f"   授权 object key: {expected_key}")
    print()

    results = []

    # Test 1: PutObject to a DIFFERENT key → must be AccessDenied
    print("=" * 60)
    print("Test 1: PutObject to OTHER key (must be AccessDenied)")
    other_key = f"recordings/2999-01-01/test_escape_{int(time.time())}.wav"
    status, body = _oss_put_object(other_key, b"test", ak_id, ak_secret, token)
    passed = _check_access_denied(status, body)
    results.append(("PutObject → other key", passed, status, body[:200] if body else ""))
    print(f"   Status: {status} — {'✅ PASS' if passed else '❌ FAIL'}")
    if not passed:
        print(f"   WARNING: STS credential was NOT properly scoped! ({status})")
        if body:
            print(f"   Body: {body[:200]}")

    # Test 2: GetObject on ANY key → must be AccessDenied
    print()
    print("=" * 60)
    print("Test 2: GetObject (must be AccessDenied)")
    status, body = _oss_get_object(expected_key, ak_id, ak_secret, token)
    passed = _check_access_denied(status, body)
    results.append(("GetObject", passed, status, body[:200] if body else ""))
    print(f"   Status: {status} — {'✅ PASS' if passed else '❌ FAIL'}")

    # Test 3: ListObjects → must be AccessDenied
    print()
    print("=" * 60)
    print("Test 3: ListObjects (must be AccessDenied)")
    status, body = _oss_list_objects(ak_id, ak_secret, token)
    passed = _check_access_denied(status, body)
    results.append(("ListObjects", passed, status, body[:200] if body else ""))
    print(f"   Status: {status} — {'✅ PASS' if passed else '❌ FAIL'}")

    # Test 4: DeleteObject → must be AccessDenied
    print()
    print("=" * 60)
    print("Test 4: DeleteObject (must be AccessDenied)")
    status, body = _oss_delete_object(expected_key, ak_id, ak_secret, token)
    passed = _check_access_denied(status, body)
    results.append(("DeleteObject", passed, status, body[:200] if body else ""))
    print(f"   Status: {status} — {'✅ PASS' if passed else '❌ FAIL'}")

    # Summary
    print()
    print("=" * 60)
    print("📊 汇总")
    print("=" * 60)
    all_pass = True
    for name, passed, status, detail in results:
        mark = "✅ PASS" if passed else "❌ FAIL"
        all_pass = all_pass and passed
        print(f"   {name}: {mark} (HTTP {status})")

    print()
    if all_pass:
        print("✅ 全部测试通过 — STS 凭证已被正确限定在单个 OSS object key 的 PutObject 权限")
    else:
        print("❌ 存在失败测试 — STS 凭证策略可能过于宽松")
        sys.exit(1)


if __name__ == "__main__":
    main()
