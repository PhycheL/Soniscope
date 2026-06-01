"""Runtime path resolution.

Resolves ``SONISCOPE_HOME`` and derives the standard runtime directories:
``inbox/``, ``inbox/failed/``, ``fragments/``, ``tmp/``.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SONISCOPE_HOME = Path.home() / "SoniScope"


def resolve_home() -> Path:
    """Return the runtime home directory.

    Reads ``$SONISCOPE_HOME``; falls back to ``~/SoniScope``.
    """
    env = os.environ.get("SONISCOPE_HOME")
    if env:
        return Path(env)
    return DEFAULT_SONISCOPE_HOME


def inbox_dir(home: Path | None = None) -> Path:
    """Return ``<home>/inbox`` (download staging area)."""
    return (home or resolve_home()) / "inbox"


def inbox_failed_dir(home: Path | None = None) -> Path:
    """Return ``<home>/inbox/failed`` (failed transcode archive)."""
    return inbox_dir(home) / "failed"


def fragments_dir(home: Path | None = None) -> Path:
    """Return ``<home>/fragments``."""
    return (home or resolve_home()) / "fragments"


def tmp_dir(home: Path | None = None) -> Path:
    """Return ``<home>/tmp`` (transcription work area)."""
    return (home or resolve_home()) / "tmp"


def init_runtime_dirs(home: Path | None = None) -> list[str]:
    """Idempotently create runtime directories.

    Returns a list of created (or already-existing) directory paths as strings.
    """
    root = home or resolve_home()
    dirs = [
        inbox_dir(root),
        inbox_failed_dir(root),
        fragments_dir(root),
        tmp_dir(root),
    ]
    created: list[str] = []
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        created.append(str(d))
    return created
