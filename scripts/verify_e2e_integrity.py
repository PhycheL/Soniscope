#!/usr/bin/env python3
"""Verify E2E fragment directory integrity — ``make verify-e2e-integrity``.

Scans ``$SONISCOPE_HOME/fragments/<DATE>/`` and confirms every Fragment
directory contains all 5 required files:

- ``audio.wav``
- ``manifest.json``
- ``transcript.json``
- ``transcript.txt``
- ``.done``

Usage::

    make verify-e2e-integrity DATE=<YYYY-MM-DD>

Environment:
    SONISCOPE_HOME: Worker runtime root (default: ~/SoniScope)
    DATE: Target date, format YYYY-MM-DD (required)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REQUIRED_FILES: list[str] = [
    "audio.wav",
    "manifest.json",
    "transcript.json",
    "transcript.txt",
    ".done",
]


def resolve_home() -> Path:
    """Return the Worker runtime home directory."""
    env = os.environ.get("SONISCOPE_HOME")
    if env:
        return Path(env)
    return Path.home() / "SoniScope"


def main() -> None:
    date_str = os.environ.get("DATE", "")
    if not date_str:
        print("❌ 请设置 DATE 环境变量，格式 YYYY-MM-DD")
        print("   用法: make verify-e2e-integrity DATE=2026-06-02")
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
        print("✅ verify-e2e-integrity PASS（无目录需检查）")
        sys.exit(0)

    passes: list[str] = []
    failures: list[tuple[str, list[str]]] = []

    for d in fragment_dirs:
        frag_id = d.name
        missing = [f for f in REQUIRED_FILES if not (d / f).is_file()]
        if missing:
            failures.append((frag_id, missing))
        else:
            passes.append(frag_id)

    total = len(fragment_dirs)
    passed = len(passes)
    failed = len(failures)

    print(f"🔍 verify-e2e-integrity  DATE={date_str}")
    print(f"   SONISCOPE_HOME: {home}")
    print(f"   扫描目录: {frag_dir}")
    print(f"\n   Fragment 总数: {total}")
    print(f"   通过: {passed}/{total}")
    print(f"   失败: {failed}/{total}\n")

    if failures:
        print("❌ 不完整的 Fragment 目录:")
        for frag_id, missing in failures:
            print(f"   {frag_id}: 缺少 {', '.join(missing)}")

    if failed > 0:
        print(f"\n❌ verify-e2e-integrity FAIL（{failed} 个 Fragment 不完整）")
        sys.exit(1)

    print("✅ verify-e2e-integrity PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
