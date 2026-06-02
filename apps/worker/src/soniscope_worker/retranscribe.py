"""Explicit retranscription CLI — force, upgrade, and batch re-run of ASR.

Provides the ``retranscribe`` entry point called by ``cli.py`` as well as the
helper functions for scanning, locking, and comparing model/params_version.

US-028: The normal poll loop (poller.py) only checks ``.done`` to decide
idempotency (AC1).  This module is the *only* way to trigger a re-run for
fragments that already have a ``.done`` marker (AC5–AC7).

Usage::

    python -m soniscope_worker retranscribe <fragment_id> [--force] [--upgrade]
    python -m soniscope_worker retranscribe --all-from <YYYY-MM-DD> [--upgrade]
"""

from __future__ import annotations

import fcntl
import json as _json
import logging
from pathlib import Path
from typing import Any

from soniscope_worker.config import SoniScopeConfig, load_config, resolve_config_path
from soniscope_worker.paths import fragments_dir, resolve_home

logger = logging.getLogger("soniscope_worker.retranscribe")


# ---------------------------------------------------------------------------
# File lock — mutual exclusion for concurrent transcriptions (AC9)
# ---------------------------------------------------------------------------


def _os_open_lock(lock_file: Path) -> int | None:
    """Low-level: open+flock, return fd or None."""
    import os as _os

    fd = _os.open(str(lock_file), _os.O_CREAT | _os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        _os.close(fd)
        return None
    return fd


os_open_lock = _os_open_lock


def _release_lock(fd: int | None, lock_file: Path) -> None:
    """Release a previously acquired lock and remove the lock file."""
    if fd is not None:
        import os as _os

        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            _os.close(fd)
        except Exception:
            pass
    try:
        lock_file.unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Manifest comparison helpers
# ---------------------------------------------------------------------------


def _differs_from_config(
    manifest: dict[str, Any],
    config: SoniScopeConfig,
) -> bool:
    """Return ``True`` when the manifest's model or params_version differs.

    Used by ``--upgrade`` to decide whether a fragment needs re-transcription
    (AC7: only re-transcribe when model or params_version has changed).
    """
    tx = manifest.get("transcription")
    if tx is None or not isinstance(tx, dict):
        # Never transcribed — definitely needs transcription
        return True

    manifest_model: str = str(tx.get("model", ""))
    manifest_params: str = str(tx.get("params_version", ""))

    config_model: str = config.transcriber.model
    config_params: str = config.transcriber.params_version

    return manifest_model != config_model or manifest_params != config_params


def _needs_upgrade(frag_dir: Path, config: SoniScopeConfig) -> bool:
    """Check whether *frag_dir* needs upgrade re-transcription.

    Reads the fragment's ``manifest.json`` and compares ``model`` /
    ``params_version`` against the current Worker configuration.
    """
    manifest_path = frag_dir / "manifest.json"
    if not manifest_path.is_file():
        return False  # can't compare without a manifest
    try:
        manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    except (_json.JSONDecodeError, OSError):
        return False
    return _differs_from_config(manifest, config)


# ---------------------------------------------------------------------------
# Single-fragment retranscribe
# ---------------------------------------------------------------------------


def _retranscribe_one(
    *,
    frag_dir: Path,
    fragment_id: str,
    config: SoniScopeConfig,
    force: bool = False,
    upgrade: bool = False,
) -> str:
    """Retranscribe a single fragment directory.

    Returns one of ``"transcribed"``, ``"skipped_done"``, ``"skipped_upgrade"``,
    ``"locked"``, or ``"failed"``.

    Raises:
        FileNotFoundError: The fragment directory or its ``audio.wav`` does not exist.
    """
    from soniscope_worker.atomics import is_done, remove_done_marker

    if not frag_dir.is_dir():
        raise FileNotFoundError(f"Fragment directory not found: {frag_dir}")

    audio_wav = frag_dir / "audio.wav"
    if not audio_wav.is_file():
        raise FileNotFoundError(f"audio.wav not found in fragment directory: {frag_dir}")

    has_done = is_done(frag_dir)

    if has_done and not force and not upgrade:
        return "skipped_done"

    if has_done and upgrade and not _needs_upgrade(frag_dir, config):
        return "skipped_upgrade"

    # ── Acquire lock (AC9) ──────────────────────────────────────────────
    lock_file = frag_dir / ".retranscribe.lock"
    fd = os_open_lock(lock_file)
    if fd is None:
        return "locked"

    try:
        # Build OSS client for the transcriber (for oss-url mode presigned URLs)
        from soniscope_worker.poller import (
            _build_oss_client,
            _fragment_oss_key,
        )

        oss_key = _fragment_oss_key(fragment_id)
        client = _build_oss_client(config)

        # Remove .done before transcribing (so crash-safety: if we crash,
        # the poll loop will pick it up on restart)
        remove_done_marker(frag_dir)

        from soniscope_worker.poller import _run_transcription_pipeline

        _run_transcription_pipeline(
            frag_dir=frag_dir,
            fragment_id=fragment_id,
            audio_wav=audio_wav,
            config=config,
            client=client,
            oss_key=oss_key,
        )

        return "transcribed"
    except Exception:
        logger.exception("retranscribe_failed fragment_id=%s", fragment_id)
        return "failed"
    finally:
        _release_lock(fd, lock_file)


# ---------------------------------------------------------------------------
# Batch retranscribe — scan fragments under a date prefix
# ---------------------------------------------------------------------------


def _scan_fragment_dirs(
    home: Path,
    from_date: str,  # YYYY-MM-DD
) -> list[tuple[str, Path]]:
    """Return sorted ``(fragment_id, frag_dir)`` pairs for fragments on or
    after *from_date*.

    Each fragment must have an ``audio.wav`` file.  Fragments without it are
    silently skipped.
    """
    frags = fragments_dir(home)
    if not frags.is_dir():
        return []

    result: list[tuple[str, Path]] = []
    for date_dir in sorted(frags.iterdir()):
        if not date_dir.is_dir():
            continue
        if date_dir.name < from_date:
            continue
        for frag_dir in sorted(date_dir.iterdir()):
            if not frag_dir.is_dir():
                continue
            audio_wav = frag_dir / "audio.wav"
            if not audio_wav.is_file():
                continue
            result.append((frag_dir.name, frag_dir))

    return result


def run_retranscribe(
    *,
    fragment_id: str | None = None,
    all_from: str | None = None,
    force: bool = False,
    upgrade: bool = False,
    config: SoniScopeConfig | None = None,
) -> dict[str, int]:
    """Main retranscribe entry point (used by CLI and programmatic callers).

    Exactly one of *fragment_id* or *all_from* must be provided.

    Returns a summary dict with keys ``transcribed``, ``skipped_done``,
    ``skipped_upgrade``, ``locked``, ``failed``.
    """
    cfg = config or load_config(resolve_config_path())
    home = resolve_home()

    summary: dict[str, int] = {
        "transcribed": 0,
        "skipped_done": 0,
        "skipped_upgrade": 0,
        "locked": 0,
        "failed": 0,
    }

    if fragment_id is not None:
        # Single fragment
        from soniscope_worker.poller import _fragment_to_date

        date = _fragment_to_date(fragment_id)
        frag_dir = home / "fragments" / date / fragment_id

        status = _retranscribe_one(
            frag_dir=frag_dir,
            fragment_id=fragment_id,
            config=cfg,
            force=force,
            upgrade=upgrade,
        )
        summary[status] += 1

    elif all_from is not None:
        # Batch mode (AC8)
        entries = _scan_fragment_dirs(home, all_from)
        logger.info(
            "retranscribe_batch_start from_date=%s count=%d force=%s upgrade=%s",
            all_from,
            len(entries),
            force,
            upgrade,
        )
        for fid, frag_dir in entries:
            status = _retranscribe_one(
                frag_dir=frag_dir,
                fragment_id=fid,
                config=cfg,
                force=force,
                upgrade=upgrade,
            )
            summary[status] += 1
            if status in ("failed",):
                logger.warning(
                    "retranscribe_batch_item fragment_id=%s status=%s", fid, status
                )
        logger.info(
            "retranscribe_batch_done transcribed=%d skipped_done=%d "
            "skipped_upgrade=%d locked=%d failed=%d",
            summary["transcribed"],
            summary["skipped_done"],
            summary["skipped_upgrade"],
            summary["locked"],
            summary["failed"],
        )

    return summary
