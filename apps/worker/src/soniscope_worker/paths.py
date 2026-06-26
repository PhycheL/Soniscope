"""运行时目录解析与初始化。

代码仓库与运行时数据分离：运行时根目录由 `$SONISCOPE_HOME` 指定，
未设置时回退到 `~/SoniScope`。`inbox/`、`tmp/`、`fragments/` 必须位于同一文件系统，
以保证后续 story 的原子 rename。
"""

import os
from pathlib import Path

DEFAULT_HOME = Path.home() / "SoniScope"


def soniscope_home() -> Path:
    """返回 Worker 运行时根目录（$SONISCOPE_HOME 或 ~/SoniScope）。"""
    env = os.environ.get("SONISCOPE_HOME")
    return Path(env) if env else DEFAULT_HOME


def inbox_dir() -> Path:
    """临时下载区 inbox/。"""
    return soniscope_home() / "inbox"


def inbox_failed_dir() -> Path:
    """转码失败留档区 inbox/failed/。"""
    return inbox_dir() / "failed"


def fragments_dir() -> Path:
    """完成态 Fragment 目录 fragments/。"""
    return soniscope_home() / "fragments"


def tmp_dir() -> Path:
    """转写工作区 tmp/。"""
    return soniscope_home() / "tmp"


def runtime_dirs() -> list[Path]:
    """返回需要初始化的运行时目录清单（顺序稳定，便于幂等创建与展示）。"""
    return [inbox_dir(), inbox_failed_dir(), fragments_dir(), tmp_dir()]


def init_runtime_dirs() -> list[Path]:
    """幂等创建所有运行时目录，返回目录清单。"""
    dirs = runtime_dirs()
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return dirs
