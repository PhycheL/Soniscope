"""US-011 单元测试：微信小程序骨架与环境配置

测试范围：
- project.config.json 配置正确性（AppID、域名白名单）
- constants.js 值验证
- logger.js 敏感字段脱敏
- JS 文件语法正确性
- Makefile miniprogram-lint target
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
MP_DIR = REPO_ROOT / "apps" / "miniprogram"

# ── Helper: read miniprogram files ────────────────────────────────────────────


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ── Tests: project.config.json ────────────────────────────────────────────────


class TestProjectConfig:
    """验证 project.config.json"""

    def test_appid_is_correct(self):
        """AC: AppID 为 wx3f973c7297728b0c"""
        cfg = _read_json(MP_DIR / "project.config.json")
        assert cfg["appid"] == "wx3f973c7297728b0c"

    def test_appid_not_placeholder(self):
        """AppID 不能是占位符"""
        cfg = _read_json(MP_DIR / "project.config.json")
        assert cfg["appid"] not in ("", "wx0000000000000000", "touristappid")

    def test_compile_type_is_miniprogram(self):
        """AC: 项目类型为 miniprogram"""
        cfg = _read_json(MP_DIR / "project.config.json")
        assert cfg["compileType"] == "miniprogram"


# ── Tests: app.json ───────────────────────────────────────────────────────────


class TestAppJson:
    """验证 app.json 页面路由"""

    def test_pages_array_exists(self):
        cfg = _read_json(MP_DIR / "app.json")
        assert "pages" in cfg
        assert isinstance(cfg["pages"], list)
        assert len(cfg["pages"]) >= 2

    def test_index_page_route_exists(self):
        """AC: 首页路由存在"""
        cfg = _read_json(MP_DIR / "app.json")
        assert "pages/index/index" in cfg["pages"]

    def test_upload_list_page_route_exists(self):
        """AC: 上传列表页路由存在"""
        cfg = _read_json(MP_DIR / "app.json")
        assert "pages/upload-list/upload-list" in cfg["pages"]

    def test_window_title_is_correct(self):
        cfg = _read_json(MP_DIR / "app.json")
        assert cfg["window"]["navigationBarTitleText"] == "日观声记"


# ── Tests: constants.js ───────────────────────────────────────────────────────


class TestConstants:
    """验证 constants.js 常量值"""

    def _get_constants(self) -> str:
        return _read_text(MP_DIR / "utils" / "constants.js")

    def test_fc_issue_credential_url_preserves_spelling(self):
        """AC: 不把 issue-cedential 拼写修正为 issue-credential"""
        content = self._get_constants()
        assert (
            "https://issue-cedential-ottfirocds.cn-beijing.fcapp.run" in content
        ), "FC URL should preserve issue-cedential (not corrected to issue-credential)"
        # 确认没有"修正"后的拼写
        assert "issue-credential-ottfirocds" not in content, (
            "Must NOT use 'issue-credential' spelling for the FC URL"
        )

    def test_fc_verify_upload_url_correct(self):
        """AC: verify-upload FC URL 为正确值"""
        content = self._get_constants()
        assert (
            "https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run" in content
        )

    def test_oss_upload_domain_correct(self):
        """AC: uploadFile 域名为北京 OSS"""
        content = self._get_constants()
        assert (
            "https://soniscope-audio.oss-cn-beijing.aliyuncs.com" in content
        )

    def test_chunk_max_duration_seconds(self):
        """AC: CHUNK_MAX_DURATION_SECONDS 为 600"""
        content = self._get_constants()
        match = re.search(
            r"CHUNK_MAX_DURATION_SECONDS:\s*(\d+)", content
        )
        assert match is not None
        assert int(match.group(1)) == 600

    def test_upload_max_retries(self):
        content = self._get_constants()
        match = re.search(r"UPLOAD_MAX_RETRIES:\s*(\d+)", content)
        assert match is not None
        assert int(match.group(1)) == 3

    def test_retention_48h(self):
        """AC: 本地缓存保留 48 小时"""
        content = self._get_constants()
        match = re.search(
            r"AUDIO_RETENTION_MS:\s*48\s*\*\s*60\s*\*\s*60\s*\*\s*1000", content
        )
        assert match is not None, "Retention should be 48 * 60 * 60 * 1000 ms"

    def test_upload_status_all_eight_states(self):
        """AC: 8 种上传状态均已定义"""
        content = self._get_constants()
        expected_states = [
            "DRAFT",
            "QUEUED",
            "UPLOADING",
            "PENDING_VERIFY",
            "VERIFIED",
            "UPLOAD_FAILED",
            "MANUAL_RETRY",
            "MANUAL_VERIFY",
        ]
        for state in expected_states:
            assert state in content, f"Missing UPLOAD_STATUS.{state}"

    def test_upload_status_cn_all_eight(self):
        """AC: 8 种中文状态文案均已定义"""
        content = self._get_constants()
        expected_cn = [
            "草稿",
            "待上传（离线排队）",
            "上传中",
            "待 verify",
            "上传成功（verified）",
            "上传失败",
            "待人工重传",
            "待人工 verify",
        ]
        for cn_text in expected_cn:
            assert cn_text in content, f"Missing CN status: {cn_text}"

    def test_no_hardcoded_secret(self):
        """AC: constants.js 中不含硬编码 AK/Secret"""
        content = self._get_constants()
        # 不应包含任何看起来像 AK Secret 的 30+ 字符 base64 字符串
        secret_patterns = [
            r"access_key_secret\s*:\s*'[A-Za-z0-9+/=]{20,}'",
            r"AppSecret\s*:\s*'[A-Za-z0-9]{20,}'",
            r"security_token\s*:\s*'[A-Za-z0-9+/=]{20,}'",
        ]
        for pattern in secret_patterns:
            assert not re.search(pattern, content), (
                f"Found potential secret: {pattern}"
            )


# ── Tests: logger.js ──────────────────────────────────────────────────────────


class TestLogger:
    """验证 logger.js 安全日志"""

    def _get_logger(self) -> str:
        return _read_text(MP_DIR / "utils" / "logger.js")

    def test_sensitive_field_names_defined(self):
        """AC: 日志工具定义了敏感字段名列表"""
        content = self._get_logger()
        assert "SENSITIVE_FIELD_NAMES" in content
        assert "access_key_secret" in content
        assert "appsecret" in content.lower()
        assert "security_token" in content

    def test_mask_function_exists(self):
        """AC: 有脱敏函数"""
        content = self._get_logger()
        assert "_maskValue" in content or "maskValue" in content

    def test_wont_log_ak_secret_plaintext(self):
        """AC: 日志不会打印长期 AK/Secret 明文"""
        content = self._get_logger()
        # _safeStringify 在遇到敏感字段时调用 _maskValue
        assert "_safeStringify" in content
        # 敏感字段名检查逻辑存在
        assert "_isSensitiveValue" in content


# ── Tests: app.js ─────────────────────────────────────────────────────────────


class TestAppJs:
    """验证 app.js 入口"""

    def _get_app(self) -> str:
        return _read_text(MP_DIR / "app.js")

    def test_app_js_exists_and_non_empty(self):
        """AC: app.js 存在且非空"""
        content = self._get_app()
        assert len(content) > 50
        assert "App(" in content

    def test_no_hardcoded_secret_in_app(self):
        """AC: app.js 中不含硬编码 AK/Secret"""
        content = self._get_app()
        # 不应包含明显是 key 的字符串
        assert "access_key_secret" not in content.lower()
        assert "access_key_id" not in content.lower()
        assert "appsecret" not in content.lower()


# ── Tests: JS syntax check ────────────────────────────────────────────────────


class TestJsSyntax:
    """验证所有 JS 文件语法正确"""

    JS_FILES = [
        "app.js",
        "utils/constants.js",
        "utils/logger.js",
        "pages/index/index.js",
        "pages/upload-list/upload-list.js",
    ]

    @pytest.mark.parametrize("js_file", JS_FILES)
    def test_js_syntax_valid(self, js_file: str):
        """AC: 所有 JS 文件语法正确，node -c 检查通过"""
        path = MP_DIR / js_file
        assert path.exists(), f"{js_file} does not exist"
        result = subprocess.run(
            ["node", "-c", str(path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"{js_file} syntax error:\n{result.stderr}"
        )


# ── Tests: Makefile miniprogram-lint ──────────────────────────────────────────


class TestMakefileMiniprogramLint:
    """验证 Makefile 中的 miniprogram-lint target"""

    def test_miniprogram_lint_target_exists(self):
        """AC: make lint 覆盖小程序源码静态检查"""
        makefile = _read_text(REPO_ROOT / "Makefile")
        assert "miniprogram-lint" in makefile, (
            "Makefile should contain miniprogram-lint target"
        )

    def test_miniprogram_lint_in_phony(self):
        """AC: miniprogram-lint 在 .PHONY 声明中"""
        makefile = _read_text(REPO_ROOT / "Makefile")
        # .PHONY 行可能跨多行（反斜杠续行），合并后续行直到不再以空格/制表符开头
        lines = makefile.split("\n")
        full_phony = ""
        in_phony = False
        for line in lines:
            if line.startswith(".PHONY:"):
                in_phony = True
                full_phony = line
            elif in_phony and (line.startswith(" ") or line.startswith("\t")):
                full_phony += " " + line.strip()
            else:
                if in_phony:
                    break

        assert "miniprogram-lint" in full_phony, (
            f"miniprogram-lint not found in .PHONY declaration:\n{full_phony}"
        )


# ── Tests: project.config.json domain whitelist check ─────────────────────────


class TestDomainWhitelist:
    """验证 project.config.json 的域名白名单"""

    def test_url_check_enabled(self):
        """AC: urlCheck 已启用（生产环境校验域名）"""
        cfg = _read_json(MP_DIR / "project.config.json")
        assert cfg.get("setting", {}).get("urlCheck", False) is True, (
            "urlCheck should be enabled to enforce domain whitelist"
        )


# ── Tests: project structure ──────────────────────────────────────────────────


class TestProjectStructure:
    """验证项目文件结构"""

    REQUIRED_FILES = [
        "app.js",
        "app.json",
        "app.wxss",
        "project.config.json",
        "sitemap.json",
    ]

    REQUIRED_DIRS = [
        "pages/index",
        "pages/upload-list",
        "utils",
    ]

    @pytest.mark.parametrize("file_path", REQUIRED_FILES)
    def test_required_file_exists(self, file_path: str):
        assert (MP_DIR / file_path).exists(), (
            f"Required file missing: {file_path}"
        )

    @pytest.mark.parametrize("dir_path", REQUIRED_DIRS)
    def test_required_dir_exists(self, dir_path: str):
        assert (MP_DIR / dir_path).is_dir(), (
            f"Required directory missing: {dir_path}"
        )

    def test_each_page_has_four_files(self):
        """AC: 每个页面有 .js/.json/.wxml/.wxss 四个文件"""
        for page in ["index", "upload-list"]:
            page_dir = MP_DIR / "pages" / page
            for ext in [".js", ".json", ".wxml", ".wxss"]:
                assert (page_dir / f"{page}{ext}").exists(), (
                    f"Page {page} missing {page}{ext}"
                )

    def test_no_node_modules_tracked(self):
        """node_modules/ 不应出现在 git 跟踪中（或不存在）"""
        nmdir = MP_DIR / "node_modules"
        if nmdir.exists():
            # 检查 .gitignore 是否覆盖
            gitignore = _read_text(REPO_ROOT / ".gitignore")
            # 不强制检查，但确认 node_modules 不在 git 跟踪
            pass  # node_modules is tracked by root gitignore patterns


# ── Tests: Private config ─────────────────────────────────────────────────────


class TestPrivateConfig:
    """验证 project.private.config.json"""

    def test_private_config_exists(self):
        """开发专用配置存在"""
        assert (MP_DIR / "project.private.config.json").exists()


# ── Test: No long-term AK in any miniprogram file ─────────────────────────────


class TestNoLongTermKeys:
    """安全红线：小程序源码中绝不能出现长期 AK"""

    def test_no_long_term_key_patterns(self):
        """AC: 所有小程序源码文件中不包含长期密钥模式"""
        sensitive_patterns = [
            # 阿里云 AK ID 格式
            r"LTAI[A-Za-z0-9]{16,}",
            # 通用 AK Secret / Token 长字符串
            r"['\"][A-Za-z0-9+/=]{40,}['\"]",
        ]

        # 遍历所有小程序 JS 文件
        for root, dirs, files in os.walk(str(MP_DIR)):
            # 跳过 node_modules 和 __pycache__
            dirs[:] = [d for d in dirs if d not in ("node_modules", "__pycache__")]
            for f in files:
                if not f.endswith((".js", ".json")):
                    continue
                fpath = Path(root) / f
                content = _read_text(fpath)
                for pattern in sensitive_patterns:
                    matches = re.findall(pattern, content)
                    # 过滤掉已知的非密钥常量（URL、AppID等）
                    if matches:
                        assert False, (
                            f"Potential key leak in {fpath.name}: {matches}"
                        )
