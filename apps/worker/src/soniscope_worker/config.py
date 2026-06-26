"""配置加载骨架。

完整的 Pydantic v2 schema、脱敏加载器与必填字段校验在 US-002 实现。
US-001 仅确定配置文件位置约定。
"""

from pathlib import Path

from soniscope_worker.paths import soniscope_home


def config_path() -> Path:
    """返回 config.yaml 的预期路径（$SONISCOPE_HOME/config.yaml）。"""
    return soniscope_home() / "config.yaml"
