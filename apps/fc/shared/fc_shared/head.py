"""verify-upload HeadObject 上传确认（US-009，tech-spec §4.2）。

把可单测的纯逻辑（HeadObject 结果 → verify 响应映射、expected_size 解析）与真实
云调用（OSS HeadObject，lazy import 云 SDK）分离，沿用 ``sts.py`` 的 Protocol 注入模式：

* 纯逻辑无 IO、直接单测，由 mypy strict + ruff + pytest 覆盖；
* HeadObject 通过 ``ObjectHeader`` Protocol 注入，单测用假实现，运行时用 ``RealObjectHeader``。

HeadObject 只能校验对象存在性与 ``Content-Length``（无法校验 sha256，见 §4.2 注），
故响应只区分「不存在 / 大小不一致 / 一致」三态。OSS 读凭证只在内部调用，绝不进响应或日志。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .errors import OBJECT_NOT_FOUND, SIZE_MISMATCH

# HeadObject 返回 404 / 对象不存在时，OSS SDK 异常携带的错误码（任一命中即视为不存在）。
_NOT_FOUND_CODES = ("NoSuchKey", "NoSuchObject", "404")


@dataclass(frozen=True)
class ObjectHead:
    """HeadObject 读回的对象元数据；对象不存在时 ``exists=False``，其余字段保持默认值。"""

    exists: bool
    content_length: int = 0
    etag: str = ""
    last_modified: str = ""


def verify_upload_result(head: ObjectHead, expected_size: int) -> dict[str, object]:
    """按 tech-spec §4.2 把 HeadObject 结果映射为 verify-upload 响应。

    * 对象不存在 → ``{"verified": False, "reason": "OBJECT_NOT_FOUND"}``
    * 存在但 Content-Length != expected_size → ``{"verified": False, "reason":
      "SIZE_MISMATCH", "actual_size": ...}``
    * 存在且大小一致 → ``{"verified": True, "etag", "size", "last_modified"}``
    """
    if not head.exists:
        return {"verified": False, "reason": OBJECT_NOT_FOUND}
    if head.content_length != expected_size:
        return {
            "verified": False,
            "reason": SIZE_MISMATCH,
            "actual_size": head.content_length,
        }
    return {
        "verified": True,
        "etag": head.etag,
        "size": head.content_length,
        "last_modified": head.last_modified,
    }


class ObjectHeader(Protocol):
    """HeadObject 注入点：用 FC 子账号 AK 读回单个 object 的元数据（便于单测打桩）。"""

    def head_object(
        self,
        *,
        bucket: str,
        region: str,
        endpoint: str,
        ak_id: str,
        ak_secret: str,
        object_key: str,
    ) -> ObjectHead: ...


def _import_oss() -> Any:
    import alibabacloud_oss_v2 as oss

    return oss


def _oss_error_code(exc: BaseException) -> str:
    """从 OSS SDK 异常中提取错误码 / 状态码（用于判定对象是否不存在）。"""
    for attr in ("code", "error_code", "Code", "status_code", "StatusCode"):
        val = getattr(exc, attr, None)
        if val:
            return str(val)
    unwrap = getattr(exc, "unwrap", None)
    if callable(unwrap):
        try:
            inner = unwrap()
        except Exception:  # noqa: BLE001 - unwrap 自身异常忽略
            inner = None
        if inner is not None and inner is not exc:
            return _oss_error_code(inner)
    return str(exc)


def is_not_found(exc: BaseException) -> bool:
    """HeadObject 异常是否表示「对象不存在」（404 / NoSuchKey）。"""
    code = _oss_error_code(exc)
    return any(token in code for token in _NOT_FOUND_CODES)


class RealObjectHeader:
    """真实 HeadObject 实现（lazy import alibabacloud-oss-v2）。"""

    def head_object(
        self,
        *,
        bucket: str,
        region: str,
        endpoint: str,
        ak_id: str,
        ak_secret: str,
        object_key: str,
    ) -> ObjectHead:
        oss = _import_oss()
        cfg = oss.config.load_default()
        cfg.credentials_provider = oss.credentials.StaticCredentialsProvider(
            access_key_id=ak_id, access_key_secret=ak_secret
        )
        cfg.region = region
        cfg.endpoint = endpoint
        client = oss.Client(cfg)
        try:
            result = client.head_object(
                oss.HeadObjectRequest(bucket=bucket, key=object_key)
            )
        except Exception as exc:  # noqa: BLE001 - 404 映射为不存在，其余上抛由 handler 收敛 500
            if is_not_found(exc):
                return ObjectHead(exists=False)
            raise
        return ObjectHead(
            exists=True,
            content_length=int(getattr(result, "content_length", 0) or 0),
            etag=str(getattr(result, "etag", "") or ""),
            last_modified=str(getattr(result, "last_modified", "") or ""),
        )


def get_header() -> ObjectHeader:
    """返回运行时 HeadObject 执行器；单测通过 monkeypatch 本函数注入假实现。"""
    return RealObjectHeader()
