"""Tests for US-002 — config schema, secret masking, and runtime dirs."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

# ── config module ────────────────────────────────────────────────────────────


class TestMaskSecret:
    """mask_secret() behaviour."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("", ""),
            ("a", "*"),
            ("12345678", "********"),
            ("123456789", "1234...6789"),
            ("abcdefghijklmnop", "abcd...mnop"),
            ("AKID1234567890ABCD", "AKID...ABCD"),
        ],
    )
    def test_mask_outputs(self, value: str, expected: str) -> None:
        from soniscope_worker.config import mask_secret

        assert mask_secret(value) == expected


class TestConfigSchema:
    """Pydantic schema validation."""

    MINIMAL = {
        "oss": {
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "bucket": "soniscope-audio",
            "access_key_id": "AKID1234",
            "access_key_secret": "SuperSecretKey123",
        },
        "poll": {"interval_seconds": 60},
        "transcriber": {
            "name": "cloud-speech",
            "provider": "aliyun-nls",
            "model": "中文普通话（识音石 V1 - 端到端模型)",
            "params_version": "v1",
            "api_endpoint": "cn-beijing",
            "appkey": "1k8tqkjQsq65wp2m",
            "access_key_id": "NLS_AK_ID",
            "access_key_secret": "NLS_AK_SECRET_LONG",
            "upload_mode": "oss-url",
        },
    }

    def test_valid_minimal_config(self) -> None:
        from soniscope_worker.config import SoniScopeConfig

        cfg = SoniScopeConfig.model_validate(self.MINIMAL)
        assert cfg.oss.endpoint == "oss-cn-beijing.aliyuncs.com"
        assert cfg.poll.interval_seconds == 60
        assert cfg.transcriber.name == "cloud-speech"
        # Defaults
        assert cfg.transcriber.upload_mode == "oss-url"
        assert cfg.transcriber.local.enabled is False

    def test_missing_oss_access_key_secret_reports_field(self) -> None:
        from pydantic import ValidationError

        from soniscope_worker.config import SoniScopeConfig

        data = {
            "oss": {
                "endpoint": "x",
                "bucket": "x",
                "access_key_id": "x",
                # missing access_key_secret
            },
            "poll": {"interval_seconds": 60},
            "transcriber": {
                "name": "cloud-speech",
                "provider": "aliyun-nls",
                "model": "x",
                "params_version": "v1",
                "api_endpoint": "x",
                "appkey": "x",
                "access_key_id": "x",
                "access_key_secret": "x",
            },
        }
        with pytest.raises(ValidationError) as exc:
            SoniScopeConfig.model_validate(data)
        err_locs = [str(e["loc"]) for e in exc.value.errors()]
        assert any("access_key_secret" in loc for loc in err_locs)

    def test_missing_multiple_fields_reports_all(self) -> None:
        from soniscope_worker.config import ConfigValidationError, load_config

        data = {"oss": {}}  # Almost everything missing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(data, f)
            tmp_path = Path(f.name)

        try:
            with pytest.raises(ConfigValidationError) as exc:
                load_config(tmp_path)
            msg = str(exc.value)
            assert "Missing required fields" in msg
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_poll_interval_negative_rejected(self) -> None:
        from pydantic import ValidationError
        from soniscope_worker.config import SoniScopeConfig

        data = {**self.MINIMAL}
        data["poll"] = {"interval_seconds": -5}
        with pytest.raises(ValidationError):
            SoniScopeConfig.model_validate(data)

    def test_transcriber_local_defaults(self) -> None:
        from soniscope_worker.config import SoniScopeConfig

        cfg = SoniScopeConfig.model_validate(self.MINIMAL)
        assert cfg.transcriber.local.enabled is False


class TestSecretMaskingInModels:
    """Sensitive fields are masked in repr, str, and model_dump."""

    MINIMAL = TestConfigSchema.MINIMAL

    def test_repr_masks_secrets(self) -> None:
        from soniscope_worker.config import SoniScopeConfig

        cfg = SoniScopeConfig.model_validate(self.MINIMAL)
        r = repr(cfg)
        # The raw secrets should NOT appear
        assert "SuperSecretKey123" not in r
        assert "NLS_AK_SECRET_LONG" not in r
        # But masked versions should
        assert "Supe...y123" in r  # "SuperSecretKey123" → first 4 + ... + last 4
        assert "NLS_...LONG" in r

    def test_str_masks_secrets(self) -> None:
        from soniscope_worker.config import SoniScopeConfig

        cfg = SoniScopeConfig.model_validate(self.MINIMAL)
        s = str(cfg)
        assert "SuperSecretKey123" not in s
        assert "NLS_AK_SECRET_LONG" not in s

    def test_model_dump_masks_secrets(self) -> None:
        from soniscope_worker.config import SoniScopeConfig

        cfg = SoniScopeConfig.model_validate(self.MINIMAL)
        d = cfg.model_dump()
        assert d["oss"]["access_key_secret"] != "SuperSecretKey123"
        assert "..." in d["oss"]["access_key_secret"]
        assert d["transcriber"]["appkey"] != "1k8tqkjQsq65wp2m"
        assert "..." in d["transcriber"]["appkey"]

    def test_sanitized_summary_no_raw_secrets(self) -> None:
        from soniscope_worker.config import SoniScopeConfig

        cfg = SoniScopeConfig.model_validate(self.MINIMAL)
        summary = cfg.sanitized_summary()
        assert "SuperSecretKey123" not in summary
        assert "NLS_AK_SECRET_LONG" not in summary
        assert "1k8tqkjQsq65wp2m" not in summary
        # Masked fragments present
        assert "Supe...y123" in summary
        assert "NLS_...LONG" in summary
        assert "1k8t...wp2m" in summary


class TestConfigLoading:
    """Config file loading and error handling."""

    def test_load_from_valid_file(self) -> None:
        from soniscope_worker.config import SoniScopeConfig, load_config

        data = TestConfigSchema.MINIMAL
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(data, f)
            tmp_path = Path(f.name)

        try:
            cfg = load_config(tmp_path)
            assert isinstance(cfg, SoniScopeConfig)
            assert cfg.oss.bucket == "soniscope-audio"
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_missing_file_raises(self) -> None:
        from soniscope_worker.config import load_config

        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/path/config.yaml"))

    def test_empty_yaml_raises(self) -> None:
        from soniscope_worker.config import ConfigValidationError, load_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            tmp_path = Path(f.name)

        try:
            with pytest.raises(ConfigValidationError):
                load_config(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)


class TestResolveConfigPath:
    """resolve_config_path() behaviour."""

    def test_uses_env_var(self) -> None:
        from soniscope_worker.config import resolve_config_path

        with mock.patch.dict(os.environ, {"SONISCOPE_HOME": "/custom/path"}):
            p = resolve_config_path()
            assert p == Path("/custom/path/config.yaml")

    def test_fallback_when_unset(self) -> None:
        from soniscope_worker.config import resolve_config_path

        with mock.patch.dict(os.environ, {}, clear=True):
            p = resolve_config_path()
            assert p == Path.home() / "SoniScope" / "config.yaml"


class TestCheckFilePermissions:
    """check_file_permissions() — 600 check."""

    def test_600_is_ok(self) -> None:
        from soniscope_worker.config import check_file_permissions

        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp_path = Path(f.name)
        try:
            tmp_path.chmod(0o600)
            ok, msg = check_file_permissions(tmp_path)
            assert ok is True
            assert "OK" in msg
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_644_warns(self) -> None:
        from soniscope_worker.config import check_file_permissions

        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp_path = Path(f.name)
        try:
            tmp_path.chmod(0o644)
            ok, msg = check_file_permissions(tmp_path)
            assert ok is False
            assert "WARNING" in msg
            assert "644" in msg
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_non_existent_file_returns_error(self) -> None:
        from soniscope_worker.config import check_file_permissions

        ok, msg = check_file_permissions(Path("/nonexistent/config.yaml"))
        assert ok is False
        assert "Cannot stat" in msg


# ── paths module ─────────────────────────────────────────────────────────────


class TestResolveHome:
    def test_uses_env_var(self) -> None:
        from soniscope_worker.paths import resolve_home

        with mock.patch.dict(os.environ, {"SONISCOPE_HOME": "/my/runtime"}):
            assert resolve_home() == Path("/my/runtime")

    def test_fallback(self) -> None:
        from soniscope_worker.paths import resolve_home

        with mock.patch.dict(os.environ, {}, clear=True):
            assert resolve_home() == Path.home() / "SoniScope"


class TestDirResolvers:
    def test_all_dirs_under_home(self) -> None:
        from soniscope_worker.paths import (
            fragments_dir,
            inbox_dir,
            inbox_failed_dir,
            tmp_dir,
        )

        h = Path("/fake/home")
        assert inbox_dir(h) == h / "inbox"
        assert inbox_failed_dir(h) == h / "inbox" / "failed"
        assert fragments_dir(h) == h / "fragments"
        assert tmp_dir(h) == h / "tmp"


class TestInitRuntimeDirs:
    def test_creates_all_four_dirs(self) -> None:
        from soniscope_worker.paths import (
            fragments_dir,
            inbox_dir,
            inbox_failed_dir,
            init_runtime_dirs,
            tmp_dir,
        )

        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            created = init_runtime_dirs(home)

            assert len(created) == 4
            assert inbox_dir(home).is_dir()
            assert inbox_failed_dir(home).is_dir()
            assert fragments_dir(home).is_dir()
            assert tmp_dir(home).is_dir()

    def test_idempotent(self) -> None:
        from soniscope_worker.paths import init_runtime_dirs

        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            first = init_runtime_dirs(home)
            second = init_runtime_dirs(home)
            assert first == second


# ── CLI integration ──────────────────────────────────────────────────────────


class TestCLICommands:
    def test_check_config_valid_file(self) -> None:
        from typer.testing import CliRunner

        from soniscope_worker.cli import app

        data = TestConfigSchema.MINIMAL
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(data, f)
            f.flush()
            tmp_path = Path(f.name)
        tmp_path.chmod(0o600)

        try:
            with mock.patch(
                "soniscope_worker.cli.resolve_config_path", return_value=tmp_path
            ):
                runner = CliRunner()
                result = runner.invoke(app, ["check-config"])
            assert result.exit_code == 0
            assert "OSS endpoint" in result.stdout
            assert "Supe...y123" in result.stdout
            assert "SuperSecretKey123" not in result.stdout
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_check_config_missing_file(self) -> None:
        from typer.testing import CliRunner

        from soniscope_worker.cli import app

        with mock.patch(
            "soniscope_worker.cli.resolve_config_path",
            return_value=Path("/nonexistent/config.yaml"),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["check-config"])
        assert result.exit_code == 1

    def test_check_config_broken_schema(self) -> None:
        from typer.testing import CliRunner

        from soniscope_worker.cli import app

        data = {"oss": {"endpoint": "x"}}  # incomplete
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(data, f)
            f.flush()
            tmp_path = Path(f.name)
        tmp_path.chmod(0o600)

        try:
            with mock.patch(
                "soniscope_worker.cli.resolve_config_path", return_value=tmp_path
            ):
                runner = CliRunner()
                result = runner.invoke(app, ["check-config"])
            assert result.exit_code == 1
            output = result.stdout + result.stderr
            assert "Missing" in output
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_check_config_warns_permissions(self) -> None:
        """When config is not 600, the warning is printed but a valid config
        still exits 0 (warning only, not error)."""
        from typer.testing import CliRunner

        from soniscope_worker.cli import app

        data = TestConfigSchema.MINIMAL
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(data, f)
            f.flush()
            tmp_path = Path(f.name)
        tmp_path.chmod(0o644)

        try:
            with mock.patch(
                "soniscope_worker.cli.resolve_config_path", return_value=tmp_path
            ):
                runner = CliRunner()
                result = runner.invoke(app, ["check-config"])
            # Valid config + non-600 perms = warning, but still exit 0
            assert result.exit_code == 0
            assert "WARNING" in result.stdout
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_init_dirs_creates_directories(self) -> None:
        from typer.testing import CliRunner

        from soniscope_worker.cli import app

        with tempfile.TemporaryDirectory() as td:
            with mock.patch.dict(os.environ, {"SONISCOPE_HOME": td}):
                runner = CliRunner()
                result = runner.invoke(app, ["init-dirs"])
            assert result.exit_code == 0
            assert (Path(td) / "inbox").is_dir()
            assert (Path(td) / "inbox" / "failed").is_dir()
            assert (Path(td) / "fragments").is_dir()
            assert (Path(td) / "tmp").is_dir()
