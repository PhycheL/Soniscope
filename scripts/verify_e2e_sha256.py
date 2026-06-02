#!/usr/bin/env python3
"""Verify E2E SHA-256 consistency — ``make verify-e2e-sha256``.

Scans ``$SONISCOPE_HOME/fragments/<DATE>/`` and validates SHA-256 rules
per tech-spec §3.3:

- **WAV passthrough path**: ``audio.sha256`` must equal
  ``upload.original_sha256`` (the audio didn't change through the pipeline).

- **Non-WAV transcode path**: ``audio.sha256`` and
  ``upload.original_sha256`` must both be non-null, non-empty values.
  They are expected to differ because the audio was re-encoded.

Usage::

    make verify-e2e-sha256 DATE=<YYYY-MM-DD>

Environment:
    SONISCOPE_HOME: Worker runtime root (default: ~/SoniScope)
    DATE: Target date, format YYYY-MM-DD (required)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def resolve_home() -> Path:
    """Return the Worker runtime home directory."""
    env = os.environ.get("SONISCOPE_HOME")
    if env:
        return Path(env)
    return Path.home() / "SoniScope"


def _sha256_consistency(manifest: dict, frag_id: str) -> str | None:
    """Check SHA-256 rules for a single fragment manifest.

    Returns an error message string on failure, or ``None`` on pass.
    """
    audio = manifest.get("audio", {})
    upload = manifest.get("upload", {})

    audio_sha = audio.get("sha256", "")
    audio_fmt = audio.get("format", "").lower()
    audio_orig_fmt = audio.get("original_format", "").lower()
    upload_sha = upload.get("original_sha256", "")

    # Both must be non-null/non-empty
    if not audio_sha:
        return f"{frag_id}: audio.sha256 为空或不存在"
    if not upload_sha:
        return f"{frag_id}: upload.original_sha256 为空或不存在"

    # Determine if this was a passthrough or transcode
    # passthrough: original_format == format (both wav) or format is wav
    is_passthrough = audio_fmt == "wav" and audio_orig_fmt in ("wav", "")

    if is_passthrough:
        # AC5: WAV passthrough → sha256 must match
        if audio_sha != upload_sha:
            return (
                f"{frag_id}: WAV 直通路径 sha256 不一致 — "
                f"audio.sha256={audio_sha[:16]}... "
                f"upload.original_sha256={upload_sha[:16]}..."
            )
    else:
        # AC6: Non-WAV transcode → both must be real, may differ
        # No strict equality check; just verify both are present and real
        if len(audio_sha) < 8 or len(upload_sha) < 8:
            return (
                f"{frag_id}: 非 WAV 转码路径 sha256 不完整 — "
                f"audio.sha256={audio_sha[:16]}... ({len(audio_sha)} chars), "
                f"upload.original_sha256={upload_sha[:16]}... ({len(upload_sha)} chars)"
            )

    return None


def main() -> None:
    date_str = os.environ.get("DATE", "")
    if not date_str:
        print("❌ 请设置 DATE 环境变量，格式 YYYY-MM-DD")
        print("   用法: make verify-e2e-sha256 DATE=2026-06-02")
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
        print("✅ verify-e2e-sha256 PASS（无目录需检查）")
        sys.exit(0)

    passes: list[str] = []
    failures: list[str] = []  # error messages

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

        error = _sha256_consistency(manifest, frag_id)
        if error:
            failures.append(error)
        else:
            passes.append(frag_id)

    total = len(fragment_dirs)
    passed = len(passes)
    failed = len(failures)

    print(f"🔍 verify-e2e-sha256  DATE={date_str}")
    print(f"   SONISCOPE_HOME: {home}")
    print(f"   扫描目录: {frag_dir}")
    print(f"\n   Fragment 总数: {total}")
    print(f"   通过: {passed}/{total}")
    print(f"   失败: {failed}/{total}\n")

    if failures:
        print("❌ SHA-256 校验失败:")
        for msg in failures:
            print(f"   {msg}")

    if failed > 0:
        print(f"\n❌ verify-e2e-sha256 FAIL（{failed} 个 Fragment 校验失败）")
        sys.exit(1)

    print("✅ verify-e2e-sha256 PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
