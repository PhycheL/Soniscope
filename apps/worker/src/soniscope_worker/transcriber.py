"""Transcriber 抽象接口、工厂方法与本地占位实现（US-025，§5.3）。

把转写器抽象为可替换接口：业务流程只依赖 :class:`Transcriber` Protocol，不直接
依赖具体 provider 类。工厂方法 :func:`create_transcriber` 按 ``config.yaml`` 的
``transcriber.name`` 分发：

- ``cloud-speech``  → :class:`CloudSpeechTranscriber`（真实阿里云 NLS 调用在 US-026 接入）
- ``whisper-local`` → :class:`WhisperLocalTranscriber`（占位，``transcribe`` 抛
  ``NotImplementedError`` 且提示本期不部署本地 Whisper）

未知 ``transcriber.name`` 抛 :class:`TranscriberError`，并列出支持的取值。

``TranscriptResult`` 是转写结果的内存结构，额外含 ``duration``（音频总时长）字段；
``duration`` **不落盘**到 ``transcript.json``（时长已记录在 ``manifest.duration_seconds``）。
:meth:`TranscriptResult.transcript_json` 派生落盘用的五字段 dict（§3.4）。
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from soniscope_worker.config import TranscriberConfig

# transcript.json 只落盘这五个字段（§3.4），刻意排除内存态 ``duration``。
_TRANSCRIPT_JSON_FIELDS = ("segments", "language", "model", "params_version", "provider")

# 工厂方法支持的 transcriber.name 取值。
SUPPORTED_TRANSCRIBERS = ("cloud-speech", "whisper-local")


class TranscriberError(Exception):
    """转写器配置错误（未知 ``transcriber.name`` 等）。"""


@dataclass
class Segment:
    """单条转写片段（``transcript.json`` 中 ``segments[]`` 的一项）。"""

    start: float
    end: float
    text: str

    def as_dict(self) -> dict[str, Any]:
        """序列化为 ``transcript.json`` 中的片段 dict。"""
        return {"start": self.start, "end": self.end, "text": self.text}


@dataclass
class TranscriptResult:
    """转写结果内存结构（§5.3）。

    ``duration`` 仅内存使用，**不落盘**到 ``transcript.json``——音频时长已记录在
    ``manifest.duration_seconds``，避免重复存储。
    """

    segments: list[Segment]
    language: str
    model: str
    params_version: str
    provider: str
    duration: float

    def transcript_json(self) -> dict[str, Any]:
        """派生落盘用的 ``transcript.json``（§3.4）：五字段，剔除 ``duration``。"""
        return {
            "segments": [seg.as_dict() for seg in self.segments],
            "language": self.language,
            "model": self.model,
            "params_version": self.params_version,
            "provider": self.provider,
        }

    def as_result_dict(self) -> dict[str, Any]:
        """含内存态 ``duration`` 的完整 dict，兼容 ``manifest.transcript_json_from_result``。"""
        data = self.transcript_json()
        data["duration"] = self.duration
        return data


@runtime_checkable
class Transcriber(Protocol):
    """转写器抽象接口（§5.3）。业务流程只依赖此 Protocol，不感知具体 provider。"""

    def transcribe(
        self,
        fragment_id: str,
        audio_path: Path,
        oss_key: str,
    ) -> TranscriptResult: ...


class CloudSpeechTranscriber:
    """云端 ASR 转写器（阿里云 NLS，US-026）。

    真实调用逻辑在 :mod:`soniscope_worker.nls`：``upload_mode=oss-url`` 走录音文件识别
    （filetrans）签名 URL 拉取；``upload_mode=direct`` 走极速版（FlashRecognizer）本地直传。
    当日累计调用 / 时长计数（§6.8 成本日志）由本实例持有，跨日自动归零、不持久化。

    NLS 后端通过 ``backend`` 注入以便单测（不触网）；缺省构造 :class:`RealNlsBackend`。
    """

    name = "cloud-speech"

    def __init__(
        self,
        config: TranscriberConfig,
        *,
        backend: Any | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self._config = config
        self._backend = backend
        self._log = log
        # 延迟构造，避免无云 SDK 时 import 报错；同时持有跨调用的当日累计计数。
        from soniscope_worker.nls import DailyCounter

        self._counter = DailyCounter()

    @property
    def config(self) -> TranscriberConfig:
        return self._config

    def transcribe(
        self,
        fragment_id: str,
        audio_path: Path,
        oss_key: str,
    ) -> TranscriptResult:
        from soniscope_worker.nls import RealNlsBackend, transcribe_via_nls

        backend = self._backend if self._backend is not None else RealNlsBackend(self._config)
        return transcribe_via_nls(
            self._config,
            fragment_id,
            audio_path,
            oss_key,
            backend=backend,
            counter=self._counter,
            log=self._log,
        )


class WhisperLocalTranscriber:
    """``whisper-local`` 占位实现（§5.3）。本期不部署本地 Whisper。"""

    name = "whisper-local"

    def __init__(self, config: TranscriberConfig) -> None:
        self._config = config

    @property
    def config(self) -> TranscriberConfig:
        return self._config

    def transcribe(
        self,
        fragment_id: str,
        audio_path: Path,
        oss_key: str,
    ) -> TranscriptResult:
        raise NotImplementedError(
            "whisper-local 本期不部署本地 Whisper；"
            "请将 config.yaml 的 transcriber.name 设为 cloud-speech。"
        )


def create_transcriber(config: TranscriberConfig) -> Transcriber:
    """按 ``config.transcriber.name`` 分发转写器实例（§5.3 工厂方法）。

    业务侧拿到的是 :class:`Transcriber` 接口，不直接依赖具体 provider 类；
    切换 provider 只改 ``config.yaml``。未知 ``name`` 抛 :class:`TranscriberError`
    并列出支持的取值。
    """
    name = config.name
    if name == "cloud-speech":
        return CloudSpeechTranscriber(config)
    if name == "whisper-local":
        return WhisperLocalTranscriber(config)
    supported = ", ".join(SUPPORTED_TRANSCRIBERS)
    raise TranscriberError(
        f"未知 transcriber.name: {name!r}；支持的取值：{supported}。"
    )
