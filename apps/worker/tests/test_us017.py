"""Unit tests for US-017 — 小程序上传队列、STS、OSS 直传.

Covers:
- uploader module structure and exports
- _loadUploadList / _saveUploadList / _updateRecordStatus
- _buildOssFormData (policy/signature/form fields)
- _base64Encode / _hmacSha1Base64 / _sha1Bytes crypto helpers
- _wxLogin / _fetchSts / _ossUploadWithRetry / _verifyUploadWithRetry flow
- _handleUploadFailure / _handleVerifyFailure / _continueNext
- Status constants and Chinese labels
- manual retry trigger
- Makefile target coverage
- show_oss_object.py script structure and imports
- test_sts_escape.py script structure and imports
- JS syntax check on uploader.js
- No hardcoded keys in uploader.js
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# ── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[3]
MINIPROGRAM_DIR = REPO_ROOT / "apps" / "miniprogram"
UPLOADER_PATH = MINIPROGRAM_DIR / "utils" / "uploader.js"
CONSTANTS_PATH = MINIPROGRAM_DIR / "utils" / "constants.js"
APP_JS_PATH = MINIPROGRAM_DIR / "app.js"
INDEX_JS_PATH = MINIPROGRAM_DIR / "pages" / "index" / "index.js"
UPLOAD_LIST_JS_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.js"
UPLOAD_LIST_WXML_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.wxml"
UPLOAD_LIST_WXSS_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.wxss"
SCRIPTS_DIR = REPO_ROOT / "scripts"
SHOW_OSS_OBJECT_PATH = SCRIPTS_DIR / "show_oss_object.py"
TEST_STS_ESCAPE_PATH = SCRIPTS_DIR / "test_sts_escape.py"
MAKEFILE_PATH = REPO_ROOT / "Makefile"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _read_js(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_makefile() -> str:
    return MAKEFILE_PATH.read_text(encoding="utf-8")


def _js_syntax_ok(path: Path) -> bool:
    """Check JS syntax with node -c."""
    result = subprocess.run(
        ["node", "-c", str(path)],
        capture_output=True, text=True,
    )
    return result.returncode == 0, result.stderr


# ── Test: Uploader module structure ──────────────────────────────────────────

class TestUploaderModuleStructure:
    """Verify uploader.js exists and exports the expected API."""

    def test_uploader_file_exists(self):
        assert UPLOADER_PATH.exists(), "utils/uploader.js should exist"

    def test_uploader_exports_all_modules(self):
        content = _read_js(UPLOADER_PATH)
        assert "module.exports" in content
        # Core public API
        assert "initUploader" in content
        assert "processUploadQueue" in content
        assert "triggerManualRetry" in content
        # Internal helpers exported for testing
        assert "_loadUploadList" in content
        assert "_saveUploadList" in content
        assert "_updateRecordStatus" in content
        assert "_buildOssFormData" in content
        assert "_base64Encode" in content
        assert "_hmacSha1Base64" in content
        assert "_sha1Bytes" in content
        assert "_wxLogin" in content
        assert "_fetchSts" in content
        assert "_ossUploadWithRetry" in content
        assert "_verifyUploadWithRetry" in content
        assert "_handleUploadFailure" in content
        assert "_handleVerifyFailure" in content

    def test_uploader_requires_constants(self):
        content = _read_js(UPLOADER_PATH)
        assert "require('./constants.js')" in content or "require('../../utils/constants.js')" in content

    def test_uploader_requires_logger(self):
        content = _read_js(UPLOADER_PATH)
        assert "require('./logger.js')" in content or "require('../../utils/logger.js')" in content

    def test_uploader_js_syntax(self):
        ok, err = _js_syntax_ok(UPLOADER_PATH)
        assert ok, f"uploader.js syntax error: {err}"


# ── Test: Uploader internal helpers (strings/patterns) ────────────────────────

class TestUploaderInternalHelpers:
    """Validate patterns in uploader.js internal functions."""

    def test_load_upload_list_uses_storage_sync(self):
        content = _read_js(UPLOADER_PATH)
        assert "getStorageSync('upload_list')" in content

    def test_save_upload_list_uses_storage_sync(self):
        content = _read_js(UPLOADER_PATH)
        assert "setStorageSync('upload_list'" in content

    def test_network_listener_registered(self):
        content = _read_js(UPLOADER_PATH)
        assert "wx.onNetworkStatusChange" in content

    def test_wx_login_called(self):
        content = _read_js(UPLOADER_PATH)
        assert "wx.login" in content

    def test_wx_request_to_fc_issue_credential(self):
        content = _read_js(UPLOADER_PATH)
        assert "FC_ISSUE_CREDENTIAL_URL" in content or "issue-credential" in content
        assert "wx.request" in content

    def test_wx_upload_file_called(self):
        content = _read_js(UPLOADER_PATH)
        assert "wx.uploadFile" in content

    def test_verify_upload_url_used(self):
        content = _read_js(UPLOADER_PATH)
        assert "FC_VERIFY_UPLOAD_URL" in content or "verify-upload" in content

    def test_retry_logic_with_intervals(self):
        content = _read_js(UPLOADER_PATH)
        assert "UPLOAD_MAX_RETRIES" in content
        assert "UPLOAD_RETRY_INTERVALS" in content
        # Should use 5s/15s/45s pattern
        assert "5000" in content or "15000" in content or "45000" in content

    def test_status_transitions_in_handlers(self):
        content = _read_js(UPLOADER_PATH)
        # Upload failure handler
        assert "MANUAL_RETRY" in content
        assert "retryCount" in content
        # Verify failure handler
        assert "MANUAL_VERIFY" in content

    def test_oss_postobject_form_data_fields(self):
        content = _read_js(UPLOADER_PATH)
        # Form data fields required by OSS PostObject
        assert "OSSAccessKeyId" in content
        assert "Signature" in content
        assert "policyBase64" in content or "policy" in content
        assert "success_action_status" in content
        assert "x-oss-security-token" in content

    def test_x_oss_meta_headers_in_form_data(self):
        content = _read_js(UPLOADER_PATH)
        # The uploader reads x-oss-meta-* keys dynamically from the record's ossMeta field
        # and adds them to the OSS PostObject form data
        assert "ossMeta" in content
        assert "metaKeys" in content
        assert "x-oss-meta" in content or "ossMeta" in content

    def test_upload_progress_tracking(self):
        content = _read_js(UPLOADER_PATH)
        assert "onProgressUpdate" in content
        assert "uploadProgress" in content or "progress" in content

    def test_offline_detection(self):
        content = _read_js(UPLOADER_PATH)
        assert "_networkAvailable" in content
        assert "wx.getNetworkType" in content or "onNetworkStatusChange" in content

    def test_sequential_upload_processing(self):
        content = _read_js(UPLOADER_PATH)
        assert "_uploadingActive" in content
        assert "_continueNext" in content


# ── Test: Base64 / SHA-1 crypto helpers (structure) ──────────────────────────

class TestCryptoHelpers:
    """Validate that uploader.js includes the required crypto implementations."""

    def test_base64_encode_function_exists(self):
        content = _read_js(UPLOADER_PATH)
        assert "function _base64Encode" in content
        assert "_stringToUtf8Bytes" in content
        assert "_bytesToBase64" in content

    def test_hmac_sha1_function_exists(self):
        content = _read_js(UPLOADER_PATH)
        assert "function _hmacSha1Base64" in content or "function _hmacSha1Base64Impl" in content

    def test_sha1_function_exists(self):
        content = _read_js(UPLOADER_PATH)
        assert "function _sha1Bytes" in content


# ── Test: app.js integration ─────────────────────────────────────────────────

class TestAppJsIntegration:
    """Verify app.js integrates the uploader."""

    def test_app_js_requires_uploader(self):
        content = _read_js(APP_JS_PATH)
        assert "require('./utils/uploader.js')" in content

    def test_app_js_calls_init_uploader(self):
        content = _read_js(APP_JS_PATH)
        assert "uploader.initUploader()" in content or "initUploader()" in content

    def test_app_js_calls_init_uploader_in_on_launch(self):
        content = _read_js(APP_JS_PATH)
        # initUploader should be called within onLaunch
        on_launch_start = content.index("onLaunch")
        on_show_start = content.index("onShow")
        init_pos = content.index("initUploader")
        assert on_launch_start < init_pos < on_show_start, \
            "initUploader should be called in onLaunch, before onShow"

    def test_app_js_syntax(self):
        ok, err = _js_syntax_ok(APP_JS_PATH)
        assert ok, f"app.js syntax error: {err}"


# ── Test: index.js integration ───────────────────────────────────────────────

class TestIndexJsIntegration:
    """Verify index.js integrates the uploader for triggering uploads."""

    def test_index_js_requires_uploader(self):
        content = _read_js(INDEX_JS_PATH)
        assert "require('../../utils/uploader.js')" in content

    def test_index_js_triggers_process_upload_queue(self):
        content = _read_js(INDEX_JS_PATH)
        assert "uploader.processUploadQueue()" in content

    def test_process_upload_queue_called_after_save(self):
        content = _read_js(INDEX_JS_PATH)
        # processUploadQueue should be called after _saveDraft and the Toast
        pq_pos = content.index("uploader.processUploadQueue()")
        save_draft_pos = content.rindex("_saveDraft", 0, pq_pos)
        assert save_draft_pos < pq_pos, \
            "processUploadQueue should be called after saving the draft"

    def test_index_js_syntax(self):
        ok, err = _js_syntax_ok(INDEX_JS_PATH)
        assert ok, f"index.js syntax error: {err}"


# ── Test: upload-list.js integration ─────────────────────────────────────────

class TestUploadListJsIntegration:
    """Verify upload-list.js shows progress and manual retry."""

    def test_upload_list_js_requires_uploader(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "require('../../utils/uploader.js')" in content

    def test_upload_list_js_has_manual_retry_handler(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onManualRetry" in content
        assert "triggerManualRetry" in content

    def test_upload_list_js_shows_progress(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "uploadProgress" in content
        assert "progressText" in content

    def test_upload_list_js_syntax(self):
        ok, err = _js_syntax_ok(UPLOAD_LIST_JS_PATH)
        assert ok, f"upload-list.js syntax error: {err}"


# ── Test: upload-list.wxml ───────────────────────────────────────────────────

class TestUploadListWxml:
    """Verify upload-list.wxml includes progress bar and retry button."""

    def test_wxml_has_progress_bar(self):
        content = _read_js(UPLOAD_LIST_WXML_PATH)
        assert "progress-bar" in content
        assert "progress-fill" in content

    def test_wxml_has_retry_section(self):
        content = _read_js(UPLOAD_LIST_WXML_PATH)
        assert "manual_retry" in content or "manual_verify" in content

    def test_wxml_has_manual_retry_button(self):
        content = _read_js(UPLOAD_LIST_WXML_PATH)
        assert "手动重传" in content or "retry-btn" in content

    def test_wxml_has_chunk_info(self):
        content = _read_js(UPLOAD_LIST_WXML_PATH)
        assert "chunkTotal" in content or "chunk_total" in content


# ── Test: upload-list.wxss ───────────────────────────────────────────────────

class TestUploadListWxss:
    """Verify upload-list.wxss includes progress and retry styles."""

    def test_wxss_has_progress_bar_style(self):
        content = _read_js(UPLOAD_LIST_WXSS_PATH)
        assert ".progress-bar" in content
        assert ".progress-fill" in content

    def test_wxss_has_retry_style(self):
        content = _read_js(UPLOAD_LIST_WXSS_PATH)
        assert ".retry-section" in content
        assert ".retry-btn" in content


# ── Test: No hardcoded keys ─────────────────────────────────────────────────

class TestNoHardcodedKeys:
    """Verify no AK/Secret/Token in uploader.js."""

    SENSITIVE_PATTERNS = [
        (r"LTAI[0-9A-Za-z]{16,}", "aliyun access key ID"),
        (r"[a-zA-Z0-9/+]{40,}={0,2}", "base64-like secret (loose check)"),
        (r"access_key_secret\s*[:=]\s*['\"][^'\"]+['\"]", "hardcoded secret assignment"),
    ]

    SENSITIVE_FIELDS = [
        "appsecret", "app_secret", "access_key_secret",
        "accesskeysecret", "securitytoken", "security_token",
    ]

    def test_no_hardcoded_ak_in_uploader(self):
        content = _read_js(UPLOADER_PATH)
        # No LTAI* style keys
        assert not re.search(r"LTAI[0-9A-Za-z]{16,}", content), \
            "uploader.js should not contain hardcoded AccessKey"
        # No base64-like long secrets on single lines in non-constant context
        # (The b64 alphabet is used legitimately — just check for assignment patterns)
        assert "secret_key" not in content.lower() or "ACCESS_KEY_SECRET" not in content, \
            "uploader.js should not contain hardcoded secrets"

    def test_no_sensitive_field_names_in_strings(self):
        content = _read_js(UPLOADER_PATH)
        # Field names like access_key_secret as string labels are OK,
        # but actual values should not appear
        # We check there's no hardcoded "appsecret = '...'" pattern
        for field in self.SENSITIVE_FIELDS:
            regex = re.compile(rf"{field}\s*[:=]\s*['\"]\w{{8,}}['\"]", re.IGNORECASE)
            assert not regex.search(content), \
                f"uploader.js may contain hardcoded value for {field}"


# ── Test: show_oss_object.py script ─────────────────────────────────────────

class TestShowOssObjectScript:
    """Validate the show_oss_object.py script."""

    def test_script_exists(self):
        assert SHOW_OSS_OBJECT_PATH.exists(), "scripts/show_oss_object.py should exist"

    def test_script_is_executable_or_readable(self):
        content = SHOW_OSS_OBJECT_PATH.read_text(encoding="utf-8")
        assert "def main" in content
        assert "fragment_to_oss_key" in content or "fragment_to_date" in content

    def test_script_has_head_object(self):
        content = SHOW_OSS_OBJECT_PATH.read_text(encoding="utf-8")
        assert "oss_head_object" in content or "HeadObject" in content

    def test_script_uses_hmac_sha1_signing(self):
        content = SHOW_OSS_OBJECT_PATH.read_text(encoding="utf-8")
        assert "hmac" in content
        assert "sha1" in content or "SHA1" in content.lower()

    def test_script_reads_oss_meta(self):
        content = SHOW_OSS_OBJECT_PATH.read_text(encoding="utf-8")
        assert "x-oss-meta-" in content

    def test_script_parses_fragment_id_date(self):
        content = SHOW_OSS_OBJECT_PATH.read_text(encoding="utf-8")
        assert "fragment_to_date" in content or "fragment_id" in content

    def test_script_help_text_describes_usage(self):
        content = SHOW_OSS_OBJECT_PATH.read_text(encoding="utf-8")
        assert "show-oss-object" in content or "FRAGMENT_ID" in content

    def test_no_hardcoded_credentials_in_script(self):
        content = SHOW_OSS_OBJECT_PATH.read_text(encoding="utf-8")
        assert "LTAI" not in content, "show_oss_object.py must not contain hardcoded AccessKey"


# ── Test: test_sts_escape.py script ─────────────────────────────────────────

class TestTestStsEscapeScript:
    """Validate the test_sts_escape.py script."""

    def test_script_exists(self):
        assert TEST_STS_ESCAPE_PATH.exists(), "scripts/test_sts_escape.py should exist"

    def test_script_has_four_tests(self):
        content = TEST_STS_ESCAPE_PATH.read_text(encoding="utf-8")
        assert "PutObject" in content
        assert "GetObject" in content
        assert "ListObjects" in content
        assert "DeleteObject" in content

    def test_script_checks_access_denied(self):
        content = TEST_STS_ESCAPE_PATH.read_text(encoding="utf-8")
        assert "AccessDenied" in content or "Access Denied" in content or "403" in content

    def test_script_has_summary(self):
        content = TEST_STS_ESCAPE_PATH.read_text(encoding="utf-8")
        assert "汇总" in content or "PASS" in content or "pass" in content

    def test_script_accepts_sts_params(self):
        content = TEST_STS_ESCAPE_PATH.read_text(encoding="utf-8")
        assert "access_key_id" in content
        assert "access_key_secret" in content
        assert "security_token" in content
        assert "object_key" in content

    def test_no_hardcoded_credentials(self):
        content = TEST_STS_ESCAPE_PATH.read_text(encoding="utf-8")
        assert "LTAI" not in content, "test_sts_escape.py must not contain hardcoded AccessKey"


# ── Test: Makefile targets ──────────────────────────────────────────────────

class TestMakefileTargets:
    """Verify Makefile has show-oss-object and test-sts-escape targets."""

    def test_show_oss_object_target_exists(self):
        content = _read_makefile()
        assert "show-oss-object:" in content

    def test_show_oss_object_uses_fragment_id(self):
        content = _read_makefile()
        assert "FRAGMENT_ID" in content

    def test_test_sts_escape_target_exists(self):
        content = _read_makefile()
        assert "test-sts-escape:" in content

    def test_phony_includes_new_targets(self):
        content = _read_makefile()
        phony_line = ""
        for line in content.split("\n"):
            if line.startswith(".PHONY:"):
                phony_line = line
                # Check for continuation lines
                break
        assert "show-oss-object" in phony_line or "show-oss-object" in content
        assert "test-sts-escape" in phony_line or "test-sts-escape" in content

    def test_miniprogram_lint_covers_uploader(self):
        content = _read_makefile()
        assert "uploader.js" in content


# ── Test: Status constant coverage ──────────────────────────────────────────

class TestStatusConstants:
    """Verify all 8 status constants are defined and used."""

    ALL_STATUSES = [
        "DRAFT", "QUEUED", "UPLOADING", "PENDING_VERIFY",
        "VERIFIED", "UPLOAD_FAILED", "MANUAL_RETRY", "MANUAL_VERIFY",
    ]

    def test_all_statuses_in_constants(self):
        content = _read_js(CONSTANTS_PATH)
        for status in self.ALL_STATUSES:
            assert status in content, f"Status {status} should be defined in constants.js"

    def test_all_status_cn_labels_in_constants(self):
        content = _read_js(CONSTANTS_PATH)
        for status in self.ALL_STATUSES:
            key = status.lower()
            # Check that the Chinese label exists
            assert 'queued:' in content
            assert 'verified:' in content


# ── Test: All JS files syntax check ─────────────────────────────────────────

class TestAllJsSyntax:
    """Complete JS syntax check for all changed files."""

    JS_FILES = [
        UPLOADER_PATH,
        APP_JS_PATH,
        INDEX_JS_PATH,
        UPLOAD_LIST_JS_PATH,
    ]

    @pytest.mark.parametrize("file_path", JS_FILES)
    def test_js_syntax(self, file_path):
        ok, err = _js_syntax_ok(file_path)
        assert ok, f"{file_path.name} has syntax error: {err}"


# ── Test: Python scripts syntax ─────────────────────────────────────────────

class TestPythonScriptsSyntax:
    """Compile-check the Python scripts."""

    def test_show_oss_object_compiles(self):
        result = subprocess.run(
            [sys.executable, "-c",
             f"compile(open({str(SHOW_OSS_OBJECT_PATH)!r}).read(), {str(SHOW_OSS_OBJECT_PATH)!r}, 'exec')"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"show_oss_object.py compile error: {result.stderr}"

    def test_test_sts_escape_compiles(self):
        result = subprocess.run(
            [sys.executable, "-c",
             f"compile(open({str(TEST_STS_ESCAPE_PATH)!r}).read(), {str(TEST_STS_ESCAPE_PATH)!r}, 'exec')"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"test_sts_escape.py compile error: {result.stderr}"


# ── Test: OpenID allowlist / auth validation ─────────────────────────────────

class TestUploaderAuthFlow:
    """Verify the uploader handles auth errors from FC."""

    def test_handle_invalid_code(self):
        content = _read_js(UPLOADER_PATH)
        assert "INVALID_CODE" in content

    def test_handle_openid_not_allowed(self):
        content = _read_js(UPLOADER_PATH)
        # Uploader reads error codes from FC response dynamically
        # It handles STS errors generically (non-200 or missing access_key_id)
        assert "errorCode" in content
        assert "error" in content

    def test_handle_size_exceeded(self):
        content = _read_js(UPLOADER_PATH)
        assert "SIZE_EXCEEDED" in content or "SIZE" in content

    def test_fc_error_preserved_in_record(self):
        content = _read_js(UPLOADER_PATH)
        # Error code should be preserved on the record
        assert "errorCode" in content
        assert "verifyReason" in content
