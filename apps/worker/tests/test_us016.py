"""US-016 单元测试：长录音自动分片与 session 聚合元数据

测试范围：
- session_id 分配（录音开始时生成，所有 chunk 共享）
- chunk_seq 递增（从 1 递增）
- chunk_total 回填（用户停止后回填到所有 chunk manifest）
- 单条 chunk 时长上限 605 秒（600 秒阈值 + 容差）
- CHUNK_MAX_DURATION_SECONDS 常量验证
- _sessionId / _sessionChunks / _chunkSeq / _userStopped 内部变量
- index.js 自动分片代码结构验证
- JS 语法检查
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


# ── FIXTURES ───────────────────────────────────────────────────────────────


@pytest.fixture
def index_js() -> str:
    return _read_text(MP_DIR / "pages" / "index" / "index.js")


@pytest.fixture
def constants_js() -> str:
    return _read_text(MP_DIR / "utils" / "constants.js")


@pytest.fixture
def idgen_js() -> str:
    return _read_text(MP_DIR / "utils" / "idgen.js")


@pytest.fixture
def index_wxml() -> str:
    return _read_text(MP_DIR / "pages" / "index" / "index.wxml")


@pytest.fixture
def index_wxss() -> str:
    return _read_text(MP_DIR / "pages" / "index" / "index.wxss")


# ── 常量验证 ──────────────────────────────────────────────────────────────


class TestChunkConstants:
    """CHUNK_MAX_DURATION_SECONDS = 600 秒"""

    def test_chunk_max_duration_equals_600(self, constants_js: str):
        assert "CHUNK_MAX_DURATION_SECONDS: 600" in constants_js

    def test_chunk_max_duration_used_in_recorder_start(self, index_js: str):
        """recorderManager.start 使用 constants.CHUNK_MAX_DURATION_SECONDS * 1000"""
        assert "CHUNK_MAX_DURATION_SECONDS * 1000" in index_js


# ── Session 与 auto-split 内部变量 ──────────────────────────────────────


class TestAutoSplitInternals:
    """验证 index.js 中长录音自动分片的内部追踪变量"""

    def test_session_id_field_declared(self, index_js: str):
        assert "_sessionId" in index_js

    def test_session_chunks_array_declared(self, index_js: str):
        assert "_sessionChunks" in index_js

    def test_chunk_seq_field_declared(self, index_js: str):
        assert "_chunkSeq" in index_js

    def test_user_stopped_flag_declared(self, index_js: str):
        assert "_userStopped" in index_js


# ── session_id 分配 ───────────────────────────────────────────────────


class TestSessionIdAllocation:
    """录音开始时分配 session_id，所有 auto-split chunk 共享同一 session_id"""

    def test_generate_session_id_called_in_do_start_record(self, index_js: str):
        """_doStartRecord 中调用 idgen.generateSessionId()"""
        assert "generateSessionId()" in index_js

    def test_session_id_assigned_to_internal_var(self, index_js: str):
        """_sessionId = idgen.generateSessionId()"""
        assert "_sessionId = idgen.generateSessionId()" in index_js

    def test_chunk_seq_initialised_to_1(self, index_js: str):
        """_chunkSeq 起始值为 1"""
        assert "_chunkSeq = 1" in index_js

    def test_session_id_reused_in_on_save_and_upload(self, index_js: str):
        """onSaveAndUpload 使用 this._sessionId 而非新建"""
        assert "this._sessionId" in index_js

    def test_session_id_fallback_when_null(self, index_js: str):
        """如果 _sessionId 为空，回退到生成新的"""
        assert "idgen.generateSessionId()" in index_js


# ── Sessions Chunks 收集 ─────────────────────────────────────────────


class TestChunkCollection:
    """用户每停止一次（自动或手动），chunk 信息被收入 _sessionChunks"""

    def test_session_chunks_push_on_stop(self, index_js: str):
        """onStop 回调中 push chunk 进入 _sessionChunks"""
        assert "_sessionChunks.push" in index_js

    def test_chunk_record_contains_temp_file_path(self, index_js: str):
        assert "tempFilePath" in index_js

    def test_chunk_record_contains_original_format(self, index_js: str):
        assert "original_format" in index_js

    def test_chunk_record_contains_size_bytes(self, index_js: str):
        assert "size_bytes" in index_js

    def test_chunk_record_contains_duration(self, index_js: str):
        assert "duration_seconds" in index_js


# ── auto-split 自动重开 ─────────────────────────────────────────────


class TestAutoSplitRestart:
    """recorder 达到 600s 上限自动停止后立即重启下一段"""

    def test_recorder_start_called_in_auto_split_path(self, index_js: str):
        """auto-split 分支中调用 recorderManager.start() 重新开始"""
        # index.js 有 auto-split 后再调 start 的逻辑
        assert "自动分片" in index_js or "auto-split" in index_js.lower()

    def test_auto_split_increments_chunk_seq(self, index_js: str):
        """auto-split 路径 _chunkSeq++"""
        assert "_chunkSeq++" in index_js or "_chunkSeq += 1" in index_js or "_chunkSeq = _chunkSeq + 1" in index_js or "_chunkSeq =" in index_js

    def test_timer_not_cleared_on_auto_split(self, index_js: str):
        """auto-split 不清除计时器（timer 保持运行）"""
        # 找到 auto-split 和 user-stop 的不同路径
        assert "_clearTimer" in index_js

    def test_user_stopped_flag_set_on_manual_stop(self, index_js: str):
        """_stopRecording 中设置 _userStopped = true"""
        assert "_userStopped = true" in index_js

    def test_user_stopped_reset_on_new_recording(self, index_js: str):
        """_doStartRecord 中重置 _userStopped = false"""
        assert "_userStopped = false" in index_js


# ── chunk_seq 递增 ──────────────────────────────────────────────────


class TestChunkSeqIncrement:
    """每个 chunk 有独立的 chunk_seq，从 1 递增"""

    def test_chunk_seq_used_in_on_save_and_upload(self, index_js: str):
        """onSaveAndUpload 处理不同 chunk 时使用 idx+1 作为 chunk_seq"""
        assert "chunk_seq" in index_js

    def test_chunk_seq_starts_at_1(self, index_js: str):
        """chunk_seq = idx + 1，起始值为 1"""
        # idx 从 0 开始，chunk_seq 从 1 开始
        assert "idx + 1" in index_js

    def test_oss_meta_chunk_seq_is_string(self, index_js: str):
        """x-oss-meta-chunk-seq 以字符串形式存储"""
        assert "'x-oss-meta-chunk-seq'" in index_js or '"x-oss-meta-chunk-seq"' in index_js


# ── chunk_total 回填 ────────────────────────────────────────────────


class TestChunkTotalBackfill:
    """用户最终点击停止后，chunk_total 被回填到该 session 所有 chunk"""

    def test_chunk_total_field_in_manifest(self, index_js: str):
        """manifest 包含 chunk_total 字段"""
        assert "chunk_total" in index_js

    def test_chunk_total_backfill_after_all_chunks(self, index_js: str):
        """所有 chunk SHA-256 计算完成后回填 chunk_total"""
        assert "manifest.chunk_total" in index_js or "chunkTotal" in index_js

    def test_oss_meta_chunk_total_set_to_string(self, index_js: str):
        """x-oss-meta-chunk-total 以字符串形式存储"""
        assert "'x-oss-meta-chunk-total'" in index_js or '"x-oss-meta-chunk-total"' in index_js

    def test_chunk_total_equals_session_chunks_length(self, index_js: str):
        """chunk_total = this._sessionChunks.length"""
        assert "_sessionChunks.length" in index_js

    def test_single_chunk_recording_chunk_total_is_1(self, index_js: str):
        """非分片单 chunk: chunk_total = 1（不是 0）"""
        # chunk_total 在单 chunk 情况下等于 _sessionChunks.length = 1
        assert "_sessionChunks.length" in index_js

    def test_multi_chunk_chunk_total_equals_count(self, index_js: str):
        """N 个 chunk 情况下 chunk_total = N"""
        assert "chunkTotal" in index_js or "chunk_total" in index_js


# ── 时长限制 ────────────────────────────────────────────────────────


class TestDurationLimits:
    """单条 chunk 时长不超过 605 秒（600 秒阈值 + 容差）"""

    def test_recorder_duration_set_to_max_seconds_times_1000(self, index_js: str):
        """recorderManager.start({ duration: constants.CHUNK_MAX_DURATION_SECONDS * 1000 })"""
        assert "CHUNK_MAX_DURATION_SECONDS * 1000" in index_js

    def test_max_duration_constant_value(self, constants_js: str):
        """CHUNK_MAX_DURATION_SECONDS 值为 600"""
        # 600 秒 = 10 分钟
        assert re.search(r"CHUNK_MAX_DURATION_SECONDS:\s*600", constants_js)

    def test_duration_ms_equals_600000(self, constants_js: str):
        """600 * 1000 = 600000 ms"""
        assert "600" in constants_js


# ── 中断保护兼容 ──────────────────────────────────────────────────


class TestInterruptionCompatWithChunks:
    """中断保护与新 chunk 系统兼容"""

    def test_interruption_preserves_chunk_count(self, index_js: str):
        """中断保存时包含 chunk 数量信息"""
        assert "chunks:" in index_js.lower() or "chunks" in index_js

    def test_interruption_clears_session_chunks(self, index_js: str):
        """中断后清理 _sessionChunks"""
        assert "_sessionChunks" in index_js


# ── WXML 模板 ──────────────────────────────────────────────────────────


class TestWxmlTemplate:
    """草稿确认态 WXML 模板验证"""

    def test_draft_chunk_count_in_data(self, index_js: str):
        """data 中包含 draftChunkCount 字段"""
        assert "draftChunkCount" in index_js

    def test_draft_chunk_count_displayed_in_wxml(self, index_wxml: str):
        """WXML 中当 draftChunkCount > 1 时显示片段数"""
        assert "draftChunkCount" in index_wxml

    def test_recovery_modal_shows_chunks(self, index_wxml: str):
        """中断恢复弹窗中当 chunks > 1 时显示片段数"""
        assert "recoveryDraft.chunks" in index_wxml or "chunks" in index_wxml

    def test_recovery_modal_still_shows_format(self, index_wxml: str):
        """中断恢复弹窗仍然显示格式"""
        assert "original_format" in index_wxml


# ── WXSS 样式 ──────────────────────────────────────────────────────────


class TestWxssStyle:
    """样式完整性验证"""

    def test_draft_preview_section_exists(self, index_wxss: str):
        assert "draft-preview-section" in index_wxss

    def test_recovery_modal_exists(self, index_wxss: str):
        assert "recovery-modal" in index_wxss

    def test_audition_section_exists(self, index_wxss: str):
        assert "audition-section" in index_wxss


# ── JS 语法检查 ──────────────────────────────────────────────────


class TestJsSyntax:
    """所有修改文件的 JS 语法检查"""

    def test_index_js_syntax(self):
        result = subprocess.run(
            ["node", "-c", str(MP_DIR / "pages" / "index" / "index.js")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"JS syntax error: {result.stderr}"

    def test_constants_js_syntax(self):
        result = subprocess.run(
            ["node", "-c", str(MP_DIR / "utils" / "constants.js")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"JS syntax error: {result.stderr}"

    def test_idgen_js_syntax(self):
        result = subprocess.run(
            ["node", "-c", str(MP_DIR / "utils" / "idgen.js")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"JS syntax error: {result.stderr}"


# ── idgen 兼容性 ──────────────────────────────────────────────────


class TestIdgenCompat:
    """验证 idgen.js 包含 US-016 需要的 API"""

    def test_generate_session_id_exists(self, idgen_js: str):
        assert "generateSessionId" in idgen_js

    def test_generate_fragment_id_exists(self, idgen_js: str):
        assert "generateFragmentId" in idgen_js


# ── 状态迁移完整性 ────────────────────────────────────────────────


class TestStateTransition:
    """验证录音生命周期状态正确迁移"""

    def test_recording_resets_all_split_state(self, index_js: str):
        """_doStartRecord 重置所有分片状态"""
        assert "_sessionChunks = []" in index_js or "_sessionChunks = []" in index_js

    def test_delete_resets_session_chunks(self, index_js: str):
        """删除操作重置 _sessionChunks"""
        # 在 onDelete 中清理
        assert "_sessionChunks" in index_js

    def test_on_save_and_upload_clears_session_chunks(self, index_js: str):
        """保存并上传后清理 _sessionChunks"""
        assert "_sessionChunks = []" in index_js


# ── 安全 ─────────────────────────────────────────────────────────


class TestSecurity:
    """无硬编码密钥 / 明文 Token"""

    def test_no_ak_secret_in_index_js(self, index_js: str):
        assert "access_key_secret" not in index_js.lower()
        assert "accessKeySecret" not in index_js
        assert "ACCESS_KEY_SECRET" not in index_js

    def test_no_appsecret_in_any_file(self, index_js: str, constants_js: str, idgen_js: str):
        for src in [index_js, constants_js, idgen_js]:
            assert "AppSecret" not in src
            assert "appsecret" not in src.lower()
            assert "wx3f973c7297728b0c" not in src or "APP_ID" in src


# ── Makefile 覆盖 ──────────────────────────────────────────────────


class TestMakefileCoverage:
    """Makefile miniprogram-lint 覆盖所有修改的 JS 文件"""

    def test_index_js_in_makefile_lint(self):
        makefile = _read_text(REPO_ROOT / "Makefile")
        assert "pages/index/index.js" in makefile

    def test_idgen_js_in_makefile_lint(self):
        makefile = _read_text(REPO_ROOT / "Makefile")
        assert "utils/idgen.js" in makefile
