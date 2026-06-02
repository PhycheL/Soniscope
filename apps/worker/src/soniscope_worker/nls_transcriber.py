"""Alibaba Cloud NLS (Intelligent Speech Interaction) ASR transcriber.

Implements :class:`CloudSpeechTranscriber` — the **cloud-speech**
transcriber that calls the Alibaba Cloud NLS *Recording File Recognition*
API (录音文件识别, ``nls-filetrans``) via the ``SubmitTask`` /
``GetTaskResult`` POP (RPC) endpoints.

Two upload modes per tech-spec §5.2:

* **oss-url** (default) — generate a 1-hour OSS presigned GET URL for the
  original OSS object key and pass it to NLS via ``file_link``.  NLS fetches
  the audio directly from OSS, saving Worker egress bandwidth.
* **direct** — read the local standardized ``audio.wav`` and send it
  base64-encoded via ``file_content`` in the SubmitTask body.

Retry policy follows tech-spec §1.5: network / 5xx errors get exponential
backoff (5s → 15s → 45s, max 3); 4xx errors fail immediately.

A structured cost-observability log line (tech-spec §6.8) is emitted after
every successful ASR call.

Usage::

    from soniscope_worker.nls_transcriber import CloudSpeechTranscriber
    from soniscope_worker.config import TranscriberConfig

    cfg = TranscriberConfig(name="cloud-speech", provider="aliyun-nls", ...)
    t = CloudSpeechTranscriber(cfg, oss_client=_build_oss_client(...))
    result = t.transcribe(fragment_id, audio_path, oss_key)
"""

from __future__ import annotations

import base64
import datetime
import json
import logging
import time as time_mod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alibabacloud_oss_v2 import Client as OSSClient

from soniscope_worker.config import TranscriberConfig
from soniscope_worker.transcript import TranscriptResult, TranscriptSegment

logger = logging.getLogger("soniscope_worker.nls_transcriber")

# ──────────────────────────────────────────────────────────────────────────────
# Region → POP endpoint mapping (NLS Recording File Recognition)
# ──────────────────────────────────────────────────────────────────────────────

_REGION_DOMAINS: dict[str, str] = {
    "cn-shanghai": "filetrans.cn-shanghai.aliyuncs.com",
    "cn-beijing": "filetrans.cn-beijing.aliyuncs.com",
    "cn-shenzhen": "filetrans.cn-shenzhen.aliyuncs.com",
}

_PRODUCT = "nls-filetrans"
_API_VERSION = "2018-08-17"
_POST_ACTION = "SubmitTask"
_GET_ACTION = "GetTaskResult"

# NLS final statuses
_STATUS_SUCCESS = "SUCCESS"
_STATUS_RUNNING = "RUNNING"
_STATUS_QUEUEING = "QUEUEING"

# Polling defaults
_POLL_INTERVAL_SECONDS = 5.0
_POLL_TIMEOUT_SECONDS = 3600.0  # 1 hour
_RENEW_THRESHOLD_SECONDS = 3000.0  # 50 min — auto re-sign OSS URL

# Retry config
_RETRY_INTERVALS = (5, 15, 45)  # seconds
_MAX_RETRIES = 3

# Cost config
_COST_PER_HOUR_YUAN = 2.5  # ¥2.50/hour for NLS 录音文件识别


# ──────────────────────────────────────────────────────────────────────────────
# In-memory cumulative counters for cost logging (per Worker process lifetime)
# ──────────────────────────────────────────────────────────────────────────────

_cumulative_calls: int = 0
_cumulative_duration_seconds: float = 0.0
_counter_date: str = ""  # YYYY-MM-DD — reset when day changes


def _reset_counters_if_new_day() -> None:
    """Reset cumulative counters when the local date rolls over."""
    global _cumulative_calls, _cumulative_duration_seconds, _counter_date
    today = datetime.date.today().isoformat()
    if _counter_date != today:
        _cumulative_calls = 0
        _cumulative_duration_seconds = 0.0
        _counter_date = today


# ──────────────────────────────────────────────────────────────────────────────
# OSS presigned URL helper
# ──────────────────────────────────────────────────────────────────────────────


def _generate_presigned_url(
    client: "OSSClient",
    bucket: str,
    object_key: str,
    *,
    expires: datetime.timedelta = datetime.timedelta(hours=1),
) -> str:
    """Generate a presigned GET URL for *object_key* valid for *expires*.

    The URL allows the bearer to download the object without any other
    credentials.  NLS uses this to pull the audio directly from OSS.
    """
    import alibabacloud_oss_v2 as oss2

    req = oss2.GetObjectRequest(bucket=bucket, key=object_key)
    result = client.presign(req, expires=expires)
    url: str = result.url
    return url


# ──────────────────────────────────────────────────────────────────────────────
# NLS SubmitTask / GetTaskResult helpers
# ──────────────────────────────────────────────────────────────────────────────


def _build_nls_client(ak_id: str, ak_secret: str, region: str) -> Any:
    """Return an ``AcsClient`` configured for the NLS region."""
    from aliyunsdkcore.client import AcsClient

    return AcsClient(ak_id, ak_secret, region)


def _submit_nls_task(
    client: Any,
    domain: str,
    *,
    appkey: str,
    file_link: str | None = None,
    file_content: str | None = None,
    enable_words: bool = True,
) -> dict[str, Any]:
    """Submit a recording file recognition task to NLS.

    Exactly one of *file_link* or *file_content* must be provided.

    Returns the raw response dict.  Raises :class:`RuntimeError` on 4xx or
    network failure so the caller can handle retries.
    """
    from aliyunsdkcore.request import CommonRequest

    task: dict[str, Any] = {
        "appkey": appkey,
        "version": "4.0",
        "enable_words": enable_words,
        "enable_sample_rate_adaptive": True,
    }

    if file_link is not None:
        task["file_link"] = file_link
    elif file_content is not None:
        task["file_content"] = file_content
    else:
        raise ValueError("Either file_link or file_content must be provided")

    request = CommonRequest()
    request.set_domain(domain)
    request.set_version(_API_VERSION)
    request.set_product(_PRODUCT)
    request.set_action_name(_POST_ACTION)
    request.set_method("POST")
    request.add_body_params("Task", json.dumps(task, ensure_ascii=False))

    raw: Any = client.do_action_with_exception(request)
    if isinstance(raw, (bytes, bytearray)):
        raw_data: bytes = bytes(raw)
    else:
        raw_data = str(raw).encode("utf-8")
    resp: dict[str, Any] = json.loads(raw_data)

    status = resp.get("StatusText")
    if status != _STATUS_SUCCESS:
        status_code = resp.get("StatusCode", "unknown")
        raise RuntimeError(
            f"NLS SubmitTask failed: StatusText={status}, StatusCode={status_code}"
        )

    return resp


def _poll_nls_result(
    client: Any,
    domain: str,
    task_id: str,
    *,
    interval: float = _POLL_INTERVAL_SECONDS,
    timeout: float = _POLL_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Poll NLS ``GetTaskResult`` until a terminal status is reached.

    Returns the final response dict.  Raises :class:`RuntimeError` on timeout
    or network failure.
    """
    from aliyunsdkcore.request import CommonRequest

    request = CommonRequest()
    request.set_domain(domain)
    request.set_version(_API_VERSION)
    request.set_product(_PRODUCT)
    request.set_action_name(_GET_ACTION)
    request.set_method("GET")
    request.add_query_param("TaskId", task_id)

    deadline = time_mod.monotonic() + timeout
    while True:
        raw = client.do_action_with_exception(request)
        resp = json.loads(raw)
        status = resp.get("StatusText")

        if status in (_STATUS_RUNNING, _STATUS_QUEUEING):
            if time_mod.monotonic() >= deadline:
                raise RuntimeError(
                    f"NLS polling timed out after {timeout:.0f}s (status={status})"
                )
            time_mod.sleep(interval)
            continue

        final_data: dict[str, Any] = resp
        return final_data


# ──────────────────────────────────────────────────────────────────────────────
# Retry wrapper
# ──────────────────────────────────────────────────────────────────────────────


def _retry_on_network_error(
    operation: str,
    callable_fn: Any,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Call *callable_fn* with exponential backoff on network / 5xx errors.

    4xx errors are re-raised immediately (per tech-spec §1.5).
    """
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return callable_fn(*args, **kwargs)
        except Exception as exc:
            msg = str(exc)
            # 4xx-like errors: fail immediately
            if "4xx" in msg or "InvalidParameter" in msg or "InvalidAppKey" in msg:
                raise
            # Check for known 4xx patterns
            is_4xx = any(
                keyword in msg.lower()
                for keyword in (
                    "invalidappkey",
                    "invalidparameter",
                    "unauthorized",
                    "forbidden",
                )
            )
            if is_4xx:
                raise

            if attempt < _MAX_RETRIES:
                wait = _RETRY_INTERVALS[attempt]
                logger.warning(
                    "%s failed (attempt %d/%d), retrying in %ds: %s",
                    operation,
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    wait,
                    msg[:200],
                )
                time_mod.sleep(wait)
            else:
                raise RuntimeError(
                    f"{operation} failed after {_MAX_RETRIES + 1} attempts: {exc}"
                ) from exc


# ──────────────────────────────────────────────────────────────────────────────
# NLS result → TranscriptResult mapping
# ──────────────────────────────────────────────────────────────────────────────


def _nls_to_transcript_result(
    nls_response: dict[str, Any],
    *,
    model: str = "",
    params_version: str = "",
    provider: str = "aliyun-nls",
    language: str = "zh",
) -> TranscriptResult:
    """Map an NLS ``GetTaskResult`` response to :class:`TranscriptResult`.

    Uses ``Result.Sentences`` (sentence-level timestamps in ms) to produce
    segments with ``start`` / ``end`` in seconds.
    """
    result_block = nls_response.get("Result") or {}
    sentences = result_block.get("Sentences") or []

    segments = [
        TranscriptSegment(
            start=float(s.get("BeginTime", 0)) / 1000.0,
            end=float(s.get("EndTime", 0)) / 1000.0,
            text=str(s.get("Text", "")),
        )
        for s in sentences
    ]

    biz_duration_ms = nls_response.get("BizDuration", 0)
    duration = float(biz_duration_ms) / 1000.0 if biz_duration_ms else 0.0

    return TranscriptResult(
        segments=segments,
        language=language,
        model=model,
        params_version=params_version,
        provider=provider,
        duration=duration,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Cost logging
# ──────────────────────────────────────────────────────────────────────────────


def _log_asr_cost(
    *,
    fragment_id: str,
    audio_duration_seconds: float,
    elapsed_seconds: float,
    provider: str,
    model: str,
) -> None:
    """Emit a structured cost-observability log line (tech-spec §6.8)."""
    _reset_counters_if_new_day()
    global _cumulative_calls, _cumulative_duration_seconds

    _cumulative_calls += 1
    _cumulative_duration_seconds += audio_duration_seconds

    estimated_cost = (audio_duration_seconds / 3600.0) * _COST_PER_HOUR_YUAN

    log_entry = json.dumps(
        {
            "event": "asr_call_completed",
            "fragment_id": fragment_id,
            "audio_duration_seconds": round(audio_duration_seconds, 2),
            "elapsed_seconds": round(elapsed_seconds, 2),
            "provider": provider,
            "model": model,
            "estimated_cost_yuan": round(estimated_cost, 4),
            "cumulative_calls_today": _cumulative_calls,
            "cumulative_duration_today_seconds": round(
                _cumulative_duration_seconds, 2
            ),
        },
        ensure_ascii=False,
    )
    logger.info(log_entry)


# ──────────────────────────────────────────────────────────────────────────────
# CloudSpeechTranscriber
# ──────────────────────────────────────────────────────────────────────────────


class CloudSpeechTranscriber:
    """Transcribe audio by calling Alibaba Cloud NLS Recording File Recognition.

    Supports two upload modes:

    * ``oss-url`` — OSS presigned GET URL (default, saves Worker egress)
    * ``direct`` — base64-encode local ``audio.wav`` and send inline
    """

    def __init__(
        self,
        config: TranscriberConfig,
        *,
        oss_client: "OSSClient | None" = None,
        oss_bucket: str = "",
    ) -> None:
        self._config = config
        self._oss_client = oss_client
        self._oss_bucket = oss_bucket

    # ── factory-friendly properties ───────────────────────────────────────

    @property
    def provider(self) -> str:
        return self._config.provider

    @property
    def upload_mode(self) -> str:
        return self._config.upload_mode

    # ── public API ────────────────────────────────────────────────────────

    def transcribe(
        self,
        fragment_id: str,
        audio_path: Path,
        oss_key: str,
    ) -> TranscriptResult:
        """Transcribe *audio_path* via NLS and return structured results.

        When ``upload_mode=oss-url`` this generates a presigned GET URL for
        *oss_key* so NLS fetches the audio directly.  When
        ``upload_mode=direct`` it reads *audio_path* and submits the content
        inline.

        Retries on network / 5xx per tech-spec §1.5.
        """
        t_start = time_mod.monotonic()

        domain = _REGION_DOMAINS.get(
            self._config.api_endpoint,
            "filetrans.cn-beijing.aliyuncs.com",
        )
        nls_client = _build_nls_client(
            self._config.access_key_id,
            self._config.access_key_secret,
            self._config.api_endpoint,
        )

        mode_label: str
        if self._config.upload_mode == "direct":
            result = self._transcribe_direct(
                fragment_id, audio_path, nls_client, domain
            )
            mode_label = "direct-upload"
        else:
            result = self._transcribe_oss_url(
                fragment_id, oss_key, nls_client, domain
            )
            mode_label = "oss-url"

        elapsed = time_mod.monotonic() - t_start

        audio_duration = result.duration or 0.0
        _log_asr_cost(
            fragment_id=fragment_id,
            audio_duration_seconds=audio_duration,
            elapsed_seconds=elapsed,
            provider=self._config.provider,
            model=self._config.model,
        )

        logger.info(
            "asr_done fragment_id=%s mode=%s duration=%.2fs elapsed=%.2fs segments=%d",
            fragment_id,
            mode_label,
            audio_duration,
            elapsed,
            len(result.segments),
        )

        return result

    # ── internal ──────────────────────────────────────────────────────────

    def _transcribe_oss_url(
        self,
        fragment_id: str,
        oss_key: str,
        nls_client: Any,
        domain: str,
    ) -> TranscriptResult:
        """oss-url mode: presign → SubmitTask → poll → map result."""
        if self._oss_client is None:
            raise RuntimeError(
                "oss-url mode requires an OSS client (pass oss_client= to constructor)"
            )

        result: TranscriptResult = _retry_on_network_error(
            "NLS SubmitTask (oss-url)",
            self._do_oss_url_transcribe,
            fragment_id,
            oss_key,
            nls_client,
            domain,
        )
        return result

    def _do_oss_url_transcribe(
        self,
        fragment_id: str,
        oss_key: str,
        nls_client: Any,
        domain: str,
    ) -> TranscriptResult:
        """Core oss-url flow (single attempt — retry wrapper handles retries)."""
        assert self._oss_client is not None  # guaranteed by caller

        # Generate presigned URL (valid 1 hour)
        presigned_url = _generate_presigned_url(
            self._oss_client,
            self._oss_bucket,
            oss_key,
            expires=datetime.timedelta(hours=1),
        )

        # Submit task
        submit_resp = _submit_nls_task(
            nls_client,
            domain,
            appkey=self._config.appkey,
            file_link=presigned_url,
        )
        task_id: str = submit_resp["TaskId"]
        logger.debug("nls_task_submitted fragment_id=%s task_id=%s", fragment_id, task_id)

        # Poll for result
        poll_start = time_mod.monotonic()
        nls_resp = _retry_on_network_error(
            "NLS GetTaskResult (oss-url)",
            self._poll_with_renew,
            nls_client,
            domain,
            task_id,
            oss_key,
            fragment_id,
            poll_start,
        )

        return _nls_to_transcript_result(
            nls_resp,
            model=self._config.model,
            params_version=self._config.params_version,
            provider=self._config.provider,
        )

    def _poll_with_renew(
        self,
        nls_client: Any,
        domain: str,
        task_id: str,
        oss_key: str,
        fragment_id: str,
        poll_start: float,
    ) -> dict[str, Any]:
        """Poll NLS, re-signing the OSS URL after 50 minutes (AC3)."""
        from aliyunsdkcore.request import CommonRequest

        request = CommonRequest()
        request.set_domain(domain)
        request.set_version(_API_VERSION)
        request.set_product(_PRODUCT)
        request.set_action_name(_GET_ACTION)
        request.set_method("GET")
        request.add_query_param("TaskId", task_id)

        deadline = poll_start + _POLL_TIMEOUT_SECONDS
        renew_issued = False

        while True:
            raw = nls_client.do_action_with_exception(request)
            resp = json.loads(raw)
            status = resp.get("StatusText")

            if status in (_STATUS_RUNNING, _STATUS_QUEUEING):
                if time_mod.monotonic() >= deadline:
                    raise RuntimeError(
                        f"NLS polling timed out for {fragment_id} (task={task_id}, status={status})"
                    )

                elapsed = time_mod.monotonic() - poll_start
                if elapsed > _RENEW_THRESHOLD_SECONDS and not renew_issued:
                    # Re-new presigned URL — submit a fresh task
                    logger.info(
                        "nls_presigned_url_renew fragment_id=%s elapsed=%.0fs",
                        fragment_id,
                        elapsed,
                    )
                    assert self._oss_client is not None
                    new_url = _generate_presigned_url(
                        self._oss_client,
                        self._oss_bucket,
                        oss_key,
                        expires=datetime.timedelta(hours=1),
                    )
                    # Re-submit with the fresh URL (AC3)
                    _submit_nls_task(
                        nls_client,
                        domain,
                        appkey=self._config.appkey,
                        file_link=new_url,
                    )
                    renew_issued = True  # only renew once

                time_mod.sleep(_POLL_INTERVAL_SECONDS)
                continue

            final_resp: dict[str, Any] = resp
            return final_resp

    def _transcribe_direct(
        self,
        fragment_id: str,
        audio_path: Path,
        nls_client: Any,
        domain: str,
    ) -> TranscriptResult:
        """Direct mode: base64-encode audio → SubmitTask → poll → map."""
        logger.info(
            "nls_direct_upload mode=direct-upload fragment_id=%s", fragment_id
        )

        # Read and base64-encode the local audio.wav
        audio_bytes = audio_path.read_bytes()
        file_content = base64.b64encode(audio_bytes).decode("ascii")

        if len(audio_bytes) > 10 * 1024 * 1024:  # 10 MB sanity check
            logger.warning(
                "nls_direct_upload_large_file fragment_id=%s size=%d",
                fragment_id,
                len(audio_bytes),
            )

        direct_result: TranscriptResult = _retry_on_network_error(
            "NLS SubmitTask (direct)",
            self._do_direct_transcribe,
            fragment_id,
            file_content,
            audio_bytes,
            nls_client,
            domain,
        )
        return direct_result

    def _do_direct_transcribe(
        self,
        fragment_id: str,
        file_content: str,
        audio_bytes: bytes,
        nls_client: Any,
        domain: str,
    ) -> TranscriptResult:
        """Core direct flow (single attempt)."""
        submit_resp = _submit_nls_task(
            nls_client,
            domain,
            appkey=self._config.appkey,
            file_content=file_content,
        )
        task_id = submit_resp["TaskId"]
        logger.debug(
            "nls_task_submitted_direct fragment_id=%s task_id=%s size=%d",
            fragment_id,
            task_id,
            len(audio_bytes),
        )

        nls_resp = _poll_nls_result(nls_client, domain, task_id)

        return _nls_to_transcript_result(
            nls_resp,
            model=self._config.model,
            params_version=self._config.params_version,
            provider=self._config.provider,
        )
