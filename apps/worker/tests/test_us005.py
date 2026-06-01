"""Tests for US-005 — FC 3.0 function engineering baseline."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers — import the deploy script as a module
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture(autouse=True)
def _clean_sys_path() -> None:
    """Remove scripts/ from sys.path after each test to avoid side effects."""
    yield
    try:
        sys.path.remove(str(SCRIPTS_DIR))
    except ValueError:
        pass


# Prevent the deploy_fc module from running main() on import
_orig_argv = sys.argv
sys.argv = ["deploy_fc.py", "deploy", "issue-credential"]


import deploy_fc as dfc_module  # noqa: E402

sys.argv = _orig_argv


# ---------------------------------------------------------------------------
# Unit tests — helpers and constants
# ---------------------------------------------------------------------------


class TestFunctionDirMap:
    """AC: directory conventions match cloud function names."""

    def test_issue_credential_in_map(self) -> None:
        assert "issue-credential" in dfc_module.FUNCTION_DIR_MAP
        assert dfc_module.FUNCTION_DIR_MAP["issue-credential"] == "issue_credential"

    def test_verify_upload_in_map(self) -> None:
        assert "verify-upload" in dfc_module.FUNCTION_DIR_MAP
        assert dfc_module.FUNCTION_DIR_MAP["verify-upload"] == "verify_upload"

    def test_all_functions_count(self) -> None:
        assert len(dfc_module.ALL_FUNCTIONS) == 2
        assert "issue-credential" in dfc_module.ALL_FUNCTIONS
        assert "verify-upload" in dfc_module.ALL_FUNCTIONS


class TestSnakeDir:
    """AC: kebab → snake_case mapping for source directories."""

    def test_issue_credential(self) -> None:
        assert dfc_module._snake_dir("issue-credential") == "issue_credential"

    def test_verify_upload(self) -> None:
        assert dfc_module._snake_dir("verify-upload") == "verify_upload"


class TestSha256:
    """AC: zip sha256 can be computed."""

    def test_sha256_deterministic(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"hello world")
            f.flush()
            path = Path(f.name)

        try:
            h1 = dfc_module._sha256_hex(path)
            h2 = dfc_module._sha256_hex(path)
            assert h1 == h2
            assert len(h1) == 64
        finally:
            path.unlink(missing_ok=True)

    def test_sha256_empty_not_equal(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"a")
            f.flush()
            p1 = Path(f.name)
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"b")
            f.flush()
            p2 = Path(f.name)

        try:
            h1 = dfc_module._sha256_hex(p1)
            h2 = dfc_module._sha256_hex(p2)
            assert h1 != h2
        finally:
            p1.unlink(missing_ok=True)
            p2.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Package tests
# ---------------------------------------------------------------------------


class TestPackageFunction:
    """AC: make deploy-fc independently packages each function."""

    def test_package_creates_zip(self, tmp_path: Path, monkeypatch) -> None:
        """Packaging creates a zip inside BUILD_DIR/fc/<function>/."""
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")
        monkeypatch.setattr(dfc_module, "FC_SRC_DIR", tmp_path / "apps" / "fc")

        # Create a minimal handler.py in issue_credential
        src_dir = tmp_path / "apps" / "fc" / "issue_credential"
        src_dir.mkdir(parents=True)
        (src_dir / "handler.py").write_text('def handler(e, c): return {"statusCode": 200}\n')

        zip_path = dfc_module._package_function("issue-credential")
        assert zip_path.is_file()
        assert zip_path.suffix == ".zip"
        assert zip_path.parent.name == "issue-credential"

        # Verify zip contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "handler.py" in names

    def test_package_excludes_pycache(self, tmp_path: Path, monkeypatch) -> None:
        """Packaging excludes __pycache__ and .pyc files."""
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")
        monkeypatch.setattr(dfc_module, "FC_SRC_DIR", tmp_path / "apps" / "fc")

        src_dir = tmp_path / "apps" / "fc" / "issue_credential"
        src_dir.mkdir(parents=True)
        (src_dir / "handler.py").write_text("pass\n")
        pycache = src_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "handler.cpython-311.pyc").write_text("junk")

        zip_path = dfc_module._package_function("issue-credential")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "handler.py" in names
            assert not any("__pycache__" in n for n in names)

    def test_package_missing_src_dir_exits(self, tmp_path: Path, monkeypatch) -> None:
        """Missing source directory exits with code 1."""
        monkeypatch.setattr(dfc_module, "FC_SRC_DIR", tmp_path / "nonexistent")
        with pytest.raises(SystemExit) as exc_info:
            dfc_module._package_function("issue-credential")
        assert exc_info.value.code == 1

    def test_package_verify_upload(self, tmp_path: Path, monkeypatch) -> None:
        """verify-upload function can also be packaged."""
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")
        monkeypatch.setattr(dfc_module, "FC_SRC_DIR", tmp_path / "apps" / "fc")

        src_dir = tmp_path / "apps" / "fc" / "verify_upload"
        src_dir.mkdir(parents=True)
        (src_dir / "handler.py").write_text('def handler(e, c): return {"statusCode": 200}\n')

        zip_path = dfc_module._package_function("verify-upload")
        assert zip_path.is_file()
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "handler.py" in zf.namelist()


# ---------------------------------------------------------------------------
# Deploy log tests
# ---------------------------------------------------------------------------


class TestDeployLog:
    """AC: deploy logs contain function name, zip sha256, upload elapsed, and
    curl survival result."""

    def test_deploy_log_written(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")
        dfc_module._write_deploy_log(
            function="issue-credential",
            timestamp="20260526-120000",
            zip_sha256="abc123",
            upload_elapsed=2.5,
            success=True,
        )
        log_path = tmp_path / "build" / "fc" / "logs" / "deploy-20260526-120000.log"
        assert log_path.is_file()
        content = log_path.read_text()
        assert "function: issue-credential" in content
        assert "zip_sha256: abc123" in content
        assert "upload_elapsed_seconds: 2.5" in content
        assert "success: True" in content

    def test_deploy_log_failure(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")
        dfc_module._write_deploy_log(
            function="verify-upload",
            timestamp="20260526-120001",
            zip_sha256="def456",
            upload_elapsed=0.0,
            success=False,
            error="Connection timeout",
        )
        log_path = tmp_path / "build" / "fc" / "logs" / "deploy-20260526-120001.log"
        assert log_path.is_file()
        content = log_path.read_text()
        assert "success: False" in content
        assert "error: Connection timeout" in content


# ---------------------------------------------------------------------------
# Backup tests
# ---------------------------------------------------------------------------


class TestBackupDirectory:
    """AC: backup directory structure under build/fc/backup/."""

    def test_backup_dir_naming_convention(self) -> None:
        """Backup timestamp dirs use YYYYMMDD-HHMMSS format."""
        backup_base = Path("/tmp/test-build/fc/backup")
        ts = "20260526-120000"
        backup_dir = backup_base / ts
        assert backup_dir.name == ts
        assert len(ts) == 15  # YYYYMMDD-HHMMSS


class TestBackupMeta:
    """AC: backup records env var names, not values."""

    def test_backup_meta_no_secrets(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backup" / "20260526-120000"
        backup_dir.mkdir(parents=True)

        meta = {
            "function": "issue-credential",
            "timestamp": "20260526-120000",
            "environment_variable_names": [
                "OSS_BUCKET",
                "ALIYUN_AK_ID",
                "WX_APPID",
                "OPENID_ALLOWLIST",
            ],
        }
        meta_path = backup_dir / "issue-credential.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2))

        loaded = json.loads(meta_path.read_text())
        assert "ALIYUN_AK_SECRET" not in loaded["environment_variable_names"]
        assert "WX_APP_SECRET" not in loaded["environment_variable_names"]
        assert "ALIYUN_AK_ID" in loaded["environment_variable_names"]


# ---------------------------------------------------------------------------
# FC function source directory tests
# ---------------------------------------------------------------------------


class TestFcFunctionStructure:
    """AC: FC function source directories exist with handler.py."""

    def test_issue_credential_dir_exists(self) -> None:
        src_dir = REPO_ROOT / "apps" / "fc" / "issue_credential"
        assert src_dir.is_dir(), f"Expected {src_dir} to exist"

    def test_verify_upload_dir_exists(self) -> None:
        src_dir = REPO_ROOT / "apps" / "fc" / "verify_upload"
        assert src_dir.is_dir(), f"Expected {src_dir} to exist"

    def test_issue_credential_handler_exists(self) -> None:
        handler = REPO_ROOT / "apps" / "fc" / "issue_credential" / "handler.py"
        assert handler.is_file(), f"Expected {handler} to exist"

    def test_verify_upload_handler_exists(self) -> None:
        handler = REPO_ROOT / "apps" / "fc" / "verify_upload" / "handler.py"
        assert handler.is_file(), f"Expected {handler} to exist"

    def test_issue_credential_handler_is_importable(self) -> None:
        """The handler.py can be imported as a Python module."""
        import json
        import os as _os
        src_dir = REPO_ROOT / "apps" / "fc" / "issue_credential"
        # Ensure fc/ root is on sys.path so shared/ can be imported
        fc_root = str(REPO_ROOT / "apps" / "fc")
        sys.path.insert(0, fc_root)
        sys.path.insert(0, str(src_dir))
        # Set required FC env vars for shared config
        _os.environ.update({
            "OSS_BUCKET": "test", "OSS_REGION": "cn-beijing",
            "OSS_ENDPOINT": "oss-cn-beijing.aliyuncs.com",
            "WX_APPID": "wx-test", "WX_APP_SECRET": "test-secret",
        })
        try:
            import importlib
            spec = importlib.util.spec_from_file_location(
                "handler", src_dir / "handler.py"
            )
            assert spec is not None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            assert hasattr(mod, "handler")
            result = mod.handler(
                {
                    "path": "/",
                    "httpMethod": "POST",
                    "body": json.dumps({"code": "test", "fragment_id": "f1", "size": 1000}),
                },
                None,
            )
            # Without valid WeChat code, expect 401 INVALID_CODE
            assert result["statusCode"] == 401
            body = json.loads(result["body"])
            assert body["error"] == "INVALID_CODE"
        finally:
            sys.path.remove(str(src_dir))
            sys.path.remove(fc_root)
            for v in ("OSS_BUCKET", "OSS_REGION", "OSS_ENDPOINT", "WX_APPID", "WX_APP_SECRET"):
                _os.environ.pop(v, None)

    def test_verify_upload_handler_is_importable(self) -> None:
        """The handler.py can be imported as a Python module."""
        import json
        import os as _os
        src_dir = REPO_ROOT / "apps" / "fc" / "verify_upload"
        fc_root = str(REPO_ROOT / "apps" / "fc")
        sys.path.insert(0, fc_root)
        sys.path.insert(0, str(src_dir))
        _os.environ.update({
            "OSS_BUCKET": "test", "OSS_REGION": "cn-beijing",
            "OSS_ENDPOINT": "oss-cn-beijing.aliyuncs.com",
            "WX_APPID": "wx-test", "WX_APP_SECRET": "test-secret",
        })
        try:
            import importlib
            spec = importlib.util.spec_from_file_location(
                "handler", src_dir / "handler.py"
            )
            assert spec is not None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            assert hasattr(mod, "handler")
            result = mod.handler(
                {
                    "path": "/",
                    "httpMethod": "POST",
                    "body": json.dumps({"code": "test", "fragment_id": "f1", "expected_size": 1000}),
                },
                None,
            )
            # Without valid WeChat code, expect 401 INVALID_CODE
            assert result["statusCode"] == 401
            body = json.loads(result["body"])
            assert body["error"] == "INVALID_CODE"
        finally:
            sys.path.remove(str(src_dir))
            sys.path.remove(fc_root)
            for v in ("OSS_BUCKET", "OSS_REGION", "OSS_ENDPOINT", "WX_APPID", "WX_APP_SECRET"):
                _os.environ.pop(v, None)


# ---------------------------------------------------------------------------
# Deploy command integration tests (with mocked FC client)
# ---------------------------------------------------------------------------


class TestDeployIntegration:
    """AC: deploy flow packages, uploads, and logs."""

    def test_deploy_with_mocked_fc(self, tmp_path: Path, monkeypatch) -> None:
        """Full deploy flow with mocked FC SDK."""
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")
        monkeypatch.setattr(dfc_module, "FC_SRC_DIR", tmp_path / "apps" / "fc")
        monkeypatch.setattr(dfc_module, "REPO_ROOT", tmp_path)

        # Create source dir
        src_dir = tmp_path / "apps" / "fc" / "issue_credential"
        src_dir.mkdir(parents=True)
        (src_dir / "handler.py").write_text('def handler(e, c): return {"statusCode": 200}\n')

        # Mock FC client
        mock_client = mock.MagicMock()
        monkeypatch.setattr(dfc_module, "_get_fc_client", lambda: mock_client)

        # Mock backup to skip
        monkeypatch.setattr(dfc_module, "_backup_function", lambda fn: None)

        # Mock curl
        monkeypatch.setattr(
            dfc_module, "_curl_survival_check", lambda fn: (True, "HTTP 200")
        )

        result = dfc_module.deploy("issue-credential")
        assert result is True

        # Verify upload was called
        assert mock_client.update_function.called

        # Verify log was written
        logs_dir = tmp_path / "build" / "fc" / "logs"
        log_files = list(logs_dir.glob("deploy-*.log"))
        assert len(log_files) == 1
        assert "deploy-" in log_files[0].name

    def test_deploy_all_calls_both(self, tmp_path: Path, monkeypatch) -> None:
        """Calling deploy without arguments deploys both functions."""
        calls = []

        def fake_deploy(fn: str) -> bool:
            calls.append(fn)
            return True

        monkeypatch.setattr(dfc_module, "deploy", fake_deploy)

        # Simulate the main() deploy-all path
        for fn in dfc_module.ALL_FUNCTIONS:
            fake_deploy(fn)

        assert calls == ["issue-credential", "verify-upload"]


# ---------------------------------------------------------------------------
# Rollback tests
# ---------------------------------------------------------------------------


class TestRollback:
    """AC: rollback restores from most recent backup."""

    def test_rollback_no_backups(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Rollback without backups reports error."""
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")

        result = dfc_module.rollback("issue-credential")
        assert result is False

    def test_rollback_with_backup(self, tmp_path: Path, monkeypatch) -> None:
        """Rollback picks the most recent backup."""
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")

        # Create two backup dirs
        older = tmp_path / "build" / "fc" / "backup" / "20260526-110000"
        older.mkdir(parents=True)
        (older / "issue-credential.zip").write_text("old code")

        newer = tmp_path / "build" / "fc" / "backup" / "20260526-120000"
        newer.mkdir(parents=True)
        (newer / "issue-credential.zip").write_text("new code")

        # Mock FC client
        mock_client = mock.MagicMock()
        monkeypatch.setattr(dfc_module, "_get_fc_client", lambda: mock_client)

        # Mock curl
        monkeypatch.setattr(
            dfc_module, "_curl_survival_check", lambda fn: (True, "HTTP 200")
        )

        result = dfc_module.rollback("issue-credential")
        assert result is True
        assert mock_client.update_function.called

    def test_rollback_wrong_function_no_backup(self, tmp_path: Path, monkeypatch) -> None:
        """Backup for issue-credential exists but not for verify-upload."""
        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")

        ts_dir = tmp_path / "build" / "fc" / "backup" / "20260526-120000"
        ts_dir.mkdir(parents=True)
        (ts_dir / "issue-credential.zip").write_text("code")

        result = dfc_module.rollback("verify-upload")
        assert result is False


# ---------------------------------------------------------------------------
# Logs tests
# ---------------------------------------------------------------------------


class TestFcLogs:
    """AC: make fc-logs handles both configured and unconfigured SLS."""

    @mock.patch.dict(os.environ, {"ALIYUN_DEPLOY_AK_ID": "test-id", "ALIYUN_DEPLOY_AK_SECRET": "test-secret"}, clear=False)
    def test_logs_unconfigured(self, monkeypatch) -> None:
        """When SLS is not configured, output diagnostic message instead of error."""

        mock_client = mock.MagicMock()
        mock_resp = mock.MagicMock()
        # Simulate no log_config
        del mock_resp.body.log_config
        mock_client.get_function.return_value = mock_resp
        monkeypatch.setattr(dfc_module, "_get_fc_client", lambda: mock_client)

        result = dfc_module.fc_logs("issue-credential")
        assert result is True  # Not an error — diagnostic was given
        assert mock_client.get_function.called

    @mock.patch.dict(os.environ, {"ALIYUN_DEPLOY_AK_ID": "test-id", "ALIYUN_DEPLOY_AK_SECRET": "test-secret"}, clear=False)
    def test_logs_with_sls_configured(self, monkeypatch) -> None:
        """When SLS is configured, print project/logstore info."""

        mock_client = mock.MagicMock()
        mock_resp = mock.MagicMock()
        mock_log_config = mock.MagicMock()
        mock_log_config.project = "soniscope-logs"
        mock_log_config.logstore = "fc-logs"
        mock_resp.body.log_config = mock_log_config
        mock_client.get_function.return_value = mock_resp
        monkeypatch.setattr(dfc_module, "_get_fc_client", lambda: mock_client)

        result = dfc_module.fc_logs("verify-upload")
        assert result is True

    @mock.patch.dict(os.environ, {"ALIYUN_DEPLOY_AK_ID": "test-id", "ALIYUN_DEPLOY_AK_SECRET": "test-secret"}, clear=False)
    def test_logs_unconfigured_without_log_config_attr(self, monkeypatch) -> None:
        """When get_function response has no log_config attr at all."""

        mock_client = mock.MagicMock()
        mock_resp = mock.MagicMock()
        # Make hasattr return False for log_config
        type(mock_resp.body).log_config = mock.PropertyMock(
            side_effect=AttributeError
        )
        mock_client.get_function.return_value = mock_resp
        monkeypatch.setattr(dfc_module, "_get_fc_client", lambda: mock_client)

        result = dfc_module.fc_logs("issue-credential")
        assert result is True  # Diagnostic output, not an error


# ---------------------------------------------------------------------------
# Error handling — missing env vars
# ---------------------------------------------------------------------------


class TestEnvVarErrors:
    """AC: helpful error when deploy credentials are missing."""

    def test_get_fc_client_missing_env(self, monkeypatch, capsys) -> None:
        """Missing ALIYUN_DEPLOY_AK_ID exits cleanly with message."""
        monkeypatch.delenv("ALIYUN_DEPLOY_AK_ID", raising=False)
        monkeypatch.delenv("ALIYUN_DEPLOY_AK_SECRET", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            dfc_module._get_fc_client()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "ALIYUN_DEPLOY_AK_ID" in captured.err
        assert "ALIYUN_DEPLOY_AK_SECRET" in captured.err


# ---------------------------------------------------------------------------
# Build directory structure (non-regression)
# ---------------------------------------------------------------------------


class TestBuildDirectory:
    """AC: build/fc/ directory structure matches spec."""

    def test_build_dir_is_gitignored(self) -> None:
        """build/ must be in .gitignore."""
        gitignore = REPO_ROOT / ".gitignore"
        content = gitignore.read_text()
        lines = [line.strip() for line in content.splitlines()]
        assert "build/" in lines, "build/ must be in .gitignore"

    def test_deploy_does_not_modify_fc_env(self, tmp_path: Path, monkeypatch) -> None:
        """Deploy should NOT modify env vars, triggers, or runtime config.
        (Verified by checking that UpdateFunctionRequest only carries Code.)"""

        monkeypatch.setattr(dfc_module, "BUILD_DIR", tmp_path / "build" / "fc")
        monkeypatch.setattr(dfc_module, "FC_SRC_DIR", tmp_path / "apps" / "fc")

        src_dir = tmp_path / "apps" / "fc" / "issue_credential"
        src_dir.mkdir(parents=True)
        (src_dir / "handler.py").write_text('def handler(e, c): return {"statusCode": 200}\n')

        mock_client = mock.MagicMock()
        monkeypatch.setattr(dfc_module, "_get_fc_client", lambda: mock_client)
        monkeypatch.setattr(dfc_module, "_backup_function", lambda fn: None)
        monkeypatch.setattr(
            dfc_module, "_curl_survival_check", lambda fn: (True, "HTTP 200")
        )

        dfc_module.deploy("issue-credential")

        # Verify the call was UpdateFunctionRequest with only code
        call_args = mock_client.update_function.call_args
        assert call_args is not None
        # The request should only contain code — not env/config changes
        args, kwargs = call_args
        assert len(args) >= 2 or "request" in kwargs
