"""Build and atomically write Fragment ``manifest.json`` per tech-spec §3.3.

The manifest is the single authoritative schema for each Fragment directory.
It combines metadata from three sources:

* **Fragment ID parsing** — ``fragment_id`` and ``device_id`` are derived from the
  fragment_id string.
* **OSS user-defined metadata** — ``session_id``, ``chunk_seq``, ``chunk_total``,
  ``recorded_at``, ``duration_seconds``, ``audio.original_format``,
  ``upload.original_sha256``, ``upload.original_size_bytes`` come from the
  ``HeadMetaResult`` returned by HeadObject (see poller.py).
* **Local audio computation** — ``audio.sha256``, ``audio.size_bytes``,
  ``audio.format`` come from ``AudioProcessResult`` (see audio.py).

The ``transcription`` block is initially empty (set to ``null``) and populated
later by the ASR transcription pipeline (US-025 / US-026).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from soniscope_worker.atomics import atomic_write_json

# ---------------------------------------------------------------------------
# Fragment ID parsing
# ---------------------------------------------------------------------------


def parse_fragment_id(fragment_id: str) -> dict[str, str | None]:
    """Parse ``device_id`` from a fragment_id string.

    Fragment ID format: ``<YYYYMMDDTHHMMSS>_<deviceShortId>_<26-char-ULID>``

    Returns a dict with ``device_id`` (the middle ``deviceShortId`` segment)
    and the original ``fragment_id``.  When the fragment_id doesn't contain
    two underscores the ``device_id`` is ``None``.
    """
    parts = fragment_id.split("_", 2)
    if len(parts) >= 2:
        device_id = parts[1]
    else:
        device_id = None
    return {"device_id": device_id}


# ---------------------------------------------------------------------------
# manifest.json builder
# ---------------------------------------------------------------------------


def build_manifest(
    *,
    fragment_id: str,
    head_meta: dict[str, Any],
    audio_result: dict[str, Any],
    config_model: str = "",
    config_params_version: str = "",
    config_provider: str = "",
    config_transcriber_name: str = "",
    config_upload_mode: str = "",
    now: str | None = None,
) -> dict[str, Any]:
    """Build the full manifest.json dict for a Fragment.

    This assembles all fields defined in tech-spec §3.3: top-level identifiers,
    ``audio`` block, ``upload`` block, and ``transcription`` block.

    Args:
        fragment_id: The fragment identifier (from OSS object key).
        head_meta: A dict produced by ``HeadMetaResult.to_manifest_draft()``.
        audio_result: A dict with the local audio computation results:
            ``audio_format``, ``original_format``, ``audio_sha256``,
            ``original_sha256``, ``audio_size_bytes``, ``original_size_bytes``,
            ``mode``.
        config_model: The ASR model name from Worker configuration.
        config_params_version: The params version from Worker configuration.
        config_provider: The ASR provider from Worker configuration.
        config_transcriber_name: The transcriber factory name from config.
        config_upload_mode: The upload mode from config (``oss-url`` or ``direct``).
        now: ISO-8601 timestamp string for the current time; defaults to
            ``datetime.datetime.now(datetime.UTC).isoformat()`` when ``None``.

    Returns:
        A dict suitable for serialization as ``manifest.json``.
    """
    parsed = parse_fragment_id(fragment_id)

    # Derive from head_meta (OSS metadata)
    session_id = head_meta.get("session_id")
    chunk_seq = head_meta.get("chunk_seq")
    chunk_total_raw = head_meta.get("chunk_total")
    recorded_at = head_meta.get("recorded_at")
    duration_seconds = head_meta.get("duration_seconds")

    upload_original_sha256 = head_meta.get("upload", {}).get("original_sha256", "")
    upload_original_size_bytes = head_meta.get("upload", {}).get("original_size_bytes")

    # chunk_total == 0 means non-sharded → manifest stores null
    chunk_total: int | None
    if chunk_total_raw is not None and chunk_total_raw > 0:
        chunk_total = chunk_total_raw
    else:
        chunk_total = None

    # audio block from audio_result
    audio_format = audio_result.get("audio_format", "wav")
    audio_original_format = head_meta.get("audio", {}).get("original_format", "unknown")
    audio_sha256 = audio_result.get("audio_sha256", "")
    audio_size_bytes = audio_result.get("audio_size_bytes", 0)

    # Current timestamp for upload.uploaded_at
    uploaded_at = now or datetime.datetime.now(datetime.UTC).isoformat()
    # Replace '+00:00' with 'Z' for UTC (ISO 8601 compact form)
    if uploaded_at.endswith("+00:00"):
        uploaded_at = uploaded_at[:-6] + "Z"

    manifest: dict[str, Any] = {
        "fragment_id": fragment_id,
        "session_id": session_id,
        "chunk_seq": chunk_seq,
        "chunk_total": chunk_total,
        "device_id": parsed["device_id"],
        "recorded_at": recorded_at,
        "duration_seconds": duration_seconds if duration_seconds is not None else 0.0,
        "audio": {
            "format": audio_format,
            "original_format": audio_original_format,
            "size_bytes": audio_size_bytes,
            "sha256": audio_sha256,
        },
        "upload": {
            "uploaded_at": uploaded_at,
            "verified_at": None,
            "verify_method": "fc-head-object",
            "original_sha256": upload_original_sha256,
            "original_size_bytes": upload_original_size_bytes,
        },
        "transcription": None,
    }

    # Record transcriber metadata if available (populated later by US-025/US-026,
    # but we store what we know now so the manifest is self-consistent)
    if config_transcriber_name:
        manifest["transcription_spec"] = {
            "transcriber": config_transcriber_name,
            "model": config_model,
            "params_version": config_params_version,
            "provider": config_provider,
            "upload_mode": config_upload_mode,
        }

    return manifest


def update_manifest_with_transcription(
    manifest: dict[str, Any],
    *,
    started_at: str,
    completed_at: str,
    elapsed_seconds: float,
    transcriber: str,
    model: str,
    params_version: str,
    provider: str,
    upload_mode: str,
) -> dict[str, Any]:
    """Populate the ``transcription`` block of a manifest dict.

    Called after ASR transcription completes (US-025/US-026).
    Returns the mutated dict (the caller owns it).
    """
    manifest["transcription"] = {
        "started_at": started_at,
        "completed_at": completed_at,
        "elapsed_seconds": elapsed_seconds,
        "transcriber": transcriber,
        "model": model,
        "params_version": params_version,
        "provider": provider,
        "upload_mode": upload_mode,
    }
    return manifest


# ---------------------------------------------------------------------------
# Convenience: build + atomically write manifest.json in one go
# ---------------------------------------------------------------------------


def write_manifest(
    target: Path,
    *,
    fragment_id: str,
    head_meta: dict[str, Any],
    audio_result: dict[str, Any],
    config_model: str = "",
    config_params_version: str = "",
    config_provider: str = "",
    config_transcriber_name: str = "",
    config_upload_mode: str = "",
    now: str | None = None,
) -> dict[str, Any]:
    """Build and atomically write ``manifest.json`` to *target*.

    Uses :func:`atomic_write_json` so the file write is safe against crashes.
    The ``.tmp`` → rename protocol guarantees the on-disk manifest is never
    partially written.

    Returns the built manifest dict for inspection / testing.
    """
    manifest = build_manifest(
        fragment_id=fragment_id,
        head_meta=head_meta,
        audio_result=audio_result,
        config_model=config_model,
        config_params_version=config_params_version,
        config_provider=config_provider,
        config_transcriber_name=config_transcriber_name,
        config_upload_mode=config_upload_mode,
        now=now,
    )
    atomic_write_json(target, manifest)
    return manifest
