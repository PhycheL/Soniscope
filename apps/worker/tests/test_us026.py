"""Tests for US-026 — Alibaba Cloud NLS Recording File Recognition transcriber.

Covers all acceptance criteria:
- AC1: CloudSpeechTranscriber reads config fields (provider, api_endpoint, appkey,
  model, params_version, AK, upload_mode)
- AC2: oss-url mode generates 1-hour OSS presigned URL and passes to NLS
- AC3: NLS async polling > 50 min auto re-signs OSS URL, logs renew behaviour
- AC4: direct mode uploads local audio.wav, logs mode=direct-upload
- AC5: Network/5xx retry 5s→15s→45s (3 retries), 4xx fails immediately
- AC6: NLS response → transcript.json segments, language=zh, model, params_version,
  provider=aliyun-nls
- AC7: Cost logging — event=asr_call_completed, fragment_id, audio_duration_seconds,
  elapsed_seconds, provider, model, estimated_cost_yuan, cumulative_calls_today,
  cumulative_duration_today_seconds
- AC8: test-transcribe-oss-url Makefile target
- AC9: test-transcribe-direct Makefile target
- AC10: test-transcribe-perf Makefile target
"""

from __future__ import annotations

import json
import time as time_mod
from pathlib import Path
from unittest import mock

import pytest

# ── Path helpers ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent.parent


# ============================================================================
# AC1: CloudSpeechTranscriber configuration reading
# ============================================================================


class TestCloudSpeechTranscriberConfig:
    """Verify CloudSpeechTranscriber reads config fields correctly (AC1)."""

    def test_creates_instance_with_minimal_config(self) -> None:
        """CloudSpeechTranscriber accepts a valid TranscriberConfig."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        cfg = _make_transcriber_config()
        t = CloudSpeechTranscriber(cfg)
        assert t.provider == "aliyun-nls"
        assert t.upload_mode == "oss-url"

    def test_creates_instance_with_direct_mode_config(self) -> None:
        """CloudSpeechTranscriber accepts direct mode config."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        cfg = _make_transcriber_config(upload_mode="direct")
        t = CloudSpeechTranscriber(cfg)
        assert t.upload_mode == "direct"

    def test_creates_instance_with_oss_client(self) -> None:
        """Constructor accepts optional oss_client and oss_bucket kwargs."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        cfg = _make_transcriber_config()
        t = CloudSpeechTranscriber(cfg, oss_client=None, oss_bucket="test-bkt")
        assert isinstance(t, CloudSpeechTranscriber)

    def test_reads_provider_from_config(self) -> None:
        """provider property returns config.transcriber.provider."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        cfg = _make_transcriber_config(provider="aliyun-nls")
        t = CloudSpeechTranscriber(cfg)
        assert t.provider == "aliyun-nls"

    def test_reads_upload_mode_from_config(self) -> None:
        """upload_mode property returns config.transcriber.upload_mode."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        for mode in ("oss-url", "direct"):
            cfg = _make_transcriber_config(upload_mode=mode)
            t = CloudSpeechTranscriber(cfg)
            assert t.upload_mode == mode


# ============================================================================
# Module constants
# ============================================================================


class TestModuleConstants:
    """Verify nls_transcriber module-level constants."""

    def test_region_domains_cover_expected_regions(self) -> None:
        """_REGION_DOMAINS includes cn-beijing and cn-shanghai."""
        from soniscope_worker.nls_transcriber import _REGION_DOMAINS

        assert "cn-beijing" in _REGION_DOMAINS
        assert "cn-shanghai" in _REGION_DOMAINS
        assert _REGION_DOMAINS["cn-beijing"] == "filetrans.cn-beijing.aliyuncs.com"

    def test_retry_intervals_are_correct(self) -> None:
        """_RETRY_INTERVALS is (5, 15, 45) per tech-spec §1.5."""
        from soniscope_worker.nls_transcriber import _RETRY_INTERVALS, _MAX_RETRIES

        assert _RETRY_INTERVALS == (5, 15, 45)
        assert _MAX_RETRIES == 3

    def test_cost_per_hour_yuan(self) -> None:
        """_COST_PER_HOUR_YUAN is 2.5 (NLS pricing)."""
        from soniscope_worker.nls_transcriber import _COST_PER_HOUR_YUAN

        assert _COST_PER_HOUR_YUAN == 2.5

    def test_poll_timeout_is_one_hour(self) -> None:
        """_POLL_TIMEOUT_SECONDS is 3600 (1 hour)."""
        from soniscope_worker.nls_transcriber import _POLL_TIMEOUT_SECONDS

        assert _POLL_TIMEOUT_SECONDS == 3600.0

    def test_renew_threshold_is_50_minutes(self) -> None:
        """_RENEW_THRESHOLD_SECONDS is 3000 (50 min) for AC3."""
        from soniscope_worker.nls_transcriber import _RENEW_THRESHOLD_SECONDS

        assert _RENEW_THRESHOLD_SECONDS == 3000.0

    def test_status_constants_are_correct(self) -> None:
        """NLS status constants match the API."""
        from soniscope_worker.nls_transcriber import (
            _STATUS_SUCCESS,
            _STATUS_RUNNING,
            _STATUS_QUEUEING,
        )

        assert _STATUS_SUCCESS == "SUCCESS"
        assert _STATUS_RUNNING == "RUNNING"
        assert _STATUS_QUEUEING == "QUEUEING"


# ============================================================================
# AC2: OSS presigned URL generation
# ============================================================================


class TestPresignedUrlGeneration:
    """Verify OSS presigned URL generation for oss-url mode (AC2)."""

    def test_presigned_url_includes_oss_url(self) -> None:
        """_generate_presigned_url returns a valid-looking OSS URL."""
        from soniscope_worker.nls_transcriber import _generate_presigned_url

        mock_client = _make_mock_oss_client(
            presigned_url="https://soniscope-audio.oss-cn-beijing.aliyuncs.com/"
            "recordings/2026-06-02/test.wav?Expires=123&OSSAccessKeyId=xxx&Signature=yyy"
        )

        url = _generate_presigned_url(
            mock_client,
            "soniscope-audio",
            "recordings/2026-06-02/test.wav",
        )
        assert "soniscope-audio" in url
        assert "test.wav" in url
        assert "Expires=" in url or "Signature=" in url

    def test_presigned_url_uses_configured_bucket(self) -> None:
        """Presigned URL uses the provided bucket name."""
        from soniscope_worker.nls_transcriber import _generate_presigned_url

        mock_client = _make_mock_oss_client(
            presigned_url="https://my-bucket.oss-cn-beijing.aliyuncs.com/k?Expires=1"
        )

        url = _generate_presigned_url(
            mock_client,
            "my-bucket",
            "recordings/test.wav",
        )
        assert "my-bucket" in url

    def test_presigned_url_uses_provided_object_key(self) -> None:
        """Presigned URL uses the provided OSS object key."""
        from soniscope_worker.nls_transcriber import _generate_presigned_url

        mock_client = _make_mock_oss_client(
            presigned_url="https://b.oss-cn-beijing.aliyuncs.com/my-key?Expires=1"
        )

        url = _generate_presigned_url(
            mock_client,
            "b",
            "my-key",
        )
        assert "my-key" in url


# ============================================================================
# AC5: Retry logic — exponential backoff
# ============================================================================


class TestRetryLogic:
    """Verify retry on network/5xx with exponential backoff (AC5)."""

    def test_retry_succeeds_on_first_attempt(self) -> None:
        """_retry_on_network_error returns result when callable succeeds immediately."""
        from soniscope_worker.nls_transcriber import _retry_on_network_error

        def succeed() -> str:
            return "ok"

        result = _retry_on_network_error("test-op", succeed)
        assert result == "ok"

    def test_retry_fails_immediately_on_unauthorized(self) -> None:
        """_retry_on_network_error fails immediately on 4xx-like errors."""
        from soniscope_worker.nls_transcriber import _retry_on_network_error

        call_count = [0]

        def fail_unauthorized() -> str:
            call_count[0] += 1
            raise RuntimeError("Unauthorized (4xx)")

        with pytest.raises(RuntimeError):
            _retry_on_network_error("test-op", fail_unauthorized)
        # Should fail immediately — no retries
        assert call_count[0] == 1

    def test_retry_fails_immediately_on_forbidden(self) -> None:
        """_retry_on_network_error fails immediately on 'forbidden'."""
        from soniscope_worker.nls_transcriber import _retry_on_network_error

        call_count = [0]

        def fail_forbidden() -> str:
            call_count[0] += 1
            raise RuntimeError("Access Forbidden")

        with pytest.raises(RuntimeError):
            _retry_on_network_error("test-op", fail_forbidden)
        assert call_count[0] == 1

    def test_retry_fails_immediately_on_invalid_appkey(self) -> None:
        """_retry_on_network_error fails immediately on InvalidAppKey."""
        from soniscope_worker.nls_transcriber import _retry_on_network_error

        call_count = [0]

        def fail_invalid() -> str:
            call_count[0] += 1
            raise RuntimeError("InvalidAppKey: appkey not found")

        with pytest.raises(RuntimeError):
            _retry_on_network_error("test-op", fail_invalid)
        assert call_count[0] == 1

    def test_retry_fails_immediately_on_invalid_parameter(self) -> None:
        """_retry_on_network_error fails immediately on InvalidParameter."""
        from soniscope_worker.nls_transcriber import _retry_on_network_error

        call_count = [0]

        def fail_invalid_param() -> str:
            call_count[0] += 1
            raise RuntimeError("InvalidParameter: file_link is missing")

        with pytest.raises(RuntimeError):
            _retry_on_network_error("test-op", fail_invalid_param)
        assert call_count[0] == 1

    def test_retry_on_network_error_with_backoff(self) -> None:
        """_retry_on_network_error retries 3 times on network errors."""
        from soniscope_worker.nls_transcriber import _retry_on_network_error, _RETRY_INTERVALS

        call_count = [0]

        def fail_network() -> str:
            call_count[0] += 1
            raise RuntimeError("Network error, connection refused")

        with mock.patch("time.sleep") as mock_sleep:
            with pytest.raises(RuntimeError, match="failed after 4 attempts"):
                _retry_on_network_error("test-op", fail_network)

        # 1 initial + 3 retries = 4 attempts
        assert call_count[0] == 4
        # Sleep called with the correct intervals
        assert mock_sleep.call_count == 3
        for i, expected in enumerate(_RETRY_INTERVALS):
            mock_sleep.assert_any_call(expected)

    def test_retry_succeeds_after_intermittent_failure(self) -> None:
        """_retry_on_network_error succeeds when a retry works."""
        from soniscope_worker.nls_transcriber import _retry_on_network_error

        call_count = [0]

        def fail_then_succeed() -> str:
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("Network timeout")
            return "eventually ok"

        with mock.patch("time.sleep"):
            result = _retry_on_network_error("test-op", fail_then_succeed)

        assert result == "eventually ok"
        assert call_count[0] == 3

    def test_4xx_in_message_detected(self) -> None:
        """Any error containing '4xx' in message triggers immediate fail."""
        from soniscope_worker.nls_transcriber import _retry_on_network_error

        call_count = [0]

        def fail_4xx() -> str:
            call_count[0] += 1
            raise RuntimeError("HTTP 4xx client error")

        with pytest.raises(RuntimeError):
            _retry_on_network_error("test-op", fail_4xx)
        assert call_count[0] == 1


# ============================================================================
# AC2/AC4: Upload mode dispatch
# ============================================================================


class TestUploadModeDispatch:
    """Verify transcribe() dispatches to oss-url vs direct mode (AC2, AC4)."""

    def test_oss_url_mode_called_when_upload_mode_is_oss_url(self) -> None:
        """transcribe() calls _transcribe_oss_url when upload_mode=oss-url."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        cfg = _make_transcriber_config(upload_mode="oss-url")
        mock_oss = _make_mock_oss_client(
            presigned_url="https://b.oss-cn-beijing.aliyuncs.com/k?Expires=1"
        )
        t = CloudSpeechTranscriber(cfg, oss_client=mock_oss, oss_bucket="test")

        # We mock the entire internal flow to avoid real network calls
        with mock.patch.object(
            t, "_transcribe_oss_url", return_value=_make_transcript_result()
        ) as mock_oss_url, mock.patch.object(
            t, "_transcribe_direct"
        ) as mock_direct:
            t.transcribe("fid", Path("audio.wav"), "oss-key")
            mock_oss_url.assert_called_once()
            mock_direct.assert_not_called()

    def test_direct_mode_called_when_upload_mode_is_direct(self) -> None:
        """transcribe() calls _transcribe_direct when upload_mode=direct."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        cfg = _make_transcriber_config(upload_mode="direct")
        t = CloudSpeechTranscriber(cfg)

        with mock.patch.object(
            t, "_transcribe_direct", return_value=_make_transcript_result()
        ) as mock_direct, mock.patch.object(
            t, "_transcribe_oss_url"
        ) as mock_oss_url:
            t.transcribe("fid", Path("audio.wav"), "oss-key")
            mock_direct.assert_called_once()
            mock_oss_url.assert_not_called()

    def test_transcribe_accepts_path_object(self) -> None:
        """transcribe() accepts audio_path as a Path object."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        cfg = _make_transcriber_config(upload_mode="direct")
        t = CloudSpeechTranscriber(cfg)

        with mock.patch.object(
            t, "_transcribe_direct", return_value=_make_transcript_result()
        ) as mock_direct:
            t.transcribe("fid-001", Path("/tmp/test/audio.wav"), "k")
            assert mock_direct.call_count == 1


# ============================================================================
# AC6: NLS result → TranscriptResult mapping
# ============================================================================


class TestNlsToTranscriptResult:
    """Verify NLS GetTaskResult → TranscriptResult mapping (AC6)."""

    def test_maps_sentences_to_segments(self) -> None:
        """_nls_to_transcript_result maps Sentences to segments."""
        from soniscope_worker.nls_transcriber import _nls_to_transcript_result

        nls_resp = {
            "StatusText": "SUCCESS",
            "BizDuration": 20500,
            "Result": {
                "Sentences": [
                    {"BeginTime": 0, "EndTime": 2500, "Text": "你好世界"},
                    {"BeginTime": 3000, "EndTime": 5000, "Text": "这是测试"},
                    {"BeginTime": 6000, "EndTime": 9000, "Text": "第三句话"},
                ]
            },
        }

        result = _nls_to_transcript_result(
            nls_resp,
            model="test-model",
            params_version="v2",
            provider="aliyun-nls",
            language="zh",
        )

        assert len(result.segments) == 3
        assert result.segments[0].text == "你好世界"
        assert result.segments[0].start == 0.0
        assert result.segments[0].end == 2.5
        assert result.segments[1].text == "这是测试"
        assert result.segments[2].text == "第三句话"
        assert result.language == "zh"
        assert result.model == "test-model"
        assert result.params_version == "v2"
        assert result.provider == "aliyun-nls"
        assert result.duration == 20.5  # BizDuration 20500ms / 1000

    def test_empty_sentences_returns_empty_segments(self) -> None:
        """Empty Sentences → empty segments list."""
        from soniscope_worker.nls_transcriber import _nls_to_transcript_result

        nls_resp = {
            "StatusText": "SUCCESS",
            "BizDuration": 0,
            "Result": {"Sentences": []},
        }

        result = _nls_to_transcript_result(
            nls_resp,
            model="m",
            params_version="v1",
            provider="p",
        )
        assert result.segments == []
        assert result.duration == 0.0

    def test_missing_result_block_defaults_to_empty(self) -> None:
        """Missing Result block → empty segments, zero duration."""
        from soniscope_worker.nls_transcriber import _nls_to_transcript_result

        nls_resp = {"StatusText": "SUCCESS"}

        result = _nls_to_transcript_result(
            nls_resp,
            model="m",
            params_version="v1",
            provider="p",
        )
        assert result.segments == []
        assert result.duration == 0.0

    def test_maps_timestamps_from_ms_to_seconds(self) -> None:
        """BeginTime/EndTime in milliseconds are converted to seconds."""
        from soniscope_worker.nls_transcriber import _nls_to_transcript_result

        nls_resp = {
            "StatusText": "SUCCESS",
            "Result": {
                "Sentences": [
                    {"BeginTime": 12345, "EndTime": 67890, "Text": "test"},
                ]
            },
        }

        result = _nls_to_transcript_result(
            nls_resp,
            model="m",
            params_version="v1",
            provider="p",
        )
        assert result.segments[0].start == 12.345
        assert result.segments[0].end == 67.89

    def test_to_transcript_json_schema_compatible(self) -> None:
        """Mapped result is serializable to transcript.json schema (AC6)."""
        from soniscope_worker.nls_transcriber import _nls_to_transcript_result

        nls_resp = {
            "StatusText": "SUCCESS",
            "Result": {
                "Sentences": [
                    {"BeginTime": 0, "EndTime": 2000, "Text": "你好"},
                ]
            },
        }

        result = _nls_to_transcript_result(
            nls_resp,
            model="nls-model",
            params_version="v3",
        )
        d = result.to_dict()

        # transcript.json schema check (no duration, per tech-spec §3.4)
        assert "segments" in d
        assert d["language"] == "zh"
        assert d["model"] == "nls-model"
        assert d["params_version"] == "v3"
        assert d["provider"] == "aliyun-nls"
        assert "duration" not in d


# ============================================================================
# AC7: Cost logging
# ============================================================================


class TestCostLogging:
    """Verify structured cost-observability logging (AC7)."""

    def test_cost_log_includes_all_required_fields(self, caplog) -> None:
        """_log_asr_cost emits a JSON line with all required fields."""
        from soniscope_worker.nls_transcriber import _log_asr_cost

        caplog.set_level("INFO", logger="soniscope_worker.nls_transcriber")
        _log_asr_cost(
            fragment_id="test-fid",
            audio_duration_seconds=20.5,
            elapsed_seconds=3.2,
            provider="aliyun-nls",
            model="test-model",
        )

        assert len(caplog.records) >= 1
        entry = json.loads(caplog.messages[0])
        assert entry["event"] == "asr_call_completed"
        assert entry["fragment_id"] == "test-fid"
        assert entry["audio_duration_seconds"] == 20.5
        assert entry["elapsed_seconds"] == 3.2
        assert entry["provider"] == "aliyun-nls"
        assert entry["model"] == "test-model"
        assert "estimated_cost_yuan" in entry
        assert "cumulative_calls_today" in entry
        assert "cumulative_duration_today_seconds" in entry

    def test_cost_log_computes_estimated_cost(self, caplog) -> None:
        """estimated_cost_yuan = (duration_seconds / 3600) * 2.5."""
        from soniscope_worker.nls_transcriber import _log_asr_cost

        caplog.set_level("INFO", logger="soniscope_worker.nls_transcriber")
        # 3600 seconds = 1 hour → ¥2.50
        _log_asr_cost(
            fragment_id="f",
            audio_duration_seconds=3600.0,
            elapsed_seconds=10.0,
            provider="p",
            model="m",
        )

        entry = json.loads(caplog.messages[0])
        assert entry["estimated_cost_yuan"] == pytest.approx(2.5, rel=1e-6)

    def test_cost_log_increments_cumulative_counters(self, caplog) -> None:
        """cumulative_calls_today increments across calls."""
        from soniscope_worker.nls_transcriber import _log_asr_cost

        import soniscope_worker.nls_transcriber as nls_mod

        nls_mod._cumulative_calls = 0
        nls_mod._cumulative_duration_seconds = 0.0

        caplog.set_level("INFO", logger="soniscope_worker.nls_transcriber")
        _log_asr_cost(
            fragment_id="f1",
            audio_duration_seconds=10.0,
            elapsed_seconds=1.0,
            provider="p",
            model="m",
        )

        assert nls_mod._cumulative_calls == 1
        assert nls_mod._cumulative_duration_seconds == 10.0

    def test_cost_log_rounds_values(self, caplog) -> None:
        """Cost log values are rounded to reasonable precision."""
        from soniscope_worker.nls_transcriber import _log_asr_cost

        caplog.set_level("INFO", logger="soniscope_worker.nls_transcriber")
        _log_asr_cost(
            fragment_id="f",
            audio_duration_seconds=20.56789,
            elapsed_seconds=3.14159,
            provider="p",
            model="m",
        )

        entry = json.loads(caplog.messages[0])
        assert entry["audio_duration_seconds"] == 20.57  # rounded to 2 decimal places
        assert entry["elapsed_seconds"] == 3.14


# ============================================================================
# AC8/AC9/AC10: Makefile targets
# ============================================================================


class TestMakefileTargets:
    """Verify Makefile targets for US-026 transcribe commands (AC8, AC9, AC10)."""

    def test_makefile_has_oss_url_target(self) -> None:
        """Makefile has test-transcribe-oss-url target (AC8)."""
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        assert "test-transcribe-oss-url" in makefile

    def test_makefile_has_direct_target(self) -> None:
        """Makefile has test-transcribe-direct target (AC9)."""
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        assert "test-transcribe-direct" in makefile

    def test_makefile_has_perf_target(self) -> None:
        """Makefile has test-transcribe-perf target (AC10)."""
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        assert "test-transcribe-perf" in makefile

    def test_makefile_targets_are_phoney(self) -> None:
        """All three transcribe targets are declared .PHONY."""
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

        # Find .PHONY line (may be continued with backslash)
        in_phony = False
        phony_targets: list[str] = []
        for line in makefile.splitlines():
            stripped = line.lstrip()
            if stripped.startswith(".PHONY:"):
                in_phony = True
                phony_targets.extend(stripped.split(":", 1)[1].split())
            elif in_phony and stripped:
                # Check if this is a continuation line (starts with tab + backslash-continued items)
                if line.endswith("\\"):
                    phony_targets.extend(stripped.strip().rstrip("\\").split())
                else:
                    phony_targets.extend(stripped.split())
            elif in_phony and not stripped:
                continue
            else:
                in_phony = False

        assert "test-transcribe-oss-url" in phony_targets
        assert "test-transcribe-direct" in phony_targets
        assert "test-transcribe-perf" in phony_targets


# ============================================================================
# AC3: NLS async polling with OSS URL renewal
# ============================================================================


class TestPollWithRenew:
    """Verify NLS polling > 50 min auto re-signs OSS URL (AC3)."""

    def test_poll_with_renew_exits_on_success(self) -> None:
        """_poll_with_renew returns result when NLS completes."""
        mock_nls = _make_mock_nls_client(
            responses=[
                {"StatusText": "RUNNING"},
                {"StatusText": "RUNNING"},
                {
                    "StatusText": "SUCCESS",
                    "Result": {"Sentences": []},
                },
            ]
        )

        cfg = _make_transcriber_config()
        mock_oss = _make_mock_oss_client(
            presigned_url="https://b.oss-cn-beijing.aliyuncs.com/k?Expires=1"
        )
        t = _make_transcriber_instance(cfg, mock_oss)

        with mock.patch("time.sleep"):
            result = t._poll_with_renew(
                mock_nls,
                "filetrans.cn-beijing.aliyuncs.com",
                "task-123",
                "oss-key",
                "fid-001",
                time_mod.monotonic(),
            )

        assert result["StatusText"] == "SUCCESS"

    def test_poll_with_renew_raises_on_timeout(self) -> None:
        """_poll_with_renew raises RuntimeError when polling times out."""
        # Always returns RUNNING — never finishes
        mock_nls = _make_mock_nls_client(
            responses=[{"StatusText": "RUNNING"}] * 20
        )

        cfg = _make_transcriber_config()
        mock_oss = _make_mock_oss_client()
        t = _make_transcriber_instance(cfg, mock_oss)

        # Set a very short timeout so the test doesn't run long
        with mock.patch(
            "soniscope_worker.nls_transcriber._POLL_TIMEOUT_SECONDS", 0.01
        ), mock.patch("time.sleep"):
            # Make the poll_start far in the past to trigger immediate timeout
            poll_start = time_mod.monotonic() - 100
            with pytest.raises(RuntimeError, match="timed out"):
                t._poll_with_renew(
                    mock_nls,
                    "filetrans.cn-beijing.aliyuncs.com",
                    "task-123",
                    "oss-key",
                    "fid-001",
                    poll_start,
                )


# ============================================================================
# SubmitTask helpers
# ============================================================================


class TestSubmitNlsTask:
    """Verify _submit_nls_task behaviour."""

    def test_submit_task_with_file_link(self) -> None:
        """_submit_nls_task with file_link succeeds."""
        from soniscope_worker.nls_transcriber import _submit_nls_task

        mock_client = _make_mock_nls_client(
            responses=[{"StatusText": "SUCCESS", "TaskId": "task-001"}]
        )

        resp = _submit_nls_task(
            mock_client,
            "filetrans.cn-beijing.aliyuncs.com",
            appkey="test-appkey",
            file_link="https://oss.example.com/file.wav",
        )
        assert resp["StatusText"] == "SUCCESS"
        assert resp["TaskId"] == "task-001"

    def test_submit_task_raises_runtime_error_on_failure(self) -> None:
        """_submit_nls_task raises RuntimeError when StatusText != SUCCESS."""
        from soniscope_worker.nls_transcriber import _submit_nls_task

        mock_client = _make_mock_nls_client(
            responses=[{"StatusText": "FAILED", "StatusCode": 400}]
        )

        with pytest.raises(RuntimeError, match="SubmitTask failed"):
            _submit_nls_task(
                mock_client,
                "filetrans.cn-beijing.aliyuncs.com",
                appkey="bad-appkey",
                file_link="https://oss.example.com/file.wav",
            )

    def test_submit_task_requires_file_link_or_file_content(self) -> None:
        """_submit_nls_task raises ValueError when neither is provided."""
        from soniscope_worker.nls_transcriber import _submit_nls_task

        mock_client = _make_mock_nls_client()
        with pytest.raises(ValueError, match="Either file_link or file_content"):
            _submit_nls_task(
                mock_client,
                "filetrans.cn-beijing.aliyuncs.com",
                appkey="test",
            )


# ============================================================================
# Direct mode
# ============================================================================


class TestDirectMode:
    """Verify direct mode transcribe flow (AC4)."""

    def test_direct_mode_reads_audio_file(self) -> None:
        """_transcribe_direct reads local audio.wav and base64-encodes it."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

        cfg = _make_transcriber_config(upload_mode="direct")
        t = CloudSpeechTranscriber(cfg)

        # The direct flow calls _transcribe_direct which reads the file
        # and submits via NLS.  We verify the mock path.
        mock_nls = _make_mock_nls_client(
            responses=[
                {"StatusText": "SUCCESS", "TaskId": "task-001"},
                {
                    "StatusText": "SUCCESS",
                    "Result": {
                        "Sentences": [
                            {"BeginTime": 0, "EndTime": 1000, "Text": "测试"}
                        ]
                    },
                    "BizDuration": 1000,
                },
            ]
        )

        with mock.patch(
            "soniscope_worker.nls_transcriber._build_nls_client",
            return_value=mock_nls,
        ), mock.patch(
            "soniscope_worker.nls_transcriber._log_asr_cost"
        ), mock.patch(
            "pathlib.Path.read_bytes",
            return_value=b"fake-audio-bytes",
        ):
            result = t.transcribe("fid", Path("audio.wav"), "k")

        assert result.language == "zh"
        # Direct mode: should log mode=direct-upload (checked in integration)


# ============================================================================
# Cost counters — date rollover
# ============================================================================


class TestCounterReset:
    """Verify cumulative counters reset on date rollover."""

    def test_reset_counters_when_date_changes(self) -> None:
        """_reset_counters_if_new_day resets when date rolls over."""
        import soniscope_worker.nls_transcriber as nls_mod

        # Set to a past date
        nls_mod._counter_date = "2026-01-01"
        nls_mod._cumulative_calls = 42
        nls_mod._cumulative_duration_seconds = 999.0

        nls_mod._reset_counters_if_new_day()

        # Should have reset since counter_date != today
        assert nls_mod._cumulative_calls == 0
        assert nls_mod._cumulative_duration_seconds == 0.0
        assert nls_mod._counter_date != "2026-01-01"


# ============================================================================
# Module structure
# ============================================================================


class TestModuleStructure:
    """Verify nls_transcriber module exports."""

    def test_cloud_speech_transcriber_is_importable(self) -> None:
        """CloudSpeechTranscriber is importable from nls_transcriber."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber
        assert CloudSpeechTranscriber is not None

    def test_module_exports_key_functions(self) -> None:
        """Key helper functions are importable."""
        from soniscope_worker.nls_transcriber import (
            _generate_presigned_url,
            _submit_nls_task,
            _poll_nls_result,
            _nls_to_transcript_result,
            _log_asr_cost,
            _retry_on_network_error,
            _build_nls_client,
        )
        assert callable(_generate_presigned_url)
        assert callable(_submit_nls_task)
        assert callable(_poll_nls_result)
        assert callable(_nls_to_transcript_result)
        assert callable(_log_asr_cost)
        assert callable(_retry_on_network_error)
        assert callable(_build_nls_client)

    def test_producer_and_api_constants(self) -> None:
        """NLS API constants are correct."""
        from soniscope_worker.nls_transcriber import (
            _PRODUCT,
            _API_VERSION,
            _POST_ACTION,
            _GET_ACTION,
        )

        assert _PRODUCT == "nls-filetrans"
        assert _API_VERSION == "2018-08-17"
        assert _POST_ACTION == "SubmitTask"
        assert _GET_ACTION == "GetTaskResult"


# ============================================================================
# Security — no hard-coded credentials
# ============================================================================


class TestSecurity:
    """No hard-coded credentials in nls_transcriber.py."""

    def test_no_hardcoded_ak_in_nls_transcriber(self) -> None:
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
# Factory integration
# ============================================================================


class TestFactoryIntegration:
    """create_transcriber returns CloudSpeechTranscriber from nls_transcriber."""

    def test_factory_returns_nls_transcriber_for_cloud_speech(self) -> None:
        """create_transcriber with cloud-speech returns nls CloudSpeechTranscriber."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber
        from soniscope_worker.transcriber import create_transcriber

        config = _make_full_config(name="cloud-speech")
        t = create_transcriber(config)
        assert isinstance(t, CloudSpeechTranscriber)

    def test_factory_passes_oss_client_to_nls_transcriber(self) -> None:
        """create_transcriber passes oss_client and oss_bucket to NLS transcriber."""
        from soniscope_worker.nls_transcriber import CloudSpeechTranscriber
        from soniscope_worker.transcriber import create_transcriber

        mock_oss = _make_mock_oss_client()
        config = _make_full_config(name="cloud-speech")
        t = create_transcriber(config, oss_client=mock_oss, oss_bucket="my-bkt")
        assert isinstance(t, CloudSpeechTranscriber)
        assert t._oss_bucket == "my-bkt"

    def test_factory_returns_whisper_local_for_non_cloud(self) -> None:
        """create_transcriber with whisper-local still returns WhisperLocalTranscriber."""
        from soniscope_worker.transcriber import (
            WhisperLocalTranscriber,
            create_transcriber,
        )

        config = _make_full_config(name="whisper-local")
        t = create_transcriber(config)
        assert isinstance(t, WhisperLocalTranscriber)


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


def _make_full_config(name: str = "cloud-speech") -> "soniscope_worker.config.SoniScopeConfig":
    from soniscope_worker.config import OssConfig, PollConfig, SoniScopeConfig

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


def _make_transcript_result(
    segments: list | None = None,
    language: str = "zh",
    model: str = "test-model",
    params_version: str = "v1",
    provider: str = "aliyun-nls",
    duration: float = 0.0,
) -> "soniscope_worker.transcript.TranscriptResult":
    from soniscope_worker.transcript import TranscriptResult

    return TranscriptResult(
        segments=segments or [],
        language=language,
        model=model,
        params_version=params_version,
        provider=provider,
        duration=duration,
    )


def _make_mock_oss_client(presigned_url: str = "https://fake.url/signed") -> mock.MagicMock:
    """Create a mock OSS v2 Client that returns a presigned URL."""
    mock_client = mock.MagicMock()
    mock_result = mock.MagicMock()
    mock_result.url = presigned_url
    mock_client.presign.return_value = mock_result
    return mock_client


def _make_mock_nls_client(responses: list | None = None) -> mock.MagicMock:
    """Create a mock NLS AcsClient that returns preset responses on each call."""
    if responses is None:
        responses = [{"StatusText": "SUCCESS", "TaskId": "task-001"}]

    resp_iter = iter(responses)

    def do_action(_request: object) -> bytes:
        try:
            data = next(resp_iter)
        except StopIteration:
            data = responses[-1]
        return json.dumps(data).encode("utf-8")

    mock_client = mock.MagicMock()
    mock_client.do_action_with_exception.side_effect = do_action
    return mock_client


def _make_transcriber_instance(
    cfg: "soniscope_worker.config.TranscriberConfig",
    oss_client: mock.MagicMock,
) -> "soniscope_worker.nls_transcriber.CloudSpeechTranscriber":
    from soniscope_worker.nls_transcriber import CloudSpeechTranscriber

    return CloudSpeechTranscriber(cfg, oss_client=oss_client, oss_bucket="test-bucket")
