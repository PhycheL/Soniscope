"""Worker 幂等规则与显式重转 CLI（US-028，tech-spec §3.7）。

**正常轮询幂等**（已在 :mod:`soniscope_worker.pipeline` 落实）：转写前只检查 ``.done``，
存在即跳过，**不**比较当前配置的 ``model`` / ``params_version``——即便升级了模型，普通轮询也
不会自动重转（AC#1）。转写完成后 ``manifest.transcription`` 记录八字段四元组 + 计时（AC#2）。

**显式重转**是唯一绕过自动幂等的存量重转入口：

```
python -m soniscope_worker retranscribe <fragment_id> \
    [--all-from <YYYY-MM-DD>] [--upgrade] [--force]
```

| flag | 行为 |
|---|---|
| （无 flag） | ``.done`` 存在 → 提示「已完成，使用 --force 或 --upgrade」并跳过（AC#5） |
| ``--upgrade`` | 仅重转 manifest ``model`` / ``params_version`` 异于当前配置者（AC#7） |
| ``--force`` | 无条件重转，原子覆盖 ``transcript.json`` / ``transcript.txt``（AC#6） |
| ``--all-from <date>`` | 批量扫描该日期及之后目录，单条失败不中断，最后汇总（AC#8） |

重转与主轮询共用 :func:`soniscope_worker.locks.fragment_lock` 文件锁，保证同一 ``fragment_id``
不会被并发转两遍（AC#9）。沿用「纯逻辑（无 IO，可直接单测）+ IO 注入」分层：转写器可注入，
``make test-*`` 用 stub 转写器自包含验证，单测全程不触网。
"""

from __future__ import annotations

import json
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from soniscope_worker.config import TranscriberConfig
from soniscope_worker.locks import fragment_lock
from soniscope_worker.oss_admin import OssAdminError, object_key_for
from soniscope_worker.pipeline import (
    _now_iso,
    _transcription_block,
    _write_transcript_outputs,
)
from soniscope_worker.recovery import (
    AUDIO_FILENAME,
    DONE_MARKER,
    MANIFEST_FILENAME,
    atomic_write_json,
    create_done_marker,
    scan_fragments,
)
from soniscope_worker.transcriber import Transcriber

# RetranscribeOutcome.status 取值。
STATUS_RETRANSCRIBED = "retranscribed"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
STATUS_NOT_FOUND = "not-found"

# 决策原因（供日志与汇总，便于人工核对 / 测试断言）。
REASON_DONE_NO_FLAG = "已完成（.done 存在），使用 --force 或 --upgrade 才会重转"
REASON_UPGRADE_SAME = "model / params_version 已是当前配置版本，--upgrade 跳过"
REASON_FORCE = "--force：无条件重转"
REASON_UPGRADE_CHANGED = "--upgrade：manifest 版本与当前配置不同，重转"
REASON_NO_DONE = "无 .done（转写未完），执行重转"


@dataclass(frozen=True)
class RetranscribeOutcome:
    """单条 Fragment 的重转结果。"""

    fragment_id: str
    status: str  # retranscribed / skipped / failed / not-found
    reason: str = ""

    @property
    def retranscribed(self) -> bool:
        return self.status == STATUS_RETRANSCRIBED


# ── 纯逻辑：是否重转决策（不读写文件，直接单测）──────────────────────────────
def should_retranscribe(
    *,
    done_exists: bool,
    manifest_model: str | None,
    manifest_params_version: str | None,
    config_model: str,
    config_params_version: str,
    force: bool,
    upgrade: bool,
) -> tuple[bool, str]:
    """根据 flag 与 manifest / config 版本判定是否重转（§3.7 决策表，纯逻辑）。

    优先级：``--force`` > ``--upgrade`` > 无 flag。``--force`` 无条件重转；``--upgrade`` 仅当
    manifest 的 ``model`` 或 ``params_version`` 与当前配置不同才重转；无 flag 时 ``.done`` 存在
    则跳过（提示用 --force/--upgrade），无 ``.done`` 则视为转写未完执行重转。
    """
    if force:
        return True, REASON_FORCE
    if upgrade:
        changed = (
            manifest_model != config_model
            or manifest_params_version != config_params_version
        )
        return (True, REASON_UPGRADE_CHANGED) if changed else (False, REASON_UPGRADE_SAME)
    if done_exists:
        return False, REASON_DONE_NO_FLAG
    return True, REASON_NO_DONE


def _read_manifest(manifest_path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    return data


# ── 单条重转 ───────────────────────────────────────────────────────────────
def retranscribe_one(
    fragment_id: str,
    transcriber: Transcriber,
    *,
    config: TranscriberConfig,
    fragments_root: Path,
    tmp_root: Path,
    lock_root: Path | None = None,
    force: bool = False,
    upgrade: bool = False,
    now_iso: Callable[[], str] | None = None,
    monotonic: Callable[[], float] | None = None,
    log: Callable[[str], None] = lambda _msg: None,
) -> RetranscribeOutcome:
    """重转单个 Fragment：按 flag 决策 → 转写现有 ``audio.wav`` → 原子覆盖 transcript / .done。

    定位目录由 ``fragment_id`` 推导（``fragments/<date>/<id>/``）。决策不通过时返回
    ``skipped``；缺目录 / ``audio.wav`` 返回 ``not-found``；缺 / 损坏 manifest 返回 ``failed``。
    实际转写在 :func:`fragment_lock` 内进行，与主轮询互斥（AC#9）。``transcript.json`` /
    ``transcript.txt`` 经临时文件 + 原子 rename 覆盖（AC#6）。
    """
    resolve_now = now_iso if now_iso is not None else _now_iso
    resolve_mono = monotonic if monotonic is not None else time.monotonic
    locks = lock_root if lock_root is not None else tmp_root

    try:
        date = object_key_for(fragment_id).split("/")[1]
    except OssAdminError as exc:
        log(f"[retranscribe] {fragment_id} 非法 fragment_id：{exc}")
        return RetranscribeOutcome(fragment_id, STATUS_FAILED, f"非法 fragment_id：{exc}")

    frag_dir = fragments_root / date / fragment_id
    audio_path = frag_dir / AUDIO_FILENAME
    manifest_path = frag_dir / MANIFEST_FILENAME
    if not frag_dir.is_dir() or not audio_path.is_file():
        log(f"[retranscribe] {fragment_id} 找不到 fragment 目录或缺 audio.wav：{frag_dir}")
        return RetranscribeOutcome(
            fragment_id, STATUS_NOT_FOUND, f"找不到 {frag_dir} 或缺 audio.wav"
        )
    if not manifest_path.is_file():
        log(f"[retranscribe] {fragment_id} 缺 manifest.json，无法重转：{manifest_path}")
        return RetranscribeOutcome(fragment_id, STATUS_FAILED, "缺 manifest.json")
    try:
        manifest = _read_manifest(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        log(f"[retranscribe] {fragment_id} manifest.json 读取失败：{exc}")
        return RetranscribeOutcome(fragment_id, STATUS_FAILED, f"manifest 读取失败：{exc}")

    transcription = manifest.get("transcription") or {}
    decided, reason = should_retranscribe(
        done_exists=(frag_dir / DONE_MARKER).exists(),
        manifest_model=transcription.get("model"),
        manifest_params_version=transcription.get("params_version"),
        config_model=config.model,
        config_params_version=config.params_version,
        force=force,
        upgrade=upgrade,
    )
    if not decided:
        log(f"[retranscribe] {fragment_id} 跳过：{reason}")
        return RetranscribeOutcome(fragment_id, STATUS_SKIPPED, reason)

    object_key = object_key_for(fragment_id)
    with fragment_lock(locks, fragment_id):
        started_at = resolve_now()
        t0 = resolve_mono()
        try:
            result = transcriber.transcribe(fragment_id, audio_path, object_key)
        except Exception as exc:  # noqa: BLE001 - 重转失败不覆盖产物 / 不重建 .done
            log(
                f"[retranscribe] {fragment_id} 转写失败：{type(exc).__name__}: {exc}"
            )
            return RetranscribeOutcome(
                fragment_id, STATUS_FAILED, f"转写失败：{type(exc).__name__}: {exc}"
            )
        completed_at = resolve_now()
        elapsed = round(resolve_mono() - t0, 3)
        try:
            # 原子覆盖 transcript.json（经 tmp/<id>.transcript.json.tmp）+ transcript.txt（AC#6）。
            _write_transcript_outputs(frag_dir, fragment_id, result, tmp_root=tmp_root)
            manifest["transcription"] = _transcription_block(
                config, result,
                started_at=started_at, completed_at=completed_at, elapsed_seconds=elapsed,
            )
            atomic_write_json(manifest_path, manifest)
        except OSError as exc:
            log(f"[retranscribe] {fragment_id} 落盘失败：{exc}")
            return RetranscribeOutcome(fragment_id, STATUS_FAILED, f"落盘失败：{exc}")
        create_done_marker(frag_dir)  # 0 字节，幂等重建
    log(f"[retranscribe] {fragment_id} 重转完成（{reason}，耗时 {elapsed}s）")
    return RetranscribeOutcome(fragment_id, STATUS_RETRANSCRIBED, reason)


# ── 批量重转（--all-from <date>）────────────────────────────────────────────
@dataclass(frozen=True)
class BatchReport:
    """批量重转汇总（AC#8）。"""

    outcomes: list[RetranscribeOutcome]

    @property
    def retranscribed(self) -> int:
        return sum(1 for o in self.outcomes if o.status == STATUS_RETRANSCRIBED)

    @property
    def skipped(self) -> int:
        return sum(1 for o in self.outcomes if o.status == STATUS_SKIPPED)

    @property
    def failed(self) -> int:
        return sum(1 for o in self.outcomes if o.status in (STATUS_FAILED, STATUS_NOT_FOUND))

    def summary(self) -> str:
        return (
            f"批量重转完成：成功 {self.retranscribed}、跳过 {self.skipped}、失败 {self.failed}"
        )


def retranscribe_all_from(
    from_date: str,
    transcriber: Transcriber,
    *,
    config: TranscriberConfig,
    fragments_root: Path,
    tmp_root: Path,
    lock_root: Path | None = None,
    force: bool = False,
    upgrade: bool = False,
    now_iso: Callable[[], str] | None = None,
    monotonic: Callable[[], float] | None = None,
    log: Callable[[str], None] = lambda _msg: None,
) -> BatchReport:
    """批量扫描 ``from_date`` 及之后的 fragment 目录逐条重转（AC#8）。

    单条失败（转写异常 / 缺 manifest 等）不中断，收敛为 ``failed`` / ``not-found`` 继续下一条，
    最后输出成功 / 跳过 / 失败汇总。日期目录名为 ``YYYY-MM-DD``，字典序与时间序一致，故
    ``date >= from_date`` 字符串比较即可筛选。
    """
    states = [s for s in scan_fragments(fragments_root) if s.date >= from_date]
    log(f"[retranscribe] --all-from {from_date}：命中 {len(states)} 个 Fragment 目录")
    outcomes: list[RetranscribeOutcome] = []
    for state in states:
        outcomes.append(
            retranscribe_one(
                state.fragment_id,
                transcriber,
                config=config,
                fragments_root=fragments_root,
                tmp_root=tmp_root,
                lock_root=lock_root,
                force=force,
                upgrade=upgrade,
                now_iso=now_iso,
                monotonic=monotonic,
                log=log,
            )
        )
    report = BatchReport(outcomes)
    log(f"[retranscribe] {report.summary()}")
    return report


# ── make retranscribe 真实入口（读 config + 真实 Transcriber + $SONISCOPE_HOME）──
def run_retranscribe(
    *,
    fragment_id: str | None,
    all_from: str | None,
    upgrade: bool,
    force: bool,
    log: Callable[[str], None] | None = None,
) -> tuple[list[str], int]:
    """``make retranscribe`` / ``python -m soniscope_worker retranscribe`` 真实入口。

    读 config.yaml + 构造真实 Transcriber + 解析 ``$SONISCOPE_HOME`` 运行时目录，按
    ``--all-from`` / ``<fragment_id>`` 分派单条或批量。缺 config 时打印诊断并以非零退出。
    既未提供 fragment_id 也未提供 ``--all-from`` 时报参数错误（非零退出）。
    """
    from soniscope_worker.config import ConfigError, config_path, load_config
    from soniscope_worker.paths import fragments_dir, tmp_dir
    from soniscope_worker.transcriber import create_transcriber

    lines: list[str] = []
    emit = log if log is not None else lines.append

    if not all_from and not fragment_id:
        emit("FAIL — 必须提供 <fragment_id> 或 --all-from <YYYY-MM-DD>")
        return lines, 1

    try:
        cfg = load_config(config_path())
    except ConfigError as exc:
        emit(f"FAIL — 无法加载 config.yaml：{exc}")
        return lines, 1

    transcriber = create_transcriber(cfg.transcriber)
    fragments_root = fragments_dir()
    tmp_root = tmp_dir()

    if all_from:
        report = retranscribe_all_from(
            all_from, transcriber, config=cfg.transcriber,
            fragments_root=fragments_root, tmp_root=tmp_root,
            force=force, upgrade=upgrade, log=emit,
        )
        return lines, (1 if report.failed else 0)

    if fragment_id is None:  # 前置 guard 已保证不可达，仅为类型收窄
        emit("FAIL — 必须提供 <fragment_id> 或 --all-from <YYYY-MM-DD>")
        return lines, 1
    outcome = retranscribe_one(
        fragment_id, transcriber, config=cfg.transcriber,
        fragments_root=fragments_root, tmp_root=tmp_root,
        force=force, upgrade=upgrade, log=emit,
    )
    emit(f"{outcome.fragment_id}: {outcome.status} — {outcome.reason}")
    return lines, (1 if outcome.status in (STATUS_FAILED, STATUS_NOT_FOUND) else 0)


# ── make test-*：自包含验证（stub 转写器，不触网）──────────────────────────
_BASE_FID = "20260527T150000_devr01_01HZX3K8MN5PQR9TFB7AYWVCDE"
_UPGRADE_OLD_FID = "20260527T150100_devr02_01HZX3K8MN5PQR9TFB7AYWVCDF"
_UPGRADE_CUR_FID = "20260527T150200_devr03_01HZX3K8MN5PQR9TFB7AYWVCDG"

_CUR_MODEL = "中文普通话（识音石 V1 - 端到端模型)"
_CUR_PARAMS = "v2"
_OLD_PARAMS = "v1"


def _stub_config(model: str = _CUR_MODEL, params_version: str = _CUR_PARAMS) -> TranscriberConfig:
    return TranscriberConfig.model_validate(
        {
            "name": "cloud-speech",
            "provider": "aliyun-nls",
            "model": model,
            "params_version": params_version,
            "api_endpoint": "cn-beijing",
            "appkey": "stub-appkey-0000",
            "access_key_id": "stub-ak-id",
            "access_key_secret": "stub-ak-secret-0000",
            "upload_mode": "oss-url",
        }
    )


class _StubTranscriber:
    """make test 用确定性占位转写器：返回可识别的新文本以验证覆盖。"""

    name = "cloud-speech"

    def __init__(self, *, text: str, model: str = _CUR_MODEL, params_version: str = _CUR_PARAMS):
        self._text = text
        self._model = model
        self._params = params_version

    def transcribe(self, fragment_id: str, audio_path: Path, oss_key: str) -> Any:
        from soniscope_worker.transcriber import Segment, TranscriptResult

        return TranscriptResult(
            segments=[Segment(0.0, 1.0, self._text)],
            language="zh",
            model=self._model,
            params_version=self._params,
            provider="aliyun-nls",
            duration=24.0,
        )


def _make_done_fragment(
    fragments_root: Path,
    tmp_root: Path,
    fragment_id: str,
    *,
    model: str,
    params_version: str,
    transcript_text: str,
) -> Path:
    """构造一个已 ``.done`` 的 Fragment（audio.wav + manifest + transcript.* + .done）。"""
    from soniscope_worker.recovery import atomic_write_text, write_transcript_json

    date = object_key_for(fragment_id).split("/")[1]
    frag_dir = fragments_root / date / fragment_id
    frag_dir.mkdir(parents=True, exist_ok=True)
    (frag_dir / AUDIO_FILENAME).write_bytes(b"RIFF....WAVEfake-audio")
    manifest = {
        "fragment_id": fragment_id,
        "session_id": None,
        "chunk_seq": 1,
        "chunk_total": None,
        "device_id": fragment_id.split("_")[1],
        "recorded_at": "2026-05-27T15:00:00+08:00",
        "duration_seconds": 24,
        "audio": {"format": "wav", "original_format": "wav", "size_bytes": 22, "sha256": "stub"},
        "upload": {
            "uploaded_at": "2026-05-27T15:00:30+08:00",
            "verified_at": "2026-05-27T15:00:32+08:00",
            "verify_method": "fc-head-object",
            "original_sha256": "stub",
            "original_size_bytes": 22,
        },
        "transcription": {
            "started_at": "2026-05-27T15:01:00+08:00",
            "completed_at": "2026-05-27T15:01:05+08:00",
            "elapsed_seconds": 5.0,
            "transcriber": "cloud-speech",
            "model": model,
            "params_version": params_version,
            "provider": "aliyun-nls",
            "upload_mode": "oss-url",
        },
    }
    atomic_write_json(frag_dir / MANIFEST_FILENAME, manifest)
    write_transcript_json(
        frag_dir,
        fragment_id,
        {
            "segments": [{"start": 0.0, "end": 1.0, "text": transcript_text}],
            "language": "zh",
            "model": model,
            "params_version": params_version,
            "provider": "aliyun-nls",
        },
        tmp_root=tmp_root,
    )
    atomic_write_text(frag_dir / "transcript.txt", transcript_text)
    create_done_marker(frag_dir)
    return frag_dir


def _read_txt(frag_dir: Path) -> str:
    return (frag_dir / "transcript.txt").read_text(encoding="utf-8")


def run_test_idempotent_skip() -> tuple[list[str], int]:
    """make test-idempotent-skip：无 flag + ``.done`` 存在 → 跳过且不重转（AC#5）。"""
    lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="soniscope-idempotent-skip-") as tmpdir:
        base = Path(tmpdir)
        fragments, tmp = base / "fragments", base / "tmp"
        frag = _make_done_fragment(
            fragments, tmp, _BASE_FID, model=_CUR_MODEL,
            params_version=_CUR_PARAMS, transcript_text="原始转写",
        )
        outcome = retranscribe_one(
            _BASE_FID, _StubTranscriber(text="不应出现"),
            config=_stub_config(), fragments_root=fragments, tmp_root=tmp, log=lines.append,
        )
        problems: list[str] = []
        if outcome.status != STATUS_SKIPPED:
            problems.append(f"无 flag + .done 应跳过，实际 {outcome.status}")
        if "已完成" not in outcome.reason:
            problems.append(f"跳过原因应提示已完成 / --force / --upgrade，实际：{outcome.reason}")
        if _read_txt(frag) != "原始转写":
            problems.append("跳过时 transcript.txt 不应被改写")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ 幂等跳过校验通过（无 flag + .done → 提示已完成并跳过，产物未改写）")
    return lines, 0


def run_test_no_auto_retranscribe() -> tuple[list[str], int]:
    """make test-no-auto-retranscribe：模型 / 参数变化时普通轮询不自动重转（AC#1）。"""
    from soniscope_worker.pipeline import _FixtureSource, run_pipeline_once

    lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="soniscope-no-auto-retrans-") as tmpdir:
        base = Path(tmpdir)
        inbox, failed = base / "inbox", base / "inbox" / "failed"
        fragments, tmp = base / "fragments", base / "tmp"
        for d in (inbox, failed, fragments, tmp):
            d.mkdir(parents=True, exist_ok=True)
        # 已 .done 的 Fragment（manifest 记录旧 params_version）。
        frag = _make_done_fragment(
            fragments, tmp, _BASE_FID, model=_CUR_MODEL,
            params_version=_OLD_PARAMS, transcript_text="原始转写",
        )
        object_key = object_key_for(_BASE_FID)
        # 当前配置已升级 params_version，但普通轮询只看 .done 不应重转。
        source = _FixtureSource(object_key, b"RIFF....WAVEfake-audio", {"sha256": "stub"})
        results = run_pipeline_once(
            source, _StubTranscriber(text="不应出现"),
            config=_stub_config(params_version=_CUR_PARAMS),
            fragments_root=fragments, inbox_root=inbox, failed_root=failed, tmp_root=tmp,
            log=lines.append,
        )
        problems: list[str] = []
        if results:
            problems.append(f"已 .done Fragment 不应被普通轮询处理，实际处理 {len(results)} 条")
        if source.download_calls:
            problems.append(f"已 .done Fragment 不应被重新下载（{len(source.download_calls)} 次）")
        if _read_txt(frag) != "原始转写":
            problems.append("普通轮询不应自动重转改写 transcript.txt")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ 普通轮询不自动重转校验通过（.done 存在即跳过，不比较 model/params_version）")
    return lines, 0


def run_test_cli_retranscribe() -> tuple[list[str], int]:
    """make test-cli-retranscribe：``--force`` 无条件重转并原子覆盖 transcript（AC#6）。"""
    lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="soniscope-cli-retrans-") as tmpdir:
        base = Path(tmpdir)
        fragments, tmp = base / "fragments", base / "tmp"
        frag = _make_done_fragment(
            fragments, tmp, _BASE_FID, model=_CUR_MODEL,
            params_version=_CUR_PARAMS, transcript_text="原始转写",
        )
        outcome = retranscribe_one(
            _BASE_FID, _StubTranscriber(text="强制重转结果"),
            config=_stub_config(), fragments_root=fragments, tmp_root=tmp,
            force=True, log=lines.append,
        )
        problems: list[str] = []
        if not outcome.retranscribed:
            problems.append(f"--force 应重转，实际 {outcome.status}：{outcome.reason}")
        if _read_txt(frag) != "强制重转结果":
            problems.append(f"--force 后 transcript.txt 应被覆盖，实际：{_read_txt(frag)!r}")
        tj = json.loads((frag / "transcript.json").read_text(encoding="utf-8"))
        if tj.get("segments", [{}])[0].get("text") != "强制重转结果":
            problems.append("--force 后 transcript.json 应被覆盖")
        if not (frag / DONE_MARKER).is_file():
            problems.append("--force 重转后 .done 应仍存在")
        if (frag / DONE_MARKER).stat().st_size != 0:
            problems.append(".done 应为 0 字节空文件")
        # transcript.json 临时文件应已清理（rename 完成）。
        if (tmp / f"{_BASE_FID}.transcript.json.tmp").exists():
            problems.append("transcript.json 落盘后临时文件未清理")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ --force 重转校验通过（无条件重转，原子覆盖 transcript.json/txt，重建 .done）")
    return lines, 0


def run_test_cli_upgrade() -> tuple[list[str], int]:
    """make test-cli-upgrade：``--upgrade`` 只重转版本不同的 Fragment（AC#7/#8）。"""
    lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="soniscope-cli-upgrade-") as tmpdir:
        base = Path(tmpdir)
        fragments, tmp = base / "fragments", base / "tmp"
        # 旧版本 Fragment（params_version=v1，应被升级重转）。
        old_frag = _make_done_fragment(
            fragments, tmp, _UPGRADE_OLD_FID, model=_CUR_MODEL,
            params_version=_OLD_PARAMS, transcript_text="旧版本转写",
        )
        # 当前版本 Fragment（params_version=v2，应跳过）。
        cur_frag = _make_done_fragment(
            fragments, tmp, _UPGRADE_CUR_FID, model=_CUR_MODEL,
            params_version=_CUR_PARAMS, transcript_text="当前版本转写",
        )
        report = retranscribe_all_from(
            "2026-05-27", _StubTranscriber(text="升级后转写", params_version=_CUR_PARAMS),
            config=_stub_config(params_version=_CUR_PARAMS),
            fragments_root=fragments, tmp_root=tmp, upgrade=True, log=lines.append,
        )
        by_id = {o.fragment_id: o for o in report.outcomes}
        problems: list[str] = []
        if by_id.get(_UPGRADE_OLD_FID, RetranscribeOutcome("", "")).status != STATUS_RETRANSCRIBED:
            problems.append("旧 params_version Fragment 应被 --upgrade 重转")
        if by_id.get(_UPGRADE_CUR_FID, RetranscribeOutcome("", "")).status != STATUS_SKIPPED:
            problems.append("当前 params_version Fragment 应被 --upgrade 跳过")
        if _read_txt(old_frag) != "升级后转写":
            problems.append("旧版本 Fragment transcript.txt 应被升级覆盖")
        if _read_txt(cur_frag) != "当前版本转写":
            problems.append("当前版本 Fragment transcript.txt 不应被改写")
        if report.retranscribed != 1 or report.skipped != 1:
            problems.append(f"汇总应为 重转 1 / 跳过 1，实际 {report.summary()}")
        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1
    lines.append("✅ --upgrade 重转校验通过（仅旧 model/params_version 被重转，当前版本跳过）")
    return lines, 0
