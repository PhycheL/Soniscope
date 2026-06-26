"""US-009 verify-upload 纯逻辑单测：HeadObject 结果映射、错误码判定、OSS 读凭证加载。

只覆盖无 IO 的纯逻辑（tech-spec §4.2）；真实 HeadObject 由 RealObjectHeader 在 live
联调中验证（US-010）。
"""

from __future__ import annotations

import pytest

import fc_shared
from fc_shared import head


def test_verify_result_object_not_found() -> None:
    result = fc_shared.verify_upload_result(head.ObjectHead(exists=False), expected_size=100)
    assert result == {"verified": False, "reason": fc_shared.OBJECT_NOT_FOUND}


def test_verify_result_size_mismatch_reports_actual() -> None:
    obj = head.ObjectHead(exists=True, content_length=100, etag="E", last_modified="LM")
    result = fc_shared.verify_upload_result(obj, expected_size=200)
    assert result == {
        "verified": False,
        "reason": fc_shared.SIZE_MISMATCH,
        "actual_size": 100,
    }


def test_verify_result_success_has_etag_size_last_modified() -> None:
    obj = head.ObjectHead(
        exists=True, content_length=12345, etag='"abc"', last_modified="Thu, 01 Jan 2026"
    )
    result = fc_shared.verify_upload_result(obj, expected_size=12345)
    assert result == {
        "verified": True,
        "etag": '"abc"',
        "size": 12345,
        "last_modified": "Thu, 01 Jan 2026",
    }


def test_verify_result_success_never_leaks_extra_fields() -> None:
    obj = head.ObjectHead(exists=True, content_length=1, etag="e", last_modified="lm")
    result = fc_shared.verify_upload_result(obj, expected_size=1)
    # 成功响应严格只含 §4.2 的 4 个字段，不夹带 AK / token 等。
    assert set(result) == {"verified", "etag", "size", "last_modified"}


@pytest.mark.parametrize("code", ["NoSuchKey", "NoSuchObject", "404"])
def test_is_not_found_true_for_missing_object_codes(code: str) -> None:
    assert head.is_not_found(_OssErr(code=code)) is True


@pytest.mark.parametrize("code", ["AccessDenied", "InternalError", "SignatureDoesNotMatch"])
def test_is_not_found_false_for_other_codes(code: str) -> None:
    assert head.is_not_found(_OssErr(code=code)) is False


def test_is_not_found_unwraps_nested_error() -> None:
    inner = _OssErr(code="NoSuchKey")
    outer = _OssErr(code="", unwrap_to=inner)
    assert head.is_not_found(outer) is True


def test_load_verify_env_ok() -> None:
    env = fc_shared.load_verify_env({"ALIYUN_AK_ID": "id", "ALIYUN_AK_SECRET": "sec"})
    assert env.ak_id == "id"
    assert env.ak_secret == "sec"


def test_load_verify_env_missing_lists_names() -> None:
    with pytest.raises(fc_shared.FcConfigError) as exc:
        fc_shared.load_verify_env({"ALIYUN_AK_ID": "id"})
    assert exc.value.missing == ["ALIYUN_AK_SECRET"]


def test_load_verify_env_blank_treated_as_missing() -> None:
    with pytest.raises(fc_shared.FcConfigError) as exc:
        fc_shared.load_verify_env({"ALIYUN_AK_ID": "   ", "ALIYUN_AK_SECRET": ""})
    assert set(exc.value.missing) == {"ALIYUN_AK_ID", "ALIYUN_AK_SECRET"}


class _OssErr(Exception):
    """模拟 OSS SDK 异常：携带 code，可选 unwrap() 返回内层异常。"""

    def __init__(self, *, code: str, unwrap_to: Exception | None = None) -> None:
        super().__init__(code or "oss-error")
        self.code = code
        self._unwrap_to = unwrap_to

    def unwrap(self) -> Exception | None:
        return self._unwrap_to
