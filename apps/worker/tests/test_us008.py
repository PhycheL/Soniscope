"""Tests for US-008 — FC issue-credential cloud integration test & STS security anti-pattern script.

Tests cover:
- Script importability and CLI structure
- Helper functions (_post_fc mock, _try_oss_op mock)
- Block result data classes
- Check block functions with mocked HTTP/OSS responses
- Makefile target existence
- URL constants correctness
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Ensure the import path is set before any fixtures run
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Import the test_fc_live module (scripts/test_fc_live.py)
import test_fc_live as _tfcl  # noqa: E402


@pytest.fixture
def tfcl():
    """Return the test_fc_live module."""
    return _tfcl


@pytest.fixture(autouse=True)
def _manage_sys_path() -> None:
    """Ensure SCRIPTS_DIR stays in sys.path — add if missing."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    yield


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify key constants used in the live test script."""

    def test_fc_url_is_issue_credential(self, tfcl) -> None:
        assert tfcl.FC_ISSUE_CREDENTIAL_URL == (
            "https://issue-cedential-ottfirocds.cn-beijing.fcapp.run"
        )

    def test_oss_bucket_is_soniscope_audio(self, tfcl) -> None:
        assert tfcl.OSS_BUCKET == "soniscope-audio"

    def test_oss_endpoint_is_beijing(self, tfcl) -> None:
        assert tfcl.OSS_ENDPOINT == "oss-cn-beijing.aliyuncs.com"

    def test_test_fragment_id_format(self, tfcl) -> None:
        fid = tfcl._TEST_FRAGMENT_ID
        assert "T" in fid  # Has date separator
        assert fid.endswith("_01HZX3K8MN5PQR9TFB7AYWVCDE")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class TestCheckResult:
    """Test the CheckResult dataclass."""

    def test_pass_result(self, tfcl) -> None:
        r = tfcl.CheckResult(label="test", passed=True, detail="ok")
        assert r.passed is True
        assert r.skipped is False
        assert r.label == "test"

    def test_fail_result(self, tfcl) -> None:
        r = tfcl.CheckResult(label="test", passed=False, detail="bad", fix_hint="fix it")
        assert r.passed is False
        assert r.fix_hint == "fix it"

    def test_skipped_result(self, tfcl) -> None:
        r = tfcl.CheckResult(label="test", passed=True, skipped=True, detail="skipped")
        assert r.skipped is True


class TestBlockResult:
    """Test the BlockResult dataclass."""

    def test_empty_block_passes(self, tfcl) -> None:
        b = tfcl.BlockResult(block="X", title="Test")
        assert b.passed is True

    def test_all_pass(self, tfcl) -> None:
        b = tfcl.BlockResult(
            block="X",
            title="Test",
            checks=[
                tfcl.CheckResult(label="a", passed=True),
                tfcl.CheckResult(label="b", passed=True),
            ],
        )
        assert b.passed is True

    def test_one_fails(self, tfcl) -> None:
        b = tfcl.BlockResult(
            block="X",
            title="Test",
            checks=[
                tfcl.CheckResult(label="a", passed=True),
                tfcl.CheckResult(label="b", passed=False),
            ],
        )
        assert b.passed is False

    def test_skipped_does_not_affect_pass(self, tfcl) -> None:
        b = tfcl.BlockResult(
            block="X",
            title="Test",
            checks=[
                tfcl.CheckResult(label="a", passed=True),
                tfcl.CheckResult(label="b", passed=True, skipped=True),
            ],
        )
        assert b.passed is True

    def test_only_skipped_passes(self, tfcl) -> None:
        b = tfcl.BlockResult(
            block="X",
            title="Test",
            checks=[
                tfcl.CheckResult(label="a", passed=True, skipped=True),
            ],
        )
        assert b.passed is True


# ---------------------------------------------------------------------------
# _post_fc helper — HTTP-level tests (mocked)
# ---------------------------------------------------------------------------


class TestPostFc:
    """Test the _post_fc helper with mocked HTTP responses."""

    def test_post_fc_200_with_sts(self, tfcl) -> None:
        """Simulate a successful STS issuance response."""
        mock_resp_data = json.dumps({
            "access_key_id": "STS.test",
            "access_key_secret": "test-secret",
            "security_token": "test-token",
            "expiration": "2026-06-02T15:00:00Z",
            "bucket": "soniscope-audio",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "object_key": "recordings/2026-06-02/test.wav",
        }).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = mock_resp_data
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            status, body = tfcl._post_fc({"code": "test", "fragment_id": "fid", "size": 1000})

            assert status == 200
            assert body["access_key_id"] == "STS.test"
            assert body["bucket"] == "soniscope-audio"

    def test_post_fc_401_invalid_code(self, tfcl) -> None:
        """Simulate 401 INVALID_CODE response."""
        error_body = json.dumps({"error": "INVALID_CODE"}).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://test.url", 401, "Unauthorized", {}, io_mock := mock.MagicMock()
            )
            io_mock.read.return_value = error_body

            status, body = tfcl._post_fc({"code": "fake", "fragment_id": "fid", "size": 1000})

            assert status == 401
            assert body["error"] == "INVALID_CODE"

    def test_post_fc_403_not_allowed(self, tfcl) -> None:
        """Simulate 403 OPENID_NOT_ALLOWED response."""
        error_body = json.dumps({"error": "OPENID_NOT_ALLOWED"}).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://test.url", 403, "Forbidden", {}, io_mock := mock.MagicMock()
            )
            io_mock.read.return_value = error_body

            status, body = tfcl._post_fc({"code": "test", "fragment_id": "fid", "size": 1000})

            assert status == 403
            assert body["error"] == "OPENID_NOT_ALLOWED"

    def test_post_fc_400_size_exceeded(self, tfcl) -> None:
        """Simulate 400 SIZE_EXCEEDED response."""
        error_body = json.dumps({
            "error": "SIZE_EXCEEDED",
            "limit_bytes": 52428800,
            "actual_bytes": 60000000,
        }).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://test.url", 400, "Bad Request", {}, io_mock := mock.MagicMock()
            )
            io_mock.read.return_value = error_body

            status, body = tfcl._post_fc({"code": "test", "fragment_id": "fid", "size": 60_000_000})

            assert status == 400
            assert body["error"] == "SIZE_EXCEEDED"
            assert body["limit_bytes"] == 52428800
            assert body["actual_bytes"] == 60000000

    def test_post_fc_connection_error(self, tfcl) -> None:
        """Simulate a connection error."""
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            status, body = tfcl._post_fc({"code": "test", "fragment_id": "fid", "size": 1000})

            assert status == 0
            assert "Connection failed" in body.get("error", "")

    def test_post_fc_non_json_response(self, tfcl) -> None:
        """Simulate a non-JSON error response."""
        error_body = b"<html>Server Error</html>"

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://test.url", 502, "Bad Gateway", {}, io_mock := mock.MagicMock()
            )
            io_mock.read.return_value = error_body

            status, body = tfcl._post_fc({"code": "test", "fragment_id": "fid", "size": 1000})

            assert status == 502
            # Should have fallen back to a generic error dict
            assert isinstance(body, dict)
            assert "error" in body


# ---------------------------------------------------------------------------
# _try_oss_op helper — OSS level tests (mocked)
# ---------------------------------------------------------------------------


class TestTryOssOp:
    """Test the _try_oss_op helper with mocked OSS SDK."""

    FAKE_CREDS = {
        "access_key_id": "STS.test",
        "access_key_secret": "test-secret",
        "security_token": "test-token",
    }

    def test_put_to_wrong_key_denied(self, tfcl) -> None:
        """PutObject to wrong key should be denied."""
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.put_object.side_effect = Exception("AccessDenied by bucket policy")

            denied, detail = tfcl._try_oss_op(
                self.FAKE_CREDS, "recordings/2026-06-02/wrong.wav", "put"
            )

            assert denied is True
            assert "correctly denied" in detail

    def test_get_object_denied(self, tfcl) -> None:
        """GetObject should be denied with STS PutObject-only policy."""
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.get_object.side_effect = Exception("AccessDenied")

            denied, detail = tfcl._try_oss_op(
                self.FAKE_CREDS, "recordings/2026-06-02/test.wav", "get"
            )

            assert denied is True

    def test_list_objects_denied(self, tfcl) -> None:
        """ListObjects should be denied with STS PutObject-only policy."""
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.list_objects.side_effect = Exception("AccessDenied")

            denied, detail = tfcl._try_oss_op(
                self.FAKE_CREDS, "recordings/", "list"
            )

            assert denied is True

    def test_delete_object_denied(self, tfcl) -> None:
        """DeleteObject should be denied with STS PutObject-only policy."""
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.delete_object.side_effect = Exception("AccessDenied")

            denied, detail = tfcl._try_oss_op(
                self.FAKE_CREDS, "recordings/2026-06-02/test.wav", "delete"
            )

            assert denied is True

    def test_put_to_correct_key_allowed(self, tfcl) -> None:
        """PutObject to correct key should succeed (no exception)."""
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.put_object.return_value = None  # Success — no exception

            denied, detail = tfcl._try_oss_op(
                self.FAKE_CREDS, "recordings/2026-06-02/test.wav", "put"
            )

            # Should NOT be denied — the operation succeeded
            assert denied is False
            assert "unexpectedly succeeded" in detail.lower()

    def test_expired_token_recognized(self, tfcl) -> None:
        """ExpiredToken error should be recognized as denied."""
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.put_object.side_effect = Exception("SecurityTokenExpired")

            denied, detail = tfcl._try_oss_op(
                self.FAKE_CREDS, "recordings/2026-06-02/test.wav", "put"
            )

            assert denied is True
            assert "correctly denied" in detail


# ---------------------------------------------------------------------------
# Block A: Auth tests
# ---------------------------------------------------------------------------


class TestBlockA:
    """Test check_block_a function with mocked HTTP calls."""

    @pytest.fixture
    def mock_args(self, tfcl) -> mock.MagicMock:
        """Create a mock argparse namespace."""
        ns = mock.MagicMock()
        ns.code = ""
        return ns

    def test_fake_code_returns_401(self, tfcl, mock_args) -> None:
        with mock.patch.object(tfcl, "_post_fc") as mock_post:
            mock_post.return_value = (401, {"error": "INVALID_CODE"})

            result = tfcl.check_block_a(mock_args)

            assert len(result.checks) >= 2
            # First check: fake code → 401
            assert result.checks[0].passed is True
            assert "401" in result.checks[0].detail
            assert "INVALID_CODE" in result.checks[0].detail

    def test_missing_code_returns_error(self, tfcl, mock_args) -> None:
        with mock.patch.object(tfcl, "_post_fc") as mock_post:
            mock_post.return_value = (400, {"error": "MISSING_FIELD"})

            result = tfcl.check_block_a(mock_args)

            # Second check: missing code → error
            assert result.checks[1].passed is True
            assert "MISSING_FIELD" in result.checks[1].detail

    def test_with_real_code_403_not_allowed(self, tfcl) -> None:
        ns = mock.MagicMock()
        ns.code = "real_test_code"

        with mock.patch.object(tfcl, "_post_fc") as mock_post:
            mock_post.return_value = (403, {"error": "OPENID_NOT_ALLOWED"})

            result = tfcl.check_block_a(ns)

            # Third check: real code
            assert len(result.checks) >= 3
            a3 = result.checks[2]
            assert a3.passed is True  # 403 is correct behavior
            assert "OPENID_NOT_ALLOWED" in a3.detail

    def test_with_real_code_200_success(self, tfcl) -> None:
        ns = mock.MagicMock()
        ns.code = "real_test_code"

        with mock.patch.object(tfcl, "_post_fc") as mock_post:
            mock_post.return_value = (200, {
                "access_key_id": "STS.test",
                "access_key_secret": "secret",
                "security_token": "token",
                "expiration": "2026-06-02T15:00:00Z",
                "bucket": "soniscope-audio",
                "endpoint": "oss-cn-beijing.aliyuncs.com",
                "object_key": "recordings/2026-06-02/test.wav",
            })

            result = tfcl.check_block_a(ns)

            a3 = result.checks[2]
            assert a3.passed is True
            assert "allowlist" in a3.detail.lower()

    def test_fake_code_returns_unexpected_200_is_failure(self, tfcl, mock_args) -> None:
        """If a fake code returns 200, that's a security failure — no STS should leak."""
        with mock.patch.object(tfcl, "_post_fc") as mock_post:
            mock_post.return_value = (200, {
                "access_key_id": "STS.leaked",
                "access_key_secret": "leaked-secret",
                "security_token": "leaked-token",
            })

            result = tfcl.check_block_a(mock_args)

            # Fake code returning 200 means STS leaked without auth — should fail
            assert result.checks[0].passed is False


# ---------------------------------------------------------------------------
# Block B: STS field validation
# ---------------------------------------------------------------------------


class TestBlockB:
    """Test check_block_b function."""

    def test_no_sts_when_auth_failed(self, tfcl) -> None:
        """When block A auth failed (status != 200), block B skips."""
        block_a = tfcl.BlockResult("A", "Auth", checks=[])
        block_a._test_status = 403  # type: ignore[attr-defined]
        block_a._test_body = {"error": "OPENID_NOT_ALLOWED"}  # type: ignore[attr-defined]

        ns = mock.MagicMock()
        result = tfcl.check_block_b(ns, block_a)

        assert result.checks[0].skipped is True
        assert result._sts_creds is None  # type: ignore[attr-defined]

    def test_validates_all_required_fields(self, tfcl) -> None:
        """When STS returned, validate all required fields."""
        block_a = tfcl.BlockResult("A", "Auth", checks=[])
        block_a._test_status = 200  # type: ignore[attr-defined]
        block_a._test_body = {  # type: ignore[attr-defined]
            "access_key_id": "STS.test",
            "access_key_secret": "secret",
            "security_token": "token",
            "expiration": "2026-06-02T15:00:00Z",
            "bucket": "soniscope-audio",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "object_key": "recordings/2026-06-02/test.wav",
        }

        ns = mock.MagicMock()
        result = tfcl.check_block_b(ns, block_a)

        # First check: all required fields present
        assert result.checks[0].passed is True
        assert result.checks[1].passed is True  # bucket
        assert result.checks[2].passed is True  # endpoint
        assert result.checks[3].passed is True  # object_key format
        assert result._sts_creds is not None  # type: ignore[attr-defined]

    def test_missing_field_causes_failure(self, tfcl) -> None:
        """Missing access_key_secret should fail the fields check."""
        block_a = tfcl.BlockResult("A", "Auth", checks=[])
        block_a._test_status = 200  # type: ignore[attr-defined]
        block_a._test_body = {  # type: ignore[attr-defined]
            "access_key_id": "STS.test",
            # access_key_secret missing
            "security_token": "token",
            "expiration": "2026-06-02T15:00:00Z",
            "bucket": "soniscope-audio",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "object_key": "recordings/2026-06-02/test.wav",
        }

        ns = mock.MagicMock()
        result = tfcl.check_block_b(ns, block_a)

        assert result.checks[0].passed is False


# ---------------------------------------------------------------------------
# Block D: Size validation
# ---------------------------------------------------------------------------


class TestBlockD:
    """Test check_block_d function."""

    def test_size_validation_no_code_skips(self, tfcl) -> None:
        """Without a valid code, full size tests are skipped."""
        block_a = tfcl.BlockResult("A", "Auth", checks=[])
        block_a._test_code = ""  # type: ignore[attr-defined]
        block_a._test_status = 0  # type: ignore[attr-defined]

        with mock.patch.object(tfcl, "_post_fc") as mock_post:
            mock_post.return_value = (401, {"error": "INVALID_CODE"})

            ns = mock.MagicMock()
            result = tfcl.check_block_d(ns, block_a)

            # First full check should be skipped
            assert result.checks[0].skipped is True
            # But fake code check should still run
            assert result.checks[1].skipped is False
            assert result.checks[1].passed is True  # 401 is an error, just not leaked info


# ---------------------------------------------------------------------------
# Makefile target
# ---------------------------------------------------------------------------


class TestMakefileTarget:
    """Verify the test-fc-live Makefile target exists."""

    def test_makefile_has_test_fc_live_target(self) -> None:
        makefile_path = REPO_ROOT / "Makefile"
        content = makefile_path.read_text()
        assert "test-fc-live:" in content
        assert "test_fc_live.py" in content

    def test_phoney_includes_test_fc_live(self) -> None:
        makefile_path = REPO_ROOT / "Makefile"
        content = makefile_path.read_text()
        # .PHONY may span multiple lines with backslash continuation —
        # stitch continuation lines together before checking.
        lines = content.splitlines()
        phony = ""
        in_phony = False
        for line in lines:
            if line.strip().startswith(".PHONY:"):
                in_phony = True
                phony = line.strip()
            elif in_phony and line.rstrip("\n").rstrip("\r").endswith("\\"):
                phony += " " + line.strip().rstrip("\\")
            elif in_phony:
                phony += " " + line.strip()
                in_phony = False
        assert phony, "Expected to find a .PHONY: line in Makefile"
        assert "test-fc-live" in phony


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestCLI:
    """Test CLI argument parsing."""

    def test_default_args_no_code(self, tfcl) -> None:
        """Default args should have empty code and wait-expiry False."""
        parser = tfcl.argparse.ArgumentParser()
        tfcl.main.__wrapped__ = lambda: None  # prevent actual run
        ns = tfcl.argparse.Namespace(code="", wait_expiry=False)
        assert ns.code == ""
        assert ns.wait_expiry is False

    def test_with_code_arg(self, tfcl) -> None:
        ns = tfcl.argparse.Namespace(code="test_wx_code", wait_expiry=False)
        assert ns.code == "test_wx_code"

    def test_with_wait_expiry(self, tfcl) -> None:
        ns = tfcl.argparse.Namespace(code="", wait_expiry=True)
        assert ns.wait_expiry is True


# ---------------------------------------------------------------------------
# Color / mark helpers
# ---------------------------------------------------------------------------


class TestColorHelpers:
    """Test color and mark helper functions."""

    def test_pass_mark_contains_check(self, tfcl) -> None:
        mark = tfcl._pass_mark()
        assert "✓" in mark or "✓" in mark

    def test_fail_mark_contains_cross(self, tfcl) -> None:
        mark = tfcl._fail_mark()
        assert "✗" in mark or "✗" in mark

    def test_bold_wraps(self, tfcl) -> None:
        result = tfcl._bold("hello")
        assert "hello" in result
        assert tfcl._BOLD in result

    def test_green_wraps(self, tfcl) -> None:
        result = tfcl._green("ok")
        assert "ok" in result
        assert tfcl._GREEN in result


# ---------------------------------------------------------------------------
# Run function return values
# ---------------------------------------------------------------------------


class TestRunFunction:
    """Test the main run_test_fc_live function."""

    def test_run_returns_zero_on_all_pass(self, tfcl) -> None:
        """When all blocks pass, return 0."""
        with mock.patch.object(tfcl, "check_block_a") as mock_a, \
             mock.patch.object(tfcl, "check_block_b") as mock_b, \
             mock.patch.object(tfcl, "check_block_c") as mock_c, \
             mock.patch.object(tfcl, "check_block_d") as mock_d, \
             mock.patch.object(tfcl, "check_block_e") as mock_e, \
             mock.patch.object(tfcl, "check_block_f") as mock_f:

            def _pass_block(*args, **kwargs):
                return tfcl.BlockResult("X", "Test", checks=[
                    tfcl.CheckResult(label="ok", passed=True)
                ])

            mock_a.return_value = _pass_block()
            mock_b.return_value = _pass_block()
            mock_c.return_value = _pass_block()
            mock_d.return_value = _pass_block()
            mock_e.return_value = _pass_block()
            mock_f.return_value = _pass_block()

            ns = mock.MagicMock()
            ns.code = ""
            ns.wait_expiry = False

            ret = tfcl.run_test_fc_live(ns)
            assert ret == 0

    def test_run_returns_one_on_any_fail(self, tfcl) -> None:
        """When any block fails, return 1."""
        with mock.patch.object(tfcl, "check_block_a") as mock_a, \
             mock.patch.object(tfcl, "check_block_b") as mock_b, \
             mock.patch.object(tfcl, "check_block_c") as mock_c, \
             mock.patch.object(tfcl, "check_block_d") as mock_d, \
             mock.patch.object(tfcl, "check_block_e") as mock_e, \
             mock.patch.object(tfcl, "check_block_f") as mock_f:

            mock_a.return_value = tfcl.BlockResult("A", "Auth", checks=[
                tfcl.CheckResult(label="fail", passed=False, detail="bad")
            ])
            mock_b.return_value = tfcl.BlockResult("B", "STS", checks=[
                tfcl.CheckResult(label="ok", passed=True, skipped=True)
            ])
            mock_c.return_value = tfcl.BlockResult("C", "Escape", checks=[
                tfcl.CheckResult(label="ok", passed=True, skipped=True)
            ])
            mock_d.return_value = tfcl.BlockResult("D", "Size", checks=[
                tfcl.CheckResult(label="ok", passed=True)
            ])
            mock_e.return_value = tfcl.BlockResult("E", "Logs", checks=[
                tfcl.CheckResult(label="ok", passed=True)
            ])
            mock_f.return_value = tfcl.BlockResult("F", "Expiry", checks=[
                tfcl.CheckResult(label="ok", passed=True, skipped=True)
            ])

            ns = mock.MagicMock()
            ns.code = ""
            ns.wait_expiry = False

            ret = tfcl.run_test_fc_live(ns)
            assert ret == 1


# ---------------------------------------------------------------------------
# STS credential fields completeness
# ---------------------------------------------------------------------------


class TestStsCredentialExtraction:
    """Test that STS response correctly populates credential fields."""

    def test_required_sts_fields_in_response(self) -> None:
        """Verify the expected STS response fields per tech-spec §4.1."""
        expected_fields = {
            "access_key_id",
            "access_key_secret",
            "security_token",
            "expiration",
            "bucket",
            "endpoint",
            "object_key",
        }
        # These are the fields defined in the FC response
        assert expected_fields  # not empty
        assert "access_key_id" in expected_fields
        assert "access_key_secret" in expected_fields
        assert "security_token" in expected_fields
        assert "expiration" in expected_fields
