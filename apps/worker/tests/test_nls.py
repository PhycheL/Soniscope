"""US-026：阿里云 NLS 云端转写器（oss-url / direct、重试、续签、成本日志）测试。

全程注入 FakeBackend + 假时钟，不触网、不调 ffprobe / 云 SDK。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soniscope_worker.config import TranscriberConfig
from soniscope_worker.nls import (
    MODE_LOG_DIRECT,
    MODE_LOG_OSS_URL,
    RESIGN_THRESHOLD_SECONDS,
    RETRY_DELAYS_SECONDS,
    STATUS_QUEUEING,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    DailyCounter,
    NlsTranscribeError,
    RealNlsBackend,
    build_cost_log,
    estimate_cost_yuan,
    flash_to_filetrans_shape,
    is_retryable_status,
    nls_result_to_transcript,
    transcribe_via_nls,
    transcript_text,
)


def _config(upload_mode: str = "oss-url") -> TranscriberConfig:
    return TranscriberConfig.model_validate(
        {
            "name": "cloud-speech",
            "provider": "aliyun-nls",
            "model": "中文普通话（识音石 V1 - 端到端模型)",
            "params_version": "v1",
            "api_endpoint": "cn-beijing",
            "appkey": "1k8tqkjQsq65wp2m",
            "access_key_id": "LTAItestkeyid",
            "access_key_secret": "testsecretvalue1234",
            "upload_mode": upload_mode,
        }
    )


def _filetrans_resp(text: str = "你好世界") -> dict[str, object]:
    return {
        "StatusText": STATUS_SUCCESS,
        "Result": {"Sentences": [{"BeginTime": 1020, "EndTime": 3942, "Text": text}]},
    }


class _FakeBackend:
    """可配置的 NLS 后端桩：记录调用、可注入轮询序列 / 异常。"""

    def __init__(
        self,
        *,
        poll_sequence: list[dict[str, object]] | None = None,
        submit_errors: list[NlsTranscribeError] | None = None,
        direct_resp: dict[str, object] | None = None,
        on_poll: object = None,
    ) -> None:
        self.poll_sequence = poll_sequence or [_filetrans_resp()]
        self._poll_idx = 0
        self.submit_errors = submit_errors or []
        self._submit_idx = 0
        self.direct_resp = direct_resp or _filetrans_resp()
        self.on_poll = on_poll
        self.presign_calls: list[str] = []
        self.submit_calls: list[str] = []
        self.poll_calls: list[str] = []
        self.direct_calls: list[Path] = []

    def presign_oss_url(self, oss_key: str, expires_seconds: int) -> str:
        self.presign_calls.append(oss_key)
        return f"https://signed/{oss_key}?n={len(self.presign_calls)}"

    def submit_oss_url(self, file_link: str) -> str:
        self.submit_calls.append(file_link)
        if self._submit_idx < len(self.submit_errors):
            err = self.submit_errors[self._submit_idx]
            self._submit_idx += 1
            raise err
        return f"task-{len(self.submit_calls)}"

    def poll_task(self, task_id: str) -> dict[str, object]:
        self.poll_calls.append(task_id)
        if callable(self.on_poll):
            self.on_poll(len(self.poll_calls))
        idx = min(self._poll_idx, len(self.poll_sequence) - 1)
        self._poll_idx += 1
        return self.poll_sequence[idx]

    def transcribe_direct(self, audio_path: Path) -> dict[str, object]:
        self.direct_calls.append(audio_path)
        return self.direct_resp


class _Clock:
    """可手动推进的假时钟（monotonic 读 t，不自动前进）。"""

    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


# ── 纯逻辑 ───────────────────────────────────────────────────────────────────
def test_is_retryable_status() -> None:
    assert is_retryable_status(0) is True  # 网络错误
    assert is_retryable_status(500) is True
    assert is_retryable_status(503) is True
    assert is_retryable_status(400) is False
    assert is_retryable_status(401) is False
    assert is_retryable_status(404) is False
    assert is_retryable_status(200) is False


def test_estimate_cost_yuan() -> None:
    # 2.5 元/小时：1 小时 → 2.5；空 / 负 → 0。
    assert estimate_cost_yuan(3600) == 2.5
    assert estimate_cost_yuan(60) == round(2.5 / 60, 4)
    assert estimate_cost_yuan(0) == 0.0
    assert estimate_cost_yuan(-5) == 0.0


def test_nls_result_to_transcript_maps_ms_to_seconds() -> None:
    result = nls_result_to_transcript(
        _filetrans_resp("人们也在"),
        model="m",
        params_version="v1",
        provider="aliyun-nls",
        duration=24.0,
    )
    assert result.language == "zh"
    assert result.provider == "aliyun-nls"
    assert result.duration == 24.0
    assert len(result.segments) == 1
    assert result.segments[0].start == 1.02  # 1020ms → 1.02s
    assert result.segments[0].end == 3.942
    assert result.segments[0].text == "人们也在"


def test_nls_result_to_transcript_empty_segments() -> None:
    result = nls_result_to_transcript(
        {"StatusText": STATUS_SUCCESS, "Result": {}},
        model="m",
        params_version="v1",
        provider="aliyun-nls",
        duration=0.0,
    )
    assert result.segments == []


def test_transcript_text_joins_segments() -> None:
    result = nls_result_to_transcript(
        {
            "Result": {
                "Sentences": [
                    {"BeginTime": 0, "EndTime": 1000, "Text": "前半"},
                    {"BeginTime": 1000, "EndTime": 2000, "Text": "后半"},
                ]
            }
        },
        model="m",
        params_version="v1",
        provider="aliyun-nls",
        duration=2.0,
    )
    assert transcript_text(result) == "前半后半"


def test_build_cost_log_fields() -> None:
    log = build_cost_log(
        fragment_id="frag-1",
        audio_duration_seconds=87.5,
        elapsed_seconds=12.3,
        provider="aliyun-nls",
        model="m",
        estimated_cost_yuan=0.06,
        cumulative_calls_today=15,
        cumulative_duration_today_seconds=1200.0,
    )
    assert log == {
        "event": "asr_call_completed",
        "fragment_id": "frag-1",
        "audio_duration_seconds": 87.5,
        "elapsed_seconds": 12.3,
        "provider": "aliyun-nls",
        "model": "m",
        "estimated_cost_yuan": 0.06,
        "cumulative_calls_today": 15,
        "cumulative_duration_today_seconds": 1200.0,
    }


def test_flash_to_filetrans_shape() -> None:
    flash = {
        "status": 20000000,
        "flash_result": {
            "sentences": [
                {"begin_time": 100, "end_time": 900, "text": "极速"},
                {"begin_time": 900, "end_time": 1500, "text": "结果"},
            ]
        },
    }
    shaped = flash_to_filetrans_shape(flash)
    assert shaped["StatusText"] == STATUS_SUCCESS
    sentences = shaped["Result"]["Sentences"]  # type: ignore[index]
    assert sentences == [
        {"BeginTime": 100, "EndTime": 900, "Text": "极速"},
        {"BeginTime": 900, "EndTime": 1500, "Text": "结果"},
    ]


def test_flash_to_filetrans_shape_missing_result() -> None:
    shaped = flash_to_filetrans_shape({"status": 20000000})
    assert shaped["Result"] == {"Sentences": []}


def test_daily_counter_accumulates_and_resets() -> None:
    counter = DailyCounter()
    assert counter.record(10.0, "2026-06-27") == (1, 10.0)
    assert counter.record(5.0, "2026-06-27") == (2, 15.0)
    # 跨日归零。
    assert counter.record(7.0, "2026-06-28") == (1, 7.0)


# ── 编排：oss-url happy path + 成本日志 ──────────────────────────────────────
def test_transcribe_oss_url_happy_path_and_cost_log() -> None:
    backend = _FakeBackend(poll_sequence=[_filetrans_resp("人们也在可支配")])
    clock = _Clock()
    counter = DailyCounter()
    logs: list[str] = []
    result = transcribe_via_nls(
        _config("oss-url"),
        "20260527T120000_devp01_01HZX3K8MN5PQR9TFB7AYWVCDE",
        Path("/tmp/audio.wav"),
        "recordings/2026-05-27/x.wav",
        backend=backend,
        counter=counter,
        log=logs.append,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        duration_probe=lambda _p: 20.0,
        today=lambda: "2026-06-27",
    )
    assert transcript_text(result) == "人们也在可支配"
    assert result.duration == 20.0
    assert backend.presign_calls == ["recordings/2026-05-27/x.wav"]
    assert len(backend.submit_calls) == 1
    # mode 日志。
    assert any(f"mode={MODE_LOG_OSS_URL}" in line for line in logs)
    # 成本日志（最后一行 JSON）。
    cost = json.loads(logs[-1])
    assert cost["event"] == "asr_call_completed"
    assert cost["audio_duration_seconds"] == 20.0
    assert cost["cumulative_calls_today"] == 1
    assert cost["cumulative_duration_today_seconds"] == 20.0
    assert cost["estimated_cost_yuan"] == estimate_cost_yuan(20.0)


def test_transcribe_oss_url_polls_running_then_success() -> None:
    backend = _FakeBackend(
        poll_sequence=[
            {"StatusText": STATUS_QUEUEING},
            {"StatusText": STATUS_RUNNING},
            _filetrans_resp("完成"),
        ]
    )
    clock = _Clock()
    result = transcribe_via_nls(
        _config("oss-url"),
        "frag",
        Path("/tmp/a.wav"),
        "recordings/2026-05-27/x.wav",
        backend=backend,
        counter=DailyCounter(),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        duration_probe=lambda _p: 5.0,
        today=lambda: "2026-06-27",
    )
    assert transcript_text(result) == "完成"
    assert len(backend.poll_calls) == 3
    # QUEUEING / RUNNING 各 sleep 一次轮询间隔。
    assert clock.sleeps.count(5.0) >= 2


def test_transcribe_oss_url_resigns_after_50_minutes() -> None:
    clock = _Clock()

    def _advance(poll_n: int) -> None:
        # 第一次轮询时把时钟推过 50 分钟，触发续签。
        if poll_n == 1:
            clock.t = RESIGN_THRESHOLD_SECONDS + 100

    backend = _FakeBackend(
        poll_sequence=[{"StatusText": STATUS_RUNNING}, _filetrans_resp("续签后完成")],
        on_poll=_advance,
    )
    logs: list[str] = []
    result = transcribe_via_nls(
        _config("oss-url"),
        "frag-x",
        Path("/tmp/a.wav"),
        "recordings/2026-05-27/x.wav",
        backend=backend,
        counter=DailyCounter(),
        log=logs.append,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        duration_probe=lambda _p: 5.0,
        today=lambda: "2026-06-27",
    )
    assert transcript_text(result) == "续签后完成"
    # 续签：presign 与 submit 各发生两次。
    assert len(backend.presign_calls) == 2
    assert len(backend.submit_calls) == 2
    assert any("重新签发" in line for line in logs)


def test_transcribe_oss_url_non_success_status_raises() -> None:
    backend = _FakeBackend(poll_sequence=[{"StatusText": "FAILED"}])
    clock = _Clock()
    with pytest.raises(NlsTranscribeError) as exc:
        transcribe_via_nls(
            _config("oss-url"),
            "frag",
            Path("/tmp/a.wav"),
            "recordings/2026-05-27/x.wav",
            backend=backend,
            counter=DailyCounter(),
            sleep=clock.sleep,
            monotonic=clock.monotonic,
            duration_probe=lambda _p: 5.0,
        )
    assert "FAILED" in exc.value.error_code


# ── 编排：direct 模式 ────────────────────────────────────────────────────────
def test_transcribe_direct_logs_mode_and_maps_result() -> None:
    backend = _FakeBackend(direct_resp=_filetrans_resp("直传结果"))
    clock = _Clock()
    logs: list[str] = []
    result = transcribe_via_nls(
        _config("direct"),
        "frag",
        Path("/tmp/audio.wav"),
        "recordings/2026-05-27/x.wav",
        backend=backend,
        counter=DailyCounter(),
        log=logs.append,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        duration_probe=lambda _p: 8.0,
        today=lambda: "2026-06-27",
    )
    assert transcript_text(result) == "直传结果"
    assert backend.direct_calls == [Path("/tmp/audio.wav")]
    # direct 不走 oss-url 路径。
    assert backend.presign_calls == []
    assert any(f"mode={MODE_LOG_DIRECT}" in line for line in logs)


# ── 重试 / 退避 ──────────────────────────────────────────────────────────────
def test_submit_retries_on_5xx_then_succeeds() -> None:
    backend = _FakeBackend(
        submit_errors=[
            NlsTranscribeError("5xx", status_code=503, error_code="HTTP_503", retryable=True),
            NlsTranscribeError("5xx", status_code=500, error_code="HTTP_500", retryable=True),
        ],
        poll_sequence=[_filetrans_resp("重试成功")],
    )
    clock = _Clock()
    result = transcribe_via_nls(
        _config("oss-url"),
        "frag",
        Path("/tmp/a.wav"),
        "recordings/2026-05-27/x.wav",
        backend=backend,
        counter=DailyCounter(),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        duration_probe=lambda _p: 5.0,
        today=lambda: "2026-06-27",
    )
    assert transcript_text(result) == "重试成功"
    # 两次退避，延迟为 5s、15s。
    assert clock.sleeps[:2] == [RETRY_DELAYS_SECONDS[0], RETRY_DELAYS_SECONDS[1]]
    assert len(backend.submit_calls) == 3


def test_submit_4xx_fails_immediately_without_retry() -> None:
    backend = _FakeBackend(
        submit_errors=[
            NlsTranscribeError("4xx", status_code=400, error_code="HTTP_400", retryable=False),
        ]
    )
    clock = _Clock()
    with pytest.raises(NlsTranscribeError) as exc:
        transcribe_via_nls(
            _config("oss-url"),
            "frag",
            Path("/tmp/a.wav"),
            "recordings/2026-05-27/x.wav",
            backend=backend,
            counter=DailyCounter(),
            sleep=clock.sleep,
            monotonic=clock.monotonic,
            duration_probe=lambda _p: 5.0,
        )
    assert exc.value.error_code == "HTTP_400"
    assert clock.sleeps == []  # 4xx 不重试
    assert len(backend.submit_calls) == 1


def test_submit_retryable_gives_up_after_max_retries() -> None:
    errs = [
        NlsTranscribeError("5xx", status_code=500, error_code="HTTP_500", retryable=True)
        for _ in range(5)
    ]
    backend = _FakeBackend(submit_errors=errs)
    clock = _Clock()
    with pytest.raises(NlsTranscribeError):
        transcribe_via_nls(
            _config("oss-url"),
            "frag",
            Path("/tmp/a.wav"),
            "recordings/2026-05-27/x.wav",
            backend=backend,
            counter=DailyCounter(),
            sleep=clock.sleep,
            monotonic=clock.monotonic,
            duration_probe=lambda _p: 5.0,
        )
    # 3 次重试 → 4 次尝试，3 次退避。
    assert len(backend.submit_calls) == 1 + len(RETRY_DELAYS_SECONDS)
    assert clock.sleeps == list(RETRY_DELAYS_SECONDS)


# ── RealNlsBackend：异常分类与缺依赖 ────────────────────────────────────────
def test_real_backend_classify_exception_5xx_retryable() -> None:
    class _ServerExc(Exception):
        http_status = 503
        error_code = "InternalError"

    err = RealNlsBackend._classify_exception(_ServerExc("boom"))
    assert err.status_code == 503
    assert err.error_code == "InternalError"
    assert err.retryable is True


def test_real_backend_classify_exception_4xx_not_retryable() -> None:
    class _ClientExc(Exception):
        http_status = 403
        error_code = "Forbidden"

    err = RealNlsBackend._classify_exception(_ClientExc("denied"))
    assert err.status_code == 403
    assert err.retryable is False


def test_real_backend_classify_exception_network_retryable() -> None:
    err = RealNlsBackend._classify_exception(ValueError("connection reset"))
    assert err.status_code == 0
    assert err.retryable is True
    # 不泄漏明文，仅类名。
    assert err.error_code == "ValueError"


def test_real_backend_presign_missing_sdk_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import soniscope_worker.config as config_mod
    import soniscope_worker.verify_prep as verify_prep

    monkeypatch.setattr(config_mod, "load_config", lambda *a, **k: _full_config())

    def _boom() -> object:
        raise verify_prep.ProbeError("缺少依赖 alibabacloud-oss-v2")

    monkeypatch.setattr(verify_prep, "_import_oss", _boom)
    backend = RealNlsBackend(_config("oss-url"))
    with pytest.raises(verify_prep.ProbeError):
        backend.presign_oss_url("recordings/2026-05-27/x.wav", 3600)


def _full_config() -> object:
    from soniscope_worker.config import SoniScopeConfig

    return SoniScopeConfig.model_validate(
        {
            "oss": {
                "endpoint": "oss-cn-beijing.aliyuncs.com",
                "bucket": "soniscope-audio",
                "access_key_id": "LTAItestkeyid",
                "access_key_secret": "testsecretvalue1234",
            },
            "poll": {"interval_seconds": 30},
            "transcriber": {
                "name": "cloud-speech",
                "provider": "aliyun-nls",
                "model": "m",
                "params_version": "v1",
                "api_endpoint": "cn-beijing",
                "appkey": "1k8tqkjQsq65wp2m",
                "access_key_id": "LTAItestkeyid",
                "access_key_secret": "testsecretvalue1234",
                "upload_mode": "oss-url",
            },
        }
    )


# ── make test 入口：缺 config 时 SKIP ───────────────────────────────────────
def test_make_test_targets_skip_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    import soniscope_worker.config as config_mod
    import soniscope_worker.nls as nls

    # 让 fixture 存在但 config 加载失败 → SKIP exit 0。
    monkeypatch.setattr("pathlib.Path.is_file", lambda self: True)

    def _no_config(*_a: object, **_k: object) -> object:
        raise config_mod.ConfigError("no config")

    monkeypatch.setattr(config_mod, "load_config", _no_config)
    for runner in (
        nls.run_test_transcribe_oss_url,
        nls.run_test_transcribe_direct,
        nls.run_test_transcribe_perf,
    ):
        lines, code = runner()
        assert code == 0
        assert any("SKIP" in line for line in lines)
