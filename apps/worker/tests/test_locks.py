"""US-028 per-fragment 文件锁 单元测试（fcntl flock，跨 open file description 互斥）。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from soniscope_worker.locks import (
    LOCK_SUFFIX,
    LockBusyError,
    fragment_lock,
    fragment_lock_path,
)

_FID = "20260527T150000_devr01_01HZX3K8MN5PQR9TFB7AYWVCDE"


def test_fragment_lock_path(tmp_path: Path) -> None:
    assert fragment_lock_path(tmp_path, _FID) == tmp_path / f"{_FID}{LOCK_SUFFIX}"


def test_fragment_lock_acquires_and_releases(tmp_path: Path) -> None:
    # 进入即创建锁文件；退出后可再次获取（已释放）。
    with fragment_lock(tmp_path, _FID):
        assert fragment_lock_path(tmp_path, _FID).exists()
    with fragment_lock(tmp_path, _FID):
        pass  # 第二次能立即拿到 → 上次已释放


def test_fragment_lock_creates_lock_root(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "locks"
    with fragment_lock(nested, _FID):
        assert nested.is_dir()


def test_non_blocking_busy_when_held(tmp_path: Path) -> None:
    # 持锁期间，另一个 open file description 非阻塞获取应抛 LockBusyError。
    path = fragment_lock_path(tmp_path, _FID)
    tmp_path.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        with pytest.raises(LockBusyError) as ei:
            with fragment_lock(tmp_path, _FID, blocking=False):
                pass
        assert ei.value.fragment_id == _FID
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    # 释放后非阻塞可获取。
    with fragment_lock(tmp_path, _FID, blocking=False):
        pass


def test_different_fragments_independent(tmp_path: Path) -> None:
    # 不同 fragment_id 用不同锁文件，互不阻塞。
    other = "20260527T150100_devr02_01HZX3K8MN5PQR9TFB7AYWVCDF"
    with fragment_lock(tmp_path, _FID):
        with fragment_lock(tmp_path, other, blocking=False):
            pass  # 不同 fragment 不冲突
