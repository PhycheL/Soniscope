"""阿里云 NLS 云端转写器（US-026，tech-spec §5.2 / §6.8）。

为 :class:`soniscope_worker.transcriber.CloudSpeechTranscriber` 提供真实的阿里云
智能语音交互（NLS）转写能力，支持两种 ``upload_mode``：

- ``oss-url``（首选，方案 A）：为 OSS 上的**原始 object** 生成有效期 1 小时的签名
  URL，提交给 NLS 录音文件识别（filetrans）让其自行拉取，异步轮询结果。轮询超过
  50 分钟时自动重新签发 URL 并重提交（日志显示续签行为）。
- ``direct``（降级，方案 B）：把本地标准化后的 ``audio.wav`` 通过 NLS 录音文件识别
  极速版（FlashRecognizer）二进制直传，同步拿结果，日志打印 ``mode=direct-upload``。

沿用本仓库「纯逻辑（无 IO，直接单测）+ IO 用 :class:`NlsBackend` Protocol 注入」分层：
单测注入 ``FakeNlsBackend`` 全程不触网，真实运行用 :class:`RealNlsBackend`（lazy import
云 SDK，复用 :mod:`soniscope_worker.verify_prep` 的 OSS / NLS 辅助）。

错误处理遵循 AGENTS 统一策略：网络错误 / 5xx 按 5s→15s→45s 指数退避重试 3 次；
4xx 立即失败并输出错误码。每次 ASR 调用完成后输出 §6.8 结构化成本日志。
"""

from __future__ import annotations

import datetime
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from soniscope_worker.config import TranscriberConfig
from soniscope_worker.fixtures import probe_media
from soniscope_worker.transcriber import Segment, TranscriptResult

# ── 常量 ─────────────────────────────────────────────────────────────────────
UPLOAD_MODE_OSS_URL = "oss-url"
UPLOAD_MODE_DIRECT = "direct"
# 日志中打印的模式标签（tech-spec §5.2）。
MODE_LOG_OSS_URL = "oss-url"
MODE_LOG_DIRECT = "direct-upload"

# 重试策略（AGENTS 错误处理表）：网络 / 5xx 退避 5s→15s→45s，最多重试 3 次。
RETRY_DELAYS_SECONDS: tuple[float, ...] = (5.0, 15.0, 45.0)
MAX_RETRIES = 3

# OSS 签名 URL 有效期（1 小时，§5.2）；轮询超过 50 分钟则重新签发。
SIGNED_URL_EXPIRES_SECONDS = 3600
RESIGN_THRESHOLD_SECONDS = 50 * 60

# NLS 录音文件识别轮询参数。
NLS_POLL_INTERVAL_SECONDS = 5.0
NLS_TOTAL_TIMEOUT_SECONDS = 2 * 3600.0

# 转写文本语言（本期固定中文，§3.4）。
LANGUAGE_ZH = "zh"

# NLS 服务状态（filetrans / 极速版）。
STATUS_SUCCESS = "SUCCESS"
STATUS_RUNNING = "RUNNING"
STATUS_QUEUEING = "QUEUEING"
STATUS_NO_VALID_FRAGMENT = "SUCCESS_WITH_NO_VALID_FRAGMENT"
_TERMINAL_SUCCESS = (STATUS_SUCCESS, STATUS_NO_VALID_FRAGMENT)

# 阿里云 NLS 极速版（FlashRecognizer）成功状态码。
FLASH_STATUS_SUCCESS = 20000000

# ASR 费率（runbook §5.3：2.5 元/小时，无免费额度）。
ASR_RATE_YUAN_PER_HOUR = 2.5


class NlsTranscribeError(Exception):
    """NLS 转写调用失败。

    ``retryable`` 标记是否属于「网络 / 5xx」可退避重试类；4xx / 应用级失败为
    ``False``（立即失败）。``error_code`` 仅含稳定错误码或异常类名，**不含敏感明文**。
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        error_code: str = "UNKNOWN",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.retryable = retryable


# ── 纯逻辑（无 IO，直接单测）────────────────────────────────────────────────
def is_retryable_status(status_code: int) -> bool:
    """判断 HTTP 状态码是否属于可退避重试类：0（网络）或 5xx → True；4xx → False。"""
    if status_code == 0:
        return True
    return 500 <= status_code <= 599


def estimate_cost_yuan(
    duration_seconds: float, rate_yuan_per_hour: float = ASR_RATE_YUAN_PER_HOUR
) -> float:
    """按时长估算单次 ASR 成本（元），保留 4 位小数（runbook §5.3 费率）。"""
    if duration_seconds <= 0:
        return 0.0
    return round(duration_seconds / 3600.0 * rate_yuan_per_hour, 4)


def _sentences_of(resp: Mapping[str, object]) -> list[Mapping[str, object]]:
    result = resp.get("Result")
    sentences = result.get("Sentences") if isinstance(result, Mapping) else None
    if not isinstance(sentences, list):
        return []
    return [s for s in sentences if isinstance(s, Mapping)]


def _ms_to_seconds(value: object) -> float:
    return float(value) / 1000.0 if isinstance(value, (int, float)) else 0.0


def nls_result_to_transcript(
    resp: Mapping[str, object],
    *,
    model: str,
    params_version: str,
    provider: str,
    duration: float,
) -> TranscriptResult:
    """把 NLS 响应（filetrans 形状）映射为 :class:`TranscriptResult`（§3.4）。

    ``BeginTime`` / ``EndTime`` 单位为毫秒，换算成秒；``language`` 固定 ``zh``；
    ``duration`` 取本地音频实测时长（不来自 NLS）。
    """
    segments = [
        Segment(
            start=_ms_to_seconds(s.get("BeginTime")),
            end=_ms_to_seconds(s.get("EndTime")),
            text=str(s.get("Text", "")),
        )
        for s in _sentences_of(resp)
    ]
    return TranscriptResult(
        segments=segments,
        language=LANGUAGE_ZH,
        model=model,
        params_version=params_version,
        provider=provider,
        duration=duration,
    )


def transcript_text(result: TranscriptResult) -> str:
    """拼接 segments[].text（供 make test 与基线比对）。"""
    return "".join(seg.text for seg in result.segments).strip()


def build_cost_log(
    *,
    fragment_id: str,
    audio_duration_seconds: float,
    elapsed_seconds: float,
    provider: str,
    model: str,
    estimated_cost_yuan: float,
    cumulative_calls_today: int,
    cumulative_duration_today_seconds: float,
) -> dict[str, object]:
    """构造 §6.8 ``asr_call_completed`` 成本可观测日志（结构化 dict）。"""
    return {
        "event": "asr_call_completed",
        "fragment_id": fragment_id,
        "audio_duration_seconds": round(audio_duration_seconds, 3),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "provider": provider,
        "model": model,
        "estimated_cost_yuan": estimated_cost_yuan,
        "cumulative_calls_today": cumulative_calls_today,
        "cumulative_duration_today_seconds": round(cumulative_duration_today_seconds, 3),
    }


def flash_to_filetrans_shape(resp: Mapping[str, object]) -> dict[str, object]:
    """把极速版（FlashRecognizer）响应归一化为 filetrans 形状，复用同一映射逻辑。

    极速版返回 ``{"status": 20000000, "flash_result": {"sentences": [...]}}``，
    句子字段是 ``begin_time`` / ``end_time`` / ``text``；归一化为
    ``{"StatusText": "SUCCESS", "Result": {"Sentences": [{"BeginTime"/"EndTime"/"Text"}]}}``。
    """
    flash = resp.get("flash_result")
    raw_sentences = flash.get("sentences") if isinstance(flash, Mapping) else None
    sentences: list[dict[str, object]] = []
    if isinstance(raw_sentences, list):
        for s in raw_sentences:
            if not isinstance(s, Mapping):
                continue
            sentences.append(
                {
                    "BeginTime": s.get("begin_time", 0),
                    "EndTime": s.get("end_time", 0),
                    "Text": s.get("text", ""),
                }
            )
    return {"StatusText": STATUS_SUCCESS, "Result": {"Sentences": sentences}}


@dataclass
class DailyCounter:
    """当日累计调用次数与时长（§6.8）；跨日自动归零，仅内存、不持久化。"""

    _day: str = ""
    calls: int = 0
    duration_seconds: float = 0.0

    def record(self, duration_seconds: float, today: str) -> tuple[int, float]:
        """记录一次调用，返回 (当日累计次数, 当日累计时长)。"""
        if today != self._day:
            self._day = today
            self.calls = 0
            self.duration_seconds = 0.0
        self.calls += 1
        self.duration_seconds += max(duration_seconds, 0.0)
        return self.calls, self.duration_seconds


# ── IO 注入点 ─────────────────────────────────────────────────────────────
@runtime_checkable
class NlsBackend(Protocol):
    """NLS 云端调用注入点（单测用 Fake，真实用 :class:`RealNlsBackend`）。"""

    def presign_oss_url(self, oss_key: str, expires_seconds: int) -> str: ...

    def submit_oss_url(self, file_link: str) -> str: ...

    def poll_task(self, task_id: str) -> Mapping[str, object]: ...

    def transcribe_direct(self, audio_path: Path) -> Mapping[str, object]: ...


def _noop_log(_msg: str) -> None:
    return None


def _probe_duration(audio_path: Path) -> float:
    """用 ffprobe 读本地音频时长（秒）。"""
    return probe_media(audio_path).duration


def _today_iso() -> str:
    return datetime.date.today().isoformat()


# ── 编排（含退避重试 + 续签）────────────────────────────────────────────────
def _with_retries(
    op: Callable[[], Any],
    *,
    label: str,
    log: Callable[[str], None],
    sleep: Callable[[float], None],
) -> Any:
    """执行 ``op``，网络 / 5xx 失败按 RETRY_DELAYS_SECONDS 退避重试；4xx 立即抛出。"""
    attempt = 0
    while True:
        try:
            return op()
        except NlsTranscribeError as exc:
            if not exc.retryable or attempt >= MAX_RETRIES:
                raise
            delay = RETRY_DELAYS_SECONDS[attempt]
            log(
                f"{label} 失败（{exc.error_code}），{delay:g}s 后重试 "
                f"（{attempt + 1}/{MAX_RETRIES}）"
            )
            sleep(delay)
            attempt += 1


def _run_oss_url(
    backend: NlsBackend,
    oss_key: str,
    fragment_id: str,
    *,
    log: Callable[[str], None],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
) -> Mapping[str, object]:
    """oss-url 模式：签发 URL → 提交 → 轮询；超 50 分钟自动续签并重提交。"""
    file_link = backend.presign_oss_url(oss_key, SIGNED_URL_EXPIRES_SECONDS)
    task_id = _with_retries(
        lambda: backend.submit_oss_url(file_link),
        label="NLS SubmitTask",
        log=log,
        sleep=sleep,
    )
    url_issued_at = monotonic()
    deadline = monotonic() + NLS_TOTAL_TIMEOUT_SECONDS
    while True:
        resp: Mapping[str, object] = _with_retries(
            lambda: backend.poll_task(task_id),  # noqa: B023 - 同迭代内即时调用，无延迟绑定
            label="NLS GetTaskResult",
            log=log,
            sleep=sleep,
        )
        status = str(resp.get("StatusText", ""))
        if status in _TERMINAL_SUCCESS:
            return resp
        if status in (STATUS_RUNNING, STATUS_QUEUEING):
            now = monotonic()
            if now >= deadline:
                raise NlsTranscribeError(
                    f"NLS 轮询超时（仍为 {status}）", error_code="POLL_TIMEOUT"
                )
            if now - url_issued_at >= RESIGN_THRESHOLD_SECONDS:
                log(
                    f"OSS 签名 URL 轮询已超 {RESIGN_THRESHOLD_SECONDS // 60} 分钟，"
                    f"重新签发并重提交任务 fragment_id={fragment_id}"
                )
                file_link = backend.presign_oss_url(oss_key, SIGNED_URL_EXPIRES_SECONDS)
                task_id = _with_retries(
                    lambda: backend.submit_oss_url(file_link),  # noqa: B023 - 即时调用
                    label="NLS 续签后 SubmitTask",
                    log=log,
                    sleep=sleep,
                )
                url_issued_at = monotonic()
            sleep(NLS_POLL_INTERVAL_SECONDS)
            continue
        raise NlsTranscribeError(
            f"NLS 识别未成功：{status}", error_code=status or "FAILED"
        )


def transcribe_via_nls(
    config: TranscriberConfig,
    fragment_id: str,
    audio_path: Path,
    oss_key: str,
    *,
    backend: NlsBackend,
    counter: DailyCounter,
    log: Callable[[str], None] = _noop_log,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    duration_probe: Callable[[Path], float] | None = None,
    today: Callable[[], str] | None = None,
) -> TranscriptResult:
    """调用 NLS 转写并返回 :class:`TranscriptResult`，附带 §6.8 成本日志。

    ``config.upload_mode`` 决定走 oss-url（默认）还是 direct。两种模式最终都把 NLS
    响应（统一为 filetrans 形状）映射为 transcript schema；``duration`` 取本地实测。
    """
    # 默认在调用时解析（而非 def-time 绑定），便于单测 monkeypatch 模块级函数。
    probe = duration_probe if duration_probe is not None else _probe_duration
    day = today if today is not None else _today_iso
    mode = config.upload_mode
    audio_duration = probe(audio_path)
    start = monotonic()
    if mode == UPLOAD_MODE_DIRECT:
        log(f"transcribe fragment_id={fragment_id} mode={MODE_LOG_DIRECT}")
        resp = _with_retries(
            lambda: backend.transcribe_direct(audio_path),
            label="NLS FlashRecognizer",
            log=log,
            sleep=sleep,
        )
    else:
        log(f"transcribe fragment_id={fragment_id} mode={MODE_LOG_OSS_URL}")
        resp = _run_oss_url(
            backend, oss_key, fragment_id, log=log, sleep=sleep, monotonic=monotonic
        )
    elapsed = monotonic() - start

    result = nls_result_to_transcript(
        resp,
        model=config.model,
        params_version=config.params_version,
        provider=config.provider,
        duration=audio_duration,
    )
    calls, cum_duration = counter.record(audio_duration, day())
    cost_log = build_cost_log(
        fragment_id=fragment_id,
        audio_duration_seconds=audio_duration,
        elapsed_seconds=elapsed,
        provider=config.provider,
        model=config.model,
        estimated_cost_yuan=estimate_cost_yuan(audio_duration),
        cumulative_calls_today=calls,
        cumulative_duration_today_seconds=cum_duration,
    )
    log(json.dumps(cost_log, ensure_ascii=False))
    return result


# ── 真实后端（lazy import 云 SDK）────────────────────────────────────────────
class RealNlsBackend:
    """真实阿里云 NLS 后端：oss-url 走 filetrans，direct 走极速版 FlashRecognizer。

    复用 :mod:`soniscope_worker.verify_prep` 的 OSS / NLS lazy import 辅助；缺少 SDK /
    凭证或网络失败时抛 :class:`NlsTranscribeError`（``error_code`` 仅含异常类名，不泄漏明文）。
    """

    def __init__(self, config: TranscriberConfig) -> None:
        self._config = config
        self._region = config.api_endpoint or "cn-beijing"

    # -- OSS 签名 URL（oss-url 模式）--
    def presign_oss_url(self, oss_key: str, expires_seconds: int) -> str:
        from soniscope_worker import verify_prep
        from soniscope_worker.config import load_config

        full = load_config()
        oss = verify_prep._import_oss()
        client = verify_prep._oss_client(
            oss,
            full.oss.endpoint,
            full.oss.access_key_id,
            full.oss.access_key_secret.get_secret_value(),
        )
        try:
            pre = client.presign(
                oss.GetObjectRequest(bucket=full.oss.bucket, key=oss_key),
                expires=datetime.timedelta(seconds=expires_seconds),
            )
        except Exception as exc:  # noqa: BLE001 - OSS SDK 抛通用异常
            raise NlsTranscribeError(
                f"生成 OSS 签名 URL 失败：{type(exc).__name__}",
                error_code=type(exc).__name__,
                retryable=True,
            ) from exc
        url = getattr(pre, "url", None)
        if not url:
            raise NlsTranscribeError("生成 OSS 签名 URL 失败：响应无 url 字段")
        return str(url)

    # -- filetrans 异步：SubmitTask / GetTaskResult --
    def _filetrans_client_and_request(self) -> tuple[Any, Any]:
        from soniscope_worker import verify_prep

        core = verify_prep._import_nls_core()
        acs_client_cls, common_request_cls = core
        client = acs_client_cls(
            self._config.access_key_id,
            self._config.access_key_secret.get_secret_value(),
            self._region,
        )
        return client, common_request_cls

    def _filetrans_request(self, common_request_cls: Any, action: str, method: str) -> Any:
        from soniscope_worker import verify_prep

        req = common_request_cls()
        req.set_domain(f"filetrans.{self._region}.aliyuncs.com")
        req.set_version(verify_prep.NLS_FILETRANS_VERSION)
        req.set_product(verify_prep.NLS_FILETRANS_PRODUCT)
        req.set_action_name(action)
        req.set_method(method)
        return req

    def submit_oss_url(self, file_link: str) -> str:
        client, common_request_cls = self._filetrans_client_and_request()
        task = {
            "appkey": self._config.appkey.get_secret_value(),
            "file_link": file_link,
            "version": "4.0",
            "enable_words": False,
            "enable_sample_rate_adaptive": True,
        }
        req = self._filetrans_request(common_request_cls, "SubmitTask", "POST")
        req.add_body_params("Task", json.dumps(task, ensure_ascii=False))
        raw = self._do_action(client, req)
        resp = json.loads(raw)
        if resp.get("StatusText") != STATUS_SUCCESS:
            raise NlsTranscribeError(
                f"NLS SubmitTask 未成功：{resp.get('StatusText')}",
                error_code=str(resp.get("StatusText") or "SUBMIT_FAILED"),
            )
        return str(resp["TaskId"])

    def poll_task(self, task_id: str) -> Mapping[str, object]:
        client, common_request_cls = self._filetrans_client_and_request()
        req = self._filetrans_request(common_request_cls, "GetTaskResult", "GET")
        req.add_query_param("TaskId", task_id)
        raw = self._do_action(client, req)
        resp: dict[str, object] = json.loads(raw)
        return resp

    def _do_action(self, client: Any, request: Any) -> Any:
        try:
            return client.do_action_with_exception(request)
        except Exception as exc:  # noqa: BLE001 - POP SDK 抛通用异常
            raise self._classify_exception(exc) from exc

    # -- 极速版 FlashRecognizer（direct 模式）--
    def transcribe_direct(self, audio_path: Path) -> Mapping[str, object]:
        token = self._create_token()
        params = urllib.parse.urlencode(
            {
                "appkey": self._config.appkey.get_secret_value(),
                "format": "wav",
                "sample_rate": "16000",
                "version": "4.0",
                "enable_inverse_text_normalization": "true",
            }
        )
        url = f"https://nls-gateway-{self._region}.aliyuncs.com/stream/v1/FlashRecognizer?{params}"
        request = urllib.request.Request(  # noqa: S310 - 固定 https NLS 网关
            url,
            data=audio_path.read_bytes(),
            method="POST",
            headers={"X-NLS-Token": token, "Content-Type": "application/octet-stream"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as r:  # noqa: S310
                raw = r.read()
        except urllib.error.HTTPError as exc:
            raise NlsTranscribeError(
                f"NLS FlashRecognizer HTTP {exc.code}",
                status_code=exc.code,
                error_code=f"HTTP_{exc.code}",
                retryable=is_retryable_status(exc.code),
            ) from exc
        except urllib.error.URLError as exc:
            raise NlsTranscribeError(
                f"NLS FlashRecognizer 网络错误：{type(exc).__name__}",
                error_code=type(exc).__name__,
                retryable=True,
            ) from exc
        resp = json.loads(raw)
        status = resp.get("status")
        if status != FLASH_STATUS_SUCCESS:
            raise NlsTranscribeError(
                f"NLS FlashRecognizer 未成功：status={status}",
                error_code=str(status or "FLASH_FAILED"),
            )
        return flash_to_filetrans_shape(resp)

    def _create_token(self) -> str:
        from soniscope_worker import verify_prep

        core = verify_prep._import_nls_core()
        acs_client_cls, common_request_cls = core
        # NLS Token 服务仅在 cn-shanghai 提供。
        client = acs_client_cls(
            self._config.access_key_id,
            self._config.access_key_secret.get_secret_value(),
            "cn-shanghai",
        )
        req = common_request_cls()
        req.set_domain("nls-meta.cn-shanghai.aliyuncs.com")
        req.set_version("2019-02-28")
        req.set_action_name("CreateToken")
        req.set_method("POST")
        raw = self._do_action(client, req)
        data = json.loads(raw)
        token = data.get("Token") if isinstance(data, dict) else None
        token_id = token.get("Id") if isinstance(token, dict) else None
        if not token_id:
            raise NlsTranscribeError("NLS CreateToken 未返回 Token.Id")
        return str(token_id)

    @staticmethod
    def _classify_exception(exc: Exception) -> NlsTranscribeError:
        status = getattr(exc, "http_status", None)
        if status is None and hasattr(exc, "get_http_status"):
            try:
                status = exc.get_http_status()
            except Exception:  # noqa: BLE001
                status = None
        code = getattr(exc, "error_code", None)
        if code is None and hasattr(exc, "get_error_code"):
            try:
                code = exc.get_error_code()
            except Exception:  # noqa: BLE001
                code = None
        status_int = int(status) if isinstance(status, int) else 0
        return NlsTranscribeError(
            f"NLS 调用失败：{type(exc).__name__}",
            status_code=status_int,
            error_code=str(code or type(exc).__name__),
            retryable=is_retryable_status(status_int),
        )


# ── make test-*：用真实 fixtures + config + NLS 端到端验证 ──────────────────
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _fixture_path(name: str) -> Path:
    return _repo_root() / "tests" / "audio" / name


# §5.4 联调基线主干（sample-20s.wav）的代表性词，用于宽松比对转写文本是否合理。
_BASELINE_KEYWORDS = ("选择", "优先级")


@dataclass
class _TranscribeTestCtx:
    """make test 用的已加载上下文（config + 后端）。"""

    config: TranscriberConfig
    backend: NlsBackend
    counter: DailyCounter = field(default_factory=DailyCounter)


def _load_test_ctx(
    lines: list[str], *, upload_mode: str | None = None
) -> _TranscribeTestCtx | None:
    """加载 config 并构造 RealNlsBackend；缺 config 时返回 None（调用方 SKIP）。"""
    from soniscope_worker.config import ConfigError, load_config

    try:
        full = load_config()
    except ConfigError as exc:
        lines.append(f"SKIP — 无法加载 config.yaml：{exc}")
        return None
    transcriber = full.transcriber
    if upload_mode is not None and upload_mode != transcriber.upload_mode:
        transcriber = transcriber.model_copy(update={"upload_mode": upload_mode})
    return _TranscribeTestCtx(config=transcriber, backend=RealNlsBackend(transcriber))


def _run_transcribe_sample(
    lines: list[str],
    *,
    fixture: str,
    oss_key: str,
    upload_mode: str,
    expected_mode_log: str,
) -> tuple[TranscriptResult | None, float]:
    """跑一条样例转写，返回 (结果, 端到端耗时秒)；SKIP / 失败时结果为 None。"""
    src = _fixture_path(fixture)
    if not src.is_file():
        lines.append(f"SKIP — 缺少 fixture：{src}（先跑 python3 scripts/fetch_test_fixtures.py）")
        return None, 0.0
    ctx = _load_test_ctx(lines, upload_mode=upload_mode)
    if ctx is None:
        return None, 0.0
    captured: list[str] = []

    def _log(msg: str) -> None:
        captured.append(msg)
        lines.append(msg)

    from soniscope_worker.fixtures import FixtureError
    from soniscope_worker.verify_prep import ProbeError

    start = time.monotonic()
    try:
        result = transcribe_via_nls(
            ctx.config,
            fragment_id=f"test-{upload_mode}",
            audio_path=src,
            oss_key=oss_key,
            backend=ctx.backend,
            counter=ctx.counter,
            log=_log,
        )
    except (NlsTranscribeError, ProbeError, FixtureError) as exc:
        lines.append(f"SKIP — NLS 调用未完成（缺 SDK / 凭证 / 网络 / ffprobe）：{exc}")
        return None, 0.0
    elapsed = time.monotonic() - start
    if not any(f"mode={expected_mode_log}" in line for line in captured):
        lines.append(f"FAIL — 日志未出现 mode={expected_mode_log}")
        return None, elapsed
    return result, elapsed


def run_test_transcribe_oss_url() -> tuple[list[str], int]:
    """make test-transcribe-oss-url：oss-url 模式转写 sample-20s.wav（AC#8）。"""
    lines: list[str] = []
    result, _ = _run_transcribe_sample(
        lines,
        fixture="sample-20s.wav",
        oss_key="sample/sample-20s.wav",
        upload_mode=UPLOAD_MODE_OSS_URL,
        expected_mode_log=MODE_LOG_OSS_URL,
    )
    if result is None:
        return lines, 0 if any("SKIP" in line for line in lines) else 1
    text = transcript_text(result)
    lines.append(f"转写文本：{text[:60]}{'…' if len(text) > 60 else ''}")
    if not text:
        lines.append("FAIL — 转写文本为空")
        return lines, 1
    if not any(kw in text for kw in _BASELINE_KEYWORDS):
        lines.append(f"FAIL — 转写主干与 §5.4 基线不符（期望含 {_BASELINE_KEYWORDS} 其一）")
        return lines, 1
    lines.append("✅ oss-url 模式转写主干与 runbook §5.4 基线相符")
    return lines, 0


def run_test_transcribe_direct() -> tuple[list[str], int]:
    """make test-transcribe-direct：临时 direct 模式转写 sample-20s.wav（AC#9）。"""
    lines: list[str] = []
    result, _ = _run_transcribe_sample(
        lines,
        fixture="sample-20s.wav",
        oss_key="sample/sample-20s.wav",
        upload_mode=UPLOAD_MODE_DIRECT,
        expected_mode_log=MODE_LOG_DIRECT,
    )
    if result is None:
        return lines, 0 if any("SKIP" in line for line in lines) else 1
    text = transcript_text(result)
    lines.append(f"转写文本：{text[:60]}{'…' if len(text) > 60 else ''}")
    if not text:
        lines.append("FAIL — 转写文本为空")
        return lines, 1
    if not any(kw in text for kw in _BASELINE_KEYWORDS):
        lines.append("FAIL — direct 模式转写主干与 oss-url 基线不一致")
        return lines, 1
    lines.append("✅ direct 模式转写主干与 oss-url 一致")
    return lines, 0


# P-01 性能基线阈值（秒）：约 1 分钟音频端到端转写耗时上限（含 NLS 异步排队）。
PERF_THRESHOLD_SECONDS = 120.0


def run_test_transcribe_perf() -> tuple[list[str], int]:
    """make test-transcribe-perf：约 1 分钟音频端到端耗时与 P-01 基线比较（AC#10）。"""
    lines: list[str] = []
    result, elapsed = _run_transcribe_sample(
        lines,
        fixture="sample-54s.wav",
        oss_key="sample/sample-54s.wav",
        upload_mode=UPLOAD_MODE_OSS_URL,
        expected_mode_log=MODE_LOG_OSS_URL,
    )
    if result is None:
        return lines, 0 if any("SKIP" in line for line in lines) else 1
    lines.append(f"端到端耗时 = {elapsed:.1f}s（P-01 阈值 {PERF_THRESHOLD_SECONDS:.0f}s）")
    if elapsed > PERF_THRESHOLD_SECONDS:
        lines.append("FAIL — 端到端耗时超过 P-01 基线阈值")
        return lines, 1
    lines.append("✅ 端到端耗时在 P-01 基线阈值内")
    return lines, 0
