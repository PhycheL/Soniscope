"""Tests for verify-prep diagnostics."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any


class _FakeCredentials:
    class StaticCredentialsProvider:
        def __init__(self, *, access_key_id: str, access_key_secret: str) -> None:
            self.access_key_id = access_key_id
            self.access_key_secret = access_key_secret


class _FakeOssConfigModule:
    @staticmethod
    def load_default() -> types.SimpleNamespace:
        return types.SimpleNamespace()


class _FakeGetObjectRequest:
    def __init__(self, *, bucket: str, key: str) -> None:
        self.bucket = bucket
        self.key = key


class _FakeHeadObjectRequest:
    def __init__(self, *, bucket: str, key: str) -> None:
        self.bucket = bucket
        self.key = key


class _FakeListObjectsRequest:
    def __init__(self, *, bucket: str, prefix: str, max_keys: int) -> None:
        self.bucket = bucket
        self.prefix = prefix
        self.max_keys = max_keys


class _FakeOssClient:
    instances: list["_FakeOssClient"] = []

    def __init__(self, _config: object) -> None:
        self.presign_calls: list[tuple[object, dict[str, Any]]] = []
        _FakeOssClient.instances.append(self)

    def presign(self, request: object, **kwargs: Any) -> types.SimpleNamespace:
        self.presign_calls.append((request, kwargs))
        return types.SimpleNamespace(url="https://signed.example/sample/sample-20s.wav?Expires=1")


class _FakeRuntimeOssClient:
    instances: list["_FakeRuntimeOssClient"] = []

    def __init__(self, _config: object) -> None:
        self.calls: list[tuple[str, object]] = []
        _FakeRuntimeOssClient.instances.append(self)

    def list_objects(self, request: object) -> types.SimpleNamespace:
        self.calls.append(("list_objects", request))
        return types.SimpleNamespace()

    def head_object(self, request: object) -> types.SimpleNamespace:
        self.calls.append(("head_object", request))
        return types.SimpleNamespace(content_length=1234)

    def get_object(self, request: object) -> types.SimpleNamespace:
        self.calls.append(("get_object", request))
        return types.SimpleNamespace(body=types.SimpleNamespace(read=lambda: b"RIFF"))

    def get_bucket_info(self, _request: object) -> object:
        raise AssertionError("A block must not call GetBucketInfo")

    def get_bucket_acl(self, _request: object) -> object:
        raise AssertionError("A block must not call GetBucketAcl")


class _FakeMissingSampleOssClient(_FakeRuntimeOssClient):
    instances: list["_FakeMissingSampleOssClient"] = []

    def __init__(self, _config: object) -> None:
        self.calls: list[tuple[str, object]] = []
        _FakeMissingSampleOssClient.instances.append(self)

    def head_object(self, request: object) -> types.SimpleNamespace:
        self.calls.append(("head_object", request))
        raise RuntimeError("NoSuchKey: sample/sample-20s.wav")


class _FakeCommonRequest:
    instances: list["_FakeCommonRequest"] = []

    def __init__(self) -> None:
        self.body_params: dict[str, str] = {}
        self.query_params: dict[str, str] = {}
        _FakeCommonRequest.instances.append(self)

    def set_domain(self, domain: str) -> None:
        self.domain = domain

    def set_version(self, version: str) -> None:
        self.version = version

    def set_product(self, product: str) -> None:
        self.product = product

    def set_action_name(self, action_name: str) -> None:
        self.action_name = action_name

    def set_method(self, method: str) -> None:
        self.method = method

    def add_body_params(self, key: str, value: str) -> None:
        self.body_params[key] = value

    def add_query_param(self, key: str, value: str) -> None:
        self.query_params[key] = value


class _FakeAcsClient:
    instances: list["_FakeAcsClient"] = []

    def __init__(self, _ak_id: str, _ak_secret: str, region: str) -> None:
        self.region = region
        self.responses = iter(
            [
                {"StatusText": "SUCCESS", "TaskId": "task-001"},
                {"StatusText": "SUCCESS", "Result": {"Sentences": [{"Text": "你好"}]}},
            ]
        )
        _FakeAcsClient.instances.append(self)

    def do_action_with_exception(self, _request: object) -> bytes:
        return json.dumps(next(self.responses)).encode("utf-8")


class _FakeAssumeRoleRequest:
    instances: list["_FakeAssumeRoleRequest"] = []

    def __init__(self) -> None:
        self.params: dict[str, Any] = {}
        _FakeAssumeRoleRequest.instances.append(self)

    def set_RoleArn(self, value: str) -> None:
        self.params["RoleArn"] = value

    def set_RoleSessionName(self, value: str) -> None:
        self.params["RoleSessionName"] = value

    def set_DurationSeconds(self, value: int) -> None:
        self.params["DurationSeconds"] = value

    def set_Policy(self, value: str) -> None:
        self.params["Policy"] = value

    def set_accept_format(self, value: str) -> None:
        self.params["accept_format"] = value


class _FakeStsAcsClient:
    instances: list["_FakeStsAcsClient"] = []

    def __init__(self, ak_id: str, ak_secret: str, region: str) -> None:
        self.ak_id = ak_id
        self.ak_secret = ak_secret
        self.region = region
        _FakeStsAcsClient.instances.append(self)

    def do_action_with_exception(self, _request: object) -> bytes:
        return json.dumps(
            {
                "Credentials": {
                    "AccessKeyId": "STS_ACCESS_KEY_ID",
                    "AccessKeySecret": "STS_ACCESS_KEY_SECRET",
                    "SecurityToken": "STS_SECURITY_TOKEN",
                    "Expiration": "2026-01-01T00:15:00Z",
                }
            }
        ).encode("utf-8")


class _FakeFailingStsAcsClient(_FakeStsAcsClient):
    instances: list["_FakeFailingStsAcsClient"] = []

    def __init__(self, ak_id: str, ak_secret: str, region: str) -> None:
        self.ak_id = ak_id
        self.ak_secret = ak_secret
        self.region = region
        _FakeFailingStsAcsClient.instances.append(self)

    def do_action_with_exception(self, _request: object) -> bytes:
        raise RuntimeError(
            "Error Code: NoPermission. Request Id: req-123. "
            "AccessKeySecret=DEPLOY_SECRET_SHOULD_NOT_LEAK SecurityToken=TOKEN_SHOULD_NOT_LEAK"
        )


def test_check_block_e_uses_oss_v2_presign_and_submits_file_link(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """E block should use OSS v2 presign and pass the signed URL to NLS."""
    from soniscope_worker import verify_prep

    _FakeOssClient.instances.clear()
    _FakeCommonRequest.instances.clear()
    _FakeAcsClient.instances.clear()

    fake_oss_module = types.SimpleNamespace(
        credentials=_FakeCredentials,
        config=_FakeOssConfigModule,
        Client=_FakeOssClient,
        GetObjectRequest=_FakeGetObjectRequest,
    )
    fake_client_module = types.SimpleNamespace(AcsClient=_FakeAcsClient)
    fake_request_module = types.SimpleNamespace(CommonRequest=_FakeCommonRequest)

    monkeypatch.setitem(sys.modules, "alibabacloud_oss_v2", fake_oss_module)
    monkeypatch.setitem(sys.modules, "aliyunsdkcore.client", fake_client_module)
    monkeypatch.setitem(sys.modules, "aliyunsdkcore.request", fake_request_module)
    monkeypatch.setattr(verify_prep.time, "sleep", lambda _seconds: None)

    repo_root = tmp_path
    sample = repo_root / "tests" / "audio" / "sample-20s.wav"
    sample.parent.mkdir(parents=True)
    sample.write_bytes(b"RIFF fake wav")
    monkeypatch.setattr(verify_prep, "_get_repo_root", lambda: repo_root)

    cfg = {
        "transcriber": {
            "appkey": "app-key",
            "access_key_id": "nls-ak",
            "access_key_secret": "nls-secret",
            "api_endpoint": "cn-beijing",
        },
        "oss": {
            "access_key_id": "oss-ak",
            "access_key_secret": "oss-secret",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "bucket": "soniscope-audio",
        },
    }

    result = verify_prep.check_block_e(cfg)

    assert result.passed
    oss_client = _FakeOssClient.instances[0]
    request, presign_kwargs = oss_client.presign_calls[0]
    assert isinstance(request, _FakeGetObjectRequest)
    assert request.bucket == "soniscope-audio"
    assert request.key == "sample/sample-20s.wav"
    assert "expires" in presign_kwargs

    submit_request = _FakeCommonRequest.instances[0]
    task = json.loads(submit_request.body_params["Task"])
    assert task["file_link"] == "https://signed.example/sample/sample-20s.wav?Expires=1"


def test_check_block_e_accepts_full_nls_pop_endpoint(monkeypatch: Any, tmp_path: Path) -> None:
    """E block should not prepend filetrans.* to an already complete endpoint."""
    from soniscope_worker import verify_prep

    _FakeOssClient.instances.clear()
    _FakeCommonRequest.instances.clear()
    _FakeAcsClient.instances.clear()

    fake_oss_module = types.SimpleNamespace(
        credentials=_FakeCredentials,
        config=_FakeOssConfigModule,
        Client=_FakeOssClient,
        GetObjectRequest=_FakeGetObjectRequest,
    )
    fake_client_module = types.SimpleNamespace(AcsClient=_FakeAcsClient)
    fake_request_module = types.SimpleNamespace(CommonRequest=_FakeCommonRequest)

    monkeypatch.setitem(sys.modules, "alibabacloud_oss_v2", fake_oss_module)
    monkeypatch.setitem(sys.modules, "aliyunsdkcore.client", fake_client_module)
    monkeypatch.setitem(sys.modules, "aliyunsdkcore.request", fake_request_module)
    monkeypatch.setattr(verify_prep.time, "sleep", lambda _seconds: None)

    repo_root = tmp_path
    sample = repo_root / "tests" / "audio" / "sample-20s.wav"
    sample.parent.mkdir(parents=True)
    sample.write_bytes(b"RIFF fake wav")
    monkeypatch.setattr(verify_prep, "_get_repo_root", lambda: repo_root)

    cfg = {
        "transcriber": {
            "appkey": "app-key",
            "access_key_id": "nls-ak",
            "access_key_secret": "nls-secret",
            "api_endpoint": "filetrans.cn-beijing.aliyuncs.com",
        },
        "oss": {
            "access_key_id": "oss-ak",
            "access_key_secret": "oss-secret",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "bucket": "soniscope-audio",
        },
    }

    result = verify_prep.check_block_e(cfg)

    assert result.passed
    submit_request = _FakeCommonRequest.instances[0]
    assert submit_request.domain == "filetrans.cn-beijing.aliyuncs.com"
    assert _FakeAcsClient.instances[0].region == "cn-beijing"


def test_check_block_a_uses_worker_runtime_oss_operations(monkeypatch: Any) -> None:
    """A block should verify Worker runtime access without bucket-level APIs."""
    from soniscope_worker import verify_prep

    _FakeRuntimeOssClient.instances.clear()

    fake_oss_module = types.SimpleNamespace(
        credentials=_FakeCredentials,
        config=_FakeOssConfigModule,
        Client=_FakeRuntimeOssClient,
        ListObjectsRequest=_FakeListObjectsRequest,
        HeadObjectRequest=_FakeHeadObjectRequest,
        GetObjectRequest=_FakeGetObjectRequest,
    )
    monkeypatch.setitem(sys.modules, "alibabacloud_oss_v2", fake_oss_module)

    cfg = {
        "oss": {
            "access_key_id": "reader-ak",
            "access_key_secret": "reader-secret",
            "endpoint": "oss-cn-beijing.aliyuncs.com",
            "bucket": "soniscope-audio",
        }
    }

    result = verify_prep.check_block_a(cfg)

    assert result.passed
    client = _FakeRuntimeOssClient.instances[0]
    assert [name for name, _request in client.calls] == [
        "list_objects",
        "head_object",
        "get_object",
    ]
    list_request = client.calls[0][1]
    assert isinstance(list_request, _FakeListObjectsRequest)
    assert list_request.bucket == "soniscope-audio"
    assert list_request.max_keys == 1
    head_request = client.calls[1][1]
    get_request = client.calls[2][1]
    assert isinstance(head_request, _FakeHeadObjectRequest)
    assert isinstance(get_request, _FakeGetObjectRequest)
    assert head_request.key == "sample/sample-20s.wav"
    assert get_request.key == "sample/sample-20s.wav"


def test_check_block_a_config_mismatch_fails_before_cloud(monkeypatch: Any) -> None:
    """A block should report config mismatches and avoid cloud calls."""
    from soniscope_worker import verify_prep

    _FakeRuntimeOssClient.instances.clear()
    fake_oss_module = types.SimpleNamespace(
        credentials=_FakeCredentials,
        config=_FakeOssConfigModule,
        Client=_FakeRuntimeOssClient,
        ListObjectsRequest=_FakeListObjectsRequest,
        HeadObjectRequest=_FakeHeadObjectRequest,
        GetObjectRequest=_FakeGetObjectRequest,
    )
    monkeypatch.setitem(sys.modules, "alibabacloud_oss_v2", fake_oss_module)

    result = verify_prep.check_block_a(
        {
            "oss": {
                "access_key_id": "reader-ak",
                "access_key_secret": "reader-secret",
                "endpoint": "oss-cn-shanghai.aliyuncs.com",
                "bucket": "wrong-bucket",
            }
        }
    )

    assert not result.passed
    detail = "\n".join(check.detail for check in result.checks)
    assert "wrong-bucket" in detail
    assert "soniscope-audio" in detail
    assert "oss-cn-shanghai.aliyuncs.com" in detail
    assert "oss-cn-beijing.aliyuncs.com" in detail
    assert not _FakeRuntimeOssClient.instances


def test_check_block_a_missing_sample_points_to_fixture_not_acl(monkeypatch: Any) -> None:
    """Missing sample object should not suggest widening bucket ACL permissions."""
    from soniscope_worker import verify_prep

    _FakeMissingSampleOssClient.instances.clear()
    fake_oss_module = types.SimpleNamespace(
        credentials=_FakeCredentials,
        config=_FakeOssConfigModule,
        Client=_FakeMissingSampleOssClient,
        ListObjectsRequest=_FakeListObjectsRequest,
        HeadObjectRequest=_FakeHeadObjectRequest,
        GetObjectRequest=_FakeGetObjectRequest,
    )
    monkeypatch.setitem(sys.modules, "alibabacloud_oss_v2", fake_oss_module)

    result = verify_prep.check_block_a(
        {
            "oss": {
                "access_key_id": "reader-ak",
                "access_key_secret": "reader-secret",
                "endpoint": "oss-cn-beijing.aliyuncs.com",
                "bucket": "soniscope-audio",
            }
        }
    )

    assert not result.passed
    hints = "\n".join(check.fix_hint for check in result.checks)
    assert "fixture" in hints or "sample" in hints
    assert "GetBucketAcl" not in hints
    assert "ACL" not in hints


def test_get_sts_credentials_uses_region_not_oss_endpoint(monkeypatch: Any) -> None:
    """STS SDK region must be cn-beijing, not the OSS endpoint string."""
    from soniscope_worker import verify_prep

    _FakeStsAcsClient.instances.clear()
    _FakeAssumeRoleRequest.instances.clear()

    fake_client_module = types.SimpleNamespace(AcsClient=_FakeStsAcsClient)
    fake_request_module = types.SimpleNamespace(
        AssumeRoleRequest=types.SimpleNamespace(AssumeRoleRequest=_FakeAssumeRoleRequest)
    )
    monkeypatch.setitem(sys.modules, "aliyunsdkcore.client", fake_client_module)
    monkeypatch.setitem(sys.modules, "aliyunsdksts.request.v20150401", fake_request_module)

    result = verify_prep._get_sts_credentials(
        "deploy-ak",
        "deploy-secret",
        "acs:ram::1633875501759333:role/soniscope-uploader-role",
        "recordings/2026-01-01/test.wav",
    )

    assert result is not None
    assert _FakeStsAcsClient.instances[0].region == "cn-beijing"


def test_get_sts_credentials_returns_sanitized_error(monkeypatch: Any) -> None:
    """STS failures should preserve useful detail without leaking secrets."""
    from soniscope_worker import verify_prep

    _FakeFailingStsAcsClient.instances.clear()
    fake_client_module = types.SimpleNamespace(AcsClient=_FakeFailingStsAcsClient)
    fake_request_module = types.SimpleNamespace(
        AssumeRoleRequest=types.SimpleNamespace(AssumeRoleRequest=_FakeAssumeRoleRequest)
    )
    monkeypatch.setitem(sys.modules, "aliyunsdkcore.client", fake_client_module)
    monkeypatch.setitem(sys.modules, "aliyunsdksts.request.v20150401", fake_request_module)

    result = verify_prep._get_sts_credentials(
        "deploy-ak",
        "DEPLOY_SECRET_SHOULD_NOT_LEAK",
        "acs:ram::1633875501759333:role/soniscope-uploader-role",
        "recordings/2026-01-01/test.wav",
    )

    assert isinstance(result, verify_prep.StsAssumeRoleFailure)
    assert "NoPermission" in result.detail
    assert "req-123" in result.detail
    assert "DEPLOY_SECRET_SHOULD_NOT_LEAK" not in result.detail
    assert "TOKEN_SHOULD_NOT_LEAK" not in result.detail
