"""Tests for standalone verify-prep A/B/F diagnostics."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "verify_prep_abf.py"


def test_verify_prep_abf_script_exists_and_reuses_block_checks() -> None:
    """The A/B/F diagnostic script should exist and call existing block checks."""
    content = SCRIPT.read_text(encoding="utf-8")

    assert "check_block_a" in content
    assert "check_block_b" in content
    assert "check_block_f" in content
    assert "access_key_secret" not in content
    assert "ALIYUN_DEPLOY_AK_SECRET" not in content
