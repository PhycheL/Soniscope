"""Basic smoke tests for the Worker skeleton."""


def test_import_succeeds() -> None:
    """The soniscope_worker package can be imported."""
    import soniscope_worker  # noqa: F401

    assert soniscope_worker.__version__ == "0.1.0"


def test_cli_help() -> None:
    """CLI entry point returns without error for help."""
    from typer.testing import CliRunner

    from soniscope_worker.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "soniscope-worker" in result.stdout


def test_run_command_exists() -> None:
    """The 'run' subcommand is registered."""
    from typer.testing import CliRunner

    from soniscope_worker.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["run"])
    # Currently a placeholder; should exit 0 and print the placeholder message.
    assert result.exit_code == 0
    assert "not yet implemented" in result.stdout


def test_paths_default_home() -> None:
    """paths.py exposes the default home constant."""
    from soniscope_worker.paths import DEFAULT_SONISCOPE_HOME

    assert DEFAULT_SONISCOPE_HOME.name == "SoniScope"
