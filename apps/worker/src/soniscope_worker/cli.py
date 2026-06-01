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
    """Start the Worker main polling loop."""
    config_path = resolve_config_path()

    # Load config
    try:
        cfg = load_config(config_path)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    except ConfigValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    # Ensure runtime dirs exist
    init_runtime_dirs()

    from soniscope_worker.poller import run_poll_loop

    run_poll_loop(cfg)


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


@app.command()
def verify_prep() -> None:
    """Run all US-001 preparation verification checks (make verify-prep)."""
    from soniscope_worker.verify_prep import run_verify_prep

    exit_code = run_verify_prep()
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command()
def test_poll_cycle() -> None:
    """Run a single poll cycle with output (for make test-poll-interval)."""
    config_path = resolve_config_path()
    try:
        cfg = load_config(config_path)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    except ConfigValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    init_runtime_dirs()

    from soniscope_worker.poller import _build_oss_client, poll_cycle, recovery_scan
    from soniscope_worker.paths import resolve_home

    home = resolve_home()

    # Run recovery scan
    removed = recovery_scan(home)
    inbox_count = len(removed["inbox_cleaned"])
    tmp_count = len(removed["tmp_cleaned"])
    frag_count = len(removed["fragment_actions"])
    if inbox_count > 0:
        typer.echo(f"Cleaned {inbox_count} stale inbox intermediate(s):")
        for p in removed["inbox_cleaned"]:
            typer.echo(f"  {p}")
    if tmp_count > 0:
        typer.echo(f"Cleaned {tmp_count} stale tmp intermediate(s):")
        for p in removed["tmp_cleaned"]:
            typer.echo(f"  {p}")
    if frag_count > 0:
        typer.echo(f"Scanned {frag_count} fragment directory(ies):")
        for action in removed["fragment_actions"]:
            typer.echo(f"  {action}")

    # Build client and run one cycle
    client = _build_oss_client(cfg)
    import time

    t0 = time.monotonic()
    summary = poll_cycle(cfg, client)
    elapsed = time.monotonic() - t0

    typer.echo(f"\nPoll cycle complete in {elapsed:.2f}s")
    typer.echo(f"  Total objects:    {summary['total_objects']}")
    typer.echo(f"  Skipped (.done):  {summary['skipped_done']}")
    typer.echo(f"  Downloaded:       {summary['downloaded']}")
    typer.echo(f"  Passthrough:      {summary['passthrough']}")
    typer.echo(f"  Transcoded:       {summary['transcoded']}")
    typer.echo(f"  Transcode failed: {summary['transcode_failed']}")
    typer.echo(f"  Manifest written: {summary['manifest_written']}")
    typer.echo(f"  SHA256 mismatch:  {summary['sha256_mismatch']}")
    typer.echo(f"  Errors:           {summary['errors']}")


if __name__ == "__main__":
    app()
