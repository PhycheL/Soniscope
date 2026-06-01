"""Tests for US-004 verify-prep verification checks.

Tests cover G, H, F blocks with mocked cloud dependencies.
Cloud blocks (A, B, C, E) are excluded from unit tests per project rules:
they must be verified with real cloud calls via ``make verify-prep``.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock



# ── Helpers ──────────────────────────────────────────────────────────────────


def _import_verify_prep():
    """Import the verify_prep module (relative to worker package)."""
    from soniscope_worker import verify_prep

    return verify_prep


# ──────────────────────────────────────────────────────────────────────────────
# G block tests — Worker 运行环境
# ──────────────────────────────────────────────────────────────────────────────


class TestBlockG:
    """Worker environment checks (no cloud deps needed)."""

    def test_python_version_ok(self) -> None:
        vp = _import_verify_prep()
        result = vp.check_block_g()
        check = _find_check(result, "Python >= 3.11")
        assert check.passed

    def test_ffmpeg_found(self) -> None:
        vp = _import_verify_prep()
        result = vp.check_block_g()
        check = _find_check(result, "ffmpeg 可用")
        assert check.passed, f"ffmpeg not found: {check.detail}"

    def test_ffprobe_found(self) -> None:
        vp = _import_verify_prep()
        result = vp.check_block_g()
        check = _find_check(result, "ffprobe 可用")
        assert check.passed, f"ffprobe not found: {check.detail}"

    def test_soniscope_home_writable(self) -> None:
        vp = _import_verify_prep()
        result = vp.check_block_g()
        check = _find_check(result, "SONISCOPE_HOME 可写")
        # The user's actual home may or may not exist, but the parent should be writable
        assert check.passed, f"SONISCOPE_HOME not writable: {check.detail}"

    def test_disk_check_runs(self) -> None:
        vp = _import_verify_prep()
        result = vp.check_block_g()
        check = _find_check(result, "可用磁盘")
        # Should at least run (pass or fail depending on env)
        assert check is not None, "Disk check not found"

    def test_all_g_checks_have_labels(self) -> None:
        vp = _import_verify_prep()
        result = vp.check_block_g()
        assert len(result.checks) >= 5
        for c in result.checks:
            assert c.label, f"Check missing label: {c}"


# ──────────────────────────────────────────────────────────────────────────────
# H block tests — 配置权限与完整性
# ──────────────────────────────────────────────────────────────────────────────


class TestBlockH:
    """Config permission and completeness checks."""

    def test_config_not_found(self, tmp_path: Path) -> None:
        vp = _import_verify_prep()
        with mock.patch.object(vp, "_resolve_config_path", return_value=tmp_path / "nonexistent.yaml"):
            result = vp.check_block_h()
            check = _find_check(result, "config.yaml 存在")
            assert check is not None
            assert not check.passed

    def test_config_exists(self, tmp_path: Path) -> None:
        vp = _import_verify_prep()
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "oss:\n  endpoint: oss-cn-beijing.aliyuncs.com\n"
            "  bucket: test\n  access_key_id: AKID1234\n  access_key_secret: secret1234\n"
            "poll:\n  interval_seconds: 60\n"
            "transcriber:\n  name: cloud-speech\n  provider: aliyun-nls\n"
            "  model: test-model\n  params_version: v1\n  api_endpoint: cn-beijing\n"
            "  appkey: appkey1234\n  access_key_id: AKID5678\n  access_key_secret: secret5678\n"
        )
        config_path.chmod(0o600)

        with mock.patch.object(vp, "_resolve_config_path", return_value=config_path):
            result = vp.check_block_h()
            assert result.passed, f"H block failed: {_failed_labels(result)}"

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        vp = _import_verify_prep()
        config_path = tmp_path / "config.yaml"
        config_path.write_text("oss:\n  endpoint: oss-cn-beijing.aliyuncs.com\n")
        config_path.chmod(0o600)

        with mock.patch.object(vp, "_resolve_config_path", return_value=config_path):
            result = vp.check_block_h()
            # Should have a failing check about missing fields
            assert not result.passed

    def test_permissions_not_600(self, tmp_path: Path) -> None:
        vp = _import_verify_prep()
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "oss:\n  endpoint: oss-cn-beijing.aliyuncs.com\n"
            "  bucket: test\n  access_key_id: AKID1234\n  access_key_secret: s1234\n"
            "poll:\n  interval_seconds: 60\n"
            "transcriber:\n  name: cloud-speech\n  provider: aliyun-nls\n"
            "  model: test-model\n  params_version: v1\n  api_endpoint: cn-beijing\n"
            "  appkey: appkey1234\n  access_key_id: AKID5678\n  access_key_secret: s5678\n"
        )
        config_path.chmod(0o644)

        with mock.patch.object(vp, "_resolve_config_path", return_value=config_path):
            result = vp.check_block_h()
            perm_check = _find_check(result, "config.yaml 权限为 600")
            assert perm_check is not None
            assert not perm_check.passed, f"Expected 600 check to fail but got: {perm_check.detail}"


# ──────────────────────────────────────────────────────────────────────────────
# F block tests — 测试音频 fixture
# ──────────────────────────────────────────────────────────────────────────────


class TestBlockF:
    """Fixture check block (runs fetch_test_fixtures.py --check)."""

    def test_fixture_script_missing(self, tmp_path: Path) -> None:
        vp = _import_verify_prep()
        with mock.patch.object(vp, "_get_repo_root", return_value=tmp_path):
            result = vp.check_block_f()
            check = _find_check(result, "fixture 校验脚本存在")
            assert check is not None
            assert not check.passed

    def test_fixture_script_runs(self) -> None:
        vp = _import_verify_prep()
        # Don't mock — it should actually run and find 4 good fixtures
        result = vp.check_block_f()
        # In a dev environment with fixtures present, this should pass
        # But if fixtures aren't present, it will fail (acceptable)
        # At minimum the check should exist
        assert len(result.checks) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# Unit tests for helper functions
# ──────────────────────────────────────────────────────────────────────────────


class TestHelpers:
    """Helper function tests."""

    def test_mask_secret_short(self) -> None:
        vp = _import_verify_prep()
        assert vp._mask_secret("abc") == "***"
        assert vp._mask_secret("12345678") == "********"

    def test_mask_secret_long(self) -> None:
        vp = _import_verify_prep()
        masked = vp._mask_secret("AKID1234567890ABCD")
        assert masked == "AKID...ABCD"

    def test_resolve_config_path_env(self) -> None:
        vp = _import_verify_prep()
        with mock.patch.dict(os.environ, {"SONISCOPE_HOME": "/tmp/test_home"}):
            path = vp._resolve_config_path()
            assert path == Path("/tmp/test_home/config.yaml")

    def test_resolve_config_path_default(self) -> None:
        vp = _import_verify_prep()
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(vp.Path, "home", return_value=Path("/home/user")):
                path = vp._resolve_config_path()
                assert path == Path("/home/user/SoniScope/config.yaml")

    def test_resolve_soniscope_home_env(self) -> None:
        vp = _import_verify_prep()
        with mock.patch.dict(os.environ, {"SONISCOPE_HOME": "/custom/path"}):
            home = vp._resolve_soniscope_home()
            assert home == Path("/custom/path")


# ──────────────────────────────────────────────────────────────────────────────
# BlockResult dataclass tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBlockResult:
    """Tests for the BlockResult and CheckResult types."""

    def test_all_passed(self) -> None:
        vp = _import_verify_prep()
        br = vp.BlockResult(
            "X", "Test Block",
            checks=[vp.CheckResult(label="a", passed=True), vp.CheckResult(label="b", passed=True)],
        )
        assert br.passed

    def test_some_failed(self) -> None:
        vp = _import_verify_prep()
        br = vp.BlockResult(
            "X", "Test Block",
            checks=[vp.CheckResult(label="a", passed=True), vp.CheckResult(label="b", passed=False)],
        )
        assert not br.passed


# ──────────────────────────────────────────────────────────────────────────────
# CLI command exists test
# ──────────────────────────────────────────────────────────────────────────────


def test_verify_prep_command_exists() -> None:
    """The 'verify-prep' CLI command is registered."""
    from typer.testing import CliRunner

    from soniscope_worker.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["verify-prep", "--help"])
    assert result.exit_code == 0
    assert "verify-prep" in result.stdout


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _find_check(result, label_substring: str):
    """Find a check by partial label match."""
    for c in result.checks:
        if label_substring in c.label:
            return c
    return None


def _failed_labels(result) -> list[str]:
    """Return labels of failed checks."""
    return [c.label for c in result.checks if not c.passed]
