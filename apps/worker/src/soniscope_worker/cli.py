"""Worker CLI（基于 typer）。

US-001 提供骨架命令；US-002 增加 check-config / init-dirs。
主轮询与 retranscribe 等在后续 story 实现。
"""

import typer

from soniscope_worker import __version__
from soniscope_worker.config import (
    ConfigError,
    config_path,
    config_permission_is_600,
    load_config,
)
from soniscope_worker.paths import init_runtime_dirs

app = typer.Typer(
    add_completion=False,
    help="SoniScope Worker：轮询 OSS、标准化音频、云端 ASR、本地落盘。",
)


@app.command()
def run() -> None:
    """启动 Worker 主轮询循环（占位，主逻辑在 US-021+ 实现）。"""
    typer.echo("soniscope-worker: 主轮询尚未实现（将在 US-021+ 交付）")


@app.command()
def version() -> None:
    """打印 Worker 版本号。"""
    typer.echo(__version__)


@app.command(name="check-config")
def check_config() -> None:
    """读取 config.yaml → 校验必填字段 → 打印脱敏摘要 → 检查权限是否为 600。"""
    path = config_path()
    try:
        cfg = load_config(path)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if not config_permission_is_600(path):
        mode = oct(path.stat().st_mode & 0o777)
        typer.echo(
            f"⚠️  警告：{path} 权限为 {mode}，应为 600（请执行：chmod 600 {path}）",
            err=True,
        )

    typer.echo(f"config: {path}")
    for line in cfg.masked_summary():
        typer.echo(line)


@app.command(name="init-dirs")
def init_dirs() -> None:
    """在 $SONISCOPE_HOME 下幂等创建 inbox/ inbox/failed/ fragments/ tmp/。"""
    for d in init_runtime_dirs():
        typer.echo(f"ok  {d}")


@app.command(name="verify-prep")
def verify_prep() -> None:
    """一键校验 US-001 人工准备产物（OSS / STS / FC / NLS / fixture / 环境）。"""
    from soniscope_worker.verify_prep import run_verify_prep

    lines, code = run_verify_prep()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)
