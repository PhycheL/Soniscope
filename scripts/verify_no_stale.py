#!/usr/bin/env python3
"""Verify no stale intermediate files — ``make verify-no-stale``.

Checks the Worker runtime directories (``$SONISCOPE_HOME/inbox/``, ``tmp/``)
for leftover intermediate files that indicate incomplete processing or an
unclean crash state:

- ``inbox/*.part`` — partial downloads
- ``inbox/*.wav.tmp`` — transcode in progress
- ``tmp/*.transcript.json.tmp`` — transcription in progress

Usage::

    make verify-no-stale

Environment:
    SONISCOPE_HOME: Worker runtime root (default: ~/SoniScope)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resolve_home() -> Path:
    """Return the Worker runtime home directory."""
    env = os.environ.get("SONISCOPE_HOME")
    if env:
        return Path(env)
    return Path.home() / "SoniScope"


def scan_stale_files(home: Path) -> dict[str, list[Path]]:
    """Scan for stale intermediate files.

    Returns a dict with keys ``part``, ``wav_tmp``, ``transcript_json_tmp``,
    each containing a list of matching Path objects.
    """
    stale: dict[str, list[Path]] = {
        "part": [],
        "wav_tmp": [],
        "transcript_json_tmp": [],
    }

    inbox = home / "inbox"
    if inbox.is_dir():
        for f in inbox.iterdir():
            if f.is_file() and f.suffix == ".part":
                stale["part"].append(f)
            elif f.is_file() and f.suffixes == [".wav", ".tmp"] and f.name.endswith(".wav.tmp"):
                stale["wav_tmp"].append(f)

    tmp = home / "tmp"
    if tmp.is_dir():
        for f in tmp.iterdir():
            if f.is_file() and f.name.endswith(".transcript.json.tmp"):
                stale["transcript_json_tmp"].append(f)

    return stale


def main() -> None:
    home = resolve_home()

    if not home.is_dir():
        print(f"❌ SONISCOPE_HOME 不存在: {home}")
        print("   请设置 SONISCOPE_HOME 环境变量或确保 ~/SoniScope 存在")
        sys.exit(1)

    stale = scan_stale_files(home)

    total = sum(len(v) for v in stale.values())

    if total == 0:
        print("✅ verify-no-stale")
        print(f"   SONISCOPE_HOME: {home}")
        print("   无残留中间态文件")
        sys.exit(0)

    print(f"❌ verify-no-stale — 发现 {total} 个残留中间态文件")
    print(f"   SONISCOPE_HOME: {home}\n")

    if stale["part"]:
        print(f"📂 inbox/*.part（{len(stale['part'])} 个 — 下载中断残留）:")
        for f in sorted(stale["part"]):
            print(f"   {f}")
        print()

    if stale["wav_tmp"]:
        print(f"📂 inbox/*.wav.tmp（{len(stale['wav_tmp'])} 个 — 转码中断残留）:")
        for f in sorted(stale["wav_tmp"]):
            print(f"   {f}")
        print()

    if stale["transcript_json_tmp"]:
        print(f"📂 tmp/*.transcript.json.tmp（{len(stale['transcript_json_tmp'])} 个 — 转写中断残留）:")
        for f in sorted(stale["transcript_json_tmp"]):
            print(f"   {f}")
        print()

    print("\n💡 修复指引：重启 Worker（make worker-run），启动恢复扫描会自动清理这些残留。")
    sys.exit(1)


if __name__ == "__main__":
    main()
