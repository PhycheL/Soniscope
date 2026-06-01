"""Audio format detection, WAV passthrough, and non-WAV transcoding.

Covers US-022: use ffprobe to detect real audio format, pass through compliant
WAV (or losslessly repackage), transcode m4a/aac/mp3/amr/etc. to WAV via ffmpeg,
and handle transcode failures by archiving to ``inbox/failed/``.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from soniscope_worker.paths import (
    fragments_dir,
    inbox_dir,
    inbox_failed_dir,
    resolve_home,
)

logger = logging.getLogger("soniscope_worker.audio")

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class AudioProbeResult:
    """Result of running ffprobe on an audio file."""

    format_name: str = ""
    codec_name: str = ""
    duration_seconds: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    bit_depth: int | None = None

    # Whether ffprobe itself succeeded (file is valid audio).
    valid: bool = False
    error: str = ""

    @property
    def is_wav(self) -> bool:
        """Return True when the detected format is ``wav``."""
        return self.valid and self.format_name.lower() == "wav"

    @property
    def is_compliant_wav(self) -> bool:
        """Return True for WAV with PCM int16 LE codec (our canonical format).

        Compliant WAV means the file can be passed through without transcoding
        or with only a lossless repackage.
        """
        return (
            self.valid
            and self.format_name.lower() == "wav"
            and self.codec_name.lower() in ("pcm_s16le", "pcm_s16be", "pcm_f32le", "pcm_u8")
        )


@dataclass
class AudioProcessResult:
    """Result of processing audio from download to fragment directory."""

    fragment_id: str = ""
    # True when processing succeeded (audio.wav is in place).
    ok: bool = False
    # Source path (.part file).
    source_path: Path | None = None
    # Destination path (audio.wav in fragments/).
    dest_path: Path | None = None
    # Audio metadata after processing.
    audio_format: str = "wav"
    original_format: str = ""
    audio_sha256: str = ""
    original_sha256: str = ""
    audio_size_bytes: int = 0
    original_size_bytes: int = 0
    # How was the audio.wav produced?
    mode: str = ""  # "passthrough" | "transcoded"
    # Error message (only when ok=False).
    error: str = ""


# ---------------------------------------------------------------------------
# ffprobe / ffmpeg wrappers
# ---------------------------------------------------------------------------

# Standard ffmpeg WAV output settings: PCM signed 16-bit little-endian, 44.1kHz, mono.
# We standardise on mono because speech ASR doesn't benefit from stereo.
_FFMPEG_WAV_ARGS: tuple[str, ...] = (
    "-acodec", "pcm_s16le",
    "-ar", "44100",
    "-ac", "1",
)


def _run_ffprobe(path: Path) -> dict[str, str]:
    """Run ffprobe on *path* and return key=value pairs.

    Uses JSON output from ffprobe for robust field extraction regardless of
    the output order.
    """
    cmd: list[str] = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format=format_name,duration:stream=codec_name,sample_rate,channels,bits_per_raw_sample",
        "-of", "json",
        str(path),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffprobe exited {proc.returncode} for {path}: {proc.stderr.strip()}"
        )

    import json as _json

    data = _json.loads(proc.stdout)
    result: dict[str, str] = {}

    # Extract format fields
    fmt = data.get("format", {})
    result["format_name"] = fmt.get("format_name", "")
    result["duration"] = fmt.get("duration", "0")

    # Extract stream fields (first audio stream)
    streams = data.get("streams", [])
    if streams:
        stream = streams[0]
        result["codec_name"] = stream.get("codec_name", "")
        result["sample_rate"] = str(stream.get("sample_rate", ""))
        result["channels"] = str(stream.get("channels", ""))
        # bits_per_raw_sample may be missing (N/A in ffprobe)
        bs = stream.get("bits_per_raw_sample", "")
        result["bit_depth"] = str(bs) if bs else ""

    return result


def probe_audio(path: Path) -> AudioProbeResult:
    """Detect the audio format of *path* using ffprobe.

    Doesn't rely on file extension — reads the real container/codec.
    """
    try:
        raw = _run_ffprobe(path)
    except (RuntimeError, FileNotFoundError) as exc:
        return AudioProbeResult(
            valid=False,
            error=str(exc),
        )

    try:
        duration = float(raw.get("duration", "0"))
    except (ValueError, TypeError):
        duration = 0.0

    sample_rate = int(raw.get("sample_rate", "0")) if raw.get("sample_rate", "").isdigit() else 0
    channels = int(raw.get("channels", "0")) if raw.get("channels", "").isdigit() else 0
    bit_depth_raw = raw.get("bit_depth", "")
    bit_depth: int | None = int(bit_depth_raw) if bit_depth_raw and bit_depth_raw.isdigit() else None

    return AudioProbeResult(
        format_name=raw.get("format_name", "").strip('"'),
        codec_name=raw.get("codec_name", ""),
        duration_seconds=duration,
        sample_rate=sample_rate,
        channels=channels,
        bit_depth=bit_depth,
        valid=True,
    )


def transcode_to_wav(src: Path, dest: Path) -> None:
    """Transcode *src* to PCM WAV at *dest* using ffmpeg.

    Args:
        src: Source audio file (any format ffmpeg can read).
        dest: Destination .wav file path (should be a ``.tmp`` path for atomic
            rename compliance).

    Raises:
        RuntimeError: If ffmpeg exits non-zero.
    """
    cmd: list[str] = [
        "ffmpeg",
        "-y",           # overwrite
        "-i", str(src),
        "-f", "wav",    # explicitly force WAV output format
        *_FFMPEG_WAV_ARGS,
        str(dest),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minutes for long files
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg transcode failed for {src}: {proc.stderr.strip()}"
        )


# ---------------------------------------------------------------------------
# Main processing pipeline — called from poll_cycle after download
# ---------------------------------------------------------------------------


def _sha256_hex(path: Path) -> str:
    """Compute SHA-256 hex digest of *path*."""
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def process_audio(
    *,
    part_path: Path,
    fragment_id: str,
    fragment_date: str,
    original_format: str,
    original_sha256: str,
    original_size_bytes: int,
    home: Path | None = None,
) -> AudioProcessResult:
    """Detect format, pass through or transcode, and atomically place audio.wav.

    This is the main audio processing entry point called after a successful
    download (the .part file exists and sha256 matches x-oss-meta-sha256).

    Steps:
    1. ffprobe the .part to get the real format (not just extension/OSS key).
    2. If compliant WAV → copy to ``fragments/<date>/<id>/audio.wav`` (passthrough).
    3. If non-WAV or non-compliant WAV → ffmpeg transcode to
       ``inbox/<id>.wav.tmp``, then atomic rename to ``audio.wav``.
    4. On transcode failure → archive the .part to ``inbox/failed/``.

    Args:
        part_path: Path to the downloaded .part file.
        fragment_id: The fragment identifier.
        fragment_date: Date string ``YYYY-MM-DD`` for the fragment subdirectory.
        original_format: OSS meta ``original-format`` (what the frontend recorded).
        original_sha256: The hex sha256 from OSS meta (frontend-computed).
        original_size_bytes: The file size from OSS Content-Length.
        home: Runtime home directory; resolved automatically when ``None``.

    Returns:
        :class:`AudioProcessResult` with ``ok=True`` when audio.wav was placed,
        or ``ok=False`` with ``error`` set.
    """
    root = home or resolve_home()
    frag_dir = fragments_dir(root) / fragment_date / fragment_id
    dest_wav = frag_dir / "audio.wav"
    inbox = inbox_dir(root)

    result = AudioProcessResult(
        fragment_id=fragment_id,
        source_path=part_path,
        dest_path=dest_wav,
        original_format=original_format,
        original_sha256=original_sha256,
        original_size_bytes=original_size_bytes,
    )

    # 1. Probe the real audio format
    probe = probe_audio(part_path)
    if not probe.valid:
        # Cannot even read the file → archive as failed
        failed_dir = inbox_failed_dir(root)
        failed_dir.mkdir(parents=True, exist_ok=True)
        failed_path = failed_dir / f"{fragment_id}.part"
        try:
            shutil.move(str(part_path), str(failed_path))
        except OSError as exc:
            logger.error(
                "process_audio.move_failed probe_invalid fragment_id=%s error=%s",
                fragment_id,
                exc,
            )
        result.error = f"ffprobe failed: {probe.error}"
        return result

    # Use detected format as the authoritative original_format when the OSS
    # meta field is missing or unreliable.
    detected_format = probe.format_name.lower()
    effective_original = original_format or detected_format

    # 2. Decide passthrough vs transcode
    if probe.is_compliant_wav:
        # Compliant WAV — passthrough
        logger.debug(
            "process_audio.passthrough fragment_id=%s format=%s codec=%s",
            fragment_id,
            probe.format_name,
            probe.codec_name,
        )
        _atomic_copy_or_rename(part_path, dest_wav)
        result.mode = "passthrough"
    else:
        # Non-WAV or non-compliant WAV — transcode
        logger.debug(
            "process_audio.transcode fragment_id=%s detected_format=%s original_format=%s",
            fragment_id,
            detected_format,
            effective_original,
        )
        tmp_path = inbox / f"{fragment_id}.wav.tmp"

        try:
            transcode_to_wav(part_path, tmp_path)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            # Transcode failed → archive to inbox/failed/
            failed_dir = inbox_failed_dir(root)
            failed_dir.mkdir(parents=True, exist_ok=True)
            failed_path = failed_dir / f"{fragment_id}.part"
            try:
                shutil.move(str(part_path), str(failed_path))
            except OSError:
                pass
            # Also clean up tmp if it exists
            tmp_path.unlink(missing_ok=True)
            result.error = f"ffmpeg transcode failed: {exc}"
            logger.error(
                "process_audio.transcode_failed fragment_id=%s error=%s",
                fragment_id,
                exc,
            )
            return result

        # Atomically rename the tmp to the final audio.wav
        _atomic_rename(tmp_path, dest_wav)
        # Clean up the .part — no longer needed after successful transcode
        part_path.unlink(missing_ok=True)
        result.mode = "transcoded"

    # 3. Compute final audio metadata
    result.audio_size_bytes = dest_wav.stat().st_size
    result.audio_sha256 = _sha256_hex(dest_wav)
    result.audio_format = "wav"
    result.original_format = effective_original
    result.ok = True

    logger.info(
        "process_audio.complete fragment_id=%s mode=%s "
        "original_format=%s audio_size=%d audio_sha256=%s",
        fragment_id,
        result.mode,
        effective_original,
        result.audio_size_bytes,
        result.audio_sha256[:12],
    )

    return result


# ---------------------------------------------------------------------------
# Atomic file helpers
# ---------------------------------------------------------------------------


def _atomic_rename(src: Path, dest: Path) -> None:
    """Atomically rename *src* to *dest*, creating parent directories.

    Uses :func:`Path.rename` which is atomic when source and destination
    are on the same filesystem (a hard requirement per tech-spec §3.5).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)


def _atomic_copy_or_rename(src: Path, dest: Path) -> None:
    """Copy *src* to *dest* and unlink *src*.

    For the WAV passthrough path we prefer rename when on the same filesystem,
    falling back to copy + unlink.  The .part file is always removed after
    successful placement.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        src.rename(dest)
    except OSError:
        shutil.copy2(src, dest)
        src.unlink(missing_ok=True)
