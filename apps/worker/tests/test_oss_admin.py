"""oss_admin 单测（US-010）：object_key 推导、删除授权门控、仅测试用删除入口。"""

from __future__ import annotations

import pytest

from soniscope_worker.oss_admin import (
    ObjectStat,
    OssAdminError,
    delete_allowed,
    format_object_stat,
    object_key_for,
    run_oss_delete_obj,
    run_show_oss_object,
)

VALID_FID = "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE"
VALID_KEY = f"recordings/2026-05-26/{VALID_FID}.wav"


class FakeStore:
    """记录 put/delete 调用的内存 OSS store。"""

    def __init__(
        self,
        *,
        fail_delete: bool = False,
        head: ObjectStat | None = None,
        fail_head: bool = False,
    ) -> None:
        self.put_calls: list[tuple[str, bytes]] = []
        self.delete_calls: list[str] = []
        self.head_calls: list[str] = []
        self._fail_delete = fail_delete
        self._head = head
        self._fail_head = fail_head

    def put_object(self, key: str, body: bytes) -> None:
        self.put_calls.append((key, body))

    def delete_object(self, key: str) -> None:
        if self._fail_delete:
            raise RuntimeError("boom")
        self.delete_calls.append(key)

    def head_object(self, key: str) -> ObjectStat:
        self.head_calls.append(key)
        if self._fail_head:
            raise RuntimeError("boom-head")
        if self._head is not None:
            return self._head
        return ObjectStat(key=key, exists=False)


# ── object_key_for ──────────────────────────────────────────────────────────
def test_object_key_for_valid() -> None:
    assert object_key_for(VALID_FID) == f"recordings/2026-05-26/{VALID_FID}.wav"


@pytest.mark.parametrize(
    "fid",
    [
        "not-a-fragment-id",
        "20260526144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",  # 缺 T
        "20260526T144800_d_01HZX3K8MN5PQR9TFB7AYWVCDE",  # device 太短
        "20260526T144800_dev01_TOOSHORT",  # ULID 太短
    ],
)
def test_object_key_for_invalid_format(fid: str) -> None:
    with pytest.raises(OssAdminError, match="格式"):
        object_key_for(fid)


def test_object_key_for_invalid_date() -> None:
    # 13 月非法日期，正则通过但 datetime 校验失败。
    with pytest.raises(OssAdminError, match="日期"):
        object_key_for("20261326T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE")


# ── delete_allowed 门控 ──────────────────────────────────────────────────────
def test_delete_allowed_confirmed() -> None:
    assert delete_allowed(confirmed=True, env={}) is True


def test_delete_allowed_env() -> None:
    assert delete_allowed(confirmed=False, env={"SONISCOPE_ALLOW_OSS_DELETE": "1"}) is True


def test_delete_allowed_denied() -> None:
    assert delete_allowed(confirmed=False, env={}) is False
    assert delete_allowed(confirmed=False, env={"SONISCOPE_ALLOW_OSS_DELETE": "0"}) is False


# ── run_oss_delete_obj 入口 ──────────────────────────────────────────────────
def test_delete_obj_unauthorized_does_not_touch_store() -> None:
    store = FakeStore()
    lines, code = run_oss_delete_obj(VALID_FID, confirmed=False, env={}, store=store)
    assert code == 1
    assert store.delete_calls == []
    assert any("仅测试用" in ln for ln in lines)
    assert any("未授权" in ln for ln in lines)


def test_delete_obj_success() -> None:
    store = FakeStore()
    lines, code = run_oss_delete_obj(VALID_FID, confirmed=True, env={}, store=store)
    assert code == 0
    assert store.delete_calls == [f"recordings/2026-05-26/{VALID_FID}.wav"]
    assert any("已删除" in ln for ln in lines)


def test_delete_obj_env_gate() -> None:
    store = FakeStore()
    lines, code = run_oss_delete_obj(
        VALID_FID, confirmed=False, env={"SONISCOPE_ALLOW_OSS_DELETE": "1"}, store=store
    )
    assert code == 0
    assert store.delete_calls == [f"recordings/2026-05-26/{VALID_FID}.wav"]


def test_delete_obj_invalid_fragment_id() -> None:
    store = FakeStore()
    lines, code = run_oss_delete_obj("bad-id", confirmed=True, env={}, store=store)
    assert code == 1
    assert store.delete_calls == []
    assert any("FAIL" in ln for ln in lines)


def test_delete_obj_store_error_is_contained() -> None:
    store = FakeStore(fail_delete=True)
    lines, code = run_oss_delete_obj(VALID_FID, confirmed=True, env={}, store=store)
    assert code == 1
    assert any("删除" in ln and "失败" in ln for ln in lines)
    # 不泄漏异常细节明文（只含类名）。
    assert all("boom" not in ln for ln in lines)


# ── format_object_stat ──────────────────────────────────────────────────────
def test_format_object_stat_exists_with_metadata() -> None:
    stat = ObjectStat(
        key=VALID_KEY,
        exists=True,
        size=4096,
        etag='"abc"',
        last_modified="2026-05-26T14:48:30Z",
        metadata={"x-oss-meta-sha256": "deadbeef", "x-oss-meta-chunk-seq": "1"},
    )
    lines = format_object_stat(stat)
    joined = "\n".join(lines)
    assert "对象存在" in joined
    assert "4096" in joined
    assert "x-oss-meta-sha256: deadbeef" in joined
    assert "x-oss-meta-chunk-seq: 1" in joined


def test_format_object_stat_missing() -> None:
    lines = format_object_stat(ObjectStat(key=VALID_KEY, exists=False))
    assert any("对象不存在" in ln for ln in lines)


# ── run_show_oss_object 入口（US-017 AC#9）──────────────────────────────────
def test_show_oss_object_exists() -> None:
    head = ObjectStat(
        key=VALID_KEY,
        exists=True,
        size=4096,
        etag='"abc"',
        last_modified="2026-05-26T14:48:30Z",
        metadata={"x-oss-meta-sha256": "deadbeef"},
    )
    store = FakeStore(head=head)
    lines, code = run_show_oss_object(VALID_FID, store=store)
    assert code == 0
    assert store.head_calls == [VALID_KEY]
    assert any("对象存在" in ln for ln in lines)
    assert any("4096" in ln for ln in lines)
    assert any("x-oss-meta-sha256: deadbeef" in ln for ln in lines)


def test_show_oss_object_missing_is_exit0() -> None:
    store = FakeStore(head=ObjectStat(key=VALID_KEY, exists=False))
    lines, code = run_show_oss_object(VALID_FID, store=store)
    assert code == 0
    assert any("对象不存在" in ln for ln in lines)


def test_show_oss_object_invalid_fragment_id() -> None:
    store = FakeStore()
    lines, code = run_show_oss_object("bad-id", store=store)
    assert code == 1
    assert store.head_calls == []
    assert any("FAIL" in ln for ln in lines)


def test_show_oss_object_head_error_is_contained() -> None:
    store = FakeStore(fail_head=True)
    lines, code = run_show_oss_object(VALID_FID, store=store)
    assert code == 1
    assert any("HeadObject" in ln and "失败" in ln for ln in lines)
    assert all("boom-head" not in ln for ln in lines)
