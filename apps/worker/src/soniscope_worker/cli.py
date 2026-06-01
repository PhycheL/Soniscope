"""CLI entry point using Typer."""

from __future__ import annotations

import typer

app = typer.Typer(name="soniscope-worker", help="SoniScope Worker CLI")


@app.command()
def run() -> None:
    """Start the Worker main polling loop (placeholder)."""
    typer.echo("Worker run — not yet implemented.")


@app.command()
def check_config() -> None:
    """Validate config.yaml and print a sanitised summary (placeholder)."""
    typer.echo("check-config — not yet implemented.")


@app.command()
def init_dirs() -> None:
    """Create runtime directories under SONISCOPE_HOME (placeholder)."""
    typer.echo("init-dirs — not yet implemented.")


if __name__ == "__main__":
    app()
