"""微信小程序源码静态检查（US-011，AC#6）。

小程序是 JS，不进 mypy/ruff。`make lint` 在 ruff 之后调用本模块对
`apps/miniprogram/` 做轻量静态校验：

- JSON 配置（project.config.json / app.json / sitemap.json / 各页面 .json）可解析；
- project.config.json 的 appid 等于真实 AppID；
- config.js 含三个合法域名，且未把 issue-cedential 错误“修正”为 issue-credential；
- app.json pages 非空、含首页与上传列表，且每个页面四件套（.js/.json/.wxml/.wxss）齐全；
- 源码中不存在硬编码长期 AK / AppSecret / STS secret / security token。

可测逻辑（check_*）均为纯函数：对已读入的文本/路径做判断，便于 pytest 覆盖；
IO（遍历文件、读文本）收敛在编排层。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# 真实云资源（与 AGENTS.md / runbook 一致）。
APP_ID = "wx3f973c7297728b0c"
FC_ISSUE_CREDENTIAL_URL = "https://issue-cedential-ottfirocds.cn-beijing.fcapp.run"
FC_VERIFY_UPLOAD_URL = "https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run"
OSS_UPLOAD_URL = "https://soniscope-audio.oss-cn-beijing.aliyuncs.com"

# issue-cedential 子域名确实少一个 r；若出现“修正”后的拼写即为错误。
MISCORRECTED_ISSUE_URL = "https://issue-credential-ottfirocds.cn-beijing.fcapp.run"

REQUIRED_DOMAINS = (FC_ISSUE_CREDENTIAL_URL, FC_VERIFY_UPLOAD_URL, OSS_UPLOAD_URL)

# 必须存在的页面（路由 → 目录），每个页面需四件套齐全。
REQUIRED_PAGES = ("pages/index/index", "pages/uploads/uploads")
PAGE_FILE_SUFFIXES = (".js", ".json", ".wxml", ".wxss")

# 受静态扫描的源码文件后缀。
SOURCE_SUFFIXES = (".js", ".json", ".wxml", ".wxss", ".wxs")

# 硬编码密钥启发式：阿里云长期 AK ID 前缀 + “敏感键名 = 非空字符串字面量”。
_AK_ID_RE = re.compile(r"\bLTAI[0-9A-Za-z]{6,}\b")
_HARDCODED_SECRET_RE = re.compile(
    r"(?i)(access[_-]?key[_-]?secret|app[_-]?secret|appsecret|"
    r"security[_-]?token|session[_-]?key)\s*[:=]\s*[\"'][^\"']{6,}[\"']"
)


@dataclass(frozen=True)
class LintIssue:
    """单条静态检查问题。"""

    path: str
    message: str


def _issue(root: Path, file: Path, message: str) -> LintIssue:
    try:
        rel = str(file.relative_to(root))
    except ValueError:
        rel = str(file)
    return LintIssue(path=rel, message=message)


def check_project_config(root: Path, text: str) -> list[LintIssue]:
    """校验 project.config.json：可解析 + appid 正确。"""
    file = root / "project.config.json"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [_issue(root, file, f"JSON 解析失败：{exc.msg}")]
    if not isinstance(data, dict):
        return [_issue(root, file, "顶层应为对象")]
    appid = data.get("appid")
    if appid != APP_ID:
        return [_issue(root, file, f"appid 应为 {APP_ID}，实际为 {appid!r}")]
    return []


def check_app_pages(root: Path, text: str) -> list[LintIssue]:
    """校验 app.json：可解析 + pages 非空 + 含必需页面 + 四件套齐全。"""
    file = root / "app.json"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [_issue(root, file, f"JSON 解析失败：{exc.msg}")]
    if not isinstance(data, dict):
        return [_issue(root, file, "顶层应为对象")]
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        return [_issue(root, file, "pages 必须为非空数组")]
    issues: list[LintIssue] = []
    for required in REQUIRED_PAGES:
        if required not in pages:
            issues.append(_issue(root, file, f"缺少必需页面路由 {required}"))
    for page in pages:
        if not isinstance(page, str):
            issues.append(_issue(root, file, f"页面路由应为字符串：{page!r}"))
            continue
        for suffix in PAGE_FILE_SUFFIXES:
            page_file = root / f"{page}{suffix}"
            if not page_file.is_file():
                issues.append(_issue(root, page_file, f"页面 {page} 缺少 {suffix} 文件"))
    return issues


def check_domains(root: Path, text: str) -> list[LintIssue]:
    """校验 config.js 含三个合法域名，且未把 issue-cedential 修正为 issue-credential。"""
    file = root / "config.js"
    issues: list[LintIssue] = []
    if MISCORRECTED_ISSUE_URL in text:
        issues.append(
            _issue(root, file, "issue-cedential 被错误修正为 issue-credential（多了一个 r）")
        )
    for domain in REQUIRED_DOMAINS:
        if domain not in text:
            issues.append(_issue(root, file, f"缺少合法域名 {domain}"))
    return issues


def scan_hardcoded_secrets(rel_path: str, text: str) -> list[str]:
    """返回某文件中疑似硬编码密钥的描述（纯函数，便于单测）。"""
    findings: list[str] = []
    if _AK_ID_RE.search(text):
        findings.append("疑似硬编码阿里云 AccessKey ID（LTAI...）")
    if _HARDCODED_SECRET_RE.search(text):
        findings.append("疑似硬编码密钥（敏感键被赋字符串字面量）")
    return findings


@dataclass(frozen=True)
class MiniprogramLayout:
    """小程序源码根目录布局。"""

    root: Path

    @property
    def project_config(self) -> Path:
        return self.root / "project.config.json"

    @property
    def app_json(self) -> Path:
        return self.root / "app.json"

    @property
    def config_js(self) -> Path:
        return self.root / "config.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_checks(root: Path) -> list[LintIssue]:
    """对小程序根目录跑全部静态检查，返回所有问题（空表示通过）。"""
    layout = MiniprogramLayout(root=root)
    issues: list[LintIssue] = []

    if not root.is_dir():
        return [LintIssue(path=str(root), message="小程序目录不存在")]

    if layout.project_config.is_file():
        issues.extend(check_project_config(root, _read(layout.project_config)))
    else:
        issues.append(_issue(root, layout.project_config, "缺少 project.config.json"))

    if layout.app_json.is_file():
        issues.extend(check_app_pages(root, _read(layout.app_json)))
    else:
        issues.append(_issue(root, layout.app_json, "缺少 app.json"))

    if layout.config_js.is_file():
        issues.extend(check_domains(root, _read(layout.config_js)))
    else:
        issues.append(_issue(root, layout.config_js, "缺少 config.js"))

    # 全量 JSON 可解析 + 硬编码密钥扫描。
    for file in sorted(root.rglob("*")):
        if not file.is_file() or file.suffix not in SOURCE_SUFFIXES:
            continue
        text = _read(file)
        if file.suffix == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                issues.append(_issue(root, file, f"JSON 解析失败：{exc.msg}"))
        # 单测夹具（test/）会刻意使用假密钥字面量验证脱敏 / 上传链路，豁免硬编码密钥扫描；
        # 生产源码（utils/ pages/ app.js 等）仍严格扫描。
        if "test" not in file.relative_to(root).parts:
            for finding in scan_hardcoded_secrets(str(file), text):
                issues.append(_issue(root, file, finding))

    return issues


def format_report(root: Path, issues: list[LintIssue]) -> list[str]:
    """渲染人类可读报告。"""
    lines = [f"== 小程序静态检查：{root} =="]
    if not issues:
        lines.append("✅ miniprogram lint passed")
        return lines
    for issue in issues:
        lines.append(f"  ✗ {issue.path}: {issue.message}")
    lines.append(f"❌ miniprogram lint failed（{len(issues)} 个问题）")
    return lines


def default_miniprogram_root() -> Path:
    """apps/worker/src/soniscope_worker/ → 仓库根 → apps/miniprogram。"""
    return Path(__file__).resolve().parents[4] / "apps" / "miniprogram"


def run_lint_miniprogram(root: Path | None = None) -> tuple[list[str], int]:
    """编排入口：返回 (报告行, 退出码)。"""
    target = root or default_miniprogram_root()
    issues = run_checks(target)
    lines = format_report(target, issues)
    return lines, (0 if not issues else 1)
