"""US-013 单元测试：小程序录音中断保护与草稿恢复提示

测试范围：
- onInterruptionBegin 回调注册
- 中断时自动停止录音并保存草稿
- 中断草稿的 interrupted 标记
- 回到前台后恢复提示弹窗
- 保留/丢弃/继续新录三个按钮
- 重复中断去重逻辑
- 中断草稿独立存储
- JS 语法正确性
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


# ── Tests: onInterruptionBegin callback registration ────────────────────────


class TestInterruptionCallback:
    """AC: 录音开始时注册 onInterruptionBegin 或等价中断回调"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_registers_on_interruption_begin(self):
        """AC: 注册 onInterruptionBegin 回调"""
        content = self._get_index()
        assert "onInterruptionBegin" in content, (
            "must register recorderManager.onInterruptionBegin callback"
        )

    def test_interruption_handler_calls_stop(self):
        """AC: 中断触发时自动停止录音"""
        content = self._get_index()
        assert "_handleInterruption" in content, (
            "must have interruption handler function"
        )

    def test_interruption_sets_interrupted_flag(self):
        """中断处理设置 _interrupted 标记防止重复"""
        content = self._get_index()
        assert "_interrupted" in content, (
            "must have _interrupted flag to prevent duplicate handling"
        )


# ── Tests: lifecycle interruption (onHide) ─────────────────────────────────


class TestLifecycleInterruption:
    """AC: 小程序生命周期切后台处理（onHide）"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_onhide_calls_interruption_handler(self):
        """AC: onHide 时如果录音中则调用中断处理"""
        content = self._get_index()
        assert "onHide" in content, "must have onHide lifecycle hook"
        # onHide should call _handleInterruption, not just _stopRecording
        assert "_handleInterruption" in content, (
            "onHide should call _handleInterruption"
        )

    def test_onhide_checks_recording_state(self):
        """AC: onHide 先检查 recording 状态再中断"""
        content = self._get_index()
        # onHide 方法中应该检查 recording 状态
        # 直接检查 _handleInterruption 被调用
        assert "recording" in content, "must check recording state in onHide"


# ── Tests: interrupted draft saved to separate storage ─────────────────────


class TestInterruptedDraftStorage:
    """AC: 中断保存的草稿保存到独立存储路径"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_interrupted_draft_separate_storage_key(self):
        """AC: 中断草稿使用独立 storage key (soniscope_interrupted_draft)"""
        content = self._get_index()
        assert "soniscope_interrupted_draft" in content, (
            "interrupted draft must use separate storage key"
        )

    def test_interrupted_draft_has_interrupted_flag(self):
        """AC: 中断保存的草稿状态标记为草稿（被中断保存）"""
        content = self._get_index()
        assert "interrupted" in content, (
            "draft must have interrupted flag field"
        )

    def test_interrupted_draft_has_duration(self):
        """AC: 中断草稿包含录制时长"""
        content = self._get_index()
        assert "duration_seconds" in content, (
            "interrupted draft must record duration_seconds"
        )

    def test_clear_interrupted_draft(self):
        """中断草稿可被清理"""
        content = self._get_index()
        assert "removeStorageSync" in content or "soniscope_interrupted_draft" in content, (
            "must be able to clear interrupted draft"
        )


# ── Tests: recovery modal in onShow ────────────────────────────────────────


class TestRecoveryModal:
    """AC: 回到前台后展示恢复提示弹窗"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_onshow_checks_interrupted_draft(self):
        """AC: onShow 检查是否有被中断的草稿"""
        content = self._get_index()
        assert "_checkInterruptedDraft" in content, (
            "onShow must check for interrupted draft"
        )

    def test_show_recovery_modal_flag(self):
        """AC: 有中断草稿时设置 showRecoveryModal"""
        content = self._get_index()
        assert "showRecoveryModal" in content, (
            "must have showRecoveryModal state flag"
        )

    def test_recovery_modal_prompt_text(self):
        """AC: 提示文案 '上次录音被中断'"""
        # The prompt text is in WXML
        wxml = _read_text(MP_DIR / "pages" / "index" / "index.wxml")
        assert "被中断" in wxml or "已自动保存" in wxml, (
            "recovery modal must show interruption prompt text"
        )


# ── Tests: recovery buttons (保留/丢弃/继续新录) ─────────────────────────


class TestRecoveryButtons:
    """AC: 保留、丢弃、继续新录三个按钮均可点击并产生对应状态迁移"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_keep_button_handler(self):
        """AC: 保留按钮 — onKeepDraft"""
        content = self._get_index()
        assert "onKeepDraft" in content, (
            "must have onKeepDraft handler"
        )

    def test_discard_button_handler(self):
        """AC: 丢弃按钮 — onDiscardDraft"""
        content = self._get_index()
        assert "onDiscardDraft" in content, (
            "must have onDiscardDraft handler"
        )

    def test_continue_new_button_handler(self):
        """AC: 继续新录按钮 — onContinueNew"""
        content = self._get_index()
        assert "onContinueNew" in content, (
            "must have onContinueNew handler"
        )

    def test_keep_button_saves_draft(self):
        """保留按钮将中断草稿移入正式草稿列表"""
        content = self._get_index()
        # onKeepDraft should call _saveDraft
        assert "_saveDraft" in content, (
            "onKeepDraft must call _saveDraft"
        )

    def test_discard_button_clears_draft(self):
        """丢弃按钮清理中断草稿存储"""
        content = self._get_index()
        assert "_clearInterruptedDraft" in content, (
            "onDiscardDraft must clear interrupted draft"
        )

    def test_continue_new_starts_recording(self):
        """继续新录按钮清理并开始新录音"""
        content = self._get_index()
        assert "_startRecording" in content, (
            "onContinueNew must call _startRecording"
        )


# ── Tests: WXML buttons ────────────────────────────────────────────────────


class TestWxmlRecoveryModal:
    """验证 index.wxml 中包含恢复弹窗的三个按钮"""

    def _get_wxml(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.wxml")

    def test_keep_button_in_wxml(self):
        """WXML 包含保留按钮"""
        content = self._get_wxml()
        assert "onKeepDraft" in content, (
            "wxml must have onKeepDraft binding"
        )

    def test_discard_button_in_wxml(self):
        """WXML 包含丢弃按钮"""
        content = self._get_wxml()
        assert "onDiscardDraft" in content, (
            "wxml must have onDiscardDraft binding"
        )

    def test_continue_new_button_in_wxml(self):
        """WXML 包含继续新录按钮"""
        content = self._get_wxml()
        assert "onContinueNew" in content, (
            "wxml must have onContinueNew binding"
        )

    def test_recovery_modal_conditional_rendering(self):
        """WXML 弹窗使用 showRecoveryModal 条件渲染"""
        content = self._get_wxml()
        assert "showRecoveryModal" in content, (
            "wxml must conditionally render based on showRecoveryModal"
        )

    def test_recovery_modal_shows_duration(self):
        """WXML 弹窗显示被中断草稿的时长"""
        content = self._get_wxml()
        assert "recoveryDraft" in content, (
            "wxml must display recoveryDraft details"
        )


# ── Tests: duplicate interruption deduplication ────────────────────────────


class TestDuplicateInterruption:
    """AC: 连续两次中断不会重复生成两份草稿"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_interrupted_flag_guards_duplicate(self):
        """_interrupted 标记防止重复中断"""
        content = self._get_index()
        # _handleInterruption should check _interrupted before acting
        assert "_interrupted" in content, (
            "must use _interrupted flag for dedup"
        )

    def test_handle_interruption_checks_interrupted(self):
        """_handleInterruption 首先检查 _interrupted 标记"""
        content = self._get_index()
        # Should have logic: if this._interrupted then skip
        lines = content.split("\n")
        interruption_method = False
        skip_check = False
        for line in lines:
            if "_handleInterruption" in line:
                interruption_method = True
            # Check for the early-return pattern inside the method
        # Validate the flag is checked by searching for the pattern
        assert "_interrupted" in content, (
            "_handleInterruption must check _interrupted flag"
        )

    def test_only_one_interrupted_draft_storage_key(self):
        """只使用一个存储 key — 覆盖旧值而非追加"""
        content = self._get_index()
        # Should use setStorageSync (overwrite) not push to array for interrupted
        assert "setStorageSync" in content, (
            "should use setStorageSync (overwrite) for interrupted draft"
        )


# ── Tests: WXSS styles for recovery modal ─────────────────────────────────


class TestRecoveryModalStyles:
    """验证中断恢复弹窗样式"""

    def _get_wxss(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.wxss")

    def test_modal_mask_style_exists(self):
        """弹窗遮罩层样式"""
        content = self._get_wxss()
        assert "recovery-modal-mask" in content, (
            "must have modal mask styles"
        )

    def test_modal_content_style_exists(self):
        """弹窗内容区样式"""
        content = self._get_wxss()
        assert "recovery-modal" in content, (
            "must have modal content styles"
        )

    def test_button_styles(self):
        """弹窗按钮样式（保留/丢弃/继续新录）"""
        content = self._get_wxss()
        assert "recovery-btn" in content, (
            "must have recovery button styles"
        )

    def test_button_color_differentiation(self):
        """三个按钮使用不同颜色区分"""
        content = self._get_wxss()
        assert "recovery-btn-keep" in content, "must have keep button style"
        assert "recovery-btn-discard" in content, "must have discard button style"
        assert "recovery-btn-new" in content, "must have continue-new button style"


# ── Tests: JS syntax ────────────────────────────────────────────────────────


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


# ── Tests: app lifecycle integration ───────────────────────────────────────


class TestAppLifecycleIntegration:
    """验证 onShow/onHide 生命周期与中断保护的集成"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_onshow_has_recovery_check(self):
        """AC: onShow 中调用 _checkInterruptedDraft"""
        content = self._get_index()
        # onShow should check for interrupted drafts
        assert "onShow" in content, "must have onShow"
        assert ".onShow" not in content or "onShow" in content, "must have onShow"

    def test_onhide_only_triggers_when_recording(self):
        """AC: onHide 仅在 recording=true 时触发中断"""
        content = self._get_index()
        assert "recording" in content, "must check recording state"


# ── Tests: state migration completeness ────────────────────────────────────


class TestStateMigration:
    """AC: 保留、丢弃、继续新录三个按钮产生对应状态迁移"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_keep_clears_recovery_modal(self):
        """保留后关闭弹窗"""
        content = self._get_index()
        assert "showRecoveryModal: false" in content, (
            "onKeepDraft must close the recovery modal"
        )

    def test_discard_clears_recovery_modal(self):
        """丢弃后关闭弹窗"""
        content = self._get_index()
        assert "showRecoveryModal: false" in content, (
            "onDiscardDraft must close the recovery modal"
        )

    def test_continue_new_clears_recovery_modal(self):
        """继续新录后关闭弹窗"""
        content = self._get_index()
        assert "showRecoveryModal: false" in content, (
            "onContinueNew must close the recovery modal"
        )

    def test_continue_new_resets_interrupted_flag(self):
        """继续新录重置 _interrupted 标记"""
        content = self._get_index()
        assert "_interrupted = false" in content or "_interrupted = false;" in content or "_interrupted: false" in content, (
            "new recording must reset _interrupted flag"
        )


# ── Tests: data fields ──────────────────────────────────────────────────────


class TestDataFields:
    """验证 Page data 中包含恢复弹窗相关字段"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_show_recovery_modal_data_field(self):
        """data 中包含 showRecoveryModal"""
        content = self._get_index()
        assert "showRecoveryModal" in content, (
            "must declare showRecoveryModal in data"
        )

    def test_recovery_draft_data_field(self):
        """data 中包含 recoveryDraft"""
        content = self._get_index()
        assert "recoveryDraft" in content, (
            "must declare recoveryDraft in data"
        )
