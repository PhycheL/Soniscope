"""`python -m soniscope_worker` 入口。"""

from soniscope_worker.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
