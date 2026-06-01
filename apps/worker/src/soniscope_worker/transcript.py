"""Structured transcription output — ``transcript.json`` and ``transcript.txt``.

Covers US-024 AC5: every completed Fragment directory must contain a
``transcript.json`` (structured per tech-spec §3.4) and a ``transcript.txt``
(pure-text derived from segments).

The ``transcript.json`` structure is:

.. code:: json

    {
      "segments": [
        { "start": 0.0, "end": 2.5, "text": "..." },
        ...
      ],
      "language": "zh",
      "model": "...",
      "params_version": "v1",
      "provider": "aliyun-nls"
    }

``TranscriptResult.duration`` is NOT persisted to ``transcript.json`` — it
belongs in ``manifest.json`` as ``duration_seconds`` (tech-spec §3.4 note).

The ``transcript.txt`` is derived from ``transcript.json`` by concatenating
``segments[].text`` strings in order, separated by newlines.

For now the actual transcription results come from the ASR pipeline
(US-025/US-026).  This module provides the schema, validation, and write
helpers so the rest of the Worker can use them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from soniscope_worker.atomics import atomic_write_json, atomic_write_text


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TranscriptSegment:
    """A single timed transcription segment."""

    start: float = 0.0
    end: float = 0.0
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "text": self.text}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptSegment":
        return cls(
            start=float(data.get("start", 0)),
            end=float(data.get("end", 0)),
            text=str(data.get("text", "")),
        )


@dataclass
class TranscriptResult:
    """In-memory transcription result.

    ``duration`` is retained in memory for the caller but is NOT persisted to
    ``transcript.json`` (per tech-spec §3.4).
    """

    segments: list[TranscriptSegment] = field(default_factory=list)
    language: str = "zh"
    model: str = ""
    params_version: str = ""
    provider: str = ""
    duration: float = 0.0  # total audio duration (memory only — not serialized)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the ``transcript.json`` schema (without ``duration``)."""
        return {
            "segments": [seg.to_dict() for seg in self.segments],
            "language": self.language,
            "model": self.model,
            "params_version": self.params_version,
            "provider": self.provider,
        }

    def to_text(self) -> str:
        """Derive ``transcript.txt`` content from segments."""
        return "\n".join(seg.text for seg in self.segments)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptResult":
        segments = [TranscriptSegment.from_dict(s) for s in data.get("segments", [])]
        return cls(
            segments=segments,
            language=str(data.get("language", "zh")),
            model=str(data.get("model", "")),
            params_version=str(data.get("params_version", "")),
            provider=str(data.get("provider", "")),
            duration=float(data.get("duration", 0)),
        )


# ---------------------------------------------------------------------------
# Placeholder transcript for fragments that haven't been transcribed yet
# ---------------------------------------------------------------------------


def make_placeholder_result(
    *,
    language: str = "zh",
    model: str = "",
    params_version: str = "",
    provider: str = "",
) -> TranscriptResult:
    """Return a placeholder transcript for fragments pending ASR.

    This is written as ``transcript.json`` after audio.wav is placed but
    before the cloud ASR call runs.  The real transcription will atomically
    replace it later.

    Per AC5, the transcript files must exist in the completed fragment
    directory even before ASR runs — they hold placeholders that get
    overwritten during the transcription phase.
    """
    return TranscriptResult(
        segments=[],
        language=language,
        model=model,
        params_version=params_version,
        provider=provider,
        duration=0.0,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_transcript_json(data: dict[str, Any]) -> TranscriptResult:
    """Validate and parse a ``transcript.json`` dict.

    Returns a :class:`TranscriptResult`.  Raises :class:`ValueError` for
    missing or malformed required fields.
    """
    if not isinstance(data, dict):
        raise ValueError("transcript.json must be a JSON object")

    segments_raw = data.get("segments")
    if not isinstance(segments_raw, list):
        raise ValueError("transcript.json must have a 'segments' array")

    segments = []
    for i, seg in enumerate(segments_raw):
        if not isinstance(seg, dict):
            raise ValueError(f"segments[{i}] must be an object")
        segments.append(TranscriptSegment.from_dict(seg))

    return TranscriptResult(
        segments=segments,
        language=str(data.get("language", "zh")),
        model=str(data.get("model", "")),
        params_version=str(data.get("params_version", "")),
        provider=str(data.get("provider", "")),
        duration=float(data.get("duration", 0)),
    )


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def write_transcript_json(target: Path, result: TranscriptResult) -> None:
    """Atomically write *result* as ``transcript.json`` to *target*.

    Uses :func:`atomic_write_json` for crash-safe writes.
    """
    atomic_write_json(target, result.to_dict())


def write_transcript_txt(target: Path, result: TranscriptResult) -> None:
    """Atomically write ``transcript.txt`` from *result* to *target*.

    Uses :func:`atomic_write_text` for crash-safe writes.
    """
    atomic_write_text(target, result.to_text())


def derive_txt_from_json_path(json_path: Path) -> str:
    """Read ``transcript.json`` from *json_path* and return the derived .txt content.

    Returns an empty string when the segments list is empty or the file is
    unreadable.
    """
    import json as _json

    try:
        data = _json.loads(json_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, _json.JSONDecodeError, OSError):
        return ""

    segments: list[dict[str, Any]] = data.get("segments", []) if isinstance(data, dict) else []
    return "\n".join(
        str(seg.get("text", "")) for seg in segments
    )
