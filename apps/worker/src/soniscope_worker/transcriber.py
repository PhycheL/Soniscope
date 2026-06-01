"""Transcriber abstract interface and factory for the SoniScope Worker.

Defines a :class:`Transcriber` Protocol that all ASR providers must
implement, along with a factory function :func:`create_transcriber` that
selects the implementation based on ``config.yaml``'s ``transcriber.name``.

US-025 provides the interface skeleton; the real cloud ASR logic is
implemented in US-026 (:class:`CloudSpeechTranscriber`), and the local
Whisper path is a placeholder for a future iteration.

Usage::

    from soniscope_worker.config import load_config
    from soniscope_worker.transcriber import create_transcriber

    cfg = load_config()
    transcriber = create_transcriber(cfg)
    result = transcriber.transcribe(fragment_id, audio_path, oss_key)
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from soniscope_worker.config import SoniScopeConfig, TranscriberConfig
from soniscope_worker.transcript import TranscriptResult, make_placeholder_result


# ---------------------------------------------------------------------------
# Transcriber Protocol (AC1)
# ---------------------------------------------------------------------------


@runtime_checkable
class Transcriber(Protocol):
    """Abstract interface for all ASR transcription providers.

    Every provider (cloud speech or local whisper) must implement this
    method so the Worker's main pipeline can treat them interchangeably
    (see AC7: business logic depends only on this interface).
    """

    def transcribe(
        self,
        fragment_id: str,
        audio_path: Path,
        oss_key: str,
    ) -> TranscriptResult:
        """Transcribe *audio_path* and return structured results.

        Args:
            fragment_id: The fragment identifier.
            audio_path: Path to the standardized ``audio.wav`` file.
            oss_key: The original OSS object key (for URL-mode ASR).

        Returns:
            A :class:`~soniscope_worker.transcript.TranscriptResult` with
            segments, language, model, params_version, provider metadata.
        """
        ...


# ---------------------------------------------------------------------------
# Cloud speech transcriber — skeleton (AC4, US-026 fills in the real logic)
# ---------------------------------------------------------------------------


class CloudSpeechTranscriber:
    """Cloud ASR transcriber using Alibaba Cloud NLS (AC4).

    In US-025 this returns a placeholder result so the interface,
    factory, and pipeline shape are testable.  US-026 replaces the body
    with the real NLS create-task / poll / fetch-result flow.
    """

    def __init__(self, config: TranscriberConfig) -> None:
        self._config = config

    @property
    def provider(self) -> str:
        """Expose the configured provider name (for logging / manifest)."""
        return self._config.provider

    def transcribe(
        self,
        fragment_id: str,
        audio_path: Path,
        oss_key: str,
    ) -> TranscriptResult:
        """Return a placeholder transcript (real ASR in US-026)."""
        return make_placeholder_result(
            language="zh",
            model=self._config.model,
            params_version=self._config.params_version,
            provider=self._config.provider,
        )


# ---------------------------------------------------------------------------
# Local whisper placeholder — raises NotImplementedError (AC5)
# ---------------------------------------------------------------------------


class WhisperLocalTranscriber:
    """Local Whisper placeholder (AC5) — not deployed in MVP.

    Calling :meth:`transcribe` always raises :class:`NotImplementedError`
    with a message pointing users to the cloud-speech alternative.
    """

    def transcribe(
        self,
        fragment_id: str,
        audio_path: Path,
        oss_key: str,
    ) -> TranscriptResult:
        """Raise :class:`NotImplementedError` — local Whisper is out of scope."""
        raise NotImplementedError(
            "本地 Whisper 转写本期不部署（MVP 仅支持云端 ASR）。"
            "请将 config.yaml 中 transcriber.name 设置为 'cloud-speech'。"
        )


# ---------------------------------------------------------------------------
# Factory (AC3, AC6)
# ---------------------------------------------------------------------------


def create_transcriber(config: SoniScopeConfig) -> Transcriber:
    """Create a :class:`Transcriber` instance based on *config* (AC3).

    ``transcriber.name`` values and the returned class (AC4/AC5):

    =================== ================================================
    transcriber.name     Class
    =================== ================================================
    ``cloud-speech``    :class:`CloudSpeechTranscriber`
    ``whisper-local``   :class:`WhisperLocalTranscriber`
    =================== ================================================

    Raises:
        ValueError: *transcriber.name* is not a supported value (AC6).
    """
    name = config.transcriber.name

    if name == "cloud-speech":
        return CloudSpeechTranscriber(config.transcriber)

    if name == "whisper-local":
        return WhisperLocalTranscriber()

    raise ValueError(
        f"未知的 transcriber.name: '{name}'。"
        f"支持的值: cloud-speech, whisper-local"
    )
