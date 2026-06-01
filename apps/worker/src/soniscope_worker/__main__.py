"""Entry point for ``python -m soniscope_worker``."""

from soniscope_worker.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
