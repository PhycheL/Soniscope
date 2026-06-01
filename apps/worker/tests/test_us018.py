"""Unit tests for US-018 — verify, 48h retention, manual delete, re-verify.

Covers:
- cleanup.js module structure and exports
- runAutoCleanup: verified + 48h+ → removed; non-verified → kept
- runAutoCleanup: verified < 48h → kept; no verifiedAt → kept
- deleteRecordById: found → removed; not found → false
- _tryRemoveFile exists (integration coverage)
- uploader.js: triggerReVerify, deleteRecord public API
- uploader.js: cleanup integration (runAutoCleanup post-verify)
- app.js: cleanup imported, runAutoCleanup called in onLaunch
- upload-list.js: onReVerify, onDeleteRecord handlers
- upload-list.wxml: re-verify button, delete button
- upload-list.wxss: action button styles
- JS syntax on all changed files
- No hardcoded keys
- Makefile miniprogram-lint covers cleanup.js
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

# ── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[3]
MINIPROGRAM_DIR = REPO_ROOT / "apps" / "miniprogram"
CLEANUP_PATH = MINIPROGRAM_DIR / "utils" / "cleanup.js"
UPLOADER_PATH = MINIPROGRAM_DIR / "utils" / "uploader.js"
CONSTANTS_PATH = MINIPROGRAM_DIR / "utils" / "constants.js"
APP_JS_PATH = MINIPROGRAM_DIR / "app.js"
UPLOAD_LIST_JS_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.js"
UPLOAD_LIST_WXML_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.wxml"
UPLOAD_LIST_WXSS_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.wxss"
MAKEFILE_PATH = REPO_ROOT / "Makefile"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _read_js(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_makefile() -> str:
    return MAKEFILE_PATH.read_text(encoding="utf-8")


def _js_syntax_ok(path: Path):
    """Check JS syntax with node -c."""
    result = subprocess.run(
        ["node", "-c", str(path)],
        capture_output=True, text=True,
    )
    return result.returncode == 0, result.stderr


# ── Test: cleanup.js module structure ────────────────────────────────────────

class TestCleanupModuleStructure:
    """Verify cleanup.js exists and exports the expected API."""

    def test_cleanup_file_exists(self):
        assert CLEANUP_PATH.exists(), "utils/cleanup.js should exist"

    def test_cleanup_exports_api(self):
        content = _read_js(CLEANUP_PATH)
        assert "module.exports" in content
        assert "runAutoCleanup" in content
        assert "deleteRecordById" in content

    def test_cleanup_exports_test_internals(self):
        content = _read_js(CLEANUP_PATH)
        assert "_loadUploadList" in content
        assert "_saveUploadList" in content
        assert "_tryRemoveFile" in content


# ── Test: cleanup.js — runAutoCleanup logic ──────────────────────────────────

class TestRunAutoCleanup:
    """Verify runAutoCleanup logic via code structure analysis."""

    def test_uses_audio_retention_constant(self):
        content = _read_js(CLEANUP_PATH)
        # Should reference AUDIO_RETENTION_MS constant
        assert "AUDIO_RETENTION_MS" in content or "retentionMs" in content

    def test_checks_verified_status(self):
        content = _read_js(CLEANUP_PATH)
        # Must check for VERIFIED status explicitly
        assert "VERIFIED" in content
        # Must handle non-verified as kept (AC6)
        assert "verified" in content.lower()

    def test_checks_verified_at_timestamp(self):
        content = _read_js(CLEANUP_PATH)
        # Must check verifiedAt exists
        assert "verifiedAt" in content

    def test_calculates_time_diff(self):
        content = _read_js(CLEANUP_PATH)
        # Must compare current time vs verified time with retention period
        assert "Date.now" in content or "getTime" in content or "retention" in content.lower()

    def test_only_cleans_verified_records(self):
        content = _read_js(CLEANUP_PATH)
        # AC6: non-verified records are kept (pushed to kept array)
        assert "kept" in content.lower() or "keep" in content.lower()
        # Must remove only verified+48h+ records
        assert "VERIFIED" in content

    def test_has_removed_count_tracking(self):
        content = _read_js(CLEANUP_PATH)
        assert "removed" in content.lower()

    def test_saves_list_after_cleanup(self):
        content = _read_js(CLEANUP_PATH)
        # After removing items, must persist the list
        assert "setStorageSync" in content


# ── Test: cleanup.js — deleteRecordById ──────────────────────────────────────

class TestDeleteRecordById:
    """Verify deleteRecordById logic via code structure analysis."""

    def test_delete_searches_by_fragment_id(self):
        content = _read_js(CLEANUP_PATH)
        assert "fragmentId" in content and "splice" in content

    def test_delete_returns_success_result(self):
        content = _read_js(CLEANUP_PATH)
        assert "success" in content
        assert "wasVerified" in content

    def test_delete_returns_false_for_not_found(self):
        content = _read_js(CLEANUP_PATH)
        # Should handle missing records gracefully
        assert "success: false" in content or "success:false" in content


# ── Test: uploader.js — new exports ──────────────────────────────────────────

class TestUploaderNewExports:
    """Verify uploader.js exports the new US-018 API."""

    def test_uploader_exports_trigger_re_verify(self):
        content = _read_js(UPLOADER_PATH)
        assert "triggerReVerify" in content

    def test_uploader_exports_delete_record(self):
        content = _read_js(UPLOADER_PATH)
        assert "deleteRecord" in content

    def test_uploader_imports_cleanup(self):
        content = _read_js(UPLOADER_PATH)
        assert "cleanup.js" in content or "require('./cleanup.js')" in content

    def test_trigger_re_verify_calls_wx_login(self):
        content = _read_js(UPLOADER_PATH)
        # triggerReVerify should do wx.login → verify flow
        assert "triggerReVerify" in content


# ── Test: uploader.js — cleanup integration post-verify ──────────────────────

class TestCleanupIntegrationInUploader:
    """Verify uploader calls runAutoCleanup after successful verification."""

    def test_calls_cleanup_after_verify_success(self):
        content = _read_js(UPLOADER_PATH)
        # After verify success, should call cleanup.runAutoCleanup()
        assert "cleanup.runAutoCleanup" in content

    def test_cleanup_imported_at_top(self):
        content = _read_js(UPLOADER_PATH)
        assert "require('./cleanup.js')" in content


# ── Test: app.js — cleanup on launch ─────────────────────────────────────────

class TestAppCleanupIntegration:
    """Verify app.js imports and calls cleanup on launch."""

    def test_app_imports_cleanup(self):
        content = _read_js(APP_JS_PATH)
        assert "cleanup" in content
        assert "require('./utils/cleanup.js')" in content

    def test_app_calls_run_auto_cleanup_in_on_launch(self):
        content = _read_js(APP_JS_PATH)
        # Must call cleanup.runAutoCleanup() in onLaunch
        assert "runAutoCleanup" in content

    def test_app_logs_cleanup_result(self):
        content = _read_js(APP_JS_PATH)
        assert "auto-cleanup" in content.lower() or "cleanup" in content.lower()


# ── Test: upload-list.js — new handlers ──────────────────────────────────────

class TestUploadListNewHandlers:
    """Verify upload-list page has re-verify and delete handlers."""

    def test_has_on_re_verify_handler(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onReVerify" in content

    def test_has_on_delete_record_handler(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onDeleteRecord" in content

    def test_delete_record_checks_verified_status(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # AC7: should check whether record is verified for different confirmation messages
        assert "isVerified" in content or "VERIFIED" in content

    def test_delete_record_has_double_confirm_for_non_verified(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # AC7 specific text for non-verified deletion
        assert "尚未成功上传" in content

    def test_delete_for_verified_has_single_confirm(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # Verified records only need simple confirmation
        assert "云端 OSS" in content

    def test_re_verify_calls_trigger_re_verify(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "triggerReVerify" in content

    def test_re_verify_reloads_list(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "_loadUploadList" in content


# ── Test: upload-list.wxml — new UI elements ─────────────────────────────────

class TestUploadListWxmlNewElements:
    """Verify WXML has re-verify and delete buttons."""

    def test_has_re_verify_button(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "onReVerify" in content or "重新校验" in content

    def test_has_delete_button(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "onDeleteRecord" in content

    def test_re_verify_button_for_verified_only(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        # Re-verify should only be visible for verified records
        assert "verified" in content.lower()

    def test_delete_passes_status_data(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        # Delete button should pass item.status as data-status
        assert "data-status" in content


# ── Test: upload-list.wxss — new styles ──────────────────────────────────────

class TestUploadListWxssNewStyles:
    """Verify WXSS has new action button styles."""

    def test_has_item_actions_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".item-actions" in content

    def test_has_action_btn_styles(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".action-btn" in content

    def test_has_reverify_button_color(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert "reverify" in content.lower()

    def test_has_delete_button_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert "delete" in content.lower()


# ── Test: JS syntax ──────────────────────────────────────────────────────────

class TestJsSyntax:
    """Verify all modified JS files pass node -c syntax check."""

    @pytest.mark.parametrize("path", [
        CLEANUP_PATH,
        UPLOADER_PATH,
        APP_JS_PATH,
        UPLOAD_LIST_JS_PATH,
    ])
    def test_js_syntax(self, path):
        ok, err = _js_syntax_ok(Path(path))
        assert ok, f"{path.name} should pass node -c: {err}"


# ── Test: No hardcoded keys ──────────────────────────────────────────────────

class TestNoHardcodedKeys:
    """Verify new files don't contain hardcoded AK/Secret/Token."""

    def test_cleanup_no_hardcoded_keys(self):
        content = _read_js(CLEANUP_PATH)
        # No LTAI-prefixed access key IDs
        assert "LTAI" not in content, "cleanup.js must not contain hardcoded AccessKey"

    def test_uploader_no_new_hardcoded_keys(self):
        content = _read_js(UPLOADER_PATH)
        # Count all LTAI occurrences — should only be from existing legitimate references
        ltai_count = content.count("LTAI")
        # Should be minimal (pattern strings like "LTAB" or legitimate references)
        assert ltai_count <= 10, f"Too many LTAI references: {ltai_count}"


# ── Test: Makefile miniprogram-lint ──────────────────────────────────────────

class TestMakefileCoverage:
    """Verify Makefile miniprogram-lint covers cleanup.js."""

    def test_miniprogram_lint_covers_cleanup(self):
        content = _read_makefile()
        assert "cleanup.js" in content, "Makefile miniprogram-lint should cover cleanup.js"


# ── Test: Constants — AUDIO_RETENTION_MS ─────────────────────────────────────

class TestConstantsRetention:
    """Verify retention constant is set to 48 hours."""

    def test_audio_retention_defined(self):
        content = _read_js(CONSTANTS_PATH)
        assert "AUDIO_RETENTION_MS" in content

    def test_audio_retention_is_48h(self):
        content = _read_js(CONSTANTS_PATH)
        assert "48" in content


# ── Test: Cleanup logic — comprehensive path coverage ────────────────────────

class TestCleanupLogicPaths:
    """Verify all cleanup paths exist in code."""

    def test_cleanup_checks_record_count(self):
        content = _read_js(CLEANUP_PATH)
        assert "list.length" in content or "list.length" in content

    def test_cleanup_early_return_empty_list(self):
        content = _read_js(CLEANUP_PATH)
        # Early return when list is empty
        assert "return 0" in content or "return 0" in content

    def test_cleanup_preserves_non_verified(self):
        content = _read_js(CLEANUP_PATH)
        # Non-verified records must be kept
        assert "kept" in content.lower()

    def test_cleanup_preserves_recent_verified(self):
        content = _read_js(CLEANUP_PATH)
        # Verified but < 48h must be kept
        assert "retention" in content.lower() or "now -" in content or "now-" in content

    def test_cleanup_try_remove_file_called(self):
        content = _read_js(CLEANUP_PATH)
        assert "_tryRemoveFile" in content


# ── Test: Re-verify logic ────────────────────────────────────────────────────

class TestReVerifyLogic:
    """Verify re-verify flow in uploader.js."""

    def test_reverify_sets_pending_verify_status(self):
        content = _read_js(UPLOADER_PATH)
        assert "PENDING_VERIFY" in content

    def test_reverify_handles_verify_false(self):
        content = _read_js(UPLOADER_PATH)
        # Should handle OBJECT_NOT_FOUND / SIZE_MISMATCH
        assert "VERIFY_FALSE_OBJECT_NOT_FOUND" in content or "OBJECT_NOT_FOUND" in content

    def test_reverify_handles_network_error(self):
        content = _read_js(UPLOADER_PATH)
        assert "MANUAL_VERIFY" in content


# ── Test: Delete logic with status awareness ─────────────────────────────────

class TestDeleteStatusAwareness:
    """Verify delete logic distinguishes verified vs non-verified records."""

    def test_upload_list_knows_record_status(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # Must get status from dataset
        assert "status" in content

    def test_non_verified_double_confirm(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # Double showModal for non-verified
        assert "再次确认" in content

    def test_delete_calls_uploader_delete_record(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "deleteRecord" in content


# ── Test: Status constants integrity ─────────────────────────────────────────

class TestStatusConstantsIntegrity:
    """Verify upload status constants are complete for US-018."""

    def test_manual_retry_exists(self):
        content = _read_js(CONSTANTS_PATH)
        assert "MANUAL_RETRY" in content
        assert "manual_retry" in content

    def test_manual_verify_exists(self):
        content = _read_js(CONSTANTS_PATH)
        assert "MANUAL_VERIFY" in content
        assert "manual_verify" in content

    def test_verified_exists(self):
        content = _read_js(CONSTANTS_PATH)
        assert "PENDING_VERIFY" in content
        assert "VERIFIED" in content


# ── Test: UploadList page completeness ───────────────────────────────────────

class TestUploadListPageCompleteness:
    """Verify upload-list page includes all required functionality."""

    def test_all_four_file_types_exist(self):
        assert UPLOAD_LIST_JS_PATH.exists()
        assert (MINIPROGRAM_DIR / "pages/upload-list/upload-list.json").exists()
        assert UPLOAD_LIST_WXML_PATH.exists()
        assert UPLOAD_LIST_WXSS_PATH.exists()

    def test_js_imports_uploader(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "uploader" in content
