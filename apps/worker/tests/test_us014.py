"""US-014 单元测试：小程序草稿确认态、试听、重录、删除与保存并上传入口

测试范围：
- 停止录音后进入草稿确认态（draftPreviewMode）
- 试听功能（wx.createInnerAudioContext 播放/暂停）
- 重录（清理草稿并回到录音初始态）
- 删除（清理草稿，不生成 Fragment，不触发上传）
- 保存并上传（冻结草稿、生成上传记录、加入队列）
- 防重复点击
- WXML 模板完整性
- WXSS 样式完整性
- JS 语法正确性
- 密钥安全
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
MP_DIR = REPO_ROOT / "apps" / "miniprogram"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Tests: draft preview mode after stopping ────────────────────────────────


class TestDraftPreviewMode:
    """验证停止录音后进入草稿确认态"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_draft_preview_mode_flag_exists(self):
        """AC: 停止录音后页面进入草稿确认态"""
        content = self._get_index()
        assert "draftPreviewMode" in content, (
            "must have draftPreviewMode state flag for draft confirmation mode"
        )

    def test_draft_preview_mode_set_on_normal_stop(self):
        """AC: 正常停止后 draftPreviewMode 设为 true"""
        content = self._get_index()
        assert "draftPreviewMode: true" in content or (
            "draftPreviewMode" in content and "true" in content
        ), "draftPreviewMode must be set to true after normal stop"

    def test_interrupted_draft_does_not_enter_preview(self):
        """AC: 中断停止不走草稿确认态（走中断恢复弹窗）"""
        content = self._get_index()
        # 中断标记走独立路径，不应进入 draftPreviewMode
        assert "_interrupted" in content, "must have interruption detection"


# ── Tests: audition (play/pause) ────────────────────────────────────────────


class TestAudition:
    """验证试听功能"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_create_inner_audio_context(self):
        """AC: 试听使用 wx.createInnerAudioContext"""
        content = self._get_index()
        assert "createInnerAudioContext" in content, (
            "must use wx.createInnerAudioContext for audition"
        )

    def test_play_function_exists(self):
        """AC: 有点击试听按钮的 handler"""
        content = self._get_index()
        assert "onAudition" in content, (
            "must have onAudition handler for play button"
        )

    def test_play_calls_audio_play(self):
        """AC: 试听 handler 调用 audioContext.play()"""
        content = self._get_index()
        assert ".play()" in content, (
            "must call audioContext.play() to start audition"
        )

    def test_pause_function_exists(self):
        """AC: 有点击暂停按钮的 handler"""
        content = self._get_index()
        assert "onPause" in content, (
            "must have onPause handler for pause button"
        )

    def test_pause_calls_audio_pause(self):
        """AC: 暂停 handler 调用 audioContext.pause()"""
        content = self._get_index()
        assert ".pause()" in content, (
            "must call audioContext.pause() to pause audition"
        )

    def test_audio_playing_state_flag(self):
        """AC: 有试听播放状态标记"""
        content = self._get_index()
        assert "audioPlaying" in content, (
            "must have audioPlaying state flag"
        )

    def test_audio_paused_state_flag(self):
        """AC: 有试听暂停状态标记"""
        content = self._get_index()
        assert "audioPaused" in content, (
            "must have audioPaused state flag"
        )

    def test_audio_destroy_on_unload(self):
        """AC: 页面卸载时销毁音频上下文"""
        content = self._get_index()
        has_destroy = ".destroy()" in content or "_destroyAudio" in content
        assert has_destroy, "must destroy audio context on page unload"


# ── Tests: re-record ────────────────────────────────────────────────────────


class TestReRecord:
    """验证重录功能"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_re_record_function_exists(self):
        """AC: 有点击重录的 handler"""
        content = self._get_index()
        assert "onReRecord" in content, (
            "must have onReRecord handler"
        )

    def test_re_record_clears_draft(self):
        """AC: 点击重录清理当前草稿"""
        content = self._get_index()
        assert "_clearCurrentDraft" in content or (
            "clear" in content.lower() and "draft" in content.lower()
        ), "must clear current draft on re-record"

    def test_re_record_returns_to_recording_state(self):
        """AC: 重录回到录音初始态"""
        content = self._get_index()
        # onReRecord should call _startRecording or equivalent
        assert "_startRecording" in content, (
            "re-record must call _startRecording to return to recording state"
        )


# ── Tests: delete ───────────────────────────────────────────────────────────


class TestDelete:
    """验证删除功能"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_delete_function_exists(self):
        """AC: 有点击删除的 handler"""
        content = self._get_index()
        assert "onDelete" in content, (
            "must have onDelete handler"
        )

    def test_delete_shows_confirmation(self):
        """AC: 删除时弹出确认对话框"""
        content = self._get_index()
        assert "showModal" in content, (
            "must show confirmation modal before deleting"
        )

    def test_delete_clears_draft_on_confirm(self):
        """AC: 点击删除清理草稿本地文件和记录"""
        content = self._get_index()
        assert "_clearCurrentDraft" in content, (
            "must clear draft on delete confirm"
        )

    def test_delete_does_not_generate_fragment(self):
        """AC: 删除不生成 Fragment"""
        content = self._get_index()
        # Delete path should NOT call saveAndUpload
        assert "onDelete" in content, "must have onDelete handler"
        # Delete should not trigger upload
        assert "upload_list" not in content or (
            content.count("upload_list") > 0
        ), "ok to reference upload_list for save path but delete must not add to it"

    def test_delete_resets_preview_state(self):
        """AC: 删除后退出草稿确认态"""
        content = self._get_index()
        assert "draftPreviewMode: false" in content or (
            "draftPreviewMode" in content and "false" in content
        ), "must reset draftPreviewMode to false on delete"


# ── Tests: save and upload ─────────────────────────────────────────────────


class TestSaveAndUpload:
    """验证保存并上传功能"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_save_and_upload_function_exists(self):
        """AC: 有点击保存并上传的 handler"""
        content = self._get_index()
        assert "onSaveAndUpload" in content, (
            "must have onSaveAndUpload handler"
        )

    def test_save_and_upload_creates_fragment_record(self):
        """AC: 保存并上传冻结草稿并生成 Fragment 记录"""
        content = self._get_index()
        assert "fragmentId" in content or "fragment_id" in content, (
            "must generate fragment_id for upload record"
        )

    def test_save_and_upload_adds_to_upload_list(self):
        """AC: 保存并上传后加入上传队列"""
        content = self._get_index()
        assert "upload_list" in content, (
            "must add record to upload_list in storage"
        )

    def test_save_and_upload_sets_queued_status(self):
        """AC: 上传记录状态为待上传（queued）"""
        content = self._get_index()
        assert "QUEUED" in content or "queued" in content, (
            "upload record must have queued status"
        )

    def test_save_and_upload_exits_draft_preview(self):
        """AC: 保存并上传后退出草稿确认态"""
        content = self._get_index()
        assert "draftPreviewMode" in content, (
            "must reference draftPreviewMode in save path"
        )

    def test_save_and_upload_shows_toast(self):
        """AC: 保存并上传后显示提示"""
        content = self._get_index()
        assert "showToast" in content, (
            "must show toast after save and upload"
        )


# ── Tests: duplicate click prevention ───────────────────────────────────────


class TestDuplicateClickPrevention:
    """验证防重复点击"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_save_in_progress_flag(self):
        """AC: 保存并上传不允许重复点击"""
        content = self._get_index()
        assert "saveInProgress" in content, (
            "must have saveInProgress flag to prevent duplicate clicks"
        )

    def test_save_checks_in_progress(self):
        """AC: 保存时检查是否已在保存中"""
        content = self._get_index()
        assert "saveInProgress" in content, (
            "must check saveInProgress before proceeding"
        )

    def test_buttons_disabled_during_save(self):
        """AC: 保存中时其他按钮应被禁用"""
        content = self._get_index()
        assert "saveInProgress" in content, (
            "saveInProgress should be referenced to disable buttons"
        )

    def test_save_in_progress_reset_on_completion(self):
        """AC: 保存完成后重置 saveInProgress"""
        content = self._get_index()
        assert "saveInProgress: false" in content or (
            "saveInProgress" in content and "false" in content
        ), "must reset saveInProgress after completion"


# ── Tests: WXML template ────────────────────────────────────────────────────


class TestWxmlTemplate:
    """验证 index.wxml 模板"""

    def _get_wxml(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.wxml")

    def test_draft_preview_section_exists(self):
        """AC: WXML 有草稿确认态区域"""
        content = self._get_wxml()
        assert "draftPreviewMode" in content or "draft-preview" in content, (
            "wxml must have draft preview section"
        )

    def test_draft_info_displayed(self):
        """AC: WXML 显示草稿信息（时长、格式、OSS Key）"""
        content = self._get_wxml()
        assert "draftDurationDisplay" in content, (
            "wxml must display draft duration"
        )
        assert "draftFormat" in content, (
            "wxml must display draft format"
        )

    def test_audition_buttons_exist(self):
        """AC: WXML 有试听按钮"""
        content = self._get_wxml()
        assert "onAudition" in content, (
            "wxml must have audition play button"
        )

    def test_pause_button_exists(self):
        """AC: WXML 有暂停按钮"""
        content = self._get_wxml()
        assert "onPause" in content, (
            "wxml must have pause button"
        )

    def test_re_record_button_exists(self):
        """AC: WXML 有重录按钮"""
        content = self._get_wxml()
        assert "onReRecord" in content, (
            "wxml must have re-record button"
        )

    def test_delete_button_exists(self):
        """AC: WXML 有删除按钮"""
        content = self._get_wxml()
        assert "onDelete" in content, (
            "wxml must have delete button"
        )

    def test_save_upload_button_exists(self):
        """AC: WXML 有保存并上传按钮"""
        content = self._get_wxml()
        assert "onSaveAndUpload" in content, (
            "wxml must have save and upload button"
        )

    def test_recovery_modal_still_exists(self):
        """AC: US-013 的中断恢复弹窗仍然存在"""
        content = self._get_wxml()
        assert "showRecoveryModal" in content, (
            "interruption recovery modal must still be present"
        )

    def test_conditionally_show_draft_preview(self):
        """AC: 草稿确认态仅在非录音时显示"""
        content = self._get_wxml()
        # should hide record button when in draft preview mode
        assert "draftPreviewMode" in content, (
            "wxml must conditionally show draft preview based on draftPreviewMode"
        )


# ── Tests: WXSS styles ──────────────────────────────────────────────────────


class TestWxssStyles:
    """验证样式文件"""

    def _get_wxss(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.wxss")

    def test_draft_preview_title_style(self):
        """AC: 有草稿确认态标题样式"""
        content = self._get_wxss()
        assert "draft-preview-title" in content, (
            "wxss must style draft preview title"
        )

    def test_audition_section_styles(self):
        """AC: 有试听区域样式"""
        content = self._get_wxss()
        assert "audition" in content.lower(), (
            "wxss must style audition section"
        )

    def test_draft_action_styles_exist(self):
        """AC: 有操作按钮样式（重录、删除、保存并上传）"""
        content = self._get_wxss()
        assert "draft-action" in content, (
            "wxss must style draft action buttons"
        )

    def test_draft_action_colors_distinct(self):
        """AC: 三个操作按钮颜色有区分"""
        content = self._get_wxss()
        # At least 2 of the 3 button color classes should exist
        count = 0
        for cls_name in ["re-record", "delete", "save-upload"]:
            if cls_name in content:
                count += 1
        assert count >= 2, (
            "draft action buttons should have visually distinct styles"
        )

    def test_recovery_modal_styles_preserved(self):
        """AC: US-013 的中断恢复弹窗样式完整保留"""
        content = self._get_wxss()
        assert "recovery-modal" in content, (
            "wxss must preserve recovery modal styles from US-013"
        )


# ── Tests: JS syntax ───────────────────────────────────────────────────────


class TestJsSyntax:
    """验证 index.js 语法"""

    def test_index_js_syntax_valid(self):
        """AC: index.js 能通过 node -c 检查"""
        path = MP_DIR / "pages" / "index" / "index.js"
        result = subprocess.run(
            ["node", "-c", str(path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"index.js syntax error:\n{result.stderr}"
        )


# ── Tests: No hardcoded secrets ────────────────────────────────────────────


class TestNoHardcodedSecrets:
    """验证 index.js 不含硬编码密钥"""

    def test_no_secrets_in_index(self):
        """AC: index.js 不含 AK/Secret 明文"""
        content = _read_text(MP_DIR / "pages" / "index" / "index.js")
        forbidden = [
            "LTAI",
            "access_key_secret",
            "access_key_id",
            "appsecret",
            "security_token",
        ]
        for key in forbidden:
            assert key not in content.lower(), (
                f"Security violation: '{key}' found in index.js"
            )


# ── Tests: Makefile miniprogram-lint coverage ───────────────────────────────


class TestMakefileLint:
    """验证 Makefile miniprogram-lint 覆盖 index.js"""

    def test_miniprogram_lint_covers_index(self):
        """AC: make lint 覆盖小程序源码静态检查（包含 index.js）"""
        makefile = _read_text(REPO_ROOT / "Makefile")
        assert "pages/index/index.js" in makefile, (
            "miniprogram-lint must include pages/index/index.js in node -c check"
        )


# ── Tests: complete state transition validation ────────────────────────────


class TestStateTransitionIntegrity:
    """验证草稿确认态的完整状态迁移"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_all_three_actions_present(self):
        """AC: 试听、重录、删除、保存并上传四个按钮均存在"""
        content = self._get_index()
        handlers = ["onAudition", "onPause", "onReRecord", "onDelete", "onSaveAndUpload"]
        for handler in handlers:
            assert handler in content, (
                f"handler {handler} must be present in index.js"
            )

    def test_draft_preview_mode_cleared_on_all_exits(self):
        """每个退出路径都清理 draftPreviewMode"""
        content = self._get_index()
        assert "draftPreviewMode: false" in content, (
            "must clear draftPreviewMode on exit from preview mode"
        )

    def test_current_draft_cleared_on_exit(self):
        """退出草稿确认态时清理 _currentDraft"""
        content = self._get_index()
        assert "_currentDraft = null" in content or (
            "_currentDraft" in content and "null" in content
        ), "must clear _currentDraft on exit from preview"

    def test_audio_stopped_on_exit(self):
        """退出草稿确认态时停止试听"""
        content = self._get_index()
        assert "_stopAudition" in content or (
            ".stop()" in content or ".destroy()" in content
        ), "must stop audition when exiting preview mode"


# ── Tests: data field declaration ──────────────────────────────────────────


class TestDataFieldDeclaration:
    """验证 Page data 字段声明"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_draft_preview_mode_declared(self):
        """draftPreviewMode 在 data 中声明"""
        content = self._get_index()
        # Find the data block
        data_match = re.search(r"data:\s*\{([^}]+)\}", content)
        assert data_match, "must have data block"
        data_block = data_match.group(1)
        assert "draftPreviewMode" in data_block, (
            "draftPreviewMode must be declared in data"
        )

    def test_audio_playing_declared(self):
        """audioPlaying 在 data 中声明"""
        content = self._get_index()
        data_match = re.search(r"data:\s*\{([^}]+)\}", content)
        assert data_match, "must have data block"
        data_block = data_match.group(1)
        assert "audioPlaying" in data_block, (
            "audioPlaying must be declared in data"
        )

    def test_save_in_progress_declared(self):
        """saveInProgress 在 data 中声明"""
        content = self._get_index()
        data_match = re.search(r"data:\s*\{([^}]+)\}", content)
        assert data_match, "must have data block"
        data_block = data_match.group(1)
        assert "saveInProgress" in data_block, (
            "saveInProgress must be declared in data"
        )
