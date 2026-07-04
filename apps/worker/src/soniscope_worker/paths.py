"""运行时目录解析与初始化。

代码仓库与运行时数据分离：运行时根目录由 `SONISCOPE_HOME` 指定。
来源顺序：当前进程环境变量 → 当前工作目录向上查找的 `.env`。`inbox/`、`tmp/`、
`fragments/` 必须位于同一文件系统，以保证后续 story 的原子 rename。
"""

import os
from pathlib import Path


class RuntimeHomeError(ValueError):
    """运行时根目录不可用。"""


def _parse_dotenv_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _dotenv_value(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        name, sep, value = line.partition("=")
        if sep and name.strip() == key:
            return _parse_dotenv_value(value)
    return None


def _find_dotenv(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


def soniscope_home() -> Path:
    """返回 Worker 运行时根目录（环境变量或仓库 `.env` 中的 SONISCOPE_HOME）。"""
    env = os.environ.get("SONISCOPE_HOME")
    if env and env.strip():
        return Path(os.path.expandvars(env.strip())).expanduser()

    dotenv = _find_dotenv()
    if dotenv is not None:
        value = _dotenv_value(dotenv, "SONISCOPE_HOME")
        if value and value.strip():
            return Path(os.path.expandvars(value.strip())).expanduser()

    raise RuntimeHomeError(
        "未设置 SONISCOPE_HOME。请先 export SONISCOPE_HOME=/path/to/SoniScope，"
        "或在仓库根目录 .env 中写入 SONISCOPE_HOME=/path/to/SoniScope。"
    )


def soniscope_home_source() -> str:
    """返回 SONISCOPE_HOME 的来源说明，仅用于诊断输出。"""
    env = os.environ.get("SONISCOPE_HOME")
    if env and env.strip():
        return "环境变量 SONISCOPE_HOME"
    dotenv = _find_dotenv()
    if dotenv is not None and _dotenv_value(dotenv, "SONISCOPE_HOME"):
        return f"{dotenv}"
    return "未设置"


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
    """幂等创建所有运行时子目录，返回目录清单。"""
    home = soniscope_home()
    if not home.exists():
        raise RuntimeHomeError(
            f"SONISCOPE_HOME 不存在：{home}\n"
            "请先手动创建/挂载工作目录，再执行 init-dirs。"
        )
    if not home.is_dir():
        raise RuntimeHomeError(f"SONISCOPE_HOME 不是目录：{home}")

    dirs = runtime_dirs()
    for d in dirs:
        d.mkdir(exist_ok=True)
    return dirs
