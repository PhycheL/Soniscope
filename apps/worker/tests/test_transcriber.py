"""US-025：Transcriber 工厂、占位实现与 TranscriptResult 序列化测试。"""

from pathlib import Path

import pytest

from soniscope_worker.config import TranscriberConfig
from soniscope_worker.manifest import transcript_json_from_result
from soniscope_worker.transcriber import (
    SUPPORTED_TRANSCRIBERS,
    CloudSpeechTranscriber,
    Segment,
    Transcriber,
    TranscriberError,
    TranscriptResult,
    WhisperLocalTranscriber,
    create_transcriber,
)


def _config(name: str = "cloud-speech") -> TranscriberConfig:
    return TranscriberConfig.model_validate(
        {
            "name": name,
            "provider": "aliyun-nls",
            "model": "中文普通话（识音石 V1 - 端到端模型)",
            "params_version": "v1",
            "api_endpoint": "cn-beijing",
            "appkey": "1k8tqkjQsq65wp2m",
            "access_key_id": "LTAItestkeyid",
            "access_key_secret": "testsecretvalue1234",
            "upload_mode": "oss-url",
        }
    )


def _result() -> TranscriptResult:
    return TranscriptResult(
        segments=[
            Segment(start=0.0, end=2.5, text="今天天气不错"),
            Segment(start=2.5, end=5.1, text="我准备去公园跑步"),
        ],
        language="zh",
        model="中文普通话（识音石 V1 - 端到端模型)",
        params_version="v1",
        provider="aliyun-nls",
        duration=24.0,
    )


# ── 工厂方法（AC#3 / #4 / #5 / #6 / #7）──────────────────────────────


def test_factory_returns_cloud_speech_instance() -> None:
    transcriber = create_transcriber(_config("cloud-speech"))
    assert isinstance(transcriber, CloudSpeechTranscriber)
    # 业务侧只依赖 Transcriber 接口（AC#7）。
    assert isinstance(transcriber, Transcriber)


def test_factory_returns_whisper_local_instance() -> None:
    transcriber = create_transcriber(_config("whisper-local"))
    assert isinstance(transcriber, WhisperLocalTranscriber)
    assert isinstance(transcriber, Transcriber)


def test_factory_unknown_name_raises_with_supported_values() -> None:
    with pytest.raises(TranscriberError) as exc:
        create_transcriber(_config("openai-whisper"))
    message = str(exc.value)
    assert "openai-whisper" in message
    for supported in SUPPORTED_TRANSCRIBERS:
        assert supported in message


# ── 占位实现（AC#4 cloud 留 US-026 / AC#5 whisper-local 抛错）────────


def test_whisper_local_transcribe_raises_not_implemented() -> None:
    transcriber = WhisperLocalTranscriber(_config("whisper-local"))
    with pytest.raises(NotImplementedError) as exc:
        transcriber.transcribe("frag", Path("/tmp/audio.wav"), "recordings/x.wav")
    assert "本地 Whisper" in str(exc.value)


def test_cloud_speech_transcribe_delegates_to_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    # US-026：CloudSpeechTranscriber.transcribe 委托注入的 NLS 后端，不再抛占位异常。
    import soniscope_worker.nls as nls

    monkeypatch.setattr(nls, "_probe_duration", lambda _p: 20.0)

    class _FakeBackend:
        def presign_oss_url(self, oss_key: str, expires_seconds: int) -> str:
            return f"https://signed/{oss_key}"

        def submit_oss_url(self, file_link: str) -> str:
            return "task-1"

        def poll_task(self, task_id: str) -> dict[str, object]:
            return {
                "StatusText": nls.STATUS_SUCCESS,
                "Result": {"Sentences": [{"BeginTime": 0, "EndTime": 1000, "Text": "你好"}]},
            }

        def transcribe_direct(self, audio_path: Path) -> dict[str, object]:
            raise AssertionError("oss-url 模式不应走 direct")

    transcriber = CloudSpeechTranscriber(
        _config("cloud-speech"),
        backend=_FakeBackend(),
        log=lambda _m: None,
    )
    result = transcriber.transcribe("frag", Path("/tmp/audio.wav"), "recordings/x.wav")
    assert result.provider == "aliyun-nls"
    assert result.duration == 20.0
    assert "".join(s.text for s in result.segments) == "你好"


def test_cloud_speech_keeps_config() -> None:
    cfg = _config("cloud-speech")
    transcriber = CloudSpeechTranscriber(cfg)
    assert transcriber.config is cfg


# ── TranscriptResult 序列化到 transcript.json 字段映射（AC#8）────────


def test_transcript_json_excludes_duration() -> None:
    data = _result().transcript_json()
    assert set(data) == {"segments", "language", "model", "params_version", "provider"}
    assert "duration" not in data


def test_transcript_json_segment_mapping() -> None:
    data = _result().transcript_json()
    assert data["segments"] == [
        {"start": 0.0, "end": 2.5, "text": "今天天气不错"},
        {"start": 2.5, "end": 5.1, "text": "我准备去公园跑步"},
    ]
    assert data["language"] == "zh"
    assert data["provider"] == "aliyun-nls"


def test_as_result_dict_includes_duration() -> None:
    data = _result().as_result_dict()
    assert data["duration"] == 24.0
    assert data["segments"][0]["text"] == "今天天气不错"


def test_as_result_dict_compatible_with_manifest_serializer() -> None:
    # manifest.transcript_json_from_result 接受含 duration 的 dict，落盘时剔除 duration。
    derived = transcript_json_from_result(_result().as_result_dict())
    assert "duration" not in derived
    assert derived == _result().transcript_json()


def test_segment_as_dict() -> None:
    assert Segment(1.0, 2.0, "你好").as_dict() == {"start": 1.0, "end": 2.0, "text": "你好"}
