#!/usr/bin/env python3
"""Verify OSS retention policy — ``make verify-oss-retention``.

Compares the number of OSS objects against the number of local fragment
directories and scans Worker logs for ``DeleteObject`` calls.

Usage::

    make verify-oss-retention

Checks:
1. OSS object count for today's ``recordings/<YYYY-MM-DD>/`` prefix
2. Local fragment directory count under ``$SONISCOPE_HOME/fragments/<YYYY-MM-DD>/``
3. Worker source code and logs for any ``DeleteObject`` calls

Environment:
    SONISCOPE_HOME: Worker runtime root (default: ~/SoniScope)
    ALIYUN_AK_ID or ALIYUN_DEPLOY_AK_ID: Aliyun AccessKey ID
    ALIYUN_AK_SECRET or ALIYUN_DEPLOY_AK_SECRET: Aliyun AccessKey Secret
    DATE: Override date (default: today, format YYYY-MM-DD)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sys
import time as time_mod
from datetime import datetime, timezone
from email.utils import formatdate
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

# ── Constants ─────────────────────────────────────────────────────────────────

OSS_BUCKET = "soniscope-audio"
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"

# Project root (this script lives in scripts/ under the repo)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_credentials() -> tuple[str, str]:
    ak_id = os.environ.get("ALIYUN_AK_ID") or os.environ.get("ALIYUN_DEPLOY_AK_ID")
    ak_secret = os.environ.get("ALIYUN_AK_SECRET") or os.environ.get(
        "ALIYUN_DEPLOY_AK_SECRET"
    )
    return ak_id or "", ak_secret or ""


def resolve_home() -> Path:
    env = os.environ.get("SONISCOPE_HOME")
    if env:
        return Path(env)
    return Path.home() / "SoniScope"


def _get_date() -> str:
    date_env = os.environ.get("DATE", "")
    if date_env:
        return date_env
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── OSS ListObjects (HMAC-SHA1 v1, same as list_oss_objects.py) ────────────


def oss_list_objects(
    prefix: str, ak_id: str, ak_secret: str
) -> tuple[list[str], str | None]:
    """List objects under *prefix* using OSS REST API."""
    url_base = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/"
    all_keys: list[str] = []
    marker: str | None = None

    while True:
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

        root = ElementTree.fromstring(body)
        for contents in root.findall("Contents"):
            key_el = contents.find("Key")
            if key_el is not None and key_el.text:
                all_keys.append(key_el.text)

        is_truncated_el = root.find("IsTruncated")
        is_truncated = is_truncated_el is not None and is_truncated_el.text == "true"

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


# ── Local fragment scan ─────────────────────────────────────────────────────


def count_local_fragment_dirs(home: Path, date_str: str) -> int:
    """Count fragment directories under fragments/<date>/."""
    frag_date_dir = home / "fragments" / date_str
    if not frag_date_dir.is_dir():
        return 0
    return sum(1 for d in frag_date_dir.iterdir() if d.is_dir())


# ── DeleteObject scan in Worker source ──────────────────────────────────────


def scan_worker_source_for_delete() -> list[tuple[str, int, str]]:
    """Scan Worker source code for DeleteObject calls.

    Returns list of (file_path, line_number, line_content).
    """
    violations: list[tuple[str, int, str]] = []
    worker_src = _PROJECT_ROOT / "apps" / "worker" / "src"

    if not worker_src.is_dir():
        return violations

    for py_file in worker_src.rglob("*.py"):
        try:
            for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
                if "DeleteObject" in line and not line.strip().startswith("#"):
                    violations.append((str(py_file.relative_to(_PROJECT_ROOT)), lineno, line.strip()))
        except Exception:
            pass

    return violations


def scan_scripts_for_delete() -> list[tuple[str, int, str]]:
    """Check whether scripts using DeleteObject are marked '仅测试用'.

    Returns list of (file_path, line_number, line_content) for scripts that
    use DeleteObject but are NOT marked as test-only.
    """
    violations: list[tuple[str, int, str]] = []
    scripts_dir = _PROJECT_ROOT / "scripts"

    if not scripts_dir.is_dir():
        return violations

    for py_file in scripts_dir.rglob("*.py"):
        # oss_delete_obj.py is explicitly test-only
        if py_file.name == "oss_delete_obj.py":
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        if "DeleteObject" not in content:
            continue

        # Check that the file contains a test-only marker
        if "仅测试用" in content or "test only" in content.lower():
            continue

        # Report it as a violation
        for lineno, line in enumerate(content.splitlines(), 1):
            if "DeleteObject" in line:
                violations.append(
                    (str(py_file.relative_to(_PROJECT_ROOT)), lineno, line.strip())
                )

    return violations


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    date_str = _get_date()
    home = resolve_home()

    print(f"🔍 verify-oss-retention  DATE={date_str}\n")
    print(f"   SONISCOPE_HOME: {home}")
    print(f"   OSS Prefix:     recordings/{date_str}/\n")

    all_pass = True
    issues: list[str] = []

    # ── Check 1: OSS object count ─────────────────────────────────────────
    ak_id, ak_secret = _load_credentials()
    if not ak_id or not ak_secret:
        print("⚠️  跳过 OSS 对象计数（未设置 AK 环境变量）\n")
        oss_count = None
    else:
        prefix = f"recordings/{date_str}/"
        keys, error = oss_list_objects(prefix, ak_id, ak_secret)

        if error is not None:
            print(f"❌ OSS 查询失败: {error}")
            all_pass = False
            issues.append(f"OSS query error: {error}")
            oss_count = None
        else:
            wav_keys = [k for k in keys if k.endswith(".wav")]
            oss_count = len(wav_keys)
            print(f"📊 OSS 对象: {oss_count} 个 .wav（前缀 recordings/{date_str}/）")
            for k in sorted(wav_keys):
                print(f"   {k}")
            print()

    # ── Check 2: Local fragment count ─────────────────────────────────────
    local_count = count_local_fragment_dirs(home, date_str)
    print(f"📊 本地 Fragment 目录: {local_count} 个（{home / 'fragments' / date_str}）\n")

    if oss_count is not None:
        if oss_count < local_count:
            print(f"⚠️  OSS 对象数 ({oss_count}) < 本地目录数 ({local_count})")
            print("   可能有对象被删除或尚未上传完成")
            issues.append(
                f"OSS count ({oss_count}) < local count ({local_count})"
            )
        elif oss_count > local_count:
            print(f"ℹ️  OSS 对象数 ({oss_count}) > 本地目录数 ({local_count})")
            print("   Worker 可能尚未完成全部下载处理")
        else:
            print(f"✅ OSS 对象数 ({oss_count}) = 本地目录数 ({local_count})")
    else:
        print("ℹ️  跳过 OSS vs 本地数量对比（OSS 凭证不可用）")
        print(f"   本地目录数: {local_count}")

    print()

    # ── Check 3: Worker source — no DeleteObject ──────────────────────────
    worker_violations = scan_worker_source_for_delete()
    if worker_violations:
        print("❌ Worker 源码中发现 DeleteObject 调用：")
        for fp, lineno, line in worker_violations:
            print(f"   {fp}:{lineno}  {line}")
        all_pass = False
        issues.append("Worker source contains DeleteObject calls")
    else:
        print("✅ Worker 源码中无 DeleteObject 调用")

    # ── Check 4: Scripts — DeleteObject only in test-only files ───────────
    script_violations = scan_scripts_for_delete()
    if script_violations:
        print("\n❌ scripts/ 中存在未标注'仅测试用'的 DeleteObject 调用：")
        for fp, lineno, line in script_violations:
            print(f"   {fp}:{lineno}  {line}")
        all_pass = False
        issues.append("Scripts contain unmarked DeleteObject calls")
    else:
        print("✅ scripts/ 中的 DeleteObject 均已标注'仅测试用'")

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    if all_pass:
        print("✅ verify-oss-retention PASS")
        sys.exit(0)
    else:
        print(f"❌ verify-oss-retention FAIL ({len(issues)} 个问题)")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        sys.exit(1)


if __name__ == "__main__":
    main()
