"""Worker OSS polling — list, HeadObject metadata, download, recovery scan.

Covers US-021: poll OSS recordings/ prefix, read x-oss-meta-* metadata,
download objects to .part, verify sha256 against x-oss-meta-sha256, and
clean up stale intermediates on startup.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alibabacloud_oss_v2 import Client as OSSClient

from soniscope_worker.config import SoniScopeConfig
from soniscope_worker.paths import (
    inbox_dir,
    resolve_home,
)

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


def recovery_scan(home: Path) -> list[str]:
    """Scan inbox/ for stale intermediate files and clean them up.

    Returns a list of removed file paths for logging purposes.

    **AC1**: ``<fragment_id>.part`` files → deleted, next poll re-downloads.
    """
    removed: list[str] = []
    inbox = inbox_dir(home)

    if not inbox.is_dir():
        return removed

    # Clean stale .part files (download interrupts)
    for part_file in sorted(inbox.glob("*.part")):
        try:
            part_file.unlink()
            removed.append(str(part_file))
        except OSError:
            pass

    # Clean stale .wav.tmp files (transcode interrupts — §3.6)
    for tmp_file in sorted(inbox.glob("*.wav.tmp")):
        try:
            tmp_file.unlink()
            removed.append(str(tmp_file))
        except OSError:
            pass

    return removed


# ---------------------------------------------------------------------------
# Main polling logic
# ---------------------------------------------------------------------------


def poll_cycle(config: SoniScopeConfig, client: "OSSClient") -> dict[str, int]:
    """Execute a single poll cycle.

    1. List OSS objects under ``recordings/``
    2. For each object not yet processed (no .done), read metadata via HeadObject
    3. Download to .part, verify sha256 against x-oss-meta-sha256

    Returns a summary dict with keys like ``total_objects``, ``skipped_done``,
    ``downloaded``, ``sha256_mismatch``, ``errors``.

    The manifest is NOT written to fragments/ in this story — that belongs
    to US-022 (format detection) and US-024 (manifest schema).
    """
    home = resolve_home()
    bucket = config.oss.bucket

    summary: dict[str, int] = {
        "total_objects": 0,
        "skipped_done": 0,
        "downloaded": 0,
        "sha256_mismatch": 0,
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

        if ok:
            summary["downloaded"] += 1
        else:
            summary["sha256_mismatch"] += 1
            # .part was already deleted by download_object — next cycle re-downloads

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
    if removed:
        logger.info(
            "recovery_scan_cleaned count=%d files=%s",
            len(removed),
            [Path(p).name for p in removed],
        )

    client = _build_oss_client(config)

    while True:
        cycle_start = time_mod.monotonic()
        logger.debug("poll_cycle_start")

        try:
            summary = poll_cycle(config, client)
            elapsed = time_mod.monotonic() - cycle_start
            logger.info(
                "poll_cycle_complete total=%d skipped_done=%d downloaded=%d "
                "mismatch=%d errors=%d elapsed=%.2fs",
                summary["total_objects"],
                summary["skipped_done"],
                summary["downloaded"],
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
