"""Tests for US-009 — FC verify-upload HeadObject upload verification."""

from __future__ import annotations

import json
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

if str(FC_ROOT) not in sys.path:
    sys.path.insert(0, str(FC_ROOT))


@pytest.fixture(autouse=True)
def _manage_sys_path() -> None:
    """Ensure FC_ROOT is in sys.path before each test, then clean up."""
    if str(FC_ROOT) not in sys.path:
        sys.path.insert(0, str(FC_ROOT))
    yield
    try:
        sys.path.remove(str(FC_ROOT))
    except ValueError:
        pass


@pytest.fixture(autouse=True)
def _clean_env() -> None:
    for var in (
        "OSS_BUCKET", "OSS_REGION", "OSS_ENDPOINT",
        "WX_APPID", "WX_APP_SECRET", "OPENID_ALLOWLIST",
        "MAX_UPLOAD_BYTES", "RAM_ROLE_ARN",
        "ALIYUN_AK_ID", "ALIYUN_AK_SECRET",
    ):
        os.environ.pop(var, None)
    yield
    for var in (
        "OSS_BUCKET", "OSS_REGION", "OSS_ENDPOINT",
        "WX_APPID", "WX_APP_SECRET", "OPENID_ALLOWLIST",
        "MAX_UPLOAD_BYTES", "RAM_ROLE_ARN",
        "ALIYUN_AK_ID", "ALIYUN_AK_SECRET",
    ):
        os.environ.pop(var, None)


def _set_required_env() -> None:
    os.environ["OSS_BUCKET"] = "soniscope-audio"
    os.environ["OSS_REGION"] = "cn-beijing"
    os.environ["OSS_ENDPOINT"] = "oss-cn-beijing.aliyuncs.com"
    os.environ["WX_APPID"] = "wx123"
    os.environ["WX_APP_SECRET"] = "secret456"
    os.environ["RAM_ROLE_ARN"] = "acs:ram::123:role/test-role"
    os.environ["ALIYUN_AK_ID"] = "ak-test"
    os.environ["ALIYUN_AK_SECRET"] = "secret-test"


def _make_event(body: dict | None = None) -> dict:
    """Build a minimal FC event for POST with given JSON body."""
    return {
        "httpMethod": "POST",
        "path": "/",
        "body": json.dumps(body) if body else "",
    }


# ---------------------------------------------------------------------------
# SharedConfig fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def _cfg() -> object:
    _set_required_env()
    from shared.config import SharedConfig, read_shared_config
    return read_shared_config()


# ---------------------------------------------------------------------------
# HeadObjectResult tests
# ---------------------------------------------------------------------------


class TestHeadObjectResult:
    """AC: HeadObjectResult NamedTuple holds found, content_length, etag, last_modified."""

    def test_found_object(self) -> None:
        from shared.oss import HeadObjectResult

        r = HeadObjectResult(found=True, content_length=12345, etag="abc", last_modified="Thu, 01 Jan 2026 00:00:00 GMT")
        assert r.found is True
        assert r.content_length == 12345
        assert r.etag == "abc"
        assert r.last_modified == "Thu, 01 Jan 2026 00:00:00 GMT"

    def test_not_found_object(self) -> None:
        from shared.oss import HeadObjectResult

        r = HeadObjectResult(found=False, content_length=None, etag=None, last_modified=None)
        assert r.found is False
        assert r.content_length is None
        assert r.etag is None
        assert r.last_modified is None

    def test_is_namedtuple(self) -> None:
        from shared.oss import HeadObjectResult

        r = HeadObjectResult(found=True, content_length=100, etag="x", last_modified="y")
        assert r.found == r[0]
        assert r.content_length == r[1]


# ---------------------------------------------------------------------------
# head_object tests (unit with mocked HTTP)
# ---------------------------------------------------------------------------


class TestHeadObject:
    """AC: HeadObject returns correct results for found, not-found, and size mismatch cases."""

    def test_object_found(self, _cfg: object) -> None:
        from shared.oss import head_object

        mock_resp = mock.MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.headers = {
            "Content-Length": "54321",
            "ETag": '"abcdef123456"',
            "Last-Modified": "Thu, 01 Jan 2026 00:00:00 GMT",
        }

        with mock.patch("shared.oss.urllib_request.urlopen", return_value=mock_resp):
            result = head_object("recordings/2026-05-26/test.wav", config=_cfg)

        assert result.found is True
        assert result.content_length == 54321
        assert result.etag == "abcdef123456"
        assert result.last_modified == "Thu, 01 Jan 2026 00:00:00 GMT"

    def test_object_not_found_404(self, _cfg: object) -> None:
        from shared.oss import head_object
        from urllib.error import HTTPError

        # Construct a real HTTPError with code 404
        exc = HTTPError("http://fake.url", 404, "Not Found", {}, None)

        with mock.patch("shared.oss.urllib_request.urlopen", side_effect=exc):
            result = head_object("recordings/2026-05-26/missing.wav", config=_cfg)

        assert result.found is False
        assert result.content_length is None
        assert result.etag is None

    def test_http_500_raises_runtime_error(self, _cfg: object) -> None:
        from shared.oss import head_object
        from urllib.error import HTTPError

        exc = HTTPError("http://fake.url", 500, "Internal Error", {}, None)

        with mock.patch("shared.oss.urllib_request.urlopen", side_effect=exc):
            with pytest.raises(RuntimeError, match="OSS HeadObject HTTP 500"):
                head_object("recordings/2026-05-26/test.wav", config=_cfg)

    def test_http_403_raises_runtime_error(self, _cfg: object) -> None:
        from shared.oss import head_object
        from urllib.error import HTTPError

        exc = HTTPError("http://fake.url", 403, "Forbidden", {}, None)

        with mock.patch("shared.oss.urllib_request.urlopen", side_effect=exc):
            with pytest.raises(RuntimeError, match="OSS HeadObject HTTP 403"):
                head_object("recordings/2026-05-26/test.wav", config=_cfg)

    def test_network_error_raises(self, _cfg: object) -> None:
        from shared.oss import head_object
        from urllib.error import URLError

        with mock.patch("shared.oss.urllib_request.urlopen", side_effect=URLError("timeout")):
            with pytest.raises(RuntimeError, match="OSS HeadObject network error"):
                head_object("recordings/2026-05-26/test.wav", config=_cfg)

    def test_reads_config_from_env_if_none(self, _cfg: object) -> None:
        from shared.oss import head_object

        mock_resp = mock.MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.headers = {
            "Content-Length": "100",
            "ETag": '"abcd"',
            "Last-Modified": "Thu, 01 Jan 2026 00:00:00 GMT",
        }

        with mock.patch("shared.oss.urllib_request.urlopen", return_value=mock_resp):
            result = head_object("recordings/2026-05-26/test.wav")

        assert result.found is True

    def test_uses_virtual_hosted_style_url(self, _cfg: object) -> None:
        from shared.oss import head_object

        mock_resp = mock.MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.headers = {
            "Content-Length": "100",
            "ETag": '"x"',
            "Last-Modified": "Thu, 01 Jan 2026 00:00:00 GMT",
        }

        with mock.patch("shared.oss.urllib_request.Request") as mock_req_class:
            mock_req = mock.MagicMock()
            mock_req_class.return_value = mock_req

            with mock.patch("shared.oss.urllib_request.urlopen", return_value=mock_resp):
                head_object("recordings/2026-05-26/test.wav", config=_cfg)

            # Check URL contains bucket.endpoint
            call_args = mock_req_class.call_args
            url = call_args[0][0] if call_args[0] else ""
            assert "soniscope-audio.oss-cn-beijing.aliyuncs.com" in url
            assert "recordings/2026-05-26/test.wav" in url


# ---------------------------------------------------------------------------
# handler tests (verify_upload _handle)
# ---------------------------------------------------------------------------


class TestVerifyUploadHandler:
    """AC: /verify-upload returns correct responses for all verification outcomes."""

    def test_object_found_size_match(self) -> None:
        """AC: verified:true when object exists and size matches."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from shared.oss import HeadObjectResult
        from issue_credential.handler import handler  # path checked in US-007

        # We need verify_upload's handler
        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=True,
                content_length=1234567,
                etag="abcd1234",
                last_modified="Thu, 01 Jan 2026 00:00:00 GMT",
            ),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 1234567,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["verified"] is True
        assert body["etag"] == "abcd1234"
        assert body["size"] == 1234567
        assert body["last_modified"] == "Thu, 01 Jan 2026 00:00:00 GMT"

    def test_object_not_found(self) -> None:
        """AC: verified:false with reason OBJECT_NOT_FOUND when object missing."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from shared.oss import HeadObjectResult
        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=False, content_length=None, etag=None, last_modified=None,
            ),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 1234567,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["verified"] is False
        assert body["reason"] == "OBJECT_NOT_FOUND"

    def test_size_mismatch(self) -> None:
        """AC: verified:false with reason SIZE_MISMATCH when sizes differ."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from shared.oss import HeadObjectResult
        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=True,
                content_length=100,
                etag="small",
                last_modified="Thu, 01 Jan 2026 00:00:00 GMT",
            ),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 200,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["verified"] is False
        assert body["reason"] == "SIZE_MISMATCH"
        assert body["actual_size"] == 100

    def test_headobject_error_returns_502(self) -> None:
        """AC: HeadObject failure returns 502 with INTERNAL_ERROR."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            side_effect=RuntimeError("OSS HeadObject network error: timeout"),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 1234567,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 502
        body = json.loads(resp["body"])
        assert body["error"] == "INTERNAL_ERROR"

    def test_auth_fails_with_invalid_code(self) -> None:
        """AC: Invalid code returns 401 INVALID_CODE."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from verify_upload.handler import handler as vu_handler

        with mock.patch(
            "shared.auth._code_to_openid",
            side_effect=Exception("WeChat error"),
        ):
            event = _make_event({
                "code": "fake_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 1234567,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 401
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_CODE"

    def test_auth_fails_openid_not_allowed(self) -> None:
        """AC: Openid not in allowlist returns 403 OPENID_NOT_ALLOWED."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "only_allowed_user"

        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="not_in_list"
        )

        with mock_auth:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 1234567,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 403
        body = json.loads(resp["body"])
        assert body["error"] == "OPENID_NOT_ALLOWED"

    def test_invalid_fragment_id_returns_400(self) -> None:
        """AC: Bad fragment_id format returns 400 INVALID_FRAGMENT_ID."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )

        with mock_auth:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "bad_no_t_separator",
                "expected_size": 1234567,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_FRAGMENT_ID"

    def test_expected_size_not_integer(self) -> None:
        """AC: Non-integer expected_size returns 400 INVALID_SIZE."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )

        with mock_auth:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": "not_a_number",
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_SIZE"

    def test_expected_size_negative(self) -> None:
        """AC: Negative expected_size returns 400 INVALID_SIZE."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )

        with mock_auth:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": -1,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_SIZE"

    def test_missing_code_returns_400(self) -> None:
        """AC: Request without code returns 400 MISSING_FIELD."""
        _set_required_env()

        from verify_upload.handler import handler as vu_handler

        event = _make_event({
            "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
            "expected_size": 1234567,
        })
        resp = vu_handler(event, {})

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "MISSING_FIELD"

    def test_missing_fragment_id_returns_400(self) -> None:
        """AC: Request without fragment_id returns 400 MISSING_FIELD."""
        _set_required_env()

        from verify_upload.handler import handler as vu_handler

        event = _make_event({
            "code": "some_code",
            "expected_size": 1234567,
        })
        resp = vu_handler(event, {})

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "MISSING_FIELD"

    def test_missing_expected_size_returns_400(self) -> None:
        """AC: Request without expected_size returns 400 MISSING_FIELD."""
        _set_required_env()

        from verify_upload.handler import handler as vu_handler

        event = _make_event({
            "code": "some_code",
            "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
        })
        resp = vu_handler(event, {})

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "MISSING_FIELD"

    def test_verify_upload_uses_same_auth_as_issue_credential(self) -> None:
        """AC: verify-upload shares auth logic with issue-credential."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "shared_user"

        from verify_upload.handler import handler as vu_handler
        from issue_credential.handler import handler as ic_handler

        # Both handlers use safe_handler which calls the same auth stack
        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="shared_user"
        )

        from shared.oss import HeadObjectResult
        vu_mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=True, content_length=100, etag="x", last_modified="y",
            ),
        )

        # Verify both handlers pass auth and get to business logic
        with mock_auth, vu_mock_head:
            # verify-upload with same code should succeed
            vu_event = _make_event({
                "code": "wx_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 100,
            })
            vu_resp = vu_handler(vu_event, {})
            assert vu_resp["statusCode"] == 200
            vu_body = json.loads(vu_resp["body"])
            assert vu_body["verified"] is True

        # issue-credential with different allowlist would fail
        os.environ["OPENID_ALLOWLIST"] = "different_user"

        ic_sts_mock = mock.patch(
            "shared.sts._call_assume_role",
            return_value={
                "access_key_id": "tmp_ak",
                "access_key_secret": "tmp_sk",
                "security_token": "tmp_token",
                "expiration": "2026-01-01T00:15:00Z",
            },
        )
        mock_auth_ic = mock.patch(
            "shared.auth._code_to_openid", return_value="different_user"
        )

        with mock_auth_ic, ic_sts_mock:
            ic_event = _make_event({
                "code": "wx_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "size": 1000,
            })
            ic_resp = ic_handler(ic_event, {})
            assert ic_resp["statusCode"] == 200

        # With mismatched allowlist, verify-upload fails
        with mock.patch(
            "shared.auth._code_to_openid", return_value="wrong_user"
        ):
            vu_event = _make_event({
                "code": "wx_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 100,
            })
            vu_resp = vu_handler(vu_event, {})
            assert vu_resp["statusCode"] == 403
            vu_body = json.loads(vu_resp["body"])
            assert vu_body["error"] == "OPENID_NOT_ALLOWED"

    def test_no_response_body_leaks_ak_secret(self) -> None:
        """AC: Response bodies don't contain AK Secret or security_token."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from shared.oss import HeadObjectResult
        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=True,
                content_length=100,
                etag="xyz",
                last_modified="Thu, 01 Jan 2026 00:00:00 GMT",
            ),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 100,
            })
            resp = vu_handler(event, {})

        body_str = json.dumps(resp)
        assert "secret-test" not in body_str
        assert "security_token" not in body_str.lower()
        assert "ak-test" not in body_str

    def test_handler_imports_are_importable(self) -> None:
        """AC: handler module imports succeed."""
        from verify_upload.handler import handler, _handle
        assert callable(handler)
        assert callable(_handle)

    def test_shared_oss_exported_from_init(self) -> None:
        """AC: shared.__init__ exports HeadObjectResult and head_object."""
        from shared import HeadObjectResult, head_object
        assert HeadObjectResult is not None
        assert callable(head_object)

    def test_deploy_fc_supports_verify_upload(self) -> None:
        """AC: deploy_fc.py lists verify-upload as a deployable function."""
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from deploy_fc import ALL_FUNCTIONS, FUNCTION_DIR_MAP

        assert "verify-upload" in ALL_FUNCTIONS
        assert FUNCTION_DIR_MAP["verify-upload"] == "verify_upload"

    def test_fragment_oss_key_for_various_dates(self) -> None:
        """AC: head_object is called with correct object_key derived by _fragment_oss_key."""
        from shared.sts import _fragment_oss_key

        # Verify _fragment_oss_key is imported and usable in handler
        fid = "20260601T120000_abcd_01HZX3K8MN5PQR9TFB7AYWVCDE"
        key = _fragment_oss_key(fid)
        assert key == "recordings/2026-06-01/20260601T120000_abcd_01HZX3K8MN5PQR9TFB7AYWVCDE.wav"

    def test_size_zero_is_valid(self) -> None:
        """Edge case: expected_size=0 should work for empty files."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from shared.oss import HeadObjectResult
        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=True,
                content_length=0,
                etag="d41d8cd98f00b204e9800998ecf8427e",
                last_modified="Thu, 01 Jan 2026 00:00:00 GMT",
            ),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid_code",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 0,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["verified"] is True
        assert body["size"] == 0


# ---------------------------------------------------------------------------
# Integration-style tests: handler + safe_handler path
# ---------------------------------------------------------------------------


class TestVerifyUploadIntegration:
    """Full request → response integration tests with mocked dependencies."""

    def test_full_flow_verified_true(self) -> None:
        """End-to-end mock: valid code, allowlist pass, object exists, size matches."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from shared.oss import HeadObjectResult
        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=True,
                content_length=54321,
                etag="etag_value",
                last_modified="Thu, 01 Jan 2026 00:00:00 GMT",
            ),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 54321,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body == {
            "verified": True,
            "etag": "etag_value",
            "size": 54321,
            "last_modified": "Thu, 01 Jan 2026 00:00:00 GMT",
        }

    def test_full_flow_not_found(self) -> None:
        """End-to-end mock: object not found."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from shared.oss import HeadObjectResult
        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=False, content_length=None, etag=None, last_modified=None,
            ),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 54321,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body == {"verified": False, "reason": "OBJECT_NOT_FOUND"}

    def test_full_flow_size_mismatch(self) -> None:
        """End-to-end mock: object exists but wrong size."""
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "openid_test_user"

        from shared.oss import HeadObjectResult
        from verify_upload.handler import handler as vu_handler

        mock_auth = mock.patch(
            "shared.auth._code_to_openid", return_value="openid_test_user"
        )
        mock_head = mock.patch(
            "verify_upload.handler.head_object",
            return_value=HeadObjectResult(
                found=True,
                content_length=999,
                etag="etag_val",
                last_modified="Thu, 01 Jan 2026 00:00:00 GMT",
            ),
        )

        with mock_auth, mock_head:
            event = _make_event({
                "code": "valid",
                "fragment_id": "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",
                "expected_size": 54321,
            })
            resp = vu_handler(event, {})

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body == {
            "verified": False,
            "reason": "SIZE_MISMATCH",
            "actual_size": 999,
        }

    def test_json_parse_error(self) -> None:
        """AC: Invalid JSON returns 400 INVALID_JSON."""
        _set_required_env()

        from verify_upload.handler import handler as vu_handler

        event = {"httpMethod": "POST", "path": "/", "body": "not-json"}
        resp = vu_handler(event, {})

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_JSON"

    def test_empty_body(self) -> None:
        """AC: Empty body returns 400."""
        _set_required_env()

        from verify_upload.handler import handler as vu_handler

        event = {"httpMethod": "POST", "path": "/", "body": ""}
        resp = vu_handler(event, {})

        assert resp["statusCode"] == 400
