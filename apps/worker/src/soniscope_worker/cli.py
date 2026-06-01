"""CLI entry point using Typer."""

from __future__ import annotations

import typer

from soniscope_worker.config import (
    ConfigValidationError,
    check_file_permissions,
    load_config,
    resolve_config_path,
)
from soniscope_worker.paths import init_runtime_dirs

app = typer.Typer(name="soniscope-worker", help="SoniScope Worker CLI")


@app.command()
def run() -> None:
    """Start the Worker main polling loop (placeholder)."""
    typer.echo("Worker run — not yet implemented.")


@app.command()
def check_config() -> None:
    """Validate config.yaml and print a sanitised summary."""
    config_path = resolve_config_path()
    typer.echo(f"Reading config: {config_path}")

    # Check file permissions first
    ok, msg = check_file_permissions(config_path)
    typer.echo(msg)
    if not ok:
        typer.echo("")  # blank line for readability

    # Load and validate
    try:
        cfg = load_config(config_path)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    except ConfigValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    # Print sanitised summary (secrets masked)
    typer.echo("")
    typer.echo(cfg.sanitized_summary())


@app.command()
def init_dirs() -> None:
    """Create runtime directories under SONISCOPE_HOME."""
    created = init_runtime_dirs()
    typer.echo("Created runtime directories:")
    for d in created:
        typer.echo(f"  {d}")


if __name__ == "__main__":
    app()
