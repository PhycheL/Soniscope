"""Per-fragment 文件锁（US-028，tech-spec §3.7 防并发转写）。

主轮询流水线（:mod:`soniscope_worker.pipeline`）与显式重转
（:mod:`soniscope_worker.retranscribe`）都可能对同一 ``fragment_id`` 触发转写。
§3.7 要求「Worker 主轮询线程可继续（不互斥），但同一 ``fragment_id`` 不会被同时转两遍」。

为此提供一个**按 fragment_id 粒度**的文件锁：两条转写路径在真正调用 Transcriber 前都先
``flock(LOCK_EX)`` 同一把锁文件 ``<lock_root>/<fragment_id>.lock``，从而保证同一 fragment
任意时刻最多一条路径在转写；不同 fragment 互不阻塞（每个 fragment 独立锁文件）。

``flock`` 是 advisory 锁但作用于跨进程的 open file description，Worker 主进程与
``retranscribe`` 子进程因此能互斥。锁文件本身是 0 字节占位、进程退出自动释放，不参与
recovery 扫描（``.lock`` 后缀不匹配 ``.transcript.json.tmp``）。
"""

from __future__ import annotations

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

LOCK_SUFFIX = ".lock"


class LockBusyError(Exception):
    """非阻塞获取锁时锁已被占用（同一 fragment 正在被另一路径转写）。"""

    def __init__(self, fragment_id: str) -> None:
        super().__init__(f"fragment {fragment_id} 正在被另一路径转写（锁被占用）")
        self.fragment_id = fragment_id


def fragment_lock_path(lock_root: Path, fragment_id: str) -> Path:
    """该 fragment 的锁文件路径 ``<lock_root>/<fragment_id>.lock``。"""
    return lock_root / f"{fragment_id}{LOCK_SUFFIX}"


@contextmanager
def fragment_lock(
    lock_root: Path, fragment_id: str, *, blocking: bool = True
) -> Iterator[None]:
    """获取 fragment 粒度的排他文件锁（context manager，退出自动释放）。

    ``blocking=True``（默认）：阻塞直到拿到锁——主轮询与 ``retranscribe`` 都用此模式，
    后到者排队等待，绝不并发转同一 fragment。``blocking=False``：拿不到立即抛
    :class:`LockBusyError`（供「跳过而非等待」的场景，如重转时若主轮询正在转该条则跳过）。
    """
    lock_root.mkdir(parents=True, exist_ok=True)
    path = fragment_lock_path(lock_root, fragment_id)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if not blocking else 0)
        try:
            fcntl.flock(fd, flags)
        except OSError as exc:
            raise LockBusyError(fragment_id) from exc
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
