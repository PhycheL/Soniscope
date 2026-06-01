"""Atomic write utilities and ``.done`` marker management.

Covers US-023 AC5/AC6: all filesystem writes use a temp-file → atomic rename
protocol, and the ``.done`` marker is a 0-byte file created last.
"""

from __future__ import annotations

import json as _json
from pathlib import Path


# ---------------------------------------------------------------------------
# Temp-path helper
# ---------------------------------------------------------------------------


def _temp_for(target: Path) -> Path:
    """Derive a temporary path alongside *target*.

    Appends ``.tmp`` to the filename so the temp file lives in the same
    directory as the target, guaranteeing same-filesystem rename.
    """
    return target.with_name(target.name + ".tmp")


# ---------------------------------------------------------------------------
# Atomic write helpers
# ---------------------------------------------------------------------------


def atomic_write_json(target: Path, data: object) -> None:
    """Atomically write *data* as JSON to *target*.

    Writes to a ``.tmp`` path first, then calls :func:`Path.rename`, which is
    atomic when source and destination are on the same filesystem (a hard
    requirement per tech-spec §3.5).
    """
    tmp = _temp_for(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    tmp.rename(target)


def atomic_write_text(target: Path, text: str) -> None:
    """Atomically write *text* to *target*.

    Same temp-then-rename protocol as :func:`atomic_write_json`.
    """
    tmp = _temp_for(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(text, encoding="utf-8")
    tmp.rename(target)


# ---------------------------------------------------------------------------
# .done marker
# ---------------------------------------------------------------------------

# The .done filename is intentionally an empty string prefix + the literal
# name ".done" — a hidden marker file.

_DONE_NAME = ".done"


def create_done_marker(dir_path: Path) -> Path:
    """Create a 0-byte ``.done`` file in *dir_path*.

    The directory (and any missing parents) is created if needed.

    Returns the path to the created marker so callers can verify it.
    """
    dir_path.mkdir(parents=True, exist_ok=True)
    done = dir_path / _DONE_NAME
    done.touch()
    return done


def is_done(dir_path: Path) -> bool:
    """Return ``True`` when *dir_path* contains a ``.done`` marker."""
    return (dir_path / _DONE_NAME).is_file()


def remove_done_marker(dir_path: Path) -> bool:
    """Remove the ``.done`` marker in *dir_path* if it exists.

    Returns ``True`` when a marker was actually removed.
    """
    done = dir_path / _DONE_NAME
    if done.is_file():
        done.unlink()
        return True
    return False
