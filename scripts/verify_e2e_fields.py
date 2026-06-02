#!/usr/bin/env python3
"""Verify E2E manifest key fields — ``make verify-e2e-fields``.

Scans ``$SONISCOPE_HOME/fragments/<DATE>/`` and confirms every Fragment's
``manifest.json`` contains non-empty values for these critical fields:

- ``upload.verified_at`` — the verify-upload FC call timestamp
- ``transcription.completed_at`` — the ASR transcription completion timestamp

Usage::

    make verify-e2e-fields DATE=<YYYY-MM-DD>

Environment:
    SONISCOPE_HOME: Worker runtime root (default: ~/SoniScope)
    DATE: Target date, format YYYY-MM-DD (required)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Fields to check, as dotted paths into manifest.json
REQUIRED_FIELDS: list[tuple[str, str]] = [
    ("upload.verified_at", "upload.verified_at"),
    ("transcription.completed_at", "transcription.completed_at"),
]


def resolve_home() -> Path:
    """Return the Worker runtime home directory."""
    env = os.environ.get("SONISCOPE_HOME")
    if env:
        return Path(env)
    return Path.home() / "SoniScope"


def _get_nested(d: dict, path: str) -> object:
    """Get a nested dict value by dotted path, e.g. ``upload.verified_at``."""
    parts = path.split(".")
    current: object = d
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _check_fields(manifest: dict, frag_id: str) -> list[str]:
    """Check required fields in a manifest.

    Returns a list of failure messages (one per missing/empty field).
    """
    failures: list[str] = []

    for field_path, display_name in REQUIRED_FIELDS:
        value = _get_nested(manifest, field_path)
        if value is None or (isinstance(value, str) and not value.strip()):
            failures.append(
                f"{frag_id}: {display_name} 为空或不存在"
            )

    return failures


def main() -> None:
    date_str = os.environ.get("DATE", "")
    if not date_str:
        print("❌ 请设置 DATE 环境变量，格式 YYYY-MM-DD")
        print("   用法: make verify-e2e-fields DATE=2026-06-02")
        sys.exit(1)

    home = resolve_home()

    if not home.is_dir():
        print(f"❌ SONISCOPE_HOME 不存在: {home}")
        print("   请设置 SONISCOPE_HOME 环境变量或确保 ~/SoniScope 存在")
        sys.exit(1)

    frag_dir = home / "fragments" / date_str
    if not frag_dir.is_dir():
        print(f"❌ 目标日期目录不存在: {frag_dir}")
        print("   请确认 DATE 正确且 Worker 已完成该日期的处理")
        sys.exit(1)

    fragment_dirs = sorted([d for d in frag_dir.iterdir() if d.is_dir()])

    if not fragment_dirs:
        print(f"ℹ️  目标日期 {date_str} 下无 Fragment 目录")
        print(f"   {frag_dir}")
        print("✅ verify-e2e-fields PASS（无目录需检查）")
        sys.exit(0)

    passes: list[str] = []
    failures: list[str] = []

    for d in fragment_dirs:
        frag_id = d.name
        manifest_path = d / "manifest.json"

        if not manifest_path.is_file():
            failures.append(f"{frag_id}: manifest.json 不存在")
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{frag_id}: manifest.json 解析失败 — {exc}")
            continue

        field_failures = _check_fields(manifest, frag_id)
        if field_failures:
            failures.extend(field_failures)
        else:
            passes.append(frag_id)

    total = len(fragment_dirs)
    passed = len(passes)
    failed = len(failures)

    print(f"🔍 verify-e2e-fields  DATE={date_str}")
    print(f"   SONISCOPE_HOME: {home}")
    print(f"   扫描目录: {frag_dir}")
    print(f"\n   Fragment 总数: {total}")
    print(f"   通过: {passed}/{total}")
    print(f"   失败: {failed}/{total}\n")

    if failures:
        print("❌ 关键字段缺失:")
        for msg in failures:
            print(f"   {msg}")

    if failed > 0:
        print(f"\n❌ verify-e2e-fields FAIL（{failed} 个字段缺失）")
        sys.exit(1)

    print("✅ verify-e2e-fields PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
