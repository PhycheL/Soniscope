"""Worker CLI（基于 typer）。

US-001 仅提供骨架命令，主轮询与 retranscribe 等在后续 story 实现。
"""

import typer

from soniscope_worker import __version__

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
