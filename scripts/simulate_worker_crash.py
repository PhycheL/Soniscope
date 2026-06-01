#!/usr/bin/env python3
"""Simulate Worker crash scenarios for recovery testing.

Covers US-023 AC7/AC8/AC9: verify that the Worker can recover from
incomplete processing by cleaning up stale intermediates and resuming
transcription.

Usage:
    python scripts/simulate_worker_crash.py CASE=<case> FRAGMENT_ID=<id>

Cases:
    crash-transcode   — kill -9 during transcription, expect restart to
                        re-transcribe and recreate .done
    missing-done      — delete .done from a completed fragment, expect
                        a restart will re-transcribe and create a new .done
    stale-part        — create a stale .part file, expect restart to clean
                        it and re-download

This is an integration/orchestration script. The actual simulation
requires an active Worker process, so the script produces actionable
instructions for manual or CI-driven execution.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path


def _resolve_home() -> Path:
    env = os.environ.get("SONISCOPE_HOME")
    if env:
        return Path(env)
    return Path.home() / "SoniScope"


def _find_fragment_dir(home: Path, fragment_id: str) -> Path | None:
    """Find the fragment directory from fragment_id's date prefix."""
    if "T" not in fragment_id:
        return None
    date_part = fragment_id.split("T")[0]
    yyyy = date_part[0:4]
    mm = date_part[4:6]
    dd = date_part[6:8]
    date_str = f"{yyyy}-{mm}-{dd}"
    frag_dir = home / "fragments" / date_str / fragment_id
    if frag_dir.exists():
        return frag_dir
    return None


def _ensure_home(home: Path) -> None:
    if not home.is_dir():
        print(f"❌ SONISCOPE_HOME does not exist: {home}")
        print("   Run 'make init-dirs' and ensure the Worker is configured.")
        sys.exit(1)


def case_crash_transcode(home: Path, fragment_id: str) -> None:
    """Simulate crash during transcription (AC7).

    Instructions for the operator:
    1. Start the Worker in the background: make worker-run &
    2. Wait for the fragment to reach transcription phase (check tmp/ for .transcript.json.tmp)
    3. Find the Worker PID and kill -9 it
    4. Restart the Worker: make worker-run
    5. Verify: the tmp/ intermediate is cleaned, transcript.json + .done are created
    """
    _ensure_home(home)
    tmp = home / "tmp"
    frag_dir = _find_fragment_dir(home, fragment_id)

    print("🧪 Simulating crash during transcription (AC7)")
    print()
    if frag_dir and frag_dir.is_dir():
        print(f"   Fragment directory: {frag_dir}")
        has_done = (frag_dir / ".done").is_file()
        has_transcript = (frag_dir / "transcript.json").is_file()
        print(f"   .done present:    {has_done}")
        print(f"   transcript.json:  {has_transcript}")
        print()
    print("   To simulate this crash:")
    print(f"   1. Make sure the Worker is running: make worker-run &")
    print(f"   2. Create a test fragment or wait for one to be processed")
    print(f"   3. Find the Worker PID: ps aux | grep soniscope_worker")
    print(f"   4. Kill it: kill -9 <PID>")
    print(f"   5. Restart: make worker-run")
    if frag_dir:
        print(f"   6. Verify: ls {frag_dir}")
    print()
    print("   Expected: tmp/ intermediates cleaned, transcript.json + .done created")


def case_missing_done(home: Path, fragment_id: str) -> None:
    """Delete .done from a completed fragment (AC8).

    This simulates the scenario where .done was lost but all other files
    exist. The Worker should re-transcribe and recreate .done.
    """
    _ensure_home(home)
    frag_dir = _find_fragment_dir(home, fragment_id)

    if not frag_dir or not frag_dir.is_dir():
        print(f"❌ Fragment directory not found: {fragment_id}")
        print(f"   Searched under: {home}/fragments/")
        print()
        print("   Make sure the fragment has been processed at least once.")
        print("   You can use make show-oss-object FRAGMENT_ID=<id> to check OSS.")
        sys.exit(1)

    done_file = frag_dir / ".done"

    if done_file.is_file():
        print(f"🗑️  Removing .done from {frag_dir.name}")
        done_file.unlink()
        print("   ✅ .done removed")
        print()
        print("   Restart the Worker (make worker-run) to trigger re-transcription.")
        print(f"   Then verify: ls {frag_dir}")
        print()
        print("   Expected: .done recreated, transcript.json/text updated")
    else:
        print(f"⚠️  .done not present in {frag_dir.name}")
        print()
        print("   This fragment is already in the 'missing-done' state.")
        print("   Simply restart the Worker to trigger re-transcription.")
        print(f"   Then verify: ls {frag_dir}")


def case_stale_part(home: Path, fragment_id: str) -> None:
    """Create a stale .part file in inbox/ (AC9).

    The Worker should clean it on startup and re-download on next poll.
    """
    _ensure_home(home)
    inbox = home / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    part_file = inbox / f"{fragment_id}.part"

    if not part_file.exists():
        print(f"📝 Creating stale .part file: {part_file.name}")
        part_file.touch()
        print("   ✅ Stale .part created")
    else:
        print(f"   ℹ️  .part already exists: {part_file.name}")

    print()
    print("   Restart the Worker (make worker-run) to trigger recovery.")
    print("   Expected: the stale .part is cleaned on startup.")
    print(f"   Then the next poll cycle will re-download: {fragment_id}")
    print()
    print(f"   Verify: {part_file} should not exist after Worker starts")


def main() -> None:
    case = os.environ.get("CASE", "")
    fragment_id = os.environ.get("FRAGMENT_ID", "")

    if not fragment_id:
        # Check for command line args
        args = sys.argv[1:]
        for arg in args:
            if arg.startswith("CASE="):
                case = arg.split("=", 1)[1]
            elif arg.startswith("FRAGMENT_ID="):
                fragment_id = arg.split("=", 1)[1]

    home = _resolve_home()

    if not case:
        print("Usage: make simulate-worker-crash CASE=<case> FRAGMENT_ID=<id>")
        print()
        print("Cases:")
        print("  crash-transcode  — simulate kill -9 during transcription (AC7)")
        print("  missing-done     — delete .done to verify re-transcription (AC8)")
        print("  stale-part       — create stale .part to verify cleanup (AC9)")
        print()
        print(f"SONISCOPE_HOME: {home}")
        sys.exit(1)

    if not fragment_id:
        print("❌ FRAGMENT_ID is required.")
        print("Usage: make simulate-worker-crash CASE=<case> FRAGMENT_ID=<id>")
        sys.exit(1)

    print(f"SONISCOPE_HOME: {home}")
    print(f"FRAGMENT_ID:    {fragment_id}")
    print()

    if case == "crash-transcode":
        case_crash_transcode(home, fragment_id)
    elif case == "missing-done":
        case_missing_done(home, fragment_id)
    elif case == "stale-part":
        case_stale_part(home, fragment_id)
    else:
        print(f"❌ Unknown CASE: {case}")
        print("   Valid cases: crash-transcode, missing-done, stale-part")
        sys.exit(1)


if __name__ == "__main__":
    main()
