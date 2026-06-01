"""Tests for US-007 — FC issue-credential STS single-file credential issuance."""

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


# ---------------------------------------------------------------------------
# fragment_id → OSS key derivation
# ---------------------------------------------------------------------------


class TestFragmentOssKey:
    """AC: fragment_id generates object_key as recordings/<YYYY-MM-DD>/<fragment_id>.wav"""

    def test_valid_fragment_id_derives_correct_key(self) -> None:
        from shared.sts import _fragment_oss_key

        fid = "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE"
        key = _fragment_oss_key(fid)
        assert key == f"recordings/2026-05-26/{fid}.wav"

    def test_another_date(self) -> None:
        from shared.sts import _fragment_oss_key

        fid = "20251201T000000_abc_01HZX3K8MN5PQR9TFB7AYWVCDE"
        key = _fragment_oss_key(fid)
        assert key == f"recordings/2025-12-01/{fid}.wav"

    def test_no_t_separator_raises(self) -> None:
        from shared.sts import _fragment_oss_key

        with pytest.raises(ValueError, match="no 'T' separator"):
            _fragment_oss_key("20260526144800_dev01_ulid")

    def test_short_date_raises(self) -> None:
        from shared.sts import _fragment_oss_key

        with pytest.raises(ValueError, match="date portion"):
            _fragment_oss_key("2026T144800_dev01_ulid")


# ---------------------------------------------------------------------------
# STS policy construction
# ---------------------------------------------------------------------------


class TestBuildStsPolicy:
    """AC: STS policy Resource is exact (no wildcards)."""

    def test_policy_resource_is_exact_single_key(self) -> None:
        from shared.sts import _build_sts_policy

        policy = _build_sts_policy("recordings/2026-05-26/test.wav", "soniscope-audio")
        statements = policy["Statement"]
        assert len(statements) == 1
        resources = statements[0]["Resource"]
        assert len(resources) == 1
        assert resources[0] == "acs:oss:*:*:soniscope-audio/recordings/2026-05-26/test.wav"

    def test_policy_no_wildcard(self) -> None:
        from shared.sts import _build_sts_policy

        policy = _build_sts_policy("recordings/2026-05-26/test.wav", "my-bucket")
        resource = policy["Statement"][0]["Resource"][0]
        assert "recordings/*" not in resource
        assert resource.endswith(".wav")

    def test_policy_allows_only_put_object(self) -> None:
        from shared.sts import _build_sts_policy

        policy = _build_sts_policy("recordings/2026-05-26/test.wav", "b")
        actions = policy["Statement"][0]["Action"]
        assert actions == ["oss:PutObject"]


# ---------------------------------------------------------------------------
# Size check
# ---------------------------------------------------------------------------


class TestSizeCheck:
    """AC: size > MAX_UPLOAD_BYTES returns 400 SIZE_EXCEEDED."""

    def test_size_exceeded_default_limit(self) -> None:
        _set_required_env()
        from shared.sts import issue_sts_credential
        from shared.auth import AuthError

        with pytest.raises(AuthError) as exc_info:
            issue_sts_credential("20260526T144800_dev01_ulid12345678901234567890123456", 60_000_000)

        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "SIZE_EXCEEDED"
        assert "limit_bytes" in exc_info.value.extra
        assert "actual_bytes" in exc_info.value.extra
        assert exc_info.value.extra["limit_bytes"] == 52428800
        assert exc_info.value.extra["actual_bytes"] == 60000000

    def test_size_within_limit(self) -> None:
        _set_required_env()
        from shared.sts import issue_sts_credential

        with mock.patch("shared.sts._call_assume_role") as mock_call:
            mock_call.return_value = {
                "access_key_id": "ak",
                "access_key_secret": "as",
                "security_token": "st",
                "expiration": "2026-01-01T00:00:00Z",
            }
            result = issue_sts_credential(
                "20260526T144800_dev01_ulid12345678901234567890123456",
                10_000_000,  # 10 MB
            )
            assert mock_call.called

    def test_custom_max_upload_bytes(self) -> None:
        _set_required_env()
        os.environ["MAX_UPLOAD_BYTES"] = "1000"
        from shared.sts import issue_sts_credential
        from shared.auth import AuthError

        with pytest.raises(AuthError) as exc_info:
            issue_sts_credential("20260526T144800_dev01_ulid12345678901234567890123456", 2000)

        assert exc_info.value.extra["limit_bytes"] == 1000
        assert exc_info.value.extra["actual_bytes"] == 2000

    def test_size_at_boundary(self) -> None:
        _set_required_env()
        from shared.sts import issue_sts_credential

        with mock.patch("shared.sts._call_assume_role") as mock_call:
            mock_call.return_value = {
                "access_key_id": "ak",
                "access_key_secret": "as",
                "security_token": "st",
                "expiration": "2026-01-01T00:00:00Z",
            }
            # Exactly at default limit
            result = issue_sts_credential(
                "20260526T144800_dev01_ulid12345678901234567890123456",
                52_428_800,
            )
            assert mock_call.called


# ---------------------------------------------------------------------------
# STS credential issuance (mocked)
# ---------------------------------------------------------------------------


class TestIssueStsCredential:
    """AC: successful STS response contains all required fields."""

    STS_RESPONSE = {
        "access_key_id": "STS.test-ak",
        "access_key_secret": "STS.test-as",
        "security_token": "STS.test-token",
        "expiration": "2026-05-26T15:03:00Z",
    }

    def test_success_response_has_all_fields(self) -> None:
        _set_required_env()
        from shared.sts import issue_sts_credential

        with mock.patch("shared.sts._call_assume_role") as mock_call:
            mock_call.return_value = self.STS_RESPONSE
            result = issue_sts_credential(
                "20260526T144800_dev01_ulid12345678901234567890123456",
                500_000,
            )

        assert result["access_key_id"] == "STS.test-ak"
        assert result["access_key_secret"] == "STS.test-as"
        assert result["security_token"] == "STS.test-token"
        assert result["expiration"] == "2026-05-26T15:03:00Z"
        assert result["bucket"] == "soniscope-audio"
        assert result["endpoint"] == "oss-cn-beijing.aliyuncs.com"
        assert "object_key" in result
        assert result["object_key"].startswith("recordings/")
        assert result["object_key"].endswith(".wav")

    def test_sts_call_uses_correct_object_key(self) -> None:
        _set_required_env()
        from shared.sts import issue_sts_credential

        with mock.patch("shared.sts._call_assume_role") as mock_call:
            mock_call.return_value = self.STS_RESPONSE
            fid = "20260526T144800_dev01_ulid12345678901234567890123456"
            issue_sts_credential(fid, 100)

        expected_key = f"recordings/2026-05-26/{fid}.wav"
        mock_call.assert_called_once()
        assert mock_call.call_args[0][0] == expected_key  # first positional arg

    def test_sts_duration_at_most_900_seconds(self) -> None:
        from shared.sts import STS_MAX_DURATION_SECONDS
        assert STS_MAX_DURATION_SECONDS <= 900


# ---------------------------------------------------------------------------
# Handler integration (mock auth + STS)
# ---------------------------------------------------------------------------


class TestHandlerIntegration:
    """AC: handler returns 200 with STS or appropriate error codes."""

    def _mock_openid(self, openid: str = "test-openid-allowed"):
        """Patch _code_to_openid so auth always succeeds."""
        return mock.patch(
            "shared.auth._code_to_openid",
            return_value=openid,
        )

    def _mock_sts(self):
        """Patch _call_assume_role to return a valid STS."""
        return mock.patch("shared.sts._call_assume_role", return_value={
            "access_key_id": "STS.ak",
            "access_key_secret": "STS.as",
            "security_token": "STS.tok",
            "expiration": "2026-06-01T00:00:00Z",
        })

    def test_200_with_complete_sts_response(self) -> None:
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "test-openid-allowed"
        from issue_credential.handler import handler

        with self._mock_openid(), self._mock_sts():
            event = {
                "httpMethod": "POST",
                "path": "/issue-credential",
                "body": json.dumps({
                    "code": "test-code",
                    "fragment_id": "20260526T144800_dev01_ulid12345678901234567890123456",
                    "size": 500000,
                }),
            }
            resp = handler(event, None)

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["access_key_id"] == "STS.ak"
        assert body["access_key_secret"] == "STS.as"
        assert body["security_token"] == "STS.tok"
        assert body["bucket"] == "soniscope-audio"
        assert body["endpoint"] == "oss-cn-beijing.aliyuncs.com"
        assert "object_key" in body
        assert body["object_key"].startswith("recordings/")

    def test_400_size_exceeded(self) -> None:
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "test-openid-allowed"
        from issue_credential.handler import handler

        with self._mock_openid():
            event = {
                "httpMethod": "POST",
                "path": "/issue-credential",
                "body": json.dumps({
                    "code": "test-code",
                    "fragment_id": "20260526T144800_dev01_ulid12345678901234567890123456",
                    "size": 999999999,
                }),
            }
            resp = handler(event, None)

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "SIZE_EXCEEDED"
        assert "limit_bytes" in body
        assert "actual_bytes" in body

    def test_400_size_not_integer(self) -> None:
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "test-openid-allowed"
        from issue_credential.handler import handler

        with self._mock_openid():
            event = {
                "httpMethod": "POST",
                "path": "/issue-credential",
                "body": json.dumps({
                    "code": "test-code",
                    "fragment_id": "20260526T144800_dev01_ulid12345678901234567890123456",
                    "size": "not-a-number",
                }),
            }
            resp = handler(event, None)

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_SIZE"

    def test_400_negative_size(self) -> None:
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "test-openid-allowed"
        from issue_credential.handler import handler

        with self._mock_openid():
            event = {
                "httpMethod": "POST",
                "path": "/issue-credential",
                "body": json.dumps({
                    "code": "test-code",
                    "fragment_id": "20260526T144800_dev01_ulid12345678901234567890123456",
                    "size": -1,
                }),
            }
            resp = handler(event, None)

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_SIZE"

    def test_401_invalid_code_no_sts_leaked(self) -> None:
        _set_required_env()
        from issue_credential.handler import handler

        event = {
            "httpMethod": "POST",
            "path": "/issue-credential",
            "body": json.dumps({
                "code": "fake-code",
                "fragment_id": "20260526T144800_dev01_ulid12345678901234567890123456",
                "size": 100,
            }),
        }

        with mock.patch("shared.auth._code_to_openid") as mock_wechat:
            from shared.auth import AuthError
            from shared.errors import ERROR_INVALID_CODE
            mock_wechat.side_effect = AuthError(401, ERROR_INVALID_CODE, "WeChat error")
            resp = handler(event, None)

        assert resp["statusCode"] == 401
        body = json.loads(resp["body"])
        assert body["error"] == "INVALID_CODE"
        assert "access_key_id" not in body
        assert "security_token" not in body

    def test_403_not_in_allowlist_no_sts_leaked(self) -> None:
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "different-openid"
        from issue_credential.handler import handler

        with self._mock_openid("unauthorized-openid"):
            event = {
                "httpMethod": "POST",
                "path": "/issue-credential",
                "body": json.dumps({
                    "code": "test-code",
                    "fragment_id": "20260526T144800_dev01_ulid12345678901234567890123456",
                    "size": 100,
                }),
            }
            resp = handler(event, None)

        assert resp["statusCode"] == 403
        body = json.loads(resp["body"])
        assert body["error"] == "OPENID_NOT_ALLOWED"
        assert "access_key_id" not in body
        assert "security_token" not in body

    def test_400_missing_fields(self) -> None:
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "x"
        from issue_credential.handler import handler

        with self._mock_openid():
            # Missing size field
            event = {
                "httpMethod": "POST",
                "path": "/issue-credential",
                "body": json.dumps({
                    "code": "test-code",
                    "fragment_id": "20260526T144800_dev01_ulid12345678901234567890123456",
                }),
            }
            resp = handler(event, None)

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "MISSING_FIELD"

    def test_502_sts_backend_failure(self) -> None:
        _set_required_env()
        os.environ["OPENID_ALLOWLIST"] = "test-openid-allowed"
        from issue_credential.handler import handler

        with self._mock_openid(), mock.patch(
            "shared.sts._call_assume_role",
            side_effect=RuntimeError("STS backend down"),
        ):
            event = {
                "httpMethod": "POST",
                "path": "/issue-credential",
                "body": json.dumps({
                    "code": "test-code",
                    "fragment_id": "20260526T144800_dev01_ulid12345678901234567890123456",
                    "size": 100,
                }),
            }
            resp = handler(event, None)

        assert resp["statusCode"] == 502
        body = json.loads(resp["body"])
        assert body["error"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# AuthError with extra fields (for SIZE_EXCEEDED)
# ---------------------------------------------------------------------------


class TestAuthErrorExtra:
    """Verify AuthError.extra is serialised into the response body."""

    def test_extra_fields_in_response(self) -> None:
        from shared.auth import AuthError, auth_error_to_response

        exc = AuthError(
            400,
            "SIZE_EXCEEDED",
            detail="too large",
            extra={"limit_bytes": 100, "actual_bytes": 999},
        )
        resp = auth_error_to_response(exc)
        body = json.loads(resp["body"])
        assert body["error"] == "SIZE_EXCEEDED"
        assert body["limit_bytes"] == 100
        assert body["actual_bytes"] == 999


# ---------------------------------------------------------------------------
# Shared config: RAM_ROLE_ARN and ALIYUN_AK_* added
# ---------------------------------------------------------------------------


class TestSharedConfigExtended:
    """AC: config reads RAM_ROLE_ARN, ALIYUN_AK_ID, ALIYUN_AK_SECRET."""

    def test_existing_tests_still_work_with_new_vars(self) -> None:
        """Verify that SharedConfig still works; new vars raise on missing."""
        from shared.config import _ConfigError, read_shared_config

        # None of the new vars are set → 8 total missing (5 old + 3 new)
        with pytest.raises(_ConfigError) as exc_info:
            read_shared_config()
        assert len(exc_info.value.missing) == 8

    def test_all_vars_present_returns_full_config(self) -> None:
        _set_required_env()
        from shared.config import read_shared_config

        cfg = read_shared_config()
        assert cfg.oss_bucket == "soniscope-audio"
        assert cfg.ram_role_arn == "acs:ram::123:role/test-role"
        assert cfg.aliyun_ak_id == "ak-test"
        assert cfg.aliyun_ak_secret == "secret-test"


# ---------------------------------------------------------------------------
# STS AssumeRole signing (hmac-sha1 construction)
# ---------------------------------------------------------------------------


class TestStsAssumeRoleCall:
    """Verify the STS API call construction is correct."""

    def test_assume_role_url_contains_required_params(self) -> None:
        _set_required_env()
        from shared.sts import _call_assume_role
        from shared.config import read_shared_config

        cfg = read_shared_config()

        with mock.patch("shared.sts.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "deadbeefcafe0000deadbeefcafe0000"
            with mock.patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__.return_value = mock.Mock()
                mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
                    "Credentials": {
                        "AccessKeyId": "ak",
                        "AccessKeySecret": "as",
                        "SecurityToken": "st",
                        "Expiration": "2026-01-01T00:00:00Z",
                    },
                }).encode()

                _call_assume_role("recordings/2026-05-26/test.wav", cfg)

        call_args = mock_urlopen.call_args[0][0]
        url = call_args.full_url if hasattr(call_args, "full_url") else str(call_args)
        assert "Action=AssumeRole" in url
        assert "RoleArn=acs%3Aram%3A%3A123%3Arole%2Ftest-role" in url
        assert "DurationSeconds=900" in url
        assert "SignatureMethod=HMAC-SHA1" in url
        assert "SignatureVersion=1.0" in url
        assert "Policy=" in url
        assert "SignatureNonce=deadbeef" in url
        assert "Signature=" in url

    def test_assume_role_uses_single_file_policy(self) -> None:
        _set_required_env()
        from shared.sts import _call_assume_role
        from shared.config import read_shared_config

        cfg = read_shared_config()

        with mock.patch("shared.sts.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "abcd1234abcd1234abcd1234abcd1234"
            with mock.patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__.return_value = mock.Mock()
                mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
                    "Credentials": {
                        "AccessKeyId": "ak",
                        "AccessKeySecret": "as",
                        "SecurityToken": "st",
                        "Expiration": "2026-01-01T00:00:00Z",
                    },
                }).encode()

                _call_assume_role("recordings/2026-05-26/test.wav", cfg)

        url = mock_urlopen.call_args[0][0].full_url
        # The Policy param in the URL should contain the exact single-key resource
        from urllib.parse import unquote
        decoded = unquote(url)
        assert 'acs:oss:*:*:soniscope-audio/recordings/2026-05-26/test.wav' in decoded
        assert 'oss:PutObject' in decoded
        # Must NOT contain a wildcard
        assert 'recordings/*' not in decoded


# ---------------------------------------------------------------------------
# Deploy packaging: shared/sts.py included
# ---------------------------------------------------------------------------


class TestDeployPackaging:
    """AC: shared/sts.py is collected when packaging FC functions."""

    def test_sts_py_exists_in_shared(self) -> None:
        path = FC_ROOT / "shared" / "sts.py"
        assert path.is_file(), f"expected {path} to exist"

    def test_deploy_collects_sts_module(self) -> None:
        import sys
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from deploy_fc import _package_function

        # Just verify packaging doesn't crash
        try:
            zip_path = _package_function("issue-credential")
            assert zip_path.exists()  # type: ignore[union-attr]
            import zipfile
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                assert "handler.py" in names
                assert "shared/sts.py" in names or any(
                    n.endswith("sts.py") and "shared" in n for n in names
                )
        finally:
            sys.path.remove(str(REPO_ROOT / "scripts"))
