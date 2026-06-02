"""Worker OSS polling — list, HeadObject metadata, download, recovery scan.

Covers US-021: poll OSS recordings/ prefix, read x-oss-meta-* metadata,
download objects to .part, verify sha256 against x-oss-meta-sha256, and
clean up stale intermediates on startup.

US-027 adds the full transcription pipeline integration: after audio.wav is
placed, the Worker calls the real ASR transcriber and atomically writes the
transcript files and .done marker.
"""

from __future__ import annotations

import hashlib
import logging
import time as time_mod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alibabacloud_oss_v2 import Client as OSSClient

from soniscope_worker.config import SoniScopeConfig
from soniscope_worker.paths import (
    fragments_dir,
    inbox_dir,
    resolve_home,
    tmp_dir,
)

logger = logging.getLogger("soniscope_worker.poller")

# Chunk size for streaming sha256 computation and download buffer operations.
_READ_CHUNK = 1024 * 1024  # 1 MiB


# ---------------------------------------------------------------------------
# Fragment ID → date / OSS key helpers
# ---------------------------------------------------------------------------


def _fragment_to_date(fragment_id: str) -> str:
    """Extract ``YYYY-MM-DD`` from fragment_id's timestamp prefix.

    Raises :class:`ValueError` when the fragment_id does not contain the
    expected ``<YYYYMMDD>T...`` prefix.
    """
    if "T" not in fragment_id:
        raise ValueError(
            f"Invalid fragment_id: no 'T' separator found: {fragment_id!r}"
        )
    date_part = fragment_id.split("T")[0]
    if len(date_part) != 8:
        raise ValueError(
            f"Invalid fragment_id date portion: {date_part!r} (from {fragment_id!r})"
        )
    yyyy = date_part[0:4]
    mm = date_part[4:6]
    dd = date_part[6:8]
    return f"{yyyy}-{mm}-{dd}"


def _fragment_oss_key(fragment_id: str) -> str:
    """Derive the OSS object key from a fragment_id.

    Format: ``recordings/<YYYY-MM-DD>/<fragment_id>.wav``
    """
    date_str = _fragment_to_date(fragment_id)
    return f"recordings/{date_str}/{fragment_id}.wav"


# ---------------------------------------------------------------------------
# OSS client builder (testable without real credentials)
# ---------------------------------------------------------------------------


def _build_oss_client(config: SoniScopeConfig) -> "OSSClient":
    """Build an OSS v2 SDK client from the Worker configuration."""
    import alibabacloud_oss_v2 as oss2

    creds = oss2.credentials.StaticCredentialsProvider(
        access_key_id=config.oss.access_key_id,
        access_key_secret=config.oss.access_key_secret,
    )
    cfg = oss2.config.load_default()
    cfg.credentials_provider = creds
    cfg.region = "cn-beijing"
    cfg.endpoint = config.oss.endpoint
    return oss2.Client(cfg)


# ---------------------------------------------------------------------------
# OSS HeadObject — read user metadata
# ---------------------------------------------------------------------------


class HeadMetaResult:
    """Parsed OSS user-defined metadata from a HeadObject response.

    Attributes match the ``x-oss-meta-*`` fields set by the mini-program
    during upload (see tech-spec §3.2).
    """

    __slots__ = (
        "found",
        "content_length",
        "etag",
        "last_modified",
        "session_id",
        "chunk_seq",
        "chunk_total",
        "recorded_at",
        "duration",
        "original_format",
        "sha256",
    )

    def __init__(
        self,
        *,
        found: bool = False,
        content_length: int | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
        session_id: str | None = None,
        chunk_seq: int | None = None,
        chunk_total: int | None = None,
        recorded_at: str | None = None,
        duration: str | None = None,
        original_format: str | None = None,
        sha256: str | None = None,
    ) -> None:
        self.found = found
        self.content_length = content_length
        self.etag = etag
        self.last_modified = last_modified
        self.session_id = session_id
        self.chunk_seq = chunk_seq
        self.chunk_total = chunk_total
        self.recorded_at = recorded_at
        self.duration = duration
        self.original_format = original_format
        self.sha256 = sha256

    def to_manifest_draft(self) -> dict[str, Any]:
        """Return a manifest draft dict from the OSS metadata fields.

        The returned dict matches the upload/* and top-level fields that
        the Worker fills from OSS metadata (see tech-spec §3.3).
        """
        result: dict[str, Any] = {}
        if self.session_id is not None:
            result["session_id"] = self.session_id
        if self.chunk_seq is not None:
            result["chunk_seq"] = self.chunk_seq
        if self.chunk_total is not None:
            result["chunk_total"] = self.chunk_total
        if self.recorded_at is not None:
            result["recorded_at"] = self.recorded_at
        if self.duration is not None:
            result["duration_seconds"] = float(self.duration)
        if self.original_format is not None:
            result["audio"] = result.get("audio", {})
            result["audio"]["original_format"] = self.original_format
        if self.sha256 is not None:
            result["upload"] = result.get("upload", {})
            result["upload"]["original_sha256"] = self.sha256
        if self.content_length is not None:
            result["upload"] = result.get("upload", {})
            result["upload"]["original_size_bytes"] = self.content_length
        return result


def head_oss_object(
    object_key: str,
    client: "OSSClient",
    bucket: str,
) -> HeadMetaResult:
    """Head an OSS object and return its user-defined metadata.

    Uses the OSS v2 SDK's ``head_object`` to read the object's headers,
    including all ``x-oss-meta-*`` user-defined metadata fields.
    """
    import alibabacloud_oss_v2 as oss2

    try:
        result = client.head_object(
            oss2.HeadObjectRequest(bucket=bucket, key=object_key)
        )
    except Exception as exc:
        # 404, 403, network errors all raised as exceptions by the SDK
        msg = str(exc)
        if "404" in msg or "NoSuchKey" in msg:
            return HeadMetaResult(found=False)
        raise RuntimeError(
            f"HeadObject failed for {object_key}: {msg}"
        ) from exc

    # Parse metadata (x-oss-meta-* is returned as a dict by the SDK)
    meta: dict[str, str] = result.metadata or {}

    chunk_seq_raw = meta.get("chunk-seq")
    chunk_total_raw = meta.get("chunk-total")

    return HeadMetaResult(
        found=True,
        content_length=result.content_length,
        etag=result.etag.strip('"') if result.etag else None,
        last_modified=(
            result.last_modified.isoformat() if result.last_modified else None
        ),
        session_id=meta.get("session-id"),
        chunk_seq=int(chunk_seq_raw) if chunk_seq_raw else None,
        chunk_total=int(chunk_total_raw) if chunk_total_raw else None,
        recorded_at=meta.get("recorded-at"),
        duration=meta.get("duration"),
        original_format=meta.get("original-format"),
        sha256=meta.get("sha256"),
    )


# ---------------------------------------------------------------------------
# OSS ListObjects — discover new objects
# ---------------------------------------------------------------------------


def list_oss_objects(
    client: "OSSClient",
    bucket: str,
    prefix: str = "recordings/",
) -> list[str]:
    """List all object keys under *prefix* in the OSS bucket.

    Returns a list of full OSS object keys (e.g.
    ``recordings/2026-06-03/20260603T120000_abc123_01J....wav``).

    Uses the v2 list API for consistency.
    """
    import alibabacloud_oss_v2 as oss2

    keys: list[str] = []
    continuation_token: str | None = None

    while True:
        request = oss2.ListObjectsV2Request(
            bucket=bucket,
            prefix=prefix,
            max_keys=200,
        )
        if continuation_token:
            request.continuation_token = continuation_token

        result = client.list_objects_v2(request)

        if result.contents:
            for obj in result.contents:
                if obj.key:
                    keys.append(obj.key)

        if result.is_truncated:
            continuation_token = result.next_continuation_token
        else:
            break

    return keys


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _sha256_hex(path: Path) -> str:
    """Compute the SHA-256 hex digest of *path*."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(_READ_CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download_object(
    object_key: str,
    client: "OSSClient",
    bucket: str,
    dest_part: Path,
    *,
    expected_sha256: str | None = None,
) -> bool:
    """Download an OSS object to *dest_part* (.part file).

    When *expected_sha256* is provided the downloaded file is verified
    after download and mismatches cause the .part to be deleted.

    Returns:
        ``True`` when the download and (optional) sha256 check succeeded.

    Raises:
        RuntimeError: on download failure (network error, etc.).
    """
    import alibabacloud_oss_v2 as oss2

    try:
        client.get_object_to_file(
            oss2.GetObjectRequest(bucket=bucket, key=object_key),
            str(dest_part),
        )
    except Exception as exc:
        raise RuntimeError(
            f"Download failed for {object_key}: {exc}"
        ) from exc

    # Verify sha256 if expected value is provided
    if expected_sha256 is not None:
        actual = _sha256_hex(dest_part)
        if actual != expected_sha256:
            dest_part.unlink(missing_ok=True)
            return False

    return True


# ---------------------------------------------------------------------------
# Fragment done-check
# ---------------------------------------------------------------------------


def is_fragment_done(home: Path, fragment_id: str) -> bool:
    """Return ``True`` when the fragment directory has a ``.done`` marker.

    The OSS object key is used to derive the expected fragment directory
    under ``fragments/<YYYY-MM-DD>/<fragment_id>/``.
    """
    date = _fragment_to_date(fragment_id)
    done_file = home / "fragments" / date / fragment_id / ".done"
    return done_file.is_file()


def oss_key_to_fragment_id(object_key: str) -> str:
    """Extract the fragment_id from an OSS object key.

    The key is expected to be of the form
    ``recordings/<YYYY-MM-DD>/<fragment_id>.wav``.

    Raises :class:`ValueError` if the key does not match the expected pattern.
    """
    # recordings/<date>/<fragment_id>.wav
    parts = object_key.rsplit("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Unexpected object key format: {object_key!r}")
    filename = parts[1]
    if not filename.endswith(".wav"):
        raise ValueError(f"Object key does not end with .wav: {object_key!r}")
    return filename[:-4]  # strip .wav


# ---------------------------------------------------------------------------
# Recovery scan — clean stale intermediates on startup
# ---------------------------------------------------------------------------


def recovery_scan(home: Path) -> dict[str, list[str]]:
    """Scan inbox/, tmp/ and fragments/ for stale intermediates on startup.

    Returns a dict with three keys:

    * ``inbox_cleaned`` — .part and .wav.tmp files removed (AC1, AC2)
    * ``tmp_cleaned`` — .transcript.json.tmp files removed (AC3)
    * ``fragment_actions`` — description strings noting fragments/ state (AC4)

    This is the comprehensive startup recovery scan required by US-023.
    """
    result: dict[str, list[str]] = {
        "inbox_cleaned": [],
        "tmp_cleaned": [],
        "fragment_actions": [],
    }

    # ── AC1: Clean stale .part files ──────────────────────────────────────
    # ── AC2: Clean stale .wav.tmp files ───────────────────────────────────
    inbox = inbox_dir(home)
    if inbox.is_dir():
        for part_file in sorted(inbox.glob("*.part")):
            try:
                part_file.unlink()
                result["inbox_cleaned"].append(str(part_file))
            except OSError:
                pass

        for wav_tmp in sorted(inbox.glob("*.wav.tmp")):
            try:
                wav_tmp.unlink()
                result["inbox_cleaned"].append(str(wav_tmp))
            except OSError:
                pass

    # ── AC3: Clean stale .transcript.json.tmp files in tmp/ ───────────────
    tmp = tmp_dir(home)
    if tmp.is_dir():
        for transcript_tmp in sorted(tmp.glob("*.transcript.json.tmp")):
            try:
                transcript_tmp.unlink()
                result["tmp_cleaned"].append(str(transcript_tmp))
            except OSError:
                pass

    # ── AC4: Scan fragments/ — classify each directory ────────────────────
    frags = fragments_dir(home)
    if not frags.is_dir():
        return result

    from soniscope_worker.atomics import is_done as _is_done

    for date_dir in sorted(frags.iterdir()):
        if not date_dir.is_dir():
            continue
        for frag_dir in sorted(date_dir.iterdir()):
            if not frag_dir.is_dir():
                continue
            audio_wav = frag_dir / "audio.wav"
            has_audio = audio_wav.is_file()
            has_done = _is_done(frag_dir)

            if has_done:
                # AC4: has .done → skip entirely
                result["fragment_actions"].append(
                    f"skip {frag_dir.name} (has .done)"
                )
            elif has_audio:
                # AC4: no .done but has audio.wav → needs transcription
                result["fragment_actions"].append(
                    f"resume {frag_dir.name} (audio present, needs transcription)"
                )
            else:
                # AC4: no .done, no audio.wav → empty directory, safe to remove
                try:
                    # Check if truly empty (no files at all)
                    if not any(frag_dir.iterdir()):
                        frag_dir.rmdir()
                        result["fragment_actions"].append(
                            f"removed empty dir {frag_dir.name}"
                        )
                    else:
                        result["fragment_actions"].append(
                            f"ignore {frag_dir.name} (no audio.wav)"
                        )
                except OSError:
                    result["fragment_actions"].append(
                        f"ignore {frag_dir.name} (cleanup failed)"
                    )

    return result


# ---------------------------------------------------------------------------
# Main polling logic
# ---------------------------------------------------------------------------


def _resume_incomplete_fragments(
    home: Path, config: SoniScopeConfig, client: "OSSClient"
) -> dict[str, int]:
    """Resume fragments that have audio.wav but no .done (AC4 crash recovery).

    Called once at startup after recovery_scan().  For each fragment directory
    under ``fragments/`` that has ``audio.wav`` but no ``.done``, run:
    manifest init → real ASR transcription → transcript write → .done.

    This provides crash-safe resumption per US-023 AC4 / US-027 AC5.
    """
    from soniscope_worker.atomics import is_done as _is_done

    result: dict[str, int] = {
        "resumed": 0,
        "resume_failed": 0,
    }

    frags = fragments_dir(home)
    if not frags.is_dir():
        return result

    for date_dir in sorted(frags.iterdir()):
        if not date_dir.is_dir():
            continue
        for frag_dir in sorted(date_dir.iterdir()):
            if not frag_dir.is_dir():
                continue
            audio_wav = frag_dir / "audio.wav"
            if not audio_wav.is_file():
                continue
            if _is_done(frag_dir):
                continue

            fragment_id = frag_dir.name
            manifest_path = frag_dir / "manifest.json"

            # If manifest.json doesn't exist yet, create a minimal one from
            # what we can infer (AC2: OSS object key → manifest skeleton)
            if not manifest_path.is_file():
                logger.info(
                    "resume_init_manifest fragment_id=%s (no manifest, building from audio)",
                    fragment_id,
                )
                try:
                    _write_minimal_manifest_from_audio(
                        manifest_path,
                        fragment_id=fragment_id,
                        audio_wav=audio_wav,
                        config=config,
                    )
                except Exception:
                    logger.exception(
                        "resume_manifest_failed fragment_id=%s", fragment_id
                    )
                    result["resume_failed"] += 1
                    continue

            # Run transcription
            try:
                _run_transcription_pipeline(
                    frag_dir=frag_dir,
                    fragment_id=fragment_id,
                    audio_wav=audio_wav,
                    config=config,
                    client=client,
                    oss_key=_fragment_oss_key(fragment_id),
                )
                result["resumed"] += 1
            except Exception:
                logger.exception(
                    "resume_transcribe_failed fragment_id=%s", fragment_id
                )
                result["resume_failed"] += 1

    return result


def _write_minimal_manifest_from_audio(
    manifest_target: Path,
    *,
    fragment_id: str,
    audio_wav: Path,
    config: SoniScopeConfig,
) -> None:
    """Build and write a minimal manifest.json when OSS metadata is unavailable.

    Used during crash recovery when the manifest was never written before
    the crash (we only have audio.wav on disk).
    """
    from soniscope_worker.manifest import write_manifest

    audio_sha256 = _sha256_hex(audio_wav)
    audio_size = audio_wav.stat().st_size

    head_meta: dict[str, Any] = {}
    audio_result: dict[str, Any] = {
        "audio_format": "wav",
        "original_format": "wav",
        "audio_sha256": audio_sha256,
        "original_sha256": "",
        "audio_size_bytes": audio_size,
        "original_size_bytes": 0,
        "mode": "passthrough",
    }

    write_manifest(
        manifest_target,
        fragment_id=fragment_id,
        head_meta=head_meta,
        audio_result=audio_result,
        config_model=config.transcriber.model,
        config_params_version=config.transcriber.params_version,
        config_provider=config.transcriber.provider,
        config_transcriber_name=config.transcriber.name,
        config_upload_mode=config.transcriber.upload_mode,
    )


def _run_transcription_pipeline(
    *,
    frag_dir: Path,
    fragment_id: str,
    audio_wav: Path,
    config: SoniScopeConfig,
    client: "OSSClient",
    oss_key: str,
) -> None:
    """Run the real ASR transcription and atomically write the outputs.

    Steps:
    1. Create transcriber via factory and call ``transcribe()``.
    2. Write ``transcript.json`` and ``transcript.txt`` atomically.
    3. Update ``manifest.json``'s ``transcription`` block.
    4. Create ``.done`` marker.

    This is the unified transcription pipeline used by both poll_cycle
    (new OSS objects) and _resume_incomplete_fragments (crash recovery).
    """
    import datetime as dt_mod

    from soniscope_worker.atomics import create_done_marker, remove_done_marker
    from soniscope_worker.manifest import update_manifest_with_transcription
    from soniscope_worker.atomics import atomic_write_json
    from soniscope_worker.transcriber import create_transcriber
    from soniscope_worker.transcript import (
        write_transcript_json,
        write_transcript_txt,
    )

    # Remove stale .done if it somehow exists (shouldn't, but be safe)
    remove_done_marker(frag_dir)

    # ── 1. ASR call ──
    transcriber = create_transcriber(
        config,
        oss_client=client,
        oss_bucket=config.oss.bucket,
    )

    t_start = time_mod.monotonic()
    try:
        transcript_result = transcriber.transcribe(
            fragment_id=fragment_id,
            audio_path=audio_wav,
            oss_key=oss_key,
        )
    except Exception:
        logger.exception(
            "transcription_failed fragment_id=%s", fragment_id
        )
        raise

    elapsed = time_mod.monotonic() - t_start

    # ── 2. Write transcript files ──
    write_transcript_json(frag_dir / "transcript.json", transcript_result)
    write_transcript_txt(frag_dir / "transcript.txt", transcript_result)

    # ── 3. Update manifest.json with transcription block ──
    manifest_path = frag_dir / "manifest.json"
    if manifest_path.is_file():
        import json as _json

        manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {}

    now = dt_mod.datetime.now(dt_mod.UTC).isoformat()
    if now.endswith("+00:00"):
        now = now[:-6] + "Z"

    update_manifest_with_transcription(
        manifest,
        started_at=now if manifest.get("upload", {}).get("uploaded_at") else (
            manifest.get("upload", {}).get("uploaded_at") or now
        ),
        completed_at=now,
        elapsed_seconds=round(elapsed, 2),
        transcriber=config.transcriber.name,
        model=config.transcriber.model,
        params_version=config.transcriber.params_version,
        provider=config.transcriber.provider,
        upload_mode=config.transcriber.upload_mode,
    )

    # Fill in started_at correctly by using the uploaded_at as a proxy when unavailable
    if "transcription" in manifest and manifest["transcription"] is not None:
        started = manifest["transcription"].get("started_at")
        if not started or started == now:
            # Use uploaded_at as approximate started_at
            uploaded = manifest.get("upload", {}).get("uploaded_at")
            if uploaded:
                manifest["transcription"]["started_at"] = uploaded
        manifest["transcription"]["started_at"] = manifest["transcription"].get("started_at", now)
        manifest["transcription"]["completed_at"] = now

    atomic_write_json(manifest_path, manifest)

    # ── 4. Create .done marker — last step (crash-safe) ──
    create_done_marker(frag_dir)
    logger.info(
        "transcription_complete fragment_id=%s segments=%d elapsed=%.2fs",
        fragment_id,
        len(transcript_result.segments),
        elapsed,
    )


def poll_cycle(config: SoniScopeConfig, client: "OSSClient") -> dict[str, int]:
    """Execute a single poll cycle.

    1. List OSS objects under ``recordings/``
    2. For each object not yet processed (no .done), read metadata via HeadObject
    3. Download to .part, verify sha256 against x-oss-meta-sha256
    4. Probe audio format, passthrough or transcode, and place audio.wav in
       the fragment directory (US-022).
    5. Write manifest.json (US-024).
    6. Call the real ASR transcriber and write transcript files (US-027).
    7. Create .done marker.

    Returns a summary dict with keys ``total_objects``, ``skipped_done``,
    ``downloaded``, ``sha256_mismatch``, ``passthrough``, ``transcoded``,
    ``transcode_failed``, ``transcribed``, ``transcribe_failed``,
    ``errors``.

    Any step failure before .done prevents the marker from being created,
    so the fragment will be retried on the next poll cycle (AC2).
    """
    from soniscope_worker.audio import process_audio

    home = resolve_home()
    bucket = config.oss.bucket

    summary: dict[str, int] = {
        "total_objects": 0,
        "skipped_done": 0,
        "downloaded": 0,
        "sha256_mismatch": 0,
        "passthrough": 0,
        "transcoded": 0,
        "transcode_failed": 0,
        "transcribed": 0,
        "transcribe_failed": 0,
        "errors": 0,
    }

    object_keys = list_oss_objects(client, bucket)
    summary["total_objects"] = len(object_keys)

    for obj_key in object_keys:
        # Derive fragment_id from object key
        try:
            fragment_id = oss_key_to_fragment_id(obj_key)
        except ValueError:
            # Non-conforming key — skip (not a soniscope fragment)
            continue

        # Skip if .done already exists
        if is_fragment_done(home, fragment_id):
            summary["skipped_done"] += 1
            continue

        # HeadObject to read metadata
        try:
            meta = head_oss_object(obj_key, client, bucket)
        except Exception:
            summary["errors"] += 1
            continue

        if not meta.found:
            # Object disappeared between list and head — skip
            continue

        # Download to inbox/<fragment_id>.part
        inbox = inbox_dir(home)
        inbox.mkdir(parents=True, exist_ok=True)
        part_path = inbox / f"{fragment_id}.part"

        try:
            ok = download_object(
                obj_key,
                client,
                bucket,
                part_path,
                expected_sha256=meta.sha256,
            )
        except Exception:
            summary["errors"] += 1
            continue

        if not ok:
            summary["sha256_mismatch"] += 1
            continue  # .part was already deleted by download_object — next cycle re-downloads

        summary["downloaded"] += 1

        # ── US-022: audio format detection, passthrough, transcode ──
        try:
            fragment_date = _fragment_to_date(fragment_id)
        except ValueError:
            summary["errors"] += 1
            continue

        audio_result = process_audio(
            part_path=part_path,
            fragment_id=fragment_id,
            fragment_date=fragment_date,
            original_format=meta.original_format or "unknown",
            original_sha256=meta.sha256 or "",
            original_size_bytes=meta.content_length or 0,
            home=home,
        )

        if not audio_result.ok:
            summary["transcode_failed"] += 1
            continue

        if audio_result.mode == "passthrough":
            summary["passthrough"] += 1
        elif audio_result.mode == "transcoded":
            summary["transcoded"] += 1

        # ── US-024: write manifest.json ──
        from soniscope_worker.manifest import write_manifest

        frag_dir = audio_result.dest_path.parent if audio_result.dest_path else None
        if frag_dir is None:
            summary["errors"] += 1
            continue

        # Build the audio_result dict for manifest builder
        audio_result_dict: dict[str, Any] = {
            "audio_format": audio_result.audio_format,
            "original_format": audio_result.original_format,
            "audio_sha256": audio_result.audio_sha256,
            "original_sha256": audio_result.original_sha256,
            "audio_size_bytes": audio_result.audio_size_bytes,
            "original_size_bytes": audio_result.original_size_bytes,
            "mode": audio_result.mode,
        }

        # Build head_meta dict from the HeadMetaResult
        head_meta_dict = meta.to_manifest_draft()

        manifest_target = frag_dir / "manifest.json"
        write_manifest(
            manifest_target,
            fragment_id=fragment_id,
            head_meta=head_meta_dict,
            audio_result=audio_result_dict,
            config_model=config.transcriber.model,
            config_params_version=config.transcriber.params_version,
            config_provider=config.transcriber.provider,
            config_transcriber_name=config.transcriber.name,
            config_upload_mode=config.transcriber.upload_mode,
        )

        # ── US-027: real ASR transcription ──
        audio_wav = frag_dir / "audio.wav"
        try:
            _run_transcription_pipeline(
                frag_dir=frag_dir,
                fragment_id=fragment_id,
                audio_wav=audio_wav,
                config=config,
                client=client,
                oss_key=obj_key,
            )
            summary["transcribed"] += 1
        except Exception:
            logger.exception(
                "poll_cycle.transcription_failed fragment_id=%s", fragment_id
            )
            summary["transcribe_failed"] += 1
            # .done is NOT created — fragment will be retried next cycle

    return summary


def run_poll_loop(config: SoniScopeConfig) -> None:
    """Run the poll → sleep → poll loop indefinitely.

    On startup this performs a recovery scan before the first poll cycle.
    Each cycle is separated by ``config.poll.interval_seconds`` seconds.
    """
    import logging
    import sys
    import time as time_mod

    # Set up simple logging to stdout
    logger = logging.getLogger("soniscope_worker.poller")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)

    home = resolve_home()
    interval = config.poll.interval_seconds

    # Allow test override via env var (for make test-poll-interval)
    env_override = __import__("os").environ.get(
        "POLL_INTERVAL_SECONDS_OVERRIDE"
    )
    if env_override is not None:
        interval = int(env_override)
        logger.info("poll_interval_override interval=%d", interval)

    # Startup recovery scan
    logger.info("worker_starting home=%s interval=%d", home, interval)
    removed = recovery_scan(home)
    inbox_count = len(removed["inbox_cleaned"])
    tmp_count = len(removed["tmp_cleaned"])
    frag_count = len(removed["fragment_actions"])
    if inbox_count > 0 or tmp_count > 0 or frag_count > 0:
        logger.info(
            "recovery_scan_summary inbox_cleaned=%d tmp_cleaned=%d fragments_scanned=%d",
            inbox_count,
            tmp_count,
            frag_count,
        )
        if inbox_count > 0:
            logger.info(
                "recovery_scan_cleaned_inbox count=%d files=%s",
                inbox_count,
                [Path(p).name for p in removed["inbox_cleaned"]],
            )
        if tmp_count > 0:
            logger.info(
                "recovery_scan_cleaned_tmp count=%d files=%s",
                tmp_count,
                [Path(p).name for p in removed["tmp_cleaned"]],
            )
        if frag_count > 0:
            for action in removed["fragment_actions"]:
                logger.info("recovery_scan_fragment: %s", action)

    client = _build_oss_client(config)

    # ── US-027 AC4/AC5: resume incomplete fragments from crash ──
    resume_result = _resume_incomplete_fragments(home, config, client)
    if resume_result["resumed"] > 0 or resume_result["resume_failed"] > 0:
        logger.info(
            "resume_summary resumed=%d failed=%d",
            resume_result["resumed"],
            resume_result["resume_failed"],
        )

    while True:
        cycle_start = time_mod.monotonic()
        logger.debug("poll_cycle_start")

        try:
            summary = poll_cycle(config, client)
            elapsed = time_mod.monotonic() - cycle_start
            logger.info(
                "poll_cycle_complete total=%d skipped_done=%d downloaded=%d "
                "passthrough=%d transcoded=%d transcode_failed=%d "
                "transcribed=%d transcribe_failed=%d "
                "mismatch=%d errors=%d elapsed=%.2fs",
                summary["total_objects"],
                summary["skipped_done"],
                summary["downloaded"],
                summary["passthrough"],
                summary["transcoded"],
                summary["transcode_failed"],
                summary["transcribed"],
                summary["transcribe_failed"],
                summary["sha256_mismatch"],
                summary["errors"],
                elapsed,
            )
        except Exception:
            logger.exception("poll_cycle_error")

        # Sleep until next cycle
        elapsed = time_mod.monotonic() - cycle_start
        sleep_seconds = max(0, interval - elapsed)
        logger.debug("poll_sleep seconds=%.1f", sleep_seconds)
        time_mod.sleep(sleep_seconds)
