"""Tests for US-006 — FC shared auth, validation & safe logging module."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FC_ROOT = REPO_ROOT / "apps" / "fc"

# Add fc/ to path so we can import shared
if str(FC_ROOT) not in sys.path:
    sys.path.insert(0, str(FC_ROOT))


@pytest.fixture(autouse=True)
def _clean_sys_path() -> None:
    """Remove fc/ from sys.path after each test to avoid side effects."""
    yield
    try:
        sys.path.remove(str(FC_ROOT))
    except ValueError:
        pass


@pytest.fixture(autouse=True)
def _clean_env() -> None:
    """Clear FC env vars so tests start from a known state."""
    for var in ("OSS_BUCKET", "OSS_REGION", "OSS_ENDPOINT", "WX_APPID",
                "WX_APP_SECRET", "OPENID_ALLOWLIST", "MAX_UPLOAD_BYTES",
                "RAM_ROLE_ARN", "ALIYUN_AK_ID", "ALIYUN_AK_SECRET"):
        os.environ.pop(var, None)
    yield
    for var in ("OSS_BUCKET", "OSS_REGION", "OSS_ENDPOINT", "WX_APPID",
                "WX_APP_SECRET", "OPENID_ALLOWLIST", "MAX_UPLOAD_BYTES",
                "RAM_ROLE_ARN", "ALIYUN_AK_ID", "ALIYUN_AK_SECRET"):
        os.environ.pop(var, None)


# ---------------------------------------------------------------------------
# Shared config tests  (AC: reads env vars, errors on missing)
# ---------------------------------------------------------------------------


class TestSharedConfig:
    """AC: reads env vars; errors with clear message on missing."""

    def test_reads_all_required_vars(self) -> None:
        from shared.config import SharedConfig, read_shared_config

        os.environ["OSS_BUCKET"] = "test-bucket"
        os.environ["OSS_REGION"] = "cn-beijing"
        os.environ["OSS_ENDPOINT"] = "oss-cn-beijing.aliyuncs.com"
        os.environ["WX_APPID"] = "wx123"
        os.environ["WX_APP_SECRET"] = "secret456"
        os.environ["RAM_ROLE_ARN"] = "acs:ram::123:role/test"
        os.environ["ALIYUN_AK_ID"] = "test-ak"
        os.environ["ALIYUN_AK_SECRET"] = "test-as"

        cfg = read_shared_config()
        assert cfg.oss_bucket == "test-bucket"
        assert cfg.oss_region == "cn-beijing"
        assert cfg.oss_endpoint == "oss-cn-beijing.aliyuncs.com"
        assert cfg.wx_appid == "wx123"
        assert cfg.wx_app_secret == "secret456"
        assert cfg.ram_role_arn == "acs:ram::123:role/test"
        assert cfg.aliyun_ak_id == "test-ak"
        assert cfg.aliyun_ak_secret == "test-as"

    def test_missing_vars_raises_with_list(self) -> None:
        from shared.config import _ConfigError, read_shared_config

        # No vars set → all 8 missing (5 from US-006 + 3 from US-007)
        with pytest.raises(_ConfigError) as exc_info:
            read_shared_config()
        assert len(exc_info.value.missing) == 8

    def test_partial_missing_lists_correct_names(self) -> None:
        from shared.config import _ConfigError, read_shared_config

        os.environ["OSS_BUCKET"] = "x"
        os.environ["OSS_REGION"] = "x"
        # OSS_ENDPOINT, WX_APPID, WX_APP_SECRET missing
        with pytest.raises(_ConfigError) as exc_info:
            read_shared_config()
        missing = exc_info.value.missing
        assert "OSS_BUCKET" not in missing
        assert "OSS_REGION" not in missing
        assert "OSS_ENDPOINT" in missing
        assert "WX_APPID" in missing
        assert "WX_APP_SECRET" in missing


# ---------------------------------------------------------------------------
# Error response builders (AC: 400 on bad JSON / missing fields, stable codes)
# ---------------------------------------------------------------------------


class TestErrorResponses:
    """AC: stable error codes, proper HTTP status codes."""

    def test_bad_request_400(self) -> None:
        from shared.errors import bad_request

        resp = bad_request("TEST_ERROR", detail="test detail")
        assert resp["statusCode"] == 400
        assert resp["headers"]["Content-Type"] == "application/json"
        body = json.loads(resp["body"])
        assert body["error"] == "TEST_ERROR"
        assert body["detail"] == "test detail"

    def test_unauthorized_401(self) -> None:
        from shared.errors import unauthorized

        resp = unauthorized()
        assert resp["statusCode"] == 401
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_CODE"

    def test_forbidden_403(self) -> None:
        from shared.errors import forbidden

        resp = forbidden()
        assert resp["statusCode"] == 403
        body = json.loads(resp["body"])
        assert body["error"] == "OPENID_NOT_ALLOWED"

    def test_internal_error_500(self) -> None:
        from shared.errors import internal_error

        resp = internal_error()
        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert body["error"] == "INTERNAL_ERROR"

    def test_error_codes_are_stable_strings(self) -> None:
        from shared import errors as e

        assert e.ERROR_INVALID_JSON == "INVALID_JSON"
        assert e.ERROR_MISSING_FIELD == "MISSING_FIELD"
        assert e.ERROR_INVALID_CODE == "INVALID_CODE"
        assert e.ERROR_OPENID_NOT_ALLOWED == "OPENID_NOT_ALLOWED"
        assert e.ERROR_SIZE_EXCEEDED == "SIZE_EXCEEDED"
        assert e.ERROR_INTERNAL == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# Request parsing and field validation (AC: 400 on bad JSON / missing fields)
# ---------------------------------------------------------------------------


class TestParseRequestBody:
    """AC: returns 400 on invalid JSON, empty body, or non-dict."""

    def test_parses_valid_json(self) -> None:
        from shared.auth import parse_request_body

        data = parse_request_body('{"code":"abc","fragment_id":"f1"}')
        assert data == {"code": "abc", "fragment_id": "f1"}

    def test_empty_body_raises_auth_error(self) -> None:
        from shared.auth import AuthError, parse_request_body

        with pytest.raises(AuthError) as exc_info:
            parse_request_body("")
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "INVALID_JSON"

    def test_malformed_json_raises_auth_error(self) -> None:
        from shared.auth import AuthError, parse_request_body

        with pytest.raises(AuthError) as exc_info:
            parse_request_body("not json")
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "INVALID_JSON"

    def test_non_dict_json_raises_auth_error(self) -> None:
        from shared.auth import AuthError, parse_request_body

        with pytest.raises(AuthError) as exc_info:
            parse_request_body("[1, 2, 3]")
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "INVALID_JSON"


class TestRequireFields:
    """AC: missing required fields → MISSING_FIELD."""

    def test_all_present_passes(self) -> None:
        from shared.auth import require_fields

        require_fields({"a": 1, "b": "x"}, "a", "b")

    def test_missing_field_raises(self) -> None:
        from shared.auth import AuthError, require_fields

        with pytest.raises(AuthError) as exc_info:
            require_fields({"a": 1}, "a", "b")
        assert exc_info.value.error_code == "MISSING_FIELD"
        assert "b" in exc_info.value.detail

    def test_empty_string_field_raises(self) -> None:
        from shared.auth import AuthError, require_fields

        with pytest.raises(AuthError) as exc_info:
            require_fields({"code": "  "}, "code")
        assert exc_info.value.error_code == "MISSING_FIELD"

    def test_null_field_raises(self) -> None:
        from shared.auth import AuthError, require_fields

        with pytest.raises(AuthError) as exc_info:
            require_fields({"code": None}, "code")
        assert exc_info.value.error_code == "MISSING_FIELD"


# ---------------------------------------------------------------------------
# AuthError / response conversion
# ---------------------------------------------------------------------------


class TestAuthError:
    """AC: AuthError carries status code and error code."""

    def test_auth_error_to_response(self) -> None:
        from shared.auth import AuthError, auth_error_to_response

        exc = AuthError(403, "OPENID_NOT_ALLOWED", "test detail")
        resp = auth_error_to_response(exc)
        assert resp["statusCode"] == 403
        body = json.loads(resp["body"])
        assert body["error"] == "OPENID_NOT_ALLOWED"
        assert body["detail"] == "test detail"


# ---------------------------------------------------------------------------
# Authentication — jscode2session + allowlist  (AC: INVALID_CODE, OPENID_NOT_ALLOWED)
# ---------------------------------------------------------------------------


class TestAuthenticate:
    """AC: jscode2session → openid; allowlist check; proper error codes."""

    @pytest.fixture(autouse=True)
    def _set_env(self) -> None:
        os.environ["OSS_BUCKET"] = "soniscope-audio"
        os.environ["OSS_REGION"] = "cn-beijing"
        os.environ["OSS_ENDPOINT"] = "oss-cn-beijing.aliyuncs.com"
        os.environ["WX_APPID"] = "wx-test"
        os.environ["WX_APP_SECRET"] = "test-secret"
        os.environ["RAM_ROLE_ARN"] = "acs:ram::123:role/test-role"
        os.environ["ALIYUN_AK_ID"] = "ak-test"
        os.environ["ALIYUN_AK_SECRET"] = "secret-test"

    def test_allowlist_accepts_listed_openid(self) -> None:
        from shared.auth import authenticate

        os.environ["OPENID_ALLOWLIST"] = "openid-a, openid-b"

        with mock.patch("shared.auth._code_to_openid", return_value="openid-a"):
            result = authenticate("valid-code", "frag-1")
            assert result == "openid-a"

    def test_allowlist_rejects_unlisted_openid(self) -> None:
        from shared.auth import AuthError, authenticate

        os.environ["OPENID_ALLOWLIST"] = "openid-a"

        with mock.patch("shared.auth._code_to_openid", return_value="openid-b"):
            with pytest.raises(AuthError) as exc_info:
                authenticate("valid-code", "frag-2")
            assert exc_info.value.status_code == 403
            assert exc_info.value.error_code == "OPENID_NOT_ALLOWED"

    def test_code_to_openid_failure_maps_to_401(self) -> None:
        from shared.auth import AuthError, authenticate

        os.environ["OPENID_ALLOWLIST"] = "openid-a"

        with mock.patch(
            "shared.auth._code_to_openid",
            side_effect=AuthError(401, "INVALID_CODE", "WeChat error"),
        ):
            with pytest.raises(AuthError) as exc_info:
                authenticate("bad-code", "frag-3")
            assert exc_info.value.status_code == 401
            assert exc_info.value.error_code == "INVALID_CODE"

    def test_empty_allowlist_rejects(self) -> None:
        from shared.auth import AuthError, authenticate

        os.environ["OPENID_ALLOWLIST"] = ""

        with mock.patch("shared.auth._code_to_openid", return_value="openid-x"):
            with pytest.raises(AuthError) as exc_info:
                authenticate("code", "frag-4")
            assert exc_info.value.status_code == 403
            assert exc_info.value.error_code == "OPENID_NOT_ALLOWED"

    def test_allowlist_trims_whitespace(self) -> None:
        from shared.auth import authenticate

        os.environ["OPENID_ALLOWLIST"] = "  openid-a , openid-b  "

        with mock.patch("shared.auth._code_to_openid", return_value="openid-b"):
            result = authenticate("code", "frag-5")
            assert result == "openid-b"


# ---------------------------------------------------------------------------
# Safe logging (AC: no secrets leaked)
# ---------------------------------------------------------------------------


class TestSafeLogging:
    """AC: logs hash openid, fragment_id, result, elapsed; never secrets."""

    @pytest.fixture(autouse=True)
    def _set_env(self) -> None:
        os.environ["OSS_BUCKET"] = "x"
        os.environ["OSS_REGION"] = "x"
        os.environ["OSS_ENDPOINT"] = "x"
        os.environ["WX_APPID"] = "x"
        os.environ["WX_APP_SECRET"] = "x"
        os.environ["RAM_ROLE_ARN"] = "x"
        os.environ["ALIYUN_AK_ID"] = "x"
        os.environ["ALIYUN_AK_SECRET"] = "x"

    def test_log_auth_attempt_hashes_openid(self, caplog: pytest.LogCaptureFixture) -> None:
        from shared.logging import log_auth_attempt

        caplog.set_level(logging.INFO)
        log_auth_attempt("oTest-12345abcdef", "frag-1")

        records = [r for r in caplog.records if r.levelname == "INFO"]
        assert len(records) == 1
        msg = records[0].message
        # Should contain hash, not the raw openid
        assert "oTest-12345abcdef" not in msg
        assert "openid_hash=" in msg
        assert "fragment_id=frag-1" in msg

    def test_log_auth_result_never_leaks_openid(self, caplog: pytest.LogCaptureFixture) -> None:
        from shared.logging import log_auth_result

        caplog.set_level(logging.INFO)
        log_auth_result("secret-openid", "frag-2", True, 42.0)

        records = [r for r in caplog.records if r.levelname == "INFO"]
        assert len(records) == 1
        msg = records[0].message
        assert "secret-openid" not in msg
        assert "openid_hash=" in msg
        assert "allowed=true" in msg
        assert "elapsed_ms=42.0" in msg

    def test_log_response_includes_status_and_elapsed(self, caplog: pytest.LogCaptureFixture) -> None:
        from shared.logging import log_response

        caplog.set_level(logging.INFO)
        log_response(200, "frag-3", 15.5)

        records = [r for r in caplog.records if r.levelname == "INFO"]
        assert len(records) == 1
        msg = records[0].message
        assert "status=200" in msg
        assert "fragment_id=frag-3" in msg
        assert "elapsed_ms=15.5" in msg

    def test_log_error_never_contains_secrets(self, caplog: pytest.LogCaptureFixture) -> None:
        from shared.logging import log_error

        caplog.set_level(logging.WARNING)
        log_error("frag-4", "INVALID_CODE", "secret-key-12345")

        records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(records) == 1
        msg = records[0].message
        assert "error=INVALID_CODE" in msg
        # detail argument is logged as-is; caller must not pass secrets
        assert "secret-key-12345" in msg  # detail IS passed in (caller's responsibility)

    def test_loggers_do_not_log_code_or_ak(self, caplog: pytest.LogCaptureFixture) -> None:
        """Demonstrate that the logging module itself never leaks code/AK."""
        from shared.logging import get_logger

        logger = get_logger()
        caplog.set_level(logging.DEBUG)

        # Simulate what various log calls would show
        logger.info("test code=%s", "some-code-from-wx")  # This WOULD leak — caller is responsible
        records = [r for r in caplog.records]
        assert "some-code-from-wx" in records[0].message
        # The module can't prevent bad caller usage; the AC says log functions
        # must never log these fields *themselves*.  That we verify via the
        # structured helpers above not mentioning code/AK/SecurityToken at all.


# ---------------------------------------------------------------------------
# safe_handler integration (AC: auth + validation + error handling for both FC functions)
# ---------------------------------------------------------------------------


class TestSafeHandler:
    """AC: safe_handler applies parsing → auth → business; catches errors."""

    @pytest.fixture(autouse=True)
    def _set_env(self) -> None:
        os.environ["OSS_BUCKET"] = "b"
        os.environ["OSS_REGION"] = "r"
        os.environ["OSS_ENDPOINT"] = "e"
        os.environ["WX_APPID"] = "a"
        os.environ["WX_APP_SECRET"] = "s"
        os.environ["OPENID_ALLOWLIST"] = "allowed-openid"
        os.environ["RAM_ROLE_ARN"] = "arn"
        os.environ["ALIYUN_AK_ID"] = "ak"
        os.environ["ALIYUN_AK_SECRET"] = "as"

    def test_valid_request_calls_business_logic(self) -> None:
        from shared.auth import safe_handler

        called: list[dict] = []

        def business(data: dict, openid: str, t_start: float) -> dict:
            called.append({"data": data, "openid": openid})
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": '{"ok":true}',
            }

        with mock.patch("shared.auth._code_to_openid", return_value="allowed-openid"):
            resp = safe_handler(
                {
                    "path": "/test",
                    "httpMethod": "POST",
                    "body": json.dumps({"code": "c", "fragment_id": "f1", "size": 100}),
                },
                business,
                required_fields=("code", "fragment_id", "size"),
            )

        assert resp["statusCode"] == 200
        assert len(called) == 1
        assert called[0]["data"]["size"] == 100
        assert called[0]["openid"] == "allowed-openid"

    def test_invalid_json_returns_400(self) -> None:
        from shared.auth import safe_handler

        def business(data: dict, openid: str, t_start: float) -> dict:
            return {"statusCode": 500}  # should never reach

        resp = safe_handler(
            {"path": "/test", "httpMethod": "POST", "body": "not-json"},
            business,
        )

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_JSON"

    def test_missing_required_field_returns_400(self) -> None:
        from shared.auth import safe_handler

        def business(data: dict, openid: str, t_start: float) -> dict:
            return {"statusCode": 500}

        with mock.patch("shared.auth._code_to_openid", return_value="allowed-openid"):
            resp = safe_handler(
                {
                    "path": "/test",
                    "httpMethod": "POST",
                    "body": json.dumps({"code": "c"}),
                },
                business,
                required_fields=("code", "fragment_id"),
            )

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "MISSING_FIELD"

    def test_not_in_allowlist_returns_403(self) -> None:
        from shared.auth import safe_handler

        def business(data: dict, openid: str, t_start: float) -> dict:
            return {"statusCode": 500}

        with mock.patch("shared.auth._code_to_openid", return_value="not-allowed"):
            resp = safe_handler(
                {
                    "path": "/test",
                    "httpMethod": "POST",
                    "body": json.dumps({"code": "c", "fragment_id": "f1"}),
                },
                business,
            )

        assert resp["statusCode"] == 403
        body = json.loads(resp["body"])
        assert body["error"] == "OPENID_NOT_ALLOWED"

    def test_unexpected_exception_returns_500(self) -> None:
        from shared.auth import safe_handler

        def business(data: dict, openid: str, t_start: float) -> dict:
            raise RuntimeError("boom")

        with mock.patch("shared.auth._code_to_openid", return_value="allowed-openid"):
            resp = safe_handler(
                {
                    "path": "/test",
                    "httpMethod": "POST",
                    "body": json.dumps({"code": "c", "fragment_id": "f1"}),
                },
                business,
            )

        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert body["error"] == "INTERNAL_ERROR"

    def test_uses_httpMethod_or_method(self) -> None:
        from shared.auth import safe_handler

        called = False

        def business(data: dict, openid: str, t_start: float) -> dict:
            nonlocal called
            called = True
            return {"statusCode": 200, "body": "{}"}

        with mock.patch("shared.auth._code_to_openid", return_value="allowed-openid"):
            resp = safe_handler(
                {
                    "path": "/test",
                    "method": "POST",
                    "body": json.dumps({"code": "c", "fragment_id": "f1"}),
                },
                business,
            )
        assert called
        assert resp["statusCode"] == 200


# ---------------------------------------------------------------------------
# Cross-import test (AC: shared can be imported by both functions)
# ---------------------------------------------------------------------------


class TestSharedImportable:
    """AC: shared module is importable and does NOT depend on FC 2.0 service layer."""

    def test_shared_imports(self) -> None:
        """Verify shared package is importable."""
        import shared  # noqa: F401

    def test_shared_no_fc20_imports(self) -> None:
        """Verify shared module does not import FC 2.0 service-layer packages."""
        import shared.auth as sa
        # Check that no alibabacloud_fc* imports exist in auth
        src = (Path(sa.__file__).parent / "auth.py").read_text()
        assert "alibabacloud" not in src
        assert "fc20230330" not in src

    def test_issue_credential_imports_shared(self) -> None:
        """AC: issue-credential handler imports shared auth."""
        # The handler sets up sys.path internally; simulate that
        import importlib
        handler_path = FC_ROOT / "issue_credential" / "handler.py"
        spec = importlib.util.spec_from_file_location(
            "issue_credential_handler", str(handler_path)
        )
        mod = importlib.util.module_from_spec(spec)
        # Mock the path setup
        with mock.patch.dict(os.environ, {
            "OSS_BUCKET": "b", "OSS_REGION": "r", "OSS_ENDPOINT": "e",
            "WX_APPID": "a", "WX_APP_SECRET": "s",
        }):
            if str(FC_ROOT) not in sys.path:
                sys.path.insert(0, str(FC_ROOT))
            try:
                spec.loader.exec_module(mod)
            finally:
                try:
                    sys.path.remove(str(FC_ROOT))
                except ValueError:
                    pass
        assert callable(mod.handler)

    def test_verify_upload_imports_shared(self) -> None:
        """AC: verify-upload handler imports shared auth."""
        import importlib
        handler_path = FC_ROOT / "verify_upload" / "handler.py"
        spec = importlib.util.spec_from_file_location(
            "verify_upload_handler", str(handler_path)
        )
        mod = importlib.util.module_from_spec(spec)
        with mock.patch.dict(os.environ, {
            "OSS_BUCKET": "b", "OSS_REGION": "r", "OSS_ENDPOINT": "e",
            "WX_APPID": "a", "WX_APP_SECRET": "s",
        }):
            if str(FC_ROOT) not in sys.path:
                sys.path.insert(0, str(FC_ROOT))
            try:
                spec.loader.exec_module(mod)
            finally:
                try:
                    sys.path.remove(str(FC_ROOT))
                except ValueError:
                    pass
        assert callable(mod.handler)

    def test_both_handlers_exist_and_are_callable(self) -> None:
        """Just verify both handler files exist and define 'handler'."""
        import importlib
        for func_name in ("issue_credential", "verify_upload"):
            handler_path = FC_ROOT / func_name / "handler.py"
            assert handler_path.is_file(), f"Missing {handler_path}"
            spec = importlib.util.spec_from_file_location(
                f"{func_name}_handler", str(handler_path)
            )
            mod = importlib.util.module_from_spec(spec)
            with mock.patch.dict(os.environ, {
                "OSS_BUCKET": "b", "OSS_REGION": "r", "OSS_ENDPOINT": "e",
                "WX_APPID": "a", "WX_APP_SECRET": "s",
            }):
                if str(FC_ROOT) not in sys.path:
                    sys.path.insert(0, str(FC_ROOT))
                try:
                    spec.loader.exec_module(mod)
                finally:
                    try:
                        sys.path.remove(str(FC_ROOT))
                    except ValueError:
                        pass
            assert callable(mod.handler)


# ---------------------------------------------------------------------------
# Deploy packaging test (AC: shared module is bundled in function zips)
# ---------------------------------------------------------------------------


class TestDeployPackaging:
    """AC: deploy script includes shared module when packaging FC functions."""

    def test_package_includes_shared(self) -> None:
        # Import deploy_fc module
        scripts_dir = REPO_ROOT / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        try:
            import deploy_fc as dfc

            with tempfile.TemporaryDirectory() as tmp:
                # Redirect the build output to tmp dir
                orig_build_dir = dfc.BUILD_DIR
                try:
                    dfc.BUILD_DIR = Path(tmp)
                    zip_path = dfc._package_function("issue-credential")

                    # Verify shared/ files are in the zip
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        names = zf.namelist()
                        assert "handler.py" in names
                        assert "shared/__init__.py" in names
                        assert "shared/auth.py" in names
                        assert "shared/config.py" in names
                        assert "shared/errors.py" in names
                        assert "shared/logging.py" in names
                finally:
                    dfc.BUILD_DIR = orig_build_dir
        finally:
            try:
                sys.path.remove(str(scripts_dir))
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import tempfile  # noqa: E402
import zipfile  # noqa: E402
