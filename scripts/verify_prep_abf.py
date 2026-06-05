#!/usr/bin/env python3
"""Run only verify-prep A/B/F diagnostics.

This is a focused helper for debugging OSS bucket access, STS AssumeRole,
and fixture readiness without running the full verify-prep command.

usage: uv run --directory apps/worker python ../../scripts/verify_prep_abf.py
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_SRC = REPO_ROOT / "apps" / "worker" / "src"
if str(WORKER_SRC) not in sys.path:
    sys.path.insert(0, str(WORKER_SRC))

from soniscope_worker import verify_prep  # noqa: E402


def main() -> int:
    config_path = verify_prep._resolve_config_path()
    cfg = verify_prep._load_config(config_path) if config_path.is_file() else {}

    print(f"Config: {config_path}")
    if not config_path.is_file():
        print("Config file is missing; A/B may report missing configuration.")
    print()

    blocks = [
        verify_prep.check_block_a(cfg),
        verify_prep.check_block_b(cfg),
        verify_prep.check_block_f(),
    ]

    for block in blocks:
        print(verify_prep._bold(f"▶ {block.block} 块 — {block.title}"))
        verify_prep._print_block_summary(block)

    passed = sum(1 for block in blocks if block.passed)
    print("=" * 60)
    print(f"A/B/F summary: {passed}/{len(blocks)} blocks passed")
    return 0 if all(block.passed for block in blocks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
