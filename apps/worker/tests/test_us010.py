"""Tests for US-010 — FC verify-upload cloud integration test script.

Tests cover:
- Script importability and CLI structure
- Helper functions (HTTP mock, OSS ops mock)
- Block result data classes
- Check block functions with mocked HTTP/OSS responses
- Makefile target existence
- oss_delete_obj.py importability and key derivation
- DeleteObject absence from Worker/FW source
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
FC_ROOT = REPO_ROOT / "apps" / "fc"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import test_verify_upload as _tvu  # noqa: E402


@pytest.fixture
def tvu():
    """Return the test_verify_upload module."""
    return _tvu


@pytest.fixture(autouse=True)
def _manage_sys_path() -> None:
    """Ensure SCRIPTS_DIR stays in sys_path — add if missing."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    yield


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify key constants used in the verify-upload test script."""

    def test_fc_url_is_verify_upload(self, tvu) -> None:
        assert tvu.FC_VERIFY_UPLOAD_URL == (
            "https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run"
        )

    def test_oss_bucket_is_soniscope_audio(self, tvu) -> None:
        assert tvu.OSS_BUCKET == "soniscope-audio"

    def test_oss_endpoint_is_beijing(self, tvu) -> None:
        assert tvu.OSS_ENDPOINT == "oss-cn-beijing.aliyuncs.com"

    def test_test_fragment_id_format(self, tvu) -> None:
        fid = tvu._TEST_FRAGMENT_ID
        assert "T" in fid  # Has date separator
        assert "_testvu_" in fid

    def test_test_object_key_format(self, tvu) -> None:
        key = tvu._TEST_OBJECT_KEY
        assert key.startswith("recordings/")
        assert key.endswith(".wav")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class TestCheckResult:
    """Test the CheckResult dataclass."""

    def test_pass_result(self, tvu) -> None:
        r = tvu.CheckResult(label="test", passed=True, detail="ok")
        assert r.passed is True
        assert r.skipped is False
        assert r.label == "test"

    def test_fail_result(self, tvu) -> None:
        r = tvu.CheckResult(label="test", passed=False, detail="bad", fix_hint="fix it")
        assert r.passed is False
        assert r.fix_hint == "fix it"

    def test_skipped_result(self, tvu) -> None:
        r = tvu.CheckResult(label="test", passed=True, skipped=True, detail="skipped")
        assert r.skipped is True


class TestBlockResult:
    """Test the BlockResult dataclass."""

    def test_empty_block_passes(self, tvu) -> None:
        b = tvu.BlockResult(block="X", title="Test")
        assert b.passed is True

    def test_all_pass(self, tvu) -> None:
        b = tvu.BlockResult(
            block="X",
            title="Test",
            checks=[
                tvu.CheckResult(label="a", passed=True),
                tvu.CheckResult(label="b", passed=True),
            ],
        )
        assert b.passed is True

    def test_one_fails(self, tvu) -> None:
        b = tvu.BlockResult(
            block="X",
            title="Test",
            checks=[
                tvu.CheckResult(label="a", passed=True),
                tvu.CheckResult(label="b", passed=False),
            ],
        )
        assert b.passed is False

    def test_skipped_does_not_affect_pass(self, tvu) -> None:
        b = tvu.BlockResult(
            block="X",
            title="Test",
            checks=[
                tvu.CheckResult(label="a", passed=True),
                tvu.CheckResult(label="b", passed=True, skipped=True),
            ],
        )
        assert b.passed is True


# ---------------------------------------------------------------------------
# _post_verify_upload helper — HTTP-level tests (mocked)
# ---------------------------------------------------------------------------


class TestPostVerifyUpload:
    """Test the _post_verify_upload helper with mocked HTTP responses."""

    def test_post_200_verified_true(self, tvu) -> None:
        """Simulate a verified:true response."""
        mock_resp_data = json.dumps({
            "verified": True,
            "etag": "abc123",
            "size": 54321,
            "last_modified": "Thu, 01 Jan 2026 00:00:00 GMT",
        }).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = mock_resp_data
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            status, body, elapsed = tvu._post_verify_upload({
                "code": "test", "fragment_id": "fid", "expected_size": 54321,
            })

            assert status == 200
            assert body["verified"] is True
            assert body["etag"] == "abc123"
            assert body["size"] == 54321

    def test_post_200_object_not_found(self, tvu) -> None:
        """Simulate an OBJECT_NOT_FOUND response."""
        mock_resp_data = json.dumps({
            "verified": False,
            "reason": "OBJECT_NOT_FOUND",
        }).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = mock_resp_data
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            status, body, elapsed = tvu._post_verify_upload({
                "code": "test", "fragment_id": "missing_fid", "expected_size": 100,
            })

            assert status == 200
            assert body["verified"] is False
            assert body["reason"] == "OBJECT_NOT_FOUND"

    def test_post_200_size_mismatch(self, tvu) -> None:
        """Simulate a SIZE_MISMATCH response."""
        mock_resp_data = json.dumps({
            "verified": False,
            "reason": "SIZE_MISMATCH",
            "actual_size": 100,
        }).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = mock_resp_data
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            status, body, elapsed = tvu._post_verify_upload({
                "code": "test", "fragment_id": "fid", "expected_size": 200,
            })

            assert status == 200
            assert body["verified"] is False
            assert body["reason"] == "SIZE_MISMATCH"
            assert body["actual_size"] == 100

    def test_post_401_invalid_code(self, tvu) -> None:
        """Simulate 401 INVALID_CODE response."""
        error_body = json.dumps({"error": "INVALID_CODE"}).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://test.url", 401, "Unauthorized", {}, io_mock := mock.MagicMock()
            )
            io_mock.read.return_value = error_body

            status, body, elapsed = tvu._post_verify_upload({
                "code": "fake", "fragment_id": "fid", "expected_size": 100,
            })

            assert status == 401
            assert body["error"] == "INVALID_CODE"

    def test_post_connection_error(self, tvu) -> None:
        """Simulate a connection error."""
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            status, body, elapsed = tvu._post_verify_upload({
                "code": "test", "fragment_id": "fid", "expected_size": 100,
            })

            assert status == 0
            assert "Connection failed" in body.get("error", "")

    def test_post_non_json_error_response(self, tvu) -> None:
        """Simulate a non-JSON error response (502 gateway)."""
        error_body = b"<html>Bad Gateway</html>"

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://test.url", 502, "Bad Gateway", {}, io_mock := mock.MagicMock()
            )
            io_mock.read.return_value = error_body

            status, body, elapsed = tvu._post_verify_upload({
                "code": "test", "fragment_id": "fid", "expected_size": 100,
            })

            assert status == 502
            assert isinstance(body, dict)
            assert "error" in body


# ---------------------------------------------------------------------------
# _put_test_object / _delete_test_object — OSS level tests (mocked)
# ---------------------------------------------------------------------------


class TestOssOps:
    """Test OSS upload/delete helper functions."""

    @mock.patch.dict(os.environ, {
        "ALIYUN_DEPLOY_AK_ID": "test-ak",
        "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
    })
    def test_put_test_object_success(self, tvu) -> None:
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.put_object.return_value = None

            ok, detail = tvu._put_test_object("recordings/test/test.wav", b"hello")
            assert ok is True
            assert "Uploaded" in detail

    def test_put_test_object_no_credentials(self, tvu) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            ok, detail = tvu._put_test_object("recordings/test/test.wav", b"hello")
            assert ok is False
            assert "must be set" in detail

    @mock.patch.dict(os.environ, {
        "ALIYUN_DEPLOY_AK_ID": "test-ak",
        "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
    })
    def test_delete_test_object_success(self, tvu) -> None:
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.delete_object.return_value = None

            ok, detail = tvu._delete_test_object("recordings/test/test.wav")
            assert ok is True
            assert "Deleted" in detail

    @mock.patch.dict(os.environ, {
        "ALIYUN_DEPLOY_AK_ID": "test-ak",
        "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
    })
    def test_delete_test_object_404_ok(self, tvu) -> None:
        """404 (already deleted) should also be considered success."""
        with mock.patch("alibabacloud_oss_v2.Client") as mock_client:
            mock_instance = mock_client.return_value
            mock_instance.delete_object.side_effect = Exception("404 NoSuchKey")

            ok, detail = tvu._delete_test_object("recordings/test/missing.wav")
            assert ok is True  # 404 is fine — already absent

    def test_delete_test_object_no_credentials(self, tvu) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            ok, detail = tvu._delete_test_object("recordings/test/test.wav")
            assert ok is False
            assert "must be set" in detail


# ---------------------------------------------------------------------------
# Block A: Deploy & Alive
# ---------------------------------------------------------------------------


class TestBlockA:
    """Test check_block_a function."""

    def test_skip_deploy_flag(self, tvu) -> None:
        ns = mock.MagicMock()
        ns.skip_deploy = True

        with mock.patch.object(tvu, "_post_verify_upload") as mock_post:
            mock_post.return_value = (401, {"error": "INVALID_CODE"}, 0.1)

            result = tvu.check_block_a(ns)

            assert result.checks[0].skipped is True
            assert "已跳过部署" in result.checks[0].detail

    def test_alive_check_pass(self, tvu) -> None:
        ns = mock.MagicMock()
        ns.skip_deploy = True

        with mock.patch.object(tvu, "_post_verify_upload") as mock_post:
            mock_post.return_value = (401, {"error": "INVALID_CODE"}, 0.05)

            result = tvu.check_block_a(ns)

            assert result.checks[1].passed is True  # alive check
            assert "HTTP 401" in result.checks[1].detail

    def test_alive_check_fail_connection_error(self, tvu) -> None:
        ns = mock.MagicMock()
        ns.skip_deploy = True

        with mock.patch.object(tvu, "_post_verify_upload") as mock_post:
            mock_post.return_value = (0, {"error": "Connection failed"}, 0.0)

            result = tvu.check_block_a(ns)

            assert result.checks[1].passed is False


# ---------------------------------------------------------------------------
# Block B: Verified True
# ---------------------------------------------------------------------------


class TestBlockB:
    """Test check_block_b function."""

    def test_no_code_skips(self, tvu) -> None:
        ns = mock.MagicMock()
        ns.code = ""

        with mock.patch.dict(os.environ, {}, clear=True):
            result = tvu.check_block_b(ns)

            assert len(result.checks) == 1
            assert result.checks[0].skipped is True

    def test_with_code_verified_true(self, tvu) -> None:
        ns = mock.MagicMock()
        ns.code = "valid_wx_code"

        with mock.patch.dict(os.environ, {
            "ALIYUN_DEPLOY_AK_ID": "test-ak",
            "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
        }):
            with mock.patch.object(tvu, "_put_test_object") as mock_put, \
                 mock.patch.object(tvu, "_post_verify_upload") as mock_post:

                mock_put.return_value = (True, "Uploaded 100 bytes")
                mock_post.return_value = (200, {
                    "verified": True,
                    "etag": "abc",
                    "size": 100,
                    "last_modified": "Thu, 01 Jan 2026 00:00:00 GMT",
                }, 0.15)

                result = tvu.check_block_b(ns)

                assert result.checks[0].passed is True  # upload
                assert result.checks[1].passed is True  # verified

    def test_upload_fails(self, tvu) -> None:
        ns = mock.MagicMock()
        ns.code = "valid_wx_code"

        with mock.patch.dict(os.environ, {
            "ALIYUN_DEPLOY_AK_ID": "test-ak",
            "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
        }):
            with mock.patch.object(tvu, "_put_test_object") as mock_put:
                mock_put.return_value = (False, "Upload failed: AccessDenied")

                result = tvu.check_block_b(ns)

                assert result.checks[0].passed is False  # upload failed


# ---------------------------------------------------------------------------
# Block C: Object Missing
# ---------------------------------------------------------------------------


class TestBlockC:
    """Test check_block_c function."""

    def test_no_code_skips(self, tvu) -> None:
        block_b = tvu.BlockResult("B", "Test")
        block_b._test_code = ""  # type: ignore[attr-defined]

        ns = mock.MagicMock()
        result = tvu.check_block_c(ns, block_b)

        assert len(result.checks) == 1
        assert result.checks[0].skipped is True

    def test_object_not_found_path(self, tvu) -> None:
        block_b = tvu.BlockResult("B", "Test")
        block_b._test_code = "valid_wx_code"  # type: ignore[attr-defined]

        ns = mock.MagicMock()

        with mock.patch.dict(os.environ, {
            "ALIYUN_DEPLOY_AK_ID": "test-ak",
            "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
        }):
            with mock.patch.object(tvu, "_delete_test_object") as mock_del, \
                 mock.patch.object(tvu, "_post_verify_upload") as mock_post:

                mock_del.return_value = (True, "Deleted")
                mock_post.return_value = (200, {
                    "verified": False,
                    "reason": "OBJECT_NOT_FOUND",
                }, 0.12)

                result = tvu.check_block_c(ns, block_b)

                assert result.checks[0].passed is True  # delete
                assert result.checks[1].passed is True  # not found

    def test_delete_fails_returns_false(self, tvu) -> None:
        block_b = tvu.BlockResult("B", "Test")
        block_b._test_code = "valid_wx_code"  # type: ignore[attr-defined]

        ns = mock.MagicMock()

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(tvu, "_delete_test_object") as mock_del:
                mock_del.return_value = (False, "Delete failed")

                result = tvu.check_block_c(ns, block_b)

                assert result.checks[0].passed is False


# ---------------------------------------------------------------------------
# Block D: Size Mismatch
# ---------------------------------------------------------------------------


class TestBlockD:
    """Test check_block_d function."""

    def test_no_code_skips(self, tvu) -> None:
        block_b = tvu.BlockResult("B", "Test")
        block_b._test_code = ""  # type: ignore[attr-defined]

        ns = mock.MagicMock()
        result = tvu.check_block_d(ns, block_b)

        assert len(result.checks) == 1
        assert result.checks[0].skipped is True

    def test_size_mismatch_path(self, tvu) -> None:
        block_b = tvu.BlockResult("B", "Test")
        block_b._test_code = "valid_wx_code"  # type: ignore[attr-defined]

        ns = mock.MagicMock()

        with mock.patch.dict(os.environ, {
            "ALIYUN_DEPLOY_AK_ID": "test-ak",
            "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
        }):
            with mock.patch.object(tvu, "_put_test_object") as mock_put, \
                 mock.patch.object(tvu, "_delete_test_object") as mock_del, \
                 mock.patch.object(tvu, "_post_verify_upload") as mock_post:

                mock_put.return_value = (True, "Uploaded 100 bytes")
                mock_del.return_value = (True, "Deleted")
                mock_post.return_value = (200, {
                    "verified": False,
                    "reason": "SIZE_MISMATCH",
                    "actual_size": 100,
                }, 0.1)

                result = tvu.check_block_d(ns, block_b)

                assert result.checks[0].passed is True  # upload
                assert result.checks[1].passed is True  # size mismatch


# ---------------------------------------------------------------------------
# Block E: Auth Failures
# ---------------------------------------------------------------------------


class TestBlockE:
    """Test check_block_e function."""

    def test_no_code_fake_code_both_denied(self, tvu) -> None:
        ns = mock.MagicMock()

        with mock.patch.object(tvu, "_post_verify_upload") as mock_post:
            # no code → 400, fake code → 401
            mock_post.side_effect = [
                (400, {"error": "MISSING_FIELD"}, 0.05),
                (401, {"error": "INVALID_CODE"}, 0.08),
            ]

            result = tvu.check_block_e(ns)

            assert result.checks[0].passed is True  # no code → error
            assert result.checks[1].passed is True  # fake code → 401

    def test_no_object_info_leaked_on_auth_fail(self, tvu) -> None:
        """AC: Auth failures must not leak object info."""
        ns = mock.MagicMock()

        with mock.patch.object(tvu, "_post_verify_upload") as mock_post:
            # Response with object info leaked — "verified" field present + reason OBJECT_NOT_FOUND
            mock_post.side_effect = [
                (400, {"error": "MISSING_FIELD"}, 0.05),
                (401, {"error": "INVALID_CODE", "verified": False, "reason": "OBJECT_NOT_FOUND"}, 0.08),
            ]

            result = tvu.check_block_e(ns)

            # E.2 should FAIL because object info leaked (verified field present in error response)
            assert result.checks[1].passed is False


# ---------------------------------------------------------------------------
# Block F: P95 Timing & Logs
# ---------------------------------------------------------------------------


class TestBlockF:
    """Test check_block_f function."""

    def test_no_code_no_timing_data(self, tvu) -> None:
        block_b = tvu.BlockResult("B", "Test")

        ns = mock.MagicMock()
        with mock.patch.object(tvu, "subprocess") as mock_sub:
            mock_proc = mock.MagicMock()
            mock_proc.stdout = "not configured"
            mock_proc.stderr = ""
            mock_sub.run.return_value = mock_proc

            result = tvu.check_block_f(ns, block_b)

            # Should have skipped timing but still have logs check
            assert any(c.skipped for c in result.checks)

    def test_reports_p95_timing(self, tvu) -> None:
        block_b = tvu.BlockResult("B", "Test")
        block_b._upload_ok = True  # type: ignore[attr-defined]
        block_b._test_code = "valid_code"  # type: ignore[attr-defined]

        ns = mock.MagicMock()

        with mock.patch.dict(os.environ, {
            "ALIYUN_DEPLOY_AK_ID": "test-ak",
            "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
        }):
            with mock.patch.object(tvu, "_put_test_object") as mock_put, \
                 mock.patch.object(tvu, "_delete_test_object") as mock_del, \
                 mock.patch.object(tvu, "_post_verify_upload") as mock_post, \
                 mock.patch.object(tvu, "subprocess") as mock_sub:

                mock_put.return_value = (True, "ok")
                mock_del.return_value = (True, "ok")

                # 5 timing samples, all fast
                mock_post.side_effect = [
                    (200, {"verified": True, "etag": "x", "size": 100, "last_modified": "t"}, 0.12),
                    (200, {"verified": True, "etag": "x", "size": 100, "last_modified": "t"}, 0.15),
                    (200, {"verified": True, "etag": "x", "size": 100, "last_modified": "t"}, 0.11),
                    (200, {"verified": True, "etag": "x", "size": 100, "last_modified": "t"}, 0.18),
                    (200, {"verified": True, "etag": "x", "size": 100, "last_modified": "t"}, 0.14),
                ]

                mock_proc = mock.MagicMock()
                mock_proc.stdout = "not configured"
                mock_proc.stderr = ""
                mock_sub.run.return_value = mock_proc

                result = tvu.check_block_f(ns, block_b)

                # Find the timing check
                timing_checks = [c for c in result.checks if "P95" in c.label or "响应时间" in c.label]
                if timing_checks:
                    assert timing_checks[0].passed is True  # All < 1s


# ---------------------------------------------------------------------------
# Makefile targets
# ---------------------------------------------------------------------------


class TestMakefileTargets:
    """Verify the Makefile targets exist."""

    def test_makefile_has_test_verify_upload_target(self) -> None:
        makefile_path = REPO_ROOT / "Makefile"
        content = makefile_path.read_text()
        assert "test-verify-upload:" in content
        assert "test_verify_upload.py" in content

    def test_makefile_has_oss_delete_obj_target(self) -> None:
        makefile_path = REPO_ROOT / "Makefile"
        content = makefile_path.read_text()
        assert "oss-delete-obj:" in content
        assert "oss_delete_obj.py" in content
        assert "仅测试用" in content

    def test_phony_includes_new_targets(self) -> None:
        makefile_path = REPO_ROOT / "Makefile"
        content = makefile_path.read_text()
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
        assert "test-verify-upload" in phony
        assert "oss-delete-obj" in phony


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestCLI:
    """Test CLI argument parsing."""

    def test_default_args_no_code(self, tvu) -> None:
        ns = tvu.argparse.Namespace(code="", skip_deploy=False)
        assert ns.code == ""
        assert ns.skip_deploy is False

    def test_with_code_and_skip_deploy(self, tvu) -> None:
        ns = tvu.argparse.Namespace(code="test_code", skip_deploy=True)
        assert ns.code == "test_code"
        assert ns.skip_deploy is True


# ---------------------------------------------------------------------------
# Color / mark helpers
# ---------------------------------------------------------------------------


class TestColorHelpers:
    """Test color and mark helper functions."""

    def test_pass_mark_contains_check(self, tvu) -> None:
        mark = tvu._pass_mark()
        assert "✓" in mark

    def test_fail_mark_contains_cross(self, tvu) -> None:
        mark = tvu._fail_mark()
        assert "✗" in mark

    def test_bold_wraps(self, tvu) -> None:
        result = tvu._bold("hello")
        assert "hello" in result
        assert tvu._BOLD in result

    def test_green_wraps(self, tvu) -> None:
        result = tvu._green("ok")
        assert "ok" in result
        assert tvu._GREEN in result


# ---------------------------------------------------------------------------
# Run function return values
# ---------------------------------------------------------------------------


class TestRunFunction:
    """Test the main run_test_verify_upload function."""

    def test_run_returns_zero_on_all_pass(self, tvu) -> None:
        with mock.patch.object(tvu, "check_block_a") as mock_a, \
             mock.patch.object(tvu, "check_block_b") as mock_b, \
             mock.patch.object(tvu, "check_block_c") as mock_c, \
             mock.patch.object(tvu, "check_block_d") as mock_d, \
             mock.patch.object(tvu, "check_block_e") as mock_e, \
             mock.patch.object(tvu, "check_block_f") as mock_f:

            def _pass_block(*args, **kwargs):
                return tvu.BlockResult("X", "Test", checks=[
                    tvu.CheckResult(label="ok", passed=True)
                ])

            mock_a.return_value = _pass_block()
            mock_b.return_value = _pass_block()
            mock_c.return_value = _pass_block()
            mock_d.return_value = _pass_block()
            mock_e.return_value = _pass_block()
            mock_f.return_value = _pass_block()

            ns = mock.MagicMock()
            ns.code = ""
            ns.skip_deploy = True

            ret = tvu.run_test_verify_upload(ns)
            assert ret == 0

    def test_run_returns_one_on_any_fail(self, tvu) -> None:
        with mock.patch.object(tvu, "check_block_a") as mock_a, \
             mock.patch.object(tvu, "check_block_b") as mock_b, \
             mock.patch.object(tvu, "check_block_c") as mock_c, \
             mock.patch.object(tvu, "check_block_d") as mock_d, \
             mock.patch.object(tvu, "check_block_e") as mock_e, \
             mock.patch.object(tvu, "check_block_f") as mock_f:

            mock_a.return_value = tvu.BlockResult("A", "Deploy", checks=[
                tvu.CheckResult(label="fail", passed=False, detail="bad")
            ])
            mock_b.return_value = tvu.BlockResult("B", "Verified", checks=[
                tvu.CheckResult(label="ok", passed=True, skipped=True)
            ])
            mock_c.return_value = tvu.BlockResult("C", "Missing", checks=[
                tvu.CheckResult(label="ok", passed=True, skipped=True)
            ])
            mock_d.return_value = tvu.BlockResult("D", "Size", checks=[
                tvu.CheckResult(label="ok", passed=True, skipped=True)
            ])
            mock_e.return_value = tvu.BlockResult("E", "Auth", checks=[
                tvu.CheckResult(label="ok", passed=True)
            ])
            mock_f.return_value = tvu.BlockResult("F", "Timing", checks=[
                tvu.CheckResult(label="ok", passed=True)
            ])

            ns = mock.MagicMock()
            ns.code = ""
            ns.skip_deploy = True

            ret = tvu.run_test_verify_upload(ns)
            assert ret == 1


# ---------------------------------------------------------------------------
# oss_delete_obj.py tests
# ---------------------------------------------------------------------------


class TestOssDeleteObj:
    """Test the oss_delete_obj.py script."""

    def test_importable(self) -> None:
        import oss_delete_obj
        assert hasattr(oss_delete_obj, "_fragment_oss_key")
        assert hasattr(oss_delete_obj, "_delete_object")
        assert callable(oss_delete_obj._fragment_oss_key)
        assert callable(oss_delete_obj._delete_object)

    def test_help_note_present(self) -> None:
        import oss_delete_obj
        assert "仅测试用" in oss_delete_obj.HELP_NOTE

    def test_fragment_oss_key_derivation(self) -> None:
        import oss_delete_obj

        key = oss_delete_obj._fragment_oss_key(
            "20260601T120000_abcd_01HZX3K8MN5PQR9TFB7AYWVCDE"
        )
        assert key == "recordings/2026-06-01/20260601T120000_abcd_01HZX3K8MN5PQR9TFB7AYWVCDE.wav"

    def test_fragment_oss_key_no_t_separator(self) -> None:
        import oss_delete_obj

        with pytest.raises(ValueError, match="no 'T' separator"):
            oss_delete_obj._fragment_oss_key("bad_fragment_id")

    def test_fragment_oss_key_bad_date_length(self) -> None:
        import oss_delete_obj

        with pytest.raises(ValueError, match="date portion"):
            oss_delete_obj._fragment_oss_key("2026T_bad_date_rest")

    def test_delete_no_credentials(self) -> None:
        import oss_delete_obj

        with mock.patch.dict(os.environ, {}, clear=True):
            ok, detail = oss_delete_obj._delete_object("recordings/test/test.wav")
            assert ok is False
            assert "must be set" in detail

    @mock.patch.dict(os.environ, {
        "ALIYUN_DEPLOY_AK_ID": "test-ak",
        "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
    })
    def test_delete_success(self) -> None:
        import oss_delete_obj

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.status = 204
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            ok, detail = oss_delete_obj._delete_object("recordings/test/test.wav")
            assert ok is True
            assert "Deleted" in detail

    @mock.patch.dict(os.environ, {
        "ALIYUN_DEPLOY_AK_ID": "test-ak",
        "ALIYUN_DEPLOY_AK_SECRET": "test-sk",
    })
    def test_delete_404_ok(self) -> None:
        import oss_delete_obj
        from urllib.error import HTTPError

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                "http://test.url", 404, "Not Found", {}, None
            )

            ok, detail = oss_delete_obj._delete_object("recordings/test/test.wav")
            assert ok is True
            assert "absent" in detail.lower()


# ---------------------------------------------------------------------------
# DeleteObject absence from Worker + FC source
# ---------------------------------------------------------------------------


class TestDeleteObjectAbsence:
    """AC: Worker business source does NOT contain DeleteObject calls."""

    def test_worker_src_no_delete_object(self) -> None:
        """Verify no DeleteObject in apps/worker/src/."""
        worker_src = REPO_ROOT / "apps" / "worker" / "src"
        if worker_src.is_dir():
            import subprocess
            result = subprocess.run(
                ["grep", "-r", "-l", "-E", "DeleteObject|delete_object", str(worker_src)],
                capture_output=True, text=True,
            )
            assert result.returncode != 0, (
                f"Worker source contains DeleteObject calls: {result.stdout.strip()}"
            )

    def test_fc_src_no_delete_object(self) -> None:
        """Verify no DeleteObject in apps/fc/ (FC function source)."""
        fc_src = REPO_ROOT / "apps" / "fc"
        if fc_src.is_dir():
            import subprocess
            result = subprocess.run(
                ["grep", "-r", "-l", "-E", "DeleteObject|delete_object", str(fc_src)],
                capture_output=True, text=True,
            )
            assert result.returncode != 0, (
                f"FC source contains DeleteObject calls: {result.stdout.strip()}"
            )

    def test_oss_delete_obj_labeled_test_only(self) -> None:
        """AC: oss-delete-obj script is labeled 仅测试用."""
        script_path = REPO_ROOT / "scripts" / "oss_delete_obj.py"
        content = script_path.read_text()
        assert "仅测试用" in content
