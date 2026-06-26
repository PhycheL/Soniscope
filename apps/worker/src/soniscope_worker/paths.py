"""运行时目录解析。

代码仓库与运行时数据分离：运行时根目录由 `$SONISCOPE_HOME` 指定，
未设置时回退到 `~/SoniScope`。完整目录初始化逻辑见 US-002。
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


def fragments_dir() -> Path:
    """完成态 Fragment 目录 fragments/。"""
    return soniscope_home() / "fragments"


def tmp_dir() -> Path:
    """转写工作区 tmp/。"""
    return soniscope_home() / "tmp"
