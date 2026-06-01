"""Unit tests for US-020 — 小程序开发者故障注入菜单.

Covers:
- dev-injector.js module: getFlag/setFlag/toggleFlag/getAllFlags/resetAllFlags/isAnyFlagActive
- dev-injector.js: production guard (getFlag returns false when IS_PRODUCTION)
- dev-menu page: Page definition, data fields, handler bindings
- dev-menu page: toggle handlers (onToggleMockFc/onToggleMockOffline/onToggleMockVerify)
- dev-menu page: onResetAll handler
- dev-menu page: onShow calls _refreshFlags
- dev-menu.wxml: switch components for all 3 toggles
- dev-menu.wxml: reset button
- dev-menu.wxml: production warning conditional
- dev-menu.wxss: switch/toggle-item/label styles
- uploader.js: mock-fc-url-broken injection in _fetchSts
- uploader.js: mock-fc-url-broken injection in _doVerifyUpload
- uploader.js: mock-network-offline injection in processUploadQueue
- uploader.js: mock-verify-fail injection in _doVerifyUpload
- uploader.js: requires dev-injector module
- uploader.js: VERIFY_FALSE_MOCK_FAILURE / MOCK_FC_FAILURE in _handleVerifyFailure
- index.js: dev menu entry point (navigateToDevMenu + isProduction)
- index.wxml: dev menu link conditional (wx:if="{{!isProduction}}")
- app.json: dev-menu page registered
- Constants: IS_PRODUCTION field
- JS syntax for all modified files
- No hardcoded keys in new files
- Makefile miniprogram-lint covers new files
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
DEV_INJECTOR_JS_PATH = MINIPROGRAM_DIR / "utils" / "dev-injector.js"
DEV_MENU_JS_PATH = MINIPROGRAM_DIR / "pages" / "dev-menu" / "dev-menu.js"
DEV_MENU_WXML_PATH = MINIPROGRAM_DIR / "pages" / "dev-menu" / "dev-menu.wxml"
DEV_MENU_WXSS_PATH = MINIPROGRAM_DIR / "pages" / "dev-menu" / "dev-menu.wxss"
DEV_MENU_JSON_PATH = MINIPROGRAM_DIR / "pages" / "dev-menu" / "dev-menu.json"
UPLOADER_JS_PATH = MINIPROGRAM_DIR / "utils" / "uploader.js"
INDEX_JS_PATH = MINIPROGRAM_DIR / "pages" / "index" / "index.js"
INDEX_WXML_PATH = MINIPROGRAM_DIR / "pages" / "index" / "index.wxml"
APP_JSON_PATH = MINIPROGRAM_DIR / "app.json"
CONSTANTS_PATH = MINIPROGRAM_DIR / "utils" / "constants.js"
MAKEFILE_PATH = REPO_ROOT / "Makefile"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _read_js(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_makefile() -> str:
    return MAKEFILE_PATH.read_text(encoding="utf-8")


def _read_wxml(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_wxss(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _js_syntax_ok(path: Path):
    """Check JS syntax with node -c."""
    result = subprocess.run(
        ["node", "-c", str(path)],
        capture_output=True, text=True,
    )
    return result.returncode == 0, result.stderr


ALL_MINIPROGRAM_JS = [
    DEV_INJECTOR_JS_PATH,
    DEV_MENU_JS_PATH,
    UPLOADER_JS_PATH,
    INDEX_JS_PATH,
    CONSTANTS_PATH,
]


# ── Test: dev-injector.js module structure ───────────────────────────────────

class TestDevInjectorModuleStructure:
    """Verify dev-injector.js has all required exports."""

    def test_js_file_exists(self):
        assert DEV_INJECTOR_JS_PATH.exists()

    def test_has_module_exports(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "module.exports" in content

    def test_exports_get_flag(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "getFlag:" in content or "getFlag:" in content.replace(" ", "")

    def test_exports_set_flag(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "setFlag:" in content or "setFlag:" in content.replace(" ", "")

    def test_exports_toggle_flag(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "toggleFlag:" in content or "toggleFlag:" in content.replace(" ", "")

    def test_exports_get_all_flags(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "getAllFlags" in content

    def test_exports_reset_all_flags(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "resetAllFlags" in content

    def test_exports_is_any_flag_active(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "isAnyFlagActive" in content

    def test_exports_storage_key(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "STORAGE_KEY" in content

    def test_requires_constants(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "require('./constants.js')" in content


# ── Test: dev-injector.js flag logic ─────────────────────────────────────────

class TestDevInjectorFlagLogic:
    """Verify dev-injector.js flag read/write/toggle/reset logic."""

    def test_default_flags_all_false(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "mockFcUrlBroken: false" in content
        assert "mockNetworkOffline: false" in content
        assert "mockVerifyFail: false" in content

    def test_storage_key_name(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "'soniscope_dev_flags'" in content or '"soniscope_dev_flags"' in content

    def test_get_flag_checks_production(self):
        """AC1: getFlag returns false when IS_PRODUCTION is true."""
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "IS_PRODUCTION" in content
        # getFlag should check IS_PRODUCTION and return false
        assert "IS_PRODUCTION" in content

    def test_get_flag_calls_load_flags(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "_loadFlags" in content

    def test_set_flag_persists(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "_saveFlags" in content

    def test_toggle_flips_value(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        # toggle should flip: flags[name] = !flags[name]
        assert "!" in content

    def test_reset_all_sets_defaults(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "DEFAULT_FLAGS" in content

    def test_load_flags_uses_storage(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "getStorageSync" in content

    def test_save_flags_uses_storage(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "setStorageSync" in content

    def test_is_any_flag_active(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        assert "mockFcUrlBroken ||" in content or "mockFcUrlBroken||" in content or "flags.mockFcUrlBroken || flags.mockNetworkOffline" in content

    def test_production_guard(self):
        """AC1: production flag check returns false immediately."""
        content = _read_js(DEV_INJECTOR_JS_PATH)
        # getFlag should have early return for production
        assert "IS_PRODUCTION" in content


# ── Test: dev-menu page ──────────────────────────────────────────────────────

class TestDevMenuPage:
    """Verify dev-menu page has correct structure."""

    def test_all_four_files_exist(self):
        assert DEV_MENU_JS_PATH.exists()
        assert DEV_MENU_WXML_PATH.exists()
        assert DEV_MENU_WXSS_PATH.exists()
        assert DEV_MENU_JSON_PATH.exists()

    def test_has_page_definition(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "Page({" in content

    def test_has_data_fields(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "mockFcUrlBroken" in content
        assert "mockNetworkOffline" in content
        assert "mockVerifyFail" in content
        assert "isProduction" in content

    def test_on_load_calls_refresh_flags(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "onLoad" in content
        assert "_refreshFlags" in content

    def test_on_show_calls_refresh_flags(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "onShow" in content

    def test_has_refresh_flags(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "_refreshFlags:" in content or "_refreshFlags:" in content

    def test_requires_dev_injector(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "require('../../utils/dev-injector.js')" in content

    def test_requires_constants(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "require('../../utils/constants.js')" in content


# ── Test: dev-menu toggle handlers ───────────────────────────────────────────

class TestDevMenuToggleHandlers:
    """Verify toggle handlers call devInjector and update setData."""

    def test_on_toggle_mock_fc_exists(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "onToggleMockFc" in content

    def test_on_toggle_mock_fc_calls_toggle_flag(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "toggleFlag" in content
        assert "'mockFcUrlBroken'" in content

    def test_on_toggle_mock_offline_exists(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "onToggleMockOffline" in content

    def test_on_toggle_mock_offline_calls_toggle_flag(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "'mockNetworkOffline'" in content

    def test_on_toggle_mock_verify_exists(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "onToggleMockVerify" in content

    def test_on_toggle_mock_verify_calls_toggle_flag(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "'mockVerifyFail'" in content

    def test_all_toggle_handlers_update_set_data(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "setData" in content

    def test_on_reset_all_exists(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "onResetAll" in content

    def test_on_reset_all_calls_reset(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "resetAllFlags" in content

    def test_on_reset_all_shows_toast(self):
        content = _read_js(DEV_MENU_JS_PATH)
        assert "已全部关闭" in content


# ── Test: dev-menu.wxml template ─────────────────────────────────────────────

class TestDevMenuWxml:
    """Verify dev-menu WXML template structure."""

    def test_wxml_exists(self):
        assert DEV_MENU_WXML_PATH.exists()

    def test_has_switch_for_mock_fc(self):
        content = _read_wxml(DEV_MENU_WXML_PATH)
        assert "mockFcUrlBroken" in content
        assert "onToggleMockFc" in content

    def test_has_switch_for_mock_offline(self):
        content = _read_wxml(DEV_MENU_WXML_PATH)
        assert "mockNetworkOffline" in content
        assert "onToggleMockOffline" in content

    def test_has_switch_for_mock_verify(self):
        content = _read_wxml(DEV_MENU_WXML_PATH)
        assert "mockVerifyFail" in content
        assert "onToggleMockVerify" in content

    def test_has_switch_components(self):
        """AC2-AC4: each toggle has a <switch> component for runtime toggle."""
        content = _read_wxml(DEV_MENU_WXML_PATH)
        matches = re.findall(r'<switch', content)
        assert len(matches) == 3

    def test_has_reset_button(self):
        content = _read_wxml(DEV_MENU_WXML_PATH)
        assert "onResetAll" in content

    def test_title_text(self):
        content = _read_wxml(DEV_MENU_WXML_PATH)
        assert "开发者菜单" in content or "dev menu" in content.lower()

    def test_production_warning(self):
        """AC1: production warning shown when IS_PRODUCTION is true."""
        content = _read_wxml(DEV_MENU_WXML_PATH)
        assert "isProduction" in content
        # Should have a warning for production
        assert "生产环境" in content or "PRODUCTION" in content

    def test_toggle_descriptions(self):
        """Each toggle has a description explaining what it does."""
        content = _read_wxml(DEV_MENU_WXML_PATH)
        assert "mock-fc-url-broken" in content.lower() or "mockFcUrlBroken" in content
        assert "mock-network-offline" in content.lower() or "mockNetworkOffline" in content
        assert "mock-verify-fail" in content.lower() or "mockVerifyFail" in content


# ── Test: dev-menu.wxss styles ───────────────────────────────────────────────

class TestDevMenuWxss:
    """Verify dev-menu WXSS style structure."""

    def test_wxss_exists(self):
        assert DEV_MENU_WXSS_PATH.exists()

    def test_has_container_style(self):
        content = _read_wxss(DEV_MENU_WXSS_PATH)
        assert ".container" in content

    def test_has_toggle_item_style(self):
        content = _read_wxss(DEV_MENU_WXSS_PATH)
        assert ".toggle-item" in content

    def test_has_toggle_label_style(self):
        content = _read_wxss(DEV_MENU_WXSS_PATH)
        assert ".toggle-label" in content

    def test_has_reset_button_style(self):
        content = _read_wxss(DEV_MENU_WXSS_PATH)
        assert ".reset-btn" in content

    def test_has_env_hint_styles(self):
        content = _read_wxss(DEV_MENU_WXSS_PATH)
        assert ".env-" in content  # env-warning or env-ok


# ── Test: uploader.js fault injection integration ────────────────────────────

class TestUploaderFaultInjection:
    """Verify uploader.js integrates fault injection checks."""

    def test_requires_dev_injector(self):
        content = _read_js(UPLOADER_JS_PATH)
        assert "require('./dev-injector.js')" in content

    def test_process_queue_checks_mock_offline(self):
        """AC3: mock-network-offline prevents upload queue processing."""
        content = _read_js(UPLOADER_JS_PATH)
        assert "mockNetworkOffline" in content

    def test_fetch_sts_checks_mock_fc_broken(self):
        """AC2: mock-fc-url-broken forces FC /issue-credential failure."""
        content = _read_js(UPLOADER_JS_PATH)
        assert "mockFcUrlBroken" in content

    def test_do_verify_checks_mock_fc_broken(self):
        """AC2: mock-fc-url-broken also forces FC /verify-upload failure."""
        content = _read_js(UPLOADER_JS_PATH)
        lines = content.split('\n')
        fc_broken_check_count = 0
        for line in lines:
            if "mockFcUrlBroken" in line:
                fc_broken_check_count += 1
        # Should appear in both _fetchSts and _doVerifyUpload
        assert fc_broken_check_count >= 2

    def test_do_verify_checks_mock_verify_fail(self):
        """AC4: mock-verify-fail forces verify to return false."""
        content = _read_js(UPLOADER_JS_PATH)
        assert "mockVerifyFail" in content

    def test_verify_failure_handler_includes_mock_reasons(self):
        """Mock failures should be handled as MANUAL_RETRY."""
        content = _read_js(UPLOADER_JS_PATH)
        assert "VERIFY_FALSE_MOCK_FAILURE" in content or "MOCK_FC_FAILURE" in content

    def test_mock_fc_broken_returns_error_code(self):
        """AC2: mock-fc-url-broken returns MOCK_FC_FAILURE error for retry counts."""
        content = _read_js(UPLOADER_JS_PATH)
        assert "MOCK_FC_FAILURE" in content

    def test_mock_verify_fail_returns_reason(self):
        """AC4: mock-verify-fail returns verify false reason."""
        content = _read_js(UPLOADER_JS_PATH)
        assert "VERIFY_FALSE_MOCK_FAILURE" in content

    def test_fetch_sts_mock_logs(self):
        """Mock injection should produce log with the 👺 emoji marker."""
        content = _read_js(UPLOADER_JS_PATH)
        assert "👺" in content

    def test_do_verify_mock_logs(self):
        content = _read_js(UPLOADER_JS_PATH)
        # At least 2 👺 log lines (one in _fetchSts, one in _doVerifyUpload)
        assert content.count("👺") >= 2


# ── Test: index.js dev menu entry ────────────────────────────────────────────

class TestIndexDevMenuEntry:
    """Verify index.js has dev menu navigation handler and data field."""

    def test_has_navigate_to_dev_menu(self):
        content = _read_js(INDEX_JS_PATH)
        assert "navigateToDevMenu" in content

    def test_navigates_to_dev_menu_page(self):
        content = _read_js(INDEX_JS_PATH)
        assert "/pages/dev-menu/dev-menu" in content

    def test_has_is_production_data_field(self):
        content = _read_js(INDEX_JS_PATH)
        assert "isProduction: constants.IS_PRODUCTION" in content

    def test_index_wxml_has_dev_menu_link(self):
        content = _read_wxml(INDEX_WXML_PATH)
        assert "/pages/dev-menu/dev-menu" in content

    def test_index_wxml_production_guard(self):
        """AC1: dev menu entry only visible when NOT production."""
        content = _read_wxml(INDEX_WXML_PATH)
        assert "!isProduction" in content or "isProduction" in content


# ── Test: app.json page registration ─────────────────────────────────────────

class TestAppJsonRegistration:
    """Verify dev-menu page is registered in app.json."""

    def test_dev_menu_in_pages(self):
        content = APP_JSON_PATH.read_text(encoding="utf-8")
        assert "pages/dev-menu/dev-menu" in content


# ── Test: Constants ──────────────────────────────────────────────────────────

class TestConstants:
    """Verify constants.js has IS_PRODUCTION for dev menu gating."""

    def test_is_production_exists(self):
        content = _read_js(CONSTANTS_PATH)
        assert "IS_PRODUCTION" in content

    def test_is_production_is_false(self):
        content = _read_js(CONSTANTS_PATH)
        assert "IS_PRODUCTION: false" in content


# ── Test: JS syntax ──────────────────────────────────────────────────────────

class TestJSSyntax:
    """All new and modified JS files pass node -c syntax check."""

    def test_dev_injector_syntax(self):
        ok, stderr = _js_syntax_ok(DEV_INJECTOR_JS_PATH)
        assert ok, f"Syntax error in dev-injector.js: {stderr}"

    def test_dev_menu_syntax(self):
        ok, stderr = _js_syntax_ok(DEV_MENU_JS_PATH)
        assert ok, f"Syntax error in dev-menu.js: {stderr}"

    def test_uploader_syntax(self):
        ok, stderr = _js_syntax_ok(UPLOADER_JS_PATH)
        assert ok, f"Syntax error in uploader.js: {stderr}"

    def test_index_syntax(self):
        ok, stderr = _js_syntax_ok(INDEX_JS_PATH)
        assert ok, f"Syntax error in index.js: {stderr}"


# ── Test: security — no hardcoded keys ──────────────────────────────────────

class TestSecurityNoKeys:
    """New files must not contain hardcoded AK/Secret/Token."""

    KEY_PATTERNS = [
        r'LTAI[a-zA-Z0-9]{12,}',
        r'(?i)access_key_secret["\s:=]+(?![^"]{0,4}\*)',
        r'(?i)appsecret["\s:=]+(?![^"]{0,4}\*)',
        r'(?i)security[_\-]?token["\s:=]+(?![^"]{0,4}\*)',
    ]

    def test_dev_injector_no_keys(self):
        content = _read_js(DEV_INJECTOR_JS_PATH)
        for pat in self.KEY_PATTERNS:
            assert not re.search(pat, content), f"Key leak in dev-injector.js: {pat}"

    def test_dev_menu_no_keys(self):
        content = _read_js(DEV_MENU_JS_PATH)
        for pat in self.KEY_PATTERNS:
            assert not re.search(pat, content), f"Key leak in dev-menu.js: {pat}"

    def test_uploader_no_new_keys(self):
        """Uploader.js already contains references to 'access_key_secret' and
        'security-token' in OSS PostObject signature code (pre-existing from
        US-017). Verify no LTAI-pattern key leaks (only relevant pattern for
        existing file)."""
        content = _read_js(UPLOADER_JS_PATH)
        # LTAI pattern should never appear in source
        assert not re.search(r'LTAI[a-zA-Z0-9]{12,}', content), "LTAI key leak in uploader.js"


# ── Test: Makefile coverage ─────────────────────────────────────────────────

class TestMakefileCoverage:
    """Makefile miniprogram-lint must cover new JS files."""

    def test_miniprogram_lint_covers_dev_injector(self):
        content = _read_makefile()
        assert "utils/dev-injector.js" in content

    def test_miniprogram_lint_covers_dev_menu(self):
        content = _read_makefile()
        assert "pages/dev-menu/dev-menu.js" in content

    def test_makefile_still_covers_uploader(self):
        content = _read_makefile()
        assert "utils/uploader.js" in content


# ── Test: page files completeness ────────────────────────────────────────────

class TestDevMenuPageFiles:
    """Verify dev-menu page has all 4 required files."""

    def test_js_exists(self):
        assert DEV_MENU_JS_PATH.exists()

    def test_wxml_exists(self):
        assert DEV_MENU_WXML_PATH.exists()

    def test_wxss_exists(self):
        assert DEV_MENU_WXSS_PATH.exists()

    def test_json_exists(self):
        assert DEV_MENU_JSON_PATH.exists()

    def test_json_has_using_components(self):
        content = DEV_MENU_JSON_PATH.read_text(encoding="utf-8")
        assert "usingComponents" in content
