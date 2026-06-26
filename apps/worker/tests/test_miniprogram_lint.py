"""US-011：小程序静态检查（miniprogram_lint）单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

from soniscope_worker.miniprogram_lint import (
    APP_ID,
    FC_ISSUE_CREDENTIAL_URL,
    FC_VERIFY_UPLOAD_URL,
    MISCORRECTED_ISSUE_URL,
    OSS_UPLOAD_URL,
    check_app_pages,
    check_domains,
    check_project_config,
    default_miniprogram_root,
    format_report,
    run_checks,
    run_lint_miniprogram,
    scan_hardcoded_secrets,
)

CONFIG_JS = (
    f"const a = '{FC_ISSUE_CREDENTIAL_URL}'\n"
    f"const b = '{FC_VERIFY_UPLOAD_URL}'\n"
    f"const c = '{OSS_UPLOAD_URL}'\n"
)


def _make_miniprogram(root: Path) -> None:
    """构造一个最小且合规的小程序目录。"""
    (root / "project.config.json").write_text(
        json.dumps({"appid": APP_ID}), encoding="utf-8"
    )
    (root / "app.json").write_text(
        json.dumps({"pages": ["pages/index/index", "pages/uploads/uploads"]}),
        encoding="utf-8",
    )
    (root / "config.js").write_text(CONFIG_JS, encoding="utf-8")
    for page in ("pages/index/index", "pages/uploads/uploads"):
        page_dir = root / page
        page_dir.parent.mkdir(parents=True, exist_ok=True)
        (root / f"{page}.js").write_text("Page({})\n", encoding="utf-8")
        (root / f"{page}.json").write_text("{}\n", encoding="utf-8")
        (root / f"{page}.wxml").write_text("<view></view>\n", encoding="utf-8")
        (root / f"{page}.wxss").write_text(".x{}\n", encoding="utf-8")


# --- check_project_config ---


def test_project_config_ok() -> None:
    assert check_project_config(Path("/r"), json.dumps({"appid": APP_ID})) == []


def test_project_config_wrong_appid() -> None:
    issues = check_project_config(Path("/r"), json.dumps({"appid": "wrong"}))
    assert len(issues) == 1
    assert APP_ID in issues[0].message


def test_project_config_invalid_json() -> None:
    issues = check_project_config(Path("/r"), "{not json")
    assert len(issues) == 1
    assert "JSON" in issues[0].message


# --- check_app_pages ---


def test_app_pages_ok(tmp_path: Path) -> None:
    _make_miniprogram(tmp_path)
    text = (tmp_path / "app.json").read_text(encoding="utf-8")
    assert check_app_pages(tmp_path, text) == []


def test_app_pages_empty() -> None:
    issues = check_app_pages(Path("/r"), json.dumps({"pages": []}))
    assert any("非空" in i.message for i in issues)


def test_app_pages_missing_required(tmp_path: Path) -> None:
    _make_miniprogram(tmp_path)
    text = json.dumps({"pages": ["pages/index/index"]})
    issues = check_app_pages(tmp_path, text)
    assert any("pages/uploads/uploads" in i.message for i in issues)


def test_app_pages_missing_page_file(tmp_path: Path) -> None:
    _make_miniprogram(tmp_path)
    (tmp_path / "pages/index/index.wxss").unlink()
    text = (tmp_path / "app.json").read_text(encoding="utf-8")
    issues = check_app_pages(tmp_path, text)
    assert any(".wxss" in i.message for i in issues)


# --- check_domains ---


def test_domains_ok() -> None:
    assert check_domains(Path("/r"), CONFIG_JS) == []


def test_domains_missing() -> None:
    issues = check_domains(Path("/r"), f"const a = '{FC_ISSUE_CREDENTIAL_URL}'\n")
    msgs = " ".join(i.message for i in issues)
    assert FC_VERIFY_UPLOAD_URL in msgs
    assert OSS_UPLOAD_URL in msgs


def test_domains_miscorrected_spelling() -> None:
    text = CONFIG_JS + f"const wrong = '{MISCORRECTED_ISSUE_URL}'\n"
    issues = check_domains(Path("/r"), text)
    assert any("修正" in i.message for i in issues)


# --- scan_hardcoded_secrets ---


def test_scan_clean() -> None:
    assert scan_hardcoded_secrets("config.js", CONFIG_JS) == []


def test_scan_ak_id() -> None:
    findings = scan_hardcoded_secrets("x.js", "const ak = 'LTAI5tAbCdEf123456'\n")
    assert findings


def test_scan_hardcoded_secret_literal() -> None:
    findings = scan_hardcoded_secrets("x.js", "access_key_secret: 'abcdef123456'\n")
    assert findings


def test_scan_security_token_literal() -> None:
    findings = scan_hardcoded_secrets("x.js", 'securityToken = "ZZZdummytoken"\n')
    assert findings


def test_logger_regex_not_flagged() -> None:
    """logger.js 的敏感键正则定义不应被误判为硬编码密钥。"""
    snippet = (
        "const SENSITIVE_KEY_RE = "
        "/(access[_-]?key[_-]?secret|app[_-]?secret|security[_-]?token)/i\n"
    )
    assert scan_hardcoded_secrets("logger.js", snippet) == []


# --- run_checks (集成 tmp 树) ---


def test_run_checks_pass(tmp_path: Path) -> None:
    _make_miniprogram(tmp_path)
    assert run_checks(tmp_path) == []


def test_run_checks_missing_dir(tmp_path: Path) -> None:
    issues = run_checks(tmp_path / "nope")
    assert len(issues) == 1
    assert "不存在" in issues[0].message


def test_run_checks_invalid_json_file(tmp_path: Path) -> None:
    _make_miniprogram(tmp_path)
    (tmp_path / "sitemap.json").write_text("{bad", encoding="utf-8")
    issues = run_checks(tmp_path)
    assert any("sitemap.json" in i.path for i in issues)


def test_run_checks_detects_secret(tmp_path: Path) -> None:
    _make_miniprogram(tmp_path)
    (tmp_path / "leak.js").write_text("const x = 'LTAI5tLEAKED000000'\n", encoding="utf-8")
    issues = run_checks(tmp_path)
    assert any("leak.js" in i.path for i in issues)


# --- format_report / run_lint_miniprogram ---


def test_format_report_pass(tmp_path: Path) -> None:
    lines = format_report(tmp_path, [])
    assert any("passed" in line for line in lines)


def test_format_report_fail(tmp_path: Path) -> None:
    from soniscope_worker.miniprogram_lint import LintIssue

    lines = format_report(tmp_path, [LintIssue(path="app.json", message="boom")])
    assert any("failed" in line for line in lines)
    assert any("boom" in line for line in lines)


def test_run_lint_on_tmp(tmp_path: Path) -> None:
    _make_miniprogram(tmp_path)
    lines, code = run_lint_miniprogram(tmp_path)
    assert code == 0
    assert any("passed" in line for line in lines)


def test_run_lint_real_miniprogram() -> None:
    """真实 apps/miniprogram 骨架应通过静态检查。"""
    root = default_miniprogram_root()
    assert root.is_dir()
    lines, code = run_lint_miniprogram(root)
    assert code == 0, "\n".join(lines)
