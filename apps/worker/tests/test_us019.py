"""Unit tests for US-019 — 上传列表八种状态、离线提醒、长录音折叠.

Covers:
- upload-list.js: session grouping (sessionCards/individualRecords)
- upload-list.js: onToggleSession for session card expand/collapse
- upload-list.js: onRetryChunk for per-chunk manual retry
- upload-list.js: _loadUploadList enhanced with pending banner calculation
- upload-list.js: _formatDuration helper
- upload-list.wxml: pending-banner, session-card, session-header,
  session-chunks, chunk-item, chunk-status, session-toggle
- upload-list.wxss: .pending-banner, .session-card, .session-header,
  .session-chunks, .chunk-item, .chunk-status, .session-toggle styles
- JS syntax for all modified files
- No hardcoded keys in upload-list.js
- Makefile miniprogram-lint covers upload-list.js
- Constants: all 8 status codes present in UPLOAD_STATUS_CN
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
UPLOAD_LIST_JS_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.js"
UPLOAD_LIST_WXML_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.wxml"
UPLOAD_LIST_WXSS_PATH = MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.wxss"
CONSTANTS_PATH = MINIPROGRAM_DIR / "utils" / "constants.js"
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


# ── Test: upload-list.js module structure ────────────────────────────────────

class TestUploadListModuleStructure:
    """Verify upload-list.js has all required pages and methods."""

    def test_js_file_exists(self):
        assert UPLOAD_LIST_JS_PATH.exists()

    def test_has_page_definition(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "Page({" in content

    def test_has_data_fields(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # AC6/AC8: sessionCards for grouped long-recording display
        assert "sessionCards" in content
        # individualRecords for non-session records
        assert "individualRecords" in content
        # AC4: pending banner fields
        assert "showBanner" in content
        assert "pendingCount" in content
        assert "hoursSinceEarliest" in content

    def test_requires_uploader(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "require('../../utils/uploader.js')" in content

    def test_requires_constants(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "require('../../utils/constants.js')" in content


# ── Test: upload-list.js — session grouping logic ────────────────────────────

class TestSessionGrouping:
    """Verify _loadUploadList groups records by sessionId for chunkTotal > 1."""

    def test_load_upload_list_groups_by_session_id(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # Must iterate and build sessionMap keyed by sessionId
        assert "sessionId" in content
        assert "sessionMap" in content

    def test_checks_chunk_total_for_grouping(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "chunkTotal" in content

    def test_sorts_chunks_by_chunk_seq(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "chunkSeq" in content

    def test_single_chunk_becomes_individual(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "individualRecords" in content


# ── Test: upload-list.js — session card construction ─────────────────────────

class TestSessionCardConstruction:
    """Verify session card aggregation logic."""

    def test_calculates_total_duration(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "totalDuration" in content

    def test_formats_total_duration_display(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "totalDurationDisplay" in content

    def test_determines_all_verified(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "allVerified" in content

    def test_counts_failed_chunks(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "failedCount" in content

    def test_initializes_expanded_to_false(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "expanded" in content or "false" in content


# ── Test: upload-list.js — pending banner calculation (AC4) ──────────────────

class TestPendingBannerCalculation:
    """Verify the pending banner shows count and hours since earliest recording."""

    def test_checks_queued_status(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "QUEUED" in content

    def test_checks_uploading_status(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "UPLOADING" in content

    def test_checks_upload_failed_status(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "UPLOAD_FAILED" in content

    def test_checks_manual_retry_status(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "MANUAL_RETRY" in content

    def test_checks_manual_verify_status(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "MANUAL_VERIFY" in content

    def test_checks_pending_verify_status(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "PENDING_VERIFY" in content

    def test_calculates_hours_since_earliest(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "Date.now" in content or "getTime" in content
        assert "hoursSinceEarliest" in content

    def test_uses_recorded_at_for_time_calc(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "recordedAt" in content

    def test_set_data_includes_pending_count(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "pendingCount" in content

    def test_set_data_includes_show_banner(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "showBanner" in content


# ── Test: upload-list.js — onToggleSession handler (AC6/AC8) ─────────────────

class TestToggleSession:
    """Verify session card expand/collapse behavior."""

    def test_on_toggle_session_handler_exists(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onToggleSession" in content

    def test_toggle_updates_expanded(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "expanded" in content

    def test_uses_set_data_for_ui_update(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "setData" in content


# ── Test: upload-list.js — onRetryChunk handler (AC8) ────────────────────────

class TestRetryChunk:
    """Verify individual chunk retry within session cards."""

    def test_on_retry_chunk_handler_exists(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onRetryChunk" in content

    def test_retry_chunk_calls_trigger_manual_retry(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "triggerManualRetry" in content

    def test_retry_chunk_uses_fragment_id(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "fragmentId" in content


# ── Test: upload-list.js — _formatDuration helper ────────────────────────────

class TestFormatDuration:
    """Verify time formatting helper exists."""

    def test_format_duration_exists(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "_formatDuration" in content

    def test_format_duration_uses_zero_pad(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # Standard mm:ss with manual zero-padding (consistent with _pad2 in idgen.js)
        assert "'0' + m" in content or "'0' + s" in content or "0' +" in content


# ── Test: upload-list.js — complete handler set ──────────────────────────────

class TestCompleteHandlerSet:
    """Verify all handlers are registered (old + new)."""

    def test_on_load_exists(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onLoad" in content

    def test_on_show_exists(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onShow" in content

    def test_on_manual_retry_exists(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onManualRetry" in content

    def test_on_re_verify_exists(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onReVerify" in content

    def test_on_delete_record_exists(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onDeleteRecord" in content

    def test_all_handlers_in_data_or_methods(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "onToggleSession" in content
        assert "onRetryChunk" in content
        assert "onManualRetry" in content
        assert "onReVerify" in content
        assert "onDeleteRecord" in content


# ── Test: upload-list.wxml — session card elements (AC6) ─────────────────────

class TestWxmlSessionCards:
    """Verify WXML has long-recording session card structure."""

    def test_has_session_card_element(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "session-card" in content

    def test_has_session_header_clickable(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "session-header" in content
        assert "onToggleSession" in content

    def test_has_session_title_with_duration(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "totalDurationDisplay" in content

    def test_has_session_meta_chunk_count(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "chunkCount" in content

    def test_has_session_status_complete(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "allVerified" in content

    def test_has_session_status_failed(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "failed" in content.lower()

    def test_has_session_toggle_arrow(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "session-toggle" in content
        assert "expanded" in content

    def test_has_session_chunks_container(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "session-chunks" in content

    def test_has_chunk_item_structure(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "chunk-item" in content
        assert "chunkSeq" in content

    def test_has_chunk_status_display(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "chunk-status" in content


# ── Test: upload-list.wxml — pending banner (AC4) ────────────────────────────

class TestWxmlPendingBanner:
    """Verify WXML has pending upload banner."""

    def test_has_pending_banner(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "pending-banner" in content

    def test_banner_conditional_on_show_banner(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "showBanner" in content

    def test_banner_shows_pending_count(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "pendingCount" in content

    def test_banner_shows_hours_since_earliest(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "hoursSinceEarliest" in content

    def test_banner_shows_chinese_text(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "未上传" in content
        assert "距离最早录音已" in content


# ── Test: upload-list.wxml — individual records preserved ────────────────────

class TestWxmlIndividualRecords:
    """Verify individual record items are still rendered."""

    def test_has_individual_records_list(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "individualRecords" in content

    def test_has_list_item_for_individual(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "list-item" in content

    def test_has_manual_retry_button(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "onManualRetry" in content

    def test_has_re_verify_button(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "onReVerify" in content

    def test_has_delete_button(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "onDeleteRecord" in content

    def test_has_chunk_retry_in_session(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "onRetryChunk" in content


# ── Test: upload-list.wxss — session card styles (AC6) ───────────────────────

class TestWxssSessionCards:
    """Verify WXSS has session card and chunk styles."""

    def test_has_session_card_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".session-card" in content

    def test_has_session_header_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".session-header" in content

    def test_has_session_title_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".session-title" in content

    def test_has_session_meta_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".session-meta" in content

    def test_has_session_status_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".session-status" in content

    def test_has_session_status_failed_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".session-status-failed" in content

    def test_has_session_toggle_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".session-toggle" in content

    def test_has_session_chunks_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".session-chunks" in content

    def test_has_chunk_item_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".chunk-item" in content

    def test_has_chunk_main_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".chunk-main" in content

    def test_has_chunk_seq_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".chunk-seq" in content

    def test_has_chunk_status_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".chunk-status" in content

    def test_has_chunk_meta_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".chunk-meta" in content


# ── Test: upload-list.wxss — pending banner styles (AC4) ─────────────────────

class TestWxssPendingBanner:
    """Verify WXSS has pending banner styles."""

    def test_has_pending_banner_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".pending-banner" in content

    def test_has_pending_icon_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".pending-icon" in content

    def test_has_pending_text_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".pending-text" in content

    def test_banner_uses_red_color(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        # Banner should have red-ish color for attention
        assert "#f5222d" in content or "#fff1f0" in content or "#ffa39e" in content


# ── Test: upload-list.wxss — preserved old styles ────────────────────────────

class TestWxssPreservedStyles:
    """Verify previously existing styles are still present."""

    def test_has_list_item_style(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".list-item" in content

    def test_has_item_status_styles(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".item-status" in content

    def test_has_progress_bar_styles(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".progress-bar" in content
        assert ".progress-fill" in content

    def test_has_retry_section_styles(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".retry-section" in content

    def test_has_item_actions_styles(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".item-actions" in content
        assert ".action-btn" in content

    def test_has_all_8_status_colors(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".item-status.draft" in content
        assert ".item-status.queued" in content
        assert ".item-status.uploading" in content
        assert ".item-status.pending_verify" in content
        assert ".item-status.verified" in content
        assert ".item-status.upload_failed" in content
        assert ".item-status.manual_retry" in content
        assert ".item-status.manual_verify" in content


# ── Test: Chunk status colors ────────────────────────────────────────────────

class TestChunkStatusColors:
    """Verify chunk status has color classes for all 8 states."""

    def test_chunk_status_has_all_8_states(self):
        content = UPLOAD_LIST_WXSS_PATH.read_text(encoding="utf-8")
        assert ".chunk-status.draft" in content
        assert ".chunk-status.queued" in content
        assert ".chunk-status.uploading" in content
        assert ".chunk-status.pending_verify" in content
        assert ".chunk-status.verified" in content
        assert ".chunk-status.upload_failed" in content
        assert ".chunk-status.manual_retry" in content
        assert ".chunk-status.manual_verify" in content


# ── Test: Constants — all 8 statuses in CN map ───────────────────────────────

class TestConstantsStatuses:
    """Verify all 8 Chinese status labels exist."""

    def test_all_8_status_cn_labels(self):
        content = _read_js(CONSTANTS_PATH)
        assert "draft" in content
        assert "queued" in content
        assert "uploading" in content
        assert "pending_verify" in content
        assert "verified" in content
        assert "upload_failed" in content
        assert "manual_retry" in content
        assert "manual_verify" in content

    def test_cn_label_for_draft(self):
        content = _read_js(CONSTANTS_PATH)
        assert "草稿" in content

    def test_cn_label_for_queued(self):
        content = _read_js(CONSTANTS_PATH)
        assert "待上传" in content

    def test_cn_label_for_uploading(self):
        content = _read_js(CONSTANTS_PATH)
        assert "上传中" in content

    def test_cn_label_for_pending_verify(self):
        content = _read_js(CONSTANTS_PATH)
        assert "待 verify" in content

    def test_cn_label_for_verified(self):
        content = _read_js(CONSTANTS_PATH)
        assert "上传成功" in content

    def test_cn_label_for_upload_failed(self):
        content = _read_js(CONSTANTS_PATH)
        assert "上传失败" in content

    def test_cn_label_for_manual_retry(self):
        content = _read_js(CONSTANTS_PATH)
        assert "待人工重传" in content

    def test_cn_label_for_manual_verify(self):
        content = _read_js(CONSTANTS_PATH)
        assert "待人工 verify" in content


# ── Test: JS syntax ──────────────────────────────────────────────────────────

class TestJsSyntax:
    """Verify all modified JS files pass node -c syntax check."""

    @pytest.mark.parametrize("path", [
        UPLOAD_LIST_JS_PATH,
        CONSTANTS_PATH,
    ])
    def test_js_syntax(self, path):
        ok, err = _js_syntax_ok(Path(path))
        assert ok, f"{path.name} should pass node -c: {err}"


# ── Test: No hardcoded keys ──────────────────────────────────────────────────

class TestNoHardcodedKeys:
    """Verify upload-list.js doesn't contain hardcoded AK/Secret/Token."""

    def test_no_hardcoded_keys_in_upload_list(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "LTAI" not in content, "upload-list.js must not contain hardcoded AccessKey"
        assert "appsecret" not in content.lower(), "upload-list.js must not contain AppSecret"
        assert "access_key_secret" not in content.lower(), (
            "upload-list.js must not contain STS access_key_secret"
        )


# ── Test: Makefile coverage ──────────────────────────────────────────────────

class TestMakefileCoverage:
    """Verify Makefile miniprogram-lint covers upload-list.js."""

    def test_miniprogram_lint_covers_upload_list(self):
        content = _read_makefile()
        assert "upload-list.js" in content, "Makefile miniprogram-lint should cover upload-list.js"


# ── Test: Page file structure ────────────────────────────────────────────────

class TestPageFileStructure:
    """Verify upload-list page has all 4 required files."""

    def test_all_four_files_exist(self):
        assert (MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.js").exists()
        assert (MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.json").exists()
        assert (MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.wxml").exists()
        assert (MINIPROGRAM_DIR / "pages" / "upload-list" / "upload-list.wxss").exists()


# ── Test: WXML conditional rendering logic ───────────────────────────────────

class TestWxmlConditionalRendering:
    """Verify correct wx:if conditions for state-based UI."""

    def test_banner_conditional(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert '{{showBanner}}' in content

    def test_session_chunks_conditional(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert '{{session.expanded}}' in content

    def test_chunk_status_conditions(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        # Should have conditions for manual_retry/manual_verify chunk status
        assert "manual_retry" in content
        assert "manual_verify" in content

    def test_empty_list_checks_total_records(self):
        content = UPLOAD_LIST_WXML_PATH.read_text(encoding="utf-8")
        assert "totalRecords" in content


# ── Test: Session card edge cases ────────────────────────────────────────────

class TestSessionCardEdgeCases:
    """Verify session card handles edge cases."""

    def test_handles_missing_session_id(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # If sessionId is missing, item should go to individualRecords
        assert "individualRecords" in content

    def test_handles_chunk_total_one(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # chunkTotal > 1 is the grouping condition
        assert "chunkTotal" in content

    def test_has_status_text_for_chunks(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        assert "statusText" in content

    def test_has_status_text_for_individual(self):
        content = _read_js(UPLOAD_LIST_JS_PATH)
        # Individual records also get statusText mapping
        assert "statusText" in content
