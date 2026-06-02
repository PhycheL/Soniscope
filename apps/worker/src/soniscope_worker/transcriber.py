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
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from alibabacloud_oss_v2 import Client as OSSClient

from soniscope_worker.config import SoniScopeConfig
from soniscope_worker.transcript import TranscriptResult


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


def create_transcriber(
    config: SoniScopeConfig,
    *,
    oss_client: "OSSClient | None" = None,
    oss_bucket: str = "",
) -> Transcriber:
    """Create a :class:`Transcriber` instance based on *config* (AC3).

    ``transcriber.name`` values and the returned class (AC4/AC5):

    =================== ================================================
    transcriber.name     Class
    =================== ================================================
    ``cloud-speech``    :class:`~nls_transcriber.CloudSpeechTranscriber`
    ``whisper-local``   :class:`WhisperLocalTranscriber`
    =================== ================================================

    When ``transcriber.name`` is ``cloud-speech`` and *oss_client* is
    provided the instance is ready for oss-url mode; without it, direct
    mode can still be used.

    Raises:
        ValueError: *transcriber.name* is not a supported value (AC6).
    """
    name = config.transcriber.name

    if name == "cloud-speech":
        # Delegate to the real NLS implementation (US-026).
        # We delay the import so the nls_transcriber module is only loaded
        # when the user actually chooses cloud-speech — this keeps
        # whisper-local runs free of the aliyunsdkcore dependency.
        from soniscope_worker.nls_transcriber import (  # noqa: PLC0415
            CloudSpeechTranscriber as NlsCloudSpeechTranscriber,
        )

        return NlsCloudSpeechTranscriber(
            config.transcriber,
            oss_client=oss_client,
            oss_bucket=oss_bucket,
        )

    if name == "whisper-local":
        return WhisperLocalTranscriber()

    raise ValueError(
        f"未知的 transcriber.name: '{name}'。"
        f"支持的值: cloud-speech, whisper-local"
    )
