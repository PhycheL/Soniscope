"""``make oss-delete-obj`` — delete an OSS object (仅测试用).

⚠️  **仅测试用** — 此脚本仅用于构造测试场景（如验证 OBJECT_NOT_FOUND 路径）。
Worker 业务源码中不存在 DeleteObject 调用。

Derives the OSS object key from a fragment_id using the standard
``recordings/<YYYY-MM-DD>/<fragment_id>.wav`` pattern, then deletes it
via the OSS REST API with HMAC-SHA1 v1 signing.

Usage::

    python scripts/oss_delete_obj.py <fragment_id>

Required environment variables:
    ALIYUN_DEPLOY_AK_ID: Aliyun AccessKey ID (deploy credentials)
    ALIYUN_DEPLOY_AK_SECRET: Aliyun AccessKey Secret (deploy credentials)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sys
import time as _time
from email.utils import formatdate
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

# ── Constants ─────────────────────────────────────────────────────────────────

OSS_BUCKET = "soniscope-audio"
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"
HELP_NOTE = "⚠️  仅测试用 — Worker 业务源码中不存在 DeleteObject 调用"


def _fragment_oss_key(fragment_id: str) -> str:
    """Derive the OSS object key from a fragment_id.

    Format: ``recordings/<YYYY-MM-DD>/<fragment_id>.wav``
    """
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


def _delete_object(object_key: str) -> tuple[bool, str]:
    """Delete *object_key* from the configured OSS bucket.

    Uses HMAC-SHA1 v1 signing against the OSS REST API.

    Returns (success, detail_message).
    """
    ak_id = os.environ.get("ALIYUN_DEPLOY_AK_ID", "")
    ak_secret = os.environ.get("ALIYUN_DEPLOY_AK_SECRET", "")

    if not ak_id or not ak_secret:
        return False, "ALIYUN_DEPLOY_AK_ID and ALIYUN_DEPLOY_AK_SECRET must be set"

    url = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{object_key}"

    date_str = formatdate(timeval=_time.time(), localtime=False, usegmt=True)
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

        with urllib_request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 204):
                return True, f"Deleted: {object_key}"
            return False, f"Unexpected status {resp.status}"

    except HTTPError as exc:
        if exc.code == 404:
            return True, f"Object already absent (404): {object_key}"
        return False, f"HTTP {exc.code}: {exc.reason}"

    except URLError as exc:
        return False, f"Network error: {exc.reason}"


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <fragment_id>", file=sys.stderr)
        print(f"\n{HELP_NOTE}", file=sys.stderr)
        sys.exit(2)

    if sys.argv[1] in ("--help", "-h", "help"):
        print(f"Usage: python {sys.argv[0]} <fragment_id>")
        print()
        print("  Delete an OSS object by fragment_id.")
        print(f"  {HELP_NOTE}")
        print()
        print("Required environment variables:")
        print("  ALIYUN_DEPLOY_AK_ID       Aliyun AccessKey ID (deploy credentials)")
        print("  ALIYUN_DEPLOY_AK_SECRET   Aliyun AccessKey Secret (deploy credentials)")
        print()
        print(f"  {HELP_NOTE}")
        sys.exit(0)

    fragment_id = sys.argv[1]

    try:
        object_key = _fragment_oss_key(fragment_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"{HELP_NOTE}")
    print(f"Fragment ID: {fragment_id}")
    print(f"Object key:  {object_key}")
    print()

    # Confirmation prompt (unless --yes flag)
    if "--yes" not in sys.argv and "-y" not in sys.argv:
        confirm = input(f"确认删除 OSS 对象 {object_key}? [y/N]: ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("已取消。")
            sys.exit(0)

    success, detail = _delete_object(object_key)
    if success:
        print(f"✅ {detail}")
    else:
        print(f"❌ {detail}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
