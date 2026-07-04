"""US-001 骨架冒烟测试：验证模块可导入、CLI 命令与运行时路径约定。"""

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from soniscope_worker import __version__
from soniscope_worker.cli import app
from soniscope_worker.config import config_path
from soniscope_worker.paths import (
    RuntimeHomeError,
    fragments_dir,
    inbox_dir,
    soniscope_home,
    tmp_dir,
)

runner = CliRunner()


def test_version_constant() -> None:
    assert __version__ == "0.1.0"


def test_cli_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_run_command_is_placeholder() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0


def test_home_from_env(monkeypatch: object) -> None:
    # monkeypatch 由 pytest 注入；此处用 os.environ 直接设置以保持类型简单。
    os.environ["SONISCOPE_HOME"] = "/tmp/soniscope-test-home"
    try:
        home = soniscope_home()
        assert home == Path("/tmp/soniscope-test-home")
        assert inbox_dir() == home / "inbox"
        assert fragments_dir() == home / "fragments"
        assert tmp_dir() == home / "tmp"
        assert config_path() == home / "config.yaml"
    finally:
        del os.environ["SONISCOPE_HOME"]


def test_home_from_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SONISCOPE_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "runtime"
    (tmp_path / ".env").write_text(f"SONISCOPE_HOME={home}\n", encoding="utf-8")
    assert soniscope_home() == home


def test_home_requires_soniscope_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SONISCOPE_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeHomeError, match="未设置 SONISCOPE_HOME"):
        soniscope_home()
