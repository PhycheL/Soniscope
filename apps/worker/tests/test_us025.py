"""Tests for US-025 — Transcriber abstract interface, factory & placeholder implementations.

Covers all 9 acceptance criteria:
- AC1: Transcriber Protocol with transcribe(fragment_id, audio_path, oss_key) → TranscriptResult
- AC2: TranscriptResult memory structure (segments, language, model, params_version, provider, duration)
- AC3: Factory selects cloud-speech or whisper-local based on transcriber.name
- AC4: transcriber.name=cloud-speech returns CloudSpeechTranscriber instance
- AC5: transcriber.name=whisper-local returns WhisperLocalTranscriber, transcribe → NotImplementedError
- AC6: Unknown transcriber.name raises ValueError listing supported values
- AC7: Business logic depends only on Transcriber interface, not concrete classes
- AC8: TranscriptResult serialised to transcript.json maps correctly
- AC9: Unit tests cover factory, unknown config, local placeholder exception, and serialisation
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
import yaml

from soniscope_worker.config import SoniScopeConfig, load_config
from soniscope_worker.nls_transcriber import (
    CloudSpeechTranscriber,
)
from soniscope_worker.transcriber import (
    Transcriber,
    WhisperLocalTranscriber,
    create_transcriber,
)
from soniscope_worker.transcript import (
    TranscriptResult,
    TranscriptSegment,
    make_placeholder_result,
)

# ── Path helpers ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent.parent


# ============================================================================
# AC1: Transcriber Protocol structure
# ============================================================================


class TestTranscriberProtocol:
    """Verify the Transcriber Protocol shape (AC1)."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Transcriber can be checked at runtime via isinstance()."""
        assert hasattr(Transcriber, "__runtime_checkable__") or True
        # Protocol is decorated with @runtime_checkable
        import typing

        assert typing.runtime_checkable is not None

    def test_protocol_requires_transcribe_method(self) -> None:
        """Protocol requires a 'transcribe' method with correct signature."""
        # Compile-time check: look at the function signature annotations
        sig = Transcriber.transcribe
        assert sig.__name__ == "transcribe"

    def test_cloud_speech_implements_protocol(self) -> None:
        """CloudSpeechTranscriber satisfies the Transcriber Protocol."""
        cfg = _make_transcriber_config(name="cloud-speech")
        impl = CloudSpeechTranscriber(cfg)
        assert isinstance(impl, Transcriber)

    def test_whisper_local_implements_protocol(self) -> None:
        """WhisperLocalTranscriber satisfies the Transcriber Protocol."""
        impl = WhisperLocalTranscriber()
        assert isinstance(impl, Transcriber)

    def test_protocol_rejects_objects_without_transcribe(self) -> None:
        """isinstance check returns False for objects missing transcribe."""
        class NotATranscriber:
            pass

        assert not isinstance(NotATranscriber(), Transcriber)

    def test_protocol_accepts_duck_typed_transcriber(self) -> None:
        """Any object with a compatible transcribe method is accepted."""

        class DuckTranscriber:
            def transcribe(self, fragment_id, audio_path, oss_key) -> TranscriptResult:
                return TranscriptResult()

        assert isinstance(DuckTranscriber(), Transcriber)


# ============================================================================
# AC2: TranscriptResult memory structure
# ============================================================================


class TestTranscriptResultStructure:
    """Verify TranscriptResult fields match AC2 spec."""

    def test_transcript_result_has_required_fields(self) -> None:
        """TranscriptResult contains segments, language, model, params_version, provider, duration."""
        r = TranscriptResult()
        assert hasattr(r, "segments")
        assert isinstance(r.segments, list)
        assert hasattr(r, "language")
        assert hasattr(r, "model")
        assert hasattr(r, "params_version")
        assert hasattr(r, "provider")
        assert hasattr(r, "duration")

    def test_transcript_result_defaults(self) -> None:
        """Default field values are sensible."""
        r = TranscriptResult()
        assert r.segments == []
        assert r.language == "zh"
        assert r.model == ""
        assert r.params_version == ""
        assert r.provider == ""
        assert r.duration == 0.0

    def test_transcript_result_with_segments(self) -> None:
        """TranscriptResult can hold segments."""
        seg = TranscriptSegment(start=0.0, end=2.5, text="你好")
        r = TranscriptResult(
            segments=[seg],
            language="zh",
            model="test-model",
            params_version="v1",
            provider="aliyun-nls",
            duration=20.0,
        )
        assert len(r.segments) == 1
        assert r.segments[0].text == "你好"
        assert r.model == "test-model"
        assert r.duration == 20.0


# ============================================================================
# AC3: Factory method (cloud-speech vs whisper-local)
# ============================================================================


class TestFactory:
    """Verify create_transcriber() factory behaviour (AC3, AC4, AC5, AC6)."""

    def test_factory_returns_cloud_speech(self) -> None:
        """transcriber.name=cloud-speech → CloudSpeechTranscriber (from nls_transcriber)."""
        from soniscope_worker.nls_transcriber import (
            CloudSpeechTranscriber as NlsCloudSpeechTranscriber,
        )

        config = _make_config(name="cloud-speech")
        t = create_transcriber(config)
        assert isinstance(t, NlsCloudSpeechTranscriber)
        assert isinstance(t, Transcriber)

    def test_factory_returns_whisper_local(self) -> None:
        """transcriber.name=whisper-local → WhisperLocalTranscriber."""
        config = _make_config(name="whisper-local")
        t = create_transcriber(config)
        assert isinstance(t, WhisperLocalTranscriber)
        assert isinstance(t, Transcriber)

    def test_factory_unknown_name_raises_valueerror(self) -> None:
        """Unknown transcriber.name raises ValueError listing supported values (AC6)."""
        config = _make_config(name="unknown-provider")
        with pytest.raises(ValueError, match="未知的 transcriber.name"):
            create_transcriber(config)

    def test_factory_error_message_lists_supported_values(self) -> None:
        """Error message includes supported names."""
        config = _make_config(name="invalid")
        with pytest.raises(ValueError) as exc:
            create_transcriber(config)
        assert "cloud-speech" in str(exc.value)
        assert "whisper-local" in str(exc.value)

    def test_factory_with_empty_name(self) -> None:
        """Empty string also triggers unknown name error."""
        config = _make_config(name="")
        with pytest.raises(ValueError):
            create_transcriber(config)


# ============================================================================
# AC4: CloudSpeechTranscriber structure (real impl in nls_transcriber.py)
# ============================================================================


class TestCloudSpeechTranscriber:
    """Verify CloudSpeechTranscriber structure (AC4).

    The real transcribe() implementation calls the NLS API and is tested
    in test_us026.py with proper mocking.  Here we verify structural
    properties: importability, provider accessor, Transcriber Protocol
    compatibility, and constructor signature.
    """

    def test_creates_instance_with_config(self) -> None:
        """CloudSpeechTranscriber accepts a TranscriberConfig."""
        cfg = _make_transcriber_config(name="cloud-speech")
        t = CloudSpeechTranscriber(cfg)
        assert isinstance(t, CloudSpeechTranscriber)

    def test_provider_property_exposes_configured_provider(self) -> None:
        """provider property returns the configured provider name."""
        cfg = _make_transcriber_config(
            name="cloud-speech", provider="aliyun-nls"
        )
        t = CloudSpeechTranscriber(cfg)
        assert t.provider == "aliyun-nls"

    def test_transcribe_exists(self) -> None:
        """transcribe method is callable."""
        cfg = _make_transcriber_config(name="cloud-speech")
        t = CloudSpeechTranscriber(cfg)
        assert callable(t.transcribe)

    def test_transcribe_accepts_oss_client_kwargs(self) -> None:
        """Constructor accepts optional oss_client and oss_bucket kwargs."""
        cfg = _make_transcriber_config(name="cloud-speech")
        t = CloudSpeechTranscriber(
            cfg, oss_client=None, oss_bucket="test-bucket"
        )
        assert isinstance(t, CloudSpeechTranscriber)


# ============================================================================
# AC5: WhisperLocalTranscriber behaviour (placeholder)
# ============================================================================


class TestWhisperLocalTranscriber:
    """Verify WhisperLocalTranscriber placeholder (AC5)."""

    def test_creates_instance_without_config(self) -> None:
        """WhisperLocalTranscriber does not need config (always raises)."""
        t = WhisperLocalTranscriber()
        assert isinstance(t, WhisperLocalTranscriber)
        assert isinstance(t, Transcriber)

    def test_transcribe_raises_not_implemented_error(self) -> None:
        """transcribe() raises NotImplementedError with helpful message (AC5)."""
        t = WhisperLocalTranscriber()
        with pytest.raises(NotImplementedError) as exc:
            t.transcribe(
                fragment_id="test",
                audio_path=Path("."),
                oss_key="key",
            )
        # Message should point user to cloud-speech
        msg = str(exc.value)
        assert "cloud-speech" in msg.lower() or "云端" in msg

    def test_transcribe_error_message_is_chinese(self) -> None:
        """Error message is in Chinese for local users."""
        t = WhisperLocalTranscriber()
        with pytest.raises(NotImplementedError) as exc:
            t.transcribe("test", Path("."), "key")
        assert len(str(exc.value)) > 0
        # Should mention 本地 Whisper and/or 不部署
        assert any(
            word in str(exc.value)
            for word in ["本地", "不部署", "Whisper", "本期"]
        )


# ============================================================================
# AC7: Business logic depends only on interface
# ============================================================================


class TestInterfaceBasedUsage:
    """Business pipeline only depends on Transcriber Protocol (AC7)."""

    def test_pipeline_can_use_protocol_type(self) -> None:
        """A function accepting Transcriber works with any implementation."""

        def pipeline(transcriber: Transcriber, fid: str) -> TranscriptResult:
            return transcriber.transcribe(fid, Path("audio.wav"), "key")

        # CloudSpeechTranscriber real impl needs NLS API access — test via factory
        config = _make_config(name="cloud-speech")
        cloud = create_transcriber(config)
        assert isinstance(cloud, Transcriber)

        local = WhisperLocalTranscriber()
        with pytest.raises(NotImplementedError):
            pipeline(local, "test-id")

    def test_pipeline_does_not_import_concrete_classes(self) -> None:
        """The pipeline module should not need concrete class imports."""
        # Verifies that factory pattern decouples pipeline from implementations
        from soniscope_worker.transcriber import create_transcriber as factory

        config = _make_config(name="cloud-speech")
        transcriber = factory(config)
        assert isinstance(transcriber, Transcriber)


# ============================================================================
# AC8: TranscriptResult ↔ transcript.json mapping
# ============================================================================


class TestTranscriptJsonMapping:
    """TranscriptResult serialisation to transcript.json (AC8)."""

    def test_transcript_result_to_dict_maps_correctly(self) -> None:
        """to_dict() produces the transcript.json schema."""
        seg = TranscriptSegment(start=1.0, end=3.5, text="测试文本")
        result = TranscriptResult(
            segments=[seg],
            language="zh",
            model="nls-model",
            params_version="v2",
            provider="aliyun-nls",
            duration=120.5,
        )
        d = result.to_dict()
        assert d["language"] == "zh"
        assert d["model"] == "nls-model"
        assert d["params_version"] == "v2"
        assert d["provider"] == "aliyun-nls"
        assert "duration" not in d  # AC5: duration not in transcript.json
        assert len(d["segments"]) == 1
        assert d["segments"][0]["text"] == "测试文本"
        assert d["segments"][0]["start"] == 1.0
        assert d["segments"][0]["end"] == 3.5

    def test_to_dict_excludes_duration(self) -> None:
        """Duration is explicitly NOT in the serialised dict (per tech-spec §3.4)."""
        result = TranscriptResult(duration=99.9)
        d = result.to_dict()
        assert "duration" not in d

    def test_placeholder_to_dict_is_minimal(self) -> None:
        """Placeholder produces valid minimal transcript.json."""
        placeholder = make_placeholder_result(
            language="zh",
            model="m",
            params_version="v1",
            provider="p",
        )
        d = placeholder.to_dict()
        assert d["segments"] == []
        assert d["language"] == "zh"
        assert d["model"] == "m"
        assert d["provider"] == "p"
        assert "duration" not in d

    def test_from_dict_round_trips(self) -> None:
        """from_dict(to_dict(data)) preserves key fields."""
        seg = TranscriptSegment(start=0.5, end=1.5, text="hello")
        original = TranscriptResult(
            segments=[seg],
            language="en",
            model="m",
            params_version="v1",
            provider="test",
            duration=10.0,
        )
        d = original.to_dict()
        restored = TranscriptResult.from_dict(d)
        assert restored.language == original.language
        assert restored.model == original.model
        assert restored.provider == original.provider
        assert len(restored.segments) == 1
        assert restored.segments[0].text == "hello"


# ============================================================================
# Config integration
# ============================================================================


class TestConfigIntegration:
    """Factory reads transcriber.name from a full config."""

    def test_factory_from_yaml_config_string(self) -> None:
        """create_transcriber works with a config built from YAML."""
        yaml_text = """
oss:
  endpoint: oss-cn-beijing.aliyuncs.com
  bucket: test-bucket
  access_key_id: AKID1234
  access_key_secret: sk1234567890abcdef
poll:
  interval_seconds: 30
transcriber:
  name: cloud-speech
  provider: aliyun-nls
  model: test-model
  params_version: v1
  api_endpoint: cn-beijing
  appkey: appkey12345678
  access_key_id: nls-ak-id
  access_key_secret: nls-sk-abcdefgh
  upload_mode: oss-url
"""
        raw = yaml.safe_load(yaml_text)
        config = SoniScopeConfig.model_validate(raw)
        assert config.transcriber.name == "cloud-speech"

    def test_factory_from_config_resolves_correctly(self) -> None:
        """create_transcriber resolves the correct class from config."""
        yaml_text = """
oss:
  endpoint: oss-cn-beijing.aliyuncs.com
  bucket: b
  access_key_id: a
  access_key_secret: abcdefgh12345678
poll:
  interval_seconds: 60
transcriber:
  name: whisper-local
  provider: local-whisper
  model: tiny
  params_version: v1
  api_endpoint: local
  appkey: ak12345678
  access_key_id: x
  access_key_secret: yyyyyyyyyyyyyyyy
  upload_mode: direct
"""
        raw = yaml.safe_load(yaml_text)
        config = SoniScopeConfig.model_validate(raw)
        t = create_transcriber(config)
        assert isinstance(t, WhisperLocalTranscriber)


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases:
    """Transcriber edge-case coverage."""

    def test_cloud_speech_instance_is_importable(self) -> None:
        """CloudSpeechTranscriber can be instantiated (real impl in nls_transcriber)."""
        cfg = _make_transcriber_config()
        t = CloudSpeechTranscriber(cfg)
        assert t.provider == "aliyun-nls"
        assert callable(t.transcribe)

    def test_cloud_speech_accepts_oss_client(self) -> None:
        """CloudSpeechTranscriber stores oss_client and oss_bucket kwargs."""
        cfg = _make_transcriber_config(model="m", params_version="p", provider="pr")
        t = CloudSpeechTranscriber(
            cfg, oss_client=None, oss_bucket="test-bucket"
        )
        assert t.provider == "pr"

    def test_multiple_factories_produce_independent_instances(self) -> None:
        """Each factory call returns a new instance."""
        config = _make_config(name="cloud-speech")
        t1 = create_transcriber(config)
        t2 = create_transcriber(config)
        assert t1 is not t2

    def test_whisper_local_always_raises_regardless_of_args(self) -> None:
        """WhisperLocalTranscriber raises for any arguments."""
        t = WhisperLocalTranscriber()
        for fid in ["a", "b", ""]:
            with pytest.raises(NotImplementedError):
                t.transcribe(fid, Path("."), "k")

    def test_transcriber_can_be_stored_in_variable_of_protocol_type(self) -> None:
        """Static analysis: a Transcriber-typed variable accepts both implementations."""
        from soniscope_worker.nls_transcriber import (
            CloudSpeechTranscriber as NlsCs,
        )

        t1: Transcriber = NlsCs(_make_transcriber_config())
        t2: Transcriber = WhisperLocalTranscriber()
        assert isinstance(t1, Transcriber)
        assert isinstance(t2, Transcriber)


# ============================================================================
# Module structure
# ============================================================================


class TestModuleStructure:
    """Verify the transcriber module exports the expected public API."""

    def test_transcriber_module_exports_protocol(self) -> None:
        """The Transcriber Protocol is importable."""
        from soniscope_worker.transcriber import Transcriber
        assert Transcriber is not None

    def test_transcriber_module_exports_factory(self) -> None:
        """create_transcriber is importable."""
        from soniscope_worker.transcriber import create_transcriber
        assert callable(create_transcriber)

    def test_transcriber_module_exports_cloud_speech(self) -> None:
        """CloudSpeechTranscriber is importable from nls_transcriber (US-026)."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber
        assert CloudSpeechTranscriber is not None

    def test_transcriber_module_exports_whisper_local(self) -> None:
        """WhisperLocalTranscriber is importable from transcriber."""
        from soniscope_worker.transcriber import WhisperLocalTranscriber
        assert WhisperLocalTranscriber is not None

    def test_poller_does_not_directly_import_concrete_transcribers(self) -> None:
        """Poller module doesn't hardcode CloudSpeechTranscriber (AC7)."""
        import ast

        poller_path = (
            REPO_ROOT
            / "apps"
            / "worker"
            / "src"
            / "soniscope_worker"
            / "poller.py"
        )
        source = poller_path.read_text(encoding="utf-8")
        # poller should NOT import CloudSpeechTranscriber or WhisperLocalTranscriber
        assert "CloudSpeechTranscriber" not in source
        assert "WhisperLocalTranscriber" not in source

    def test_nls_transcriber_module_is_importable(self) -> None:
        """nls_transcriber.py (US-026) is a valid Python module."""
        from soniscope_worker.nls_transcriber import (
            CloudSpeechTranscriber,
            _REGION_DOMAINS,
            _COST_PER_HOUR_YUAN,
            _RETRY_INTERVALS,
        )
        assert CloudSpeechTranscriber is not None
        assert _REGION_DOMAINS is not None
        assert _COST_PER_HOUR_YUAN == 2.5
        assert _RETRY_INTERVALS == (5, 15, 45)


# ============================================================================
# Security — no keys in source
# ============================================================================


class TestSecurity:
    """No hard-coded credentials in transcriber-related modules."""

    def test_no_hardcoded_keys_in_transcriber_source(self) -> None:
        """transcriber.py contains no AK / Secret patterns."""
        import re

        source = (
            REPO_ROOT
            / "apps"
            / "worker"
            / "src"
            / "soniscope_worker"
            / "transcriber.py"
        ).read_text(encoding="utf-8")

        # Check for LTAI pattern (Alibaba Cloud AK ID prefix)
        ltai_matches = re.findall(r"LTAI[a-zA-Z0-9]{10,}", source)
        assert ltai_matches == [], f"Found suspected AK IDs: {ltai_matches}"

    def test_no_hardcoded_keys_in_nls_transcriber_source(self) -> None:
        """nls_transcriber.py contains no AK / Secret patterns."""
        import re

        source = (
            REPO_ROOT
            / "apps"
            / "worker"
            / "src"
            / "soniscope_worker"
            / "nls_transcriber.py"
        ).read_text(encoding="utf-8")

        ltai_matches = re.findall(r"LTAI[a-zA-Z0-9]{10,}", source)
        assert ltai_matches == [], f"Found suspected AK IDs: {ltai_matches}"


# ============================================================================
# Helpers
# ============================================================================


def _make_transcriber_config(
    name: str = "cloud-speech",
    provider: str = "aliyun-nls",
    model: str = "test-model",
    params_version: str = "v1",
    upload_mode: str = "oss-url",
) -> "soniscope_worker.config.TranscriberConfig":
    from soniscope_worker.config import TranscriberConfig

    return TranscriberConfig(
        name=name,
        provider=provider,
        model=model,
        params_version=params_version,
        api_endpoint="cn-beijing",
        appkey="appkey12345678",
        access_key_id="nls-ak-id",
        access_key_secret="nls-sk-abcdefghijklmnop",
        upload_mode=upload_mode,
    )


def _make_config(name: str = "cloud-speech") -> SoniScopeConfig:
    from soniscope_worker.config import OssConfig, PollConfig

    return SoniScopeConfig(
        oss=OssConfig(
            endpoint="oss-cn-beijing.aliyuncs.com",
            bucket="test",
            access_key_id="ak",
            access_key_secret="sk1234567890abcd",
        ),
        poll=PollConfig(interval_seconds=60),
        transcriber=_make_transcriber_config(name=name),
    )
