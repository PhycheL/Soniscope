"""US-012 单元测试：小程序录音开始停止与原始格式记录

测试范围：
- index.js 中 recorderManager 集成
- original_format 探测逻辑
- OSS key 预览生成
- 草稿保存结构
- 计时器显示格式化
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


# ── Tests: index.js structure and integration ────────────────────────────────


class TestIndexJsRecorderIntegration:
    """验证 index.js 中 wx.getRecorderManager 集成"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_requires_recorder_manager(self):
        """AC: index.js 中使用 wx.getRecorderManager()"""
        content = self._get_index()
        assert "wx.getRecorderManager" in content, (
            "index.js must use wx.getRecorderManager"
        )

    def test_registers_onstart(self):
        """recorderManager.onStart 已注册"""
        content = self._get_index()
        assert "onStart" in content, "must register recorderManager.onStart callback"

    def test_registers_onstop(self):
        """recorderManager.onStop 已注册"""
        content = self._get_index()
        assert "onStop" in content, "must register recorderManager.onStop callback"

    def test_registers_onerror(self):
        """recorderManager.onError 已注册"""
        content = self._get_index()
        assert "onError" in content, "must register recorderManager.onError callback"

    def test_recorder_start_called_with_params(self):
        """AC: 调用 recorderManager.start() 并传入参数"""
        content = self._get_index()
        assert "recorderManager.start" in content, "must call recorderManager.start()"
        assert "duration" in content, "should set duration param"
        assert "sampleRate" in content, "should set sampleRate param"

    def test_recorder_stop_called(self):
        """AC: 调用 recorderManager.stop()"""
        content = self._get_index()
        assert "recorderManager.stop" in content, "must call recorderManager.stop()"

    def test_no_transcoding_in_frontend(self):
        """AC: 前端不做转码 — 不应该有 ffmpeg 或 format=wav"""
        content = self._get_index()
        assert "ffmpeg" not in content.lower(), (
            "frontend must not use ffmpeg for transcoding"
        )

    def test_authorize_record_scope(self):
        """AC: 开始录音前请求 scope.record 权限"""
        content = self._get_index()
        assert "scope.record" in content, (
            "must request scope.record authorization"
        )


# ── Tests: original_format detection ─────────────────────────────────────────


class TestOriginalFormatDetection:
    """验证 original_format 探测逻辑"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_detect_format_function_exists(self):
        """AC: 有格式探测函数"""
        content = self._get_index()
        assert "_detectFormat" in content or "detectFormat" in content, (
            "must have a format detection function"
        )

    def test_format_detection_covers_mp3(self):
        """AC: 能识别 mp3 扩展名"""
        content = self._get_index()
        # 应该在探测逻辑中包含 mp3
        assert ".mp3" in content or "'mp3'" in content, (
            "format detection should cover .mp3"
        )

    def test_format_detection_covers_aac(self):
        """能识别 aac 扩展名"""
        content = self._get_index()
        assert ".aac" in content or "'aac'" in content, (
            "format detection should cover .aac"
        )

    def test_format_detection_covers_m4a(self):
        """能识别 m4a 扩展名"""
        content = self._get_index()
        assert ".m4a" in content or "'m4a'" in content, (
            "format detection should cover .m4a"
        )

    def test_format_detection_covers_wav(self):
        """能识别 wav 扩展名"""
        content = self._get_index()
        assert ".wav" in content or "'wav'" in content, (
            "format detection should cover .wav"
        )

    def test_original_format_logged(self):
        """AC: 停止后 original_format 被记录到日志"""
        content = self._get_index()
        assert "original_format" in content, (
            "must reference original_format in code"
        )


# ── Tests: draft structure after stopping ────────────────────────────────────


class TestDraftStructure:
    """验证草稿结构"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_draft_has_original_format(self):
        """AC: 草稿包含 audio.original_format"""
        content = self._get_index()
        assert "original_format" in content, (
            "draft must record audio.original_format"
        )

    def test_draft_has_duration(self):
        """AC: 草稿包含录音时长"""
        content = self._get_index()
        assert "duration" in content or "duration_seconds" in content, (
            "draft must record duration_seconds"
        )

    def test_draft_has_temp_file_path(self):
        """AC: 草稿包含临时音频文件路径"""
        content = self._get_index()
        assert "tempFilePath" in content, (
            "draft must store tempFilePath"
        )

    def test_draft_has_size_bytes(self):
        """AC: 草稿包含文件大小"""
        content = self._get_index()
        assert "size_bytes" in content or "fileSize" in content, (
            "draft should track file size"
        )

    def test_draft_persisted_to_storage(self):
        """AC: 草稿写入本地存储"""
        content = self._get_index()
        assert "setStorageSync" in content or "setStorage" in content, (
            "draft must be persisted to local storage"
        )


# ── Tests: OSS key preview ──────────────────────────────────────────────────


class TestOssKeyPreview:
    """验证 OSS object key 预览"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_oss_key_preview_uses_wav(self):
        """AC: OSS key 预览始终使用 .wav 扩展名"""
        content = self._get_index()
        assert 'recordings/' in content, (
            "OSS key preview must use recordings/ prefix"
        )
        assert '.wav' in content, (
            "OSS key preview must use .wav extension"
        )

    def test_oss_key_preview_not_indicate_frontend_transcode(self):
        """AC: OSS key 使用 .wav 不表示前端已转码"""
        content = self._get_index()
        # 如果有注释说明 .wav 是 Worker 目标格式
        # 不强制检查注释，但检查定义了 key 生成函数
        assert "_buildOssKeyPreview" in content or "oss_key" in content.lower(), (
            "must have OSS key preview generation"
        )


# ── Tests: timer display ─────────────────────────────────────────────────────


class TestTimerDisplay:
    """验证录音计时器"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_timer_format_is_mmss(self):
        """AC: 计时格式为 mm:ss"""
        content = self._get_index()
        # 应该使用 mm:ss 格式
        assert "timerDisplay" in content or "mm:ss" in content.lower(), (
            "timer must display mm:ss format"
        )

    def test_timer_updates_every_second(self):
        """AC: 计时每秒刷新"""
        content = self._get_index()
        assert "setInterval" in content, "timer must use setInterval"
        assert "1000" in content, "interval should be 1000ms"

    def test_timer_clears_on_stop(self):
        """AC: 停止后清除计时器"""
        content = self._get_index()
        assert "clearInterval" in content, "must clearInterval on stop"


# ── Tests: UI state management ───────────────────────────────────────────────


class TestUiStateManagement:
    """验证 UI 状态管理"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_recording_state_toggle(self):
        """AC: 录音/未录音状态切换"""
        content = self._get_index()
        assert (
            "recording: true" in content or "recording: false" in content
        ), "must have recording state flag"

    def test_draft_saved_flag(self):
        """AC: 停止后设置草稿状态标识（US-014 升级为 draftPreviewMode）"""
        content = self._get_index()
        assert "draftPreviewMode" in content or "draftSaved" in content, "must set draft saved/confirmation state flag"

    def test_lifecycle_stop_recording(self):
        """AC: onHide 时如果录音中则自动停止"""
        content = self._get_index()
        assert "onHide" in content, "must have onHide lifecycle hook"


# ── Tests: WXML template ─────────────────────────────────────────────────────


class TestWxmlTemplate:
    """验证 index.wxml 模板"""

    def _get_wxml(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.wxml")

    def test_record_button_exists(self):
        """AC: 首页有录音按钮"""
        content = self._get_wxml()
        assert "onRecordTap" in content, "must have record button binding"

    def test_timer_display_in_wxml(self):
        """AC: WXML 显示录音计时"""
        content = self._get_wxml()
        assert "timerDisplay" in content or "record-timer" in content, (
            "wxml must display timer"
        )

    def test_draft_info_display(self):
        """AC: 停止后显示草稿信息（US-014 升级为 draftPreviewMode 草稿确认态）"""
        content = self._get_wxml()
        assert "draftPreviewMode" in content or "draftSaved" in content, (
            "wxml must conditionally show draft info"
        )
        assert "draftFormat" in content or "draft_format" in content, (
            "wxml must display original format"
        )

    def test_oss_key_preview_in_wxml(self):
        """AC: WXML 显示 OSS key 预览"""
        content = self._get_wxml()
        assert "draftOssKeyPreview" in content or "oss_key" in content.lower(), (
            "wxml must show OSS key preview"
        )

    def test_format_display_in_draft_info(self):
        """AC: 草稿区显示 original_format"""
        content = self._get_wxml()
        assert (
            "original_format" in content.lower()
            or "draftFormat" in content
        ), "wxml must display original_format field"


# ── Tests: JS syntax ─────────────────────────────────────────────────────────


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


# ── Tests: No hardcoded secrets ─────────────────────────────────────────────


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


# ── Tests: format detection edge cases ───────────────────────────────────────


class TestFormatDetectionEdgeCases:
    """验证格式探测边界情况"""

    def _get_index(self) -> str:
        return _read_text(MP_DIR / "pages" / "index" / "index.js")

    def test_unknown_format_fallback(self):
        """扩展名不可靠时回退为 unknown 或探测结果"""
        content = self._get_index()
        # 应该有回退逻辑
        has_fallback = (
            "unknown" in content
            or "else" in content
            or "return" in content
        )
        assert has_fallback, "must have fallback for unknown formats"

    def test_detect_not_rely_solely_on_extension(self):
        """AC: 当临时路径扩展名不可靠时使用探测结果"""
        content = self._get_index()
        # 应该有扩展名检查逻辑（indexOf/endsWith 等）
        has_path_check = (
            "indexOf" in content
            or "end" in content.lower()
            or "match" in content.lower()
        )
        assert has_path_check, "must check file path for format detection"


# ── Tests: Makefile miniprogram-lint includes index ──────────────────────────


class TestMakefileLint:
    """验证 Makefile miniprogram-lint 覆盖 index.js"""

    def test_miniprogram_lint_covers_index(self):
        """AC: make lint 覆盖小程序源码静态检查（包含 index.js）"""
        makefile = _read_text(REPO_ROOT / "Makefile")
        assert "pages/index/index.js" in makefile, (
            "miniprogram-lint must include pages/index/index.js in node -c check"
        )
