"""把小程序 JS 单元测试（node 内置 test runner）纳入统一质量门 `make test`。

小程序源码（apps/miniprogram/）不进 mypy/ruff/pytest 直接覆盖（见 codebase patterns），
但 US-013 的中断保护逻辑必须有单元测试。这里以子进程方式运行 `node --test`，
让 pytest（make test）成为唯一质量门并保持绿色；node 缺失时跳过（真机/Worker 主机均装有 node）。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MINIPROGRAM_TEST_DIR = _REPO_ROOT / "apps" / "miniprogram" / "test"


def _test_files() -> list[str]:
    return sorted(str(p) for p in _MINIPROGRAM_TEST_DIR.glob("*.test.js"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不可用，跳过小程序 JS 单元测试")
def test_miniprogram_js_unit_tests() -> None:
    files = _test_files()
    assert files, f"未找到小程序 JS 测试文件：{_MINIPROGRAM_TEST_DIR}"
    # 该 node 版本 `node --test <dir>` 会把目录当模块加载，故传显式文件清单。
    result = subprocess.run(
        ["node", "--test", *files],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
