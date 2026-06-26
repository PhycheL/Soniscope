"""OSS 对象运维辅助（US-010 首交付 ``oss-delete-obj``，US-017/US-029 复用）。

提供由 ``fragment_id`` 推导 OSS object key 的纯逻辑，以及一个把 OSS put/delete IO
收敛到 ``OssObjectStore`` 协议的注入点（单测用 Fake 替换，真实运行用 OSS SDK）。

**安全红线**：``DeleteObject`` 是**仅测试用**能力（构造 verify 失败场景），绝不出现在
Worker 业务路径中（轮询 / 下载 / 转写 / 落盘均不删除 OSS）。删除前必须显式确认
（``--yes``）或开启测试环境变量 ``SONISCOPE_ALLOW_OSS_DELETE=1``，否则拒绝执行。
所有输出绝不打印 AK Secret 明文。
"""

from __future__ import annotations

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from soniscope_worker.config import ConfigError, config_path, load_config

# fragment_id 格式：<YYYYMMDDTHHMMSS>_<deviceShortId(4-8)>_<26 字符 ULID>
# （与 fc_shared.sts._FRAGMENT_ID_RE / AGENTS.md / tech-spec 一致）。
_FRAGMENT_ID_RE = re.compile(
    r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})T\d{6}"
    r"_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$"
)

# 删除 OSS 对象的测试环境开关（非交互场景，如 make test-verify-upload 内部）。
TEST_ONLY_DELETE_ENV = "SONISCOPE_ALLOW_OSS_DELETE"


class OssAdminError(Exception):
    """OSS 运维操作错误（非法 fragment_id、缺依赖、未授权删除等）。"""


def object_key_for(fragment_id: str) -> str:
    """由 ``fragment_id`` 推导 ``recordings/<YYYY-MM-DD>/<fragment_id>.wav``。

    格式或日期非法时抛 ``OssAdminError``（与 FC 侧 object_key_for 规则一致）。
    """
    match = _FRAGMENT_ID_RE.match(fragment_id)
    if match is None:
        raise OssAdminError(f"非法 fragment_id 格式：{fragment_id!r}")
    year, month, day = match["year"], match["month"], match["day"]
    try:
        datetime.datetime(int(year), int(month), int(day))  # noqa: DTZ001 - 仅校验日期合法性
    except ValueError as exc:
        raise OssAdminError(f"非法 fragment_id 日期：{fragment_id!r}") from exc
    return f"recordings/{year}-{month}-{day}/{fragment_id}.wav"


def delete_allowed(*, confirmed: bool, env: Mapping[str, str]) -> bool:
    """删除是否被授权：显式 ``--yes`` 或 ``SONISCOPE_ALLOW_OSS_DELETE=1``。"""
    return confirmed or env.get(TEST_ONLY_DELETE_ENV, "") == "1"


def _is_not_found(exc: BaseException) -> bool:
    """从 OSS 异常判定 404 / NoSuchKey（对象不存在）。"""
    for attr in ("status_code", "statusCode", "code", "error_code", "Code"):
        val = getattr(exc, attr, None)
        if val in (404, "404", "NoSuchKey", "NoSuchObject"):
            return True
    text = str(exc)
    return "NoSuchKey" in text or "404" in text or "NoSuchObject" in text


def format_object_stat(stat: ObjectStat) -> list[str]:
    """渲染 show-oss-object 输出（绝不打印 AK Secret）。"""
    if not stat.exists:
        return [f"对象不存在：{stat.key}", "（尚未上传，或 fragment_id 对应的对象已被删除）"]
    lines = [
        f"✅ 对象存在：{stat.key}",
        f"  size          : {stat.size}",
        f"  etag          : {stat.etag}",
        f"  last_modified : {stat.last_modified}",
    ]
    if stat.metadata:
        lines.append("  用户自定义元数据：")
        for k in sorted(stat.metadata):
            lines.append(f"    {k}: {stat.metadata[k]}")
    else:
        lines.append("  用户自定义元数据：（无）")
    return lines


@dataclass(frozen=True)
class ObjectStat:
    """HeadObject 读回的对象详情（show-oss-object 输出，US-017 AC#9）。"""

    key: str
    exists: bool
    size: int | None = None
    etag: str = ""
    last_modified: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)


class OssObjectStore(Protocol):
    """OSS put / delete / head 的注入点（单测用 Fake 替换）。

    put（构造测试对象）+ delete（仅测试用，构造对象缺失场景）+ head_object
    （show-oss-object 读取对象存在性 / size / etag / last_modified / 用户自定义元数据，US-017）。
    """

    def put_object(self, key: str, body: bytes) -> None: ...

    def delete_object(self, key: str) -> None: ...

    def head_object(self, key: str) -> ObjectStat: ...


# ── 真实实现（lazy import OSS SDK；用 config.yaml 的 OSS AK）─────────────────
class RealOssObjectStore:
    """真实 OSS 对象存储；用 config.yaml 的长期 OSS AK 建客户端。

    构造时加载 config（缺失 / 非法 config 抛 ``OssAdminError``），调用时才触网。
    """

    def __init__(self) -> None:
        try:
            cfg = load_config(config_path())
        except ConfigError as exc:
            raise OssAdminError(f"加载 config.yaml 失败：{exc}") from exc
        self._bucket = cfg.oss.bucket
        self._endpoint = cfg.oss.endpoint
        self._ak_id = cfg.oss.access_key_id
        self._ak_secret = cfg.oss.access_key_secret.get_secret_value()
        self._oss: Any | None = None

    @property
    def bucket(self) -> str:
        return self._bucket

    def _client(self) -> Any:
        from soniscope_worker.verify_prep import _import_oss, _oss_client

        if self._oss is None:
            self._oss = _import_oss()
        return _oss_client(self._oss, self._endpoint, self._ak_id, self._ak_secret)

    def put_object(self, key: str, body: bytes) -> None:
        oss = self._oss or self._import()
        client = self._client()
        client.put_object(oss.PutObjectRequest(bucket=self._bucket, key=key, body=body))

    def delete_object(self, key: str) -> None:
        oss = self._oss or self._import()
        client = self._client()
        client.delete_object(oss.DeleteObjectRequest(bucket=self._bucket, key=key))

    def head_object(self, key: str) -> ObjectStat:
        oss = self._oss or self._import()
        client = self._client()
        try:
            result = client.head_object(oss.HeadObjectRequest(bucket=self._bucket, key=key))
        except Exception as exc:  # noqa: BLE001 - 404 → 不存在，其余上抛由入口收敛
            if _is_not_found(exc):
                return ObjectStat(key=key, exists=False)
            raise
        raw_meta = getattr(result, "metadata", None) or {}
        metadata = {str(k): str(v) for k, v in dict(raw_meta).items()}
        return ObjectStat(
            key=key,
            exists=True,
            size=int(getattr(result, "content_length", 0) or 0),
            etag=str(getattr(result, "etag", "") or ""),
            last_modified=str(getattr(result, "last_modified", "") or ""),
            metadata=metadata,
        )

    def _import(self) -> Any:
        from soniscope_worker.verify_prep import _import_oss

        self._oss = _import_oss()
        return self._oss


# ── oss-delete-obj 入口（仅测试用）──────────────────────────────────────────
def run_oss_delete_obj(
    fragment_id: str,
    *,
    confirmed: bool,
    env: Mapping[str, str],
    store: OssObjectStore | None = None,
) -> tuple[list[str], int]:
    """删除指定 fragment 的 OSS 对象（仅测试用）。返回（输出行, 退出码）。"""
    lines: list[str] = ["⚠️  oss-delete-obj 仅测试用：构造 verify 失败场景，不用于生产。"]
    if not delete_allowed(confirmed=confirmed, env=env):
        lines.append(
            "未授权删除：请加 --yes 或设 SONISCOPE_ALLOW_OSS_DELETE=1（仅测试环境）。"
        )
        return lines, 1
    try:
        key = object_key_for(fragment_id)
    except OssAdminError as exc:
        lines.append(f"FAIL — {exc}")
        return lines, 1
    used = store
    if used is None:
        try:
            used = RealOssObjectStore()
        except OssAdminError as exc:
            lines.append(f"FAIL — {exc}")
            return lines, 1
    try:
        used.delete_object(key)
    except Exception as exc:  # noqa: BLE001 - 收敛为单项 fail，不泄漏明文
        lines.append(f"FAIL — 删除 {key} 失败：{type(exc).__name__}")
        return lines, 1
    lines.append(f"✅ 已删除 OSS 对象：{key}")
    return lines, 0


# ── show-oss-object 入口（US-017 首交付，US-029 复用）───────────────────────
def run_show_oss_object(
    fragment_id: str,
    *,
    store: OssObjectStore | None = None,
) -> tuple[list[str], int]:
    """由 ``fragment_id`` 推导 object key 并 HeadObject 输出对象详情。返回（输出行, 退出码）。

    对象存在 → exit 0；对象不存在 → exit 0（输出「对象不存在」，便于脚本判断而非报错）；
    非法 fragment_id / 缺依赖 / HeadObject 异常 → exit 1。绝不打印 AK Secret 明文。
    """
    lines: list[str] = []
    try:
        key = object_key_for(fragment_id)
    except OssAdminError as exc:
        return [f"FAIL — {exc}"], 1
    used = store
    if used is None:
        try:
            used = RealOssObjectStore()
        except OssAdminError as exc:
            return [f"FAIL — {exc}"], 1
    try:
        stat = used.head_object(key)
    except Exception as exc:  # noqa: BLE001 - 收敛为单项 fail，不泄漏明文
        return [f"FAIL — HeadObject {key} 失败：{type(exc).__name__}"], 1
    lines.extend(format_object_stat(stat))
    return lines, 0
