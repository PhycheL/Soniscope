"""Worker OSS 轮询、HeadObject 元数据读取与安全下载（US-021）。

本模块是 Worker 主流水线的入口：按 ``poll.interval_seconds`` 周期列出 OSS
``recordings/`` 前缀对象，跳过本地已有 ``.done`` 的 Fragment，把新对象下载到
``inbox/<fragment_id>.part``，下载后计算 sha256 并与 HeadObject 读回的
``x-oss-meta-sha256`` 比对（不一致删除 ``.part`` 等下一轮重下），同时把
``x-oss-meta-*`` 用户自定义元数据映射到 manifest 草稿字段。

沿用既有「纯逻辑（无 IO，可直接单测）+ IO 用 ``OssSource`` Protocol 注入」的分层：
单测注入 ``FakeSource`` 不触网，真实运行用 ``RealOssSource``（lazy import OSS SDK）。

**安全红线**：本模块（Worker 业务路径）**绝不**调用 OSS ``DeleteObject`` 或等价删除；
``OssSource`` 协议只暴露 list / head / download，不含任何删除能力。``.part`` 的删除
仅针对**本地** inbox 中间态文件（sha256 不符或崩溃残留），与 OSS 对象删除无关。
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from soniscope_worker.config import ConfigError, SoniScopeConfig, config_path, load_config
from soniscope_worker.fixtures import sha256_of
from soniscope_worker.oss_admin import OssAdminError, object_key_for
from soniscope_worker.paths import fragments_dir, inbox_dir

RECORDINGS_PREFIX = "recordings/"

# x-oss-meta-* 用户自定义元数据键（OSS SDK 读回时通常已去掉前缀，这里两种都兼容）。
META_PREFIX = "x-oss-meta-"
META_SESSION_ID = "session-id"
META_CHUNK_SEQ = "chunk-seq"
META_CHUNK_TOTAL = "chunk-total"
META_RECORDED_AT = "recorded-at"
META_DURATION = "duration"
META_ORIGINAL_FORMAT = "original-format"
META_SHA256 = "sha256"

# 扫描间隔校验容差（make test-poll-interval 用），单位秒。
SCAN_INTERVAL_TOLERANCE_SECONDS = 5.0


# ── 纯逻辑：object key ↔ fragment_id ↔ 本地路径 ─────────────────────────────
def fragment_id_from_key(key: str) -> str | None:
    """从 OSS object key 反推 ``fragment_id``；非 ``recordings/<date>/<id>.wav`` 返回 None。

    通过 ``object_key_for(fragment_id) == key`` 往返校验，一并保证 fragment_id 格式、
    日期合法且路径中的日期与 fragment_id 前缀一致。
    """
    if not key.startswith(RECORDINGS_PREFIX) or not key.endswith(".wav"):
        return None
    fragment_id = key.rsplit("/", 1)[-1][: -len(".wav")]
    try:
        if object_key_for(fragment_id) == key:
            return fragment_id
    except OssAdminError:
        return None
    return None


def date_of(fragment_id: str) -> str:
    """由 ``fragment_id`` 推导日期目录 ``<YYYY-MM-DD>``（与 object key 一致）。"""
    return object_key_for(fragment_id).split("/")[1]


def fragment_dir(fragments_root: Path, date: str, fragment_id: str) -> Path:
    """完成态 Fragment 目录 ``fragments/<date>/<fragment_id>/``。"""
    return fragments_root / date / fragment_id


def done_marker_path(fragments_root: Path, date: str, fragment_id: str) -> Path:
    """该 Fragment 的 ``.done`` 标记路径。"""
    return fragment_dir(fragments_root, date, fragment_id) / ".done"


def part_path(inbox_root: Path, fragment_id: str) -> Path:
    """下载中间态 ``inbox/<fragment_id>.part``。"""
    return inbox_root / f"{fragment_id}.part"


# ── 纯逻辑：元数据 → manifest 草稿 ──────────────────────────────────────────
def normalize_metadata(raw: Mapping[str, str]) -> dict[str, str]:
    """归一化用户自定义元数据键：小写、去掉可能存在的 ``x-oss-meta-`` 前缀。"""
    out: dict[str, str] = {}
    for k, v in raw.items():
        key = str(k).lower()
        if key.startswith(META_PREFIX):
            key = key[len(META_PREFIX) :]
        out[key] = str(v)
    return out


def _as_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _as_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


@dataclass(frozen=True)
class ManifestDraft:
    """从 OSS 用户自定义元数据映射出的 manifest 草稿字段（US-024 最终落盘）。

    ``chunk_total`` 遵循 §3.2 约定：OSS 端非分片存 ``"0"``，映射到 manifest 为 ``None``。
    """

    fragment_id: str
    session_id: str | None = None
    chunk_seq: int | None = None
    chunk_total: int | None = None
    recorded_at: str | None = None
    duration_seconds: float | None = None
    original_format: str | None = None
    original_sha256: str | None = None


def metadata_to_draft(fragment_id: str, raw: Mapping[str, str]) -> ManifestDraft:
    """把 HeadObject 读回的 ``x-oss-meta-*`` 元数据映射为 manifest 草稿字段。"""
    meta = normalize_metadata(raw)
    chunk_total = _as_int(meta.get(META_CHUNK_TOTAL))
    if chunk_total is not None and chunk_total <= 0:
        chunk_total = None  # OSS 非分片用 "0" → manifest None（§3.2）
    return ManifestDraft(
        fragment_id=fragment_id,
        session_id=meta.get(META_SESSION_ID) or None,
        chunk_seq=_as_int(meta.get(META_CHUNK_SEQ)),
        chunk_total=chunk_total,
        recorded_at=meta.get(META_RECORDED_AT) or None,
        duration_seconds=_as_float(meta.get(META_DURATION)),
        original_format=meta.get(META_ORIGINAL_FORMAT) or None,
        original_sha256=(meta.get(META_SHA256) or None),
    )


# ── 纯逻辑：下载计划 + 扫描间隔校验 ────────────────────────────────────────
@dataclass(frozen=True)
class OssListing:
    """OSS list 返回的单个对象（key + size）。"""

    key: str
    size: int = 0


@dataclass(frozen=True)
class PollPlan:
    """一个待下载对象的计划项。"""

    fragment_id: str
    object_key: str
    date: str
    size: int


@dataclass(frozen=True)
class ScanPlan:
    """一轮扫描的决策结果。"""

    to_download: list[PollPlan] = field(default_factory=list)
    skipped_done: list[str] = field(default_factory=list)
    ignored_keys: list[str] = field(default_factory=list)


def plan_downloads(
    listings: list[OssListing], *, done_check: Callable[[str, str], bool]
) -> ScanPlan:
    """根据 list 结果与本地 ``.done`` 状态决定下载哪些对象（纯逻辑）。

    - 非 ``recordings/<date>/<id>.wav`` 的 key 进 ``ignored_keys``；
    - 本地已有 ``.done`` 的 fragment 进 ``skipped_done``（不下载、不转写，AC#2）；
    - 其余进 ``to_download``。
    """
    plan = ScanPlan()
    for lst in listings:
        fid = fragment_id_from_key(lst.key)
        if fid is None:
            plan.ignored_keys.append(lst.key)
            continue
        date = date_of(fid)
        if done_check(fid, date):
            plan.skipped_done.append(fid)
            continue
        plan.to_download.append(PollPlan(fid, lst.key, date, lst.size))
    return plan


def check_scan_intervals(
    timestamps: list[float], interval: float, *, tolerance: float = SCAN_INTERVAL_TOLERANCE_SECONDS
) -> tuple[bool, list[float]]:
    """校验相邻扫描时间戳的间隔是否约等于配置间隔（make test-poll-interval）。

    返回 ``(是否全部在容差内, 各相邻间隔列表)``；样本不足 2 个判 False。
    """
    if len(timestamps) < 2:
        return False, []
    gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    ok = all(abs(g - interval) <= tolerance for g in gaps)
    return ok, gaps


# ── IO 注入点：OssSource（list / head / download，绝不含 delete）────────────
class OssSource(Protocol):
    """Worker 只读 OSS 数据源：列举 / 读元数据 / 下载。

    刻意**不**暴露任何删除方法 —— Worker 业务路径绝不删除 OSS 对象（AGENTS 红线）。
    """

    def list_recordings(self) -> list[OssListing]:
        """列出 ``recordings/`` 前缀下的全部对象。"""
        ...

    def head_metadata(self, object_key: str) -> Mapping[str, str]:
        """HeadObject 读回用户自定义元数据（x-oss-meta-*）。"""
        ...

    def download(self, object_key: str, dest: Path) -> None:
        """把对象下载到 ``dest``（调用方负责 ``.part`` 命名与后续校验）。"""
        ...


# ── 单对象处理 ────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ObjectOutcome:
    """单个对象处理结果。"""

    fragment_id: str
    object_key: str
    status: str  # downloaded / sha256_mismatch / error
    draft: ManifestDraft | None = None
    sha256: str | None = None
    part_path: Path | None = None
    detail: str = ""


def process_plan(
    plan: PollPlan, source: OssSource, *, inbox_root: Path, fragments_root: Path
) -> ObjectOutcome:
    """下载单个对象到 ``.part`` → 计算 sha256 → 读元数据 → 比对 sha256。

    sha256 不一致时删除本地 ``.part``（仅本地中间态文件，非 OSS 删除），返回
    ``sha256_mismatch``，等下一轮重下（AC#4）。下载或读元数据异常收敛为
    ``error``（残留 ``.part`` 由启动恢复扫描 / 下一轮覆盖处理，AC#6）。
    """
    inbox_root.mkdir(parents=True, exist_ok=True)
    part = part_path(inbox_root, plan.fragment_id)
    try:
        source.download(plan.object_key, part)
        actual_sha = sha256_of(part)
        raw_meta = source.head_metadata(plan.object_key)
    except Exception as exc:  # noqa: BLE001 - 单对象失败不影响整轮，收敛为单项 error
        return ObjectOutcome(
            fragment_id=plan.fragment_id,
            object_key=plan.object_key,
            status="error",
            part_path=part if part.exists() else None,
            detail=f"{type(exc).__name__}: {exc}",
        )
    draft = metadata_to_draft(plan.fragment_id, raw_meta)
    if draft.original_sha256 and actual_sha != draft.original_sha256:
        part.unlink(missing_ok=True)  # 删本地 .part（非 OSS），下一轮重下
        return ObjectOutcome(
            fragment_id=plan.fragment_id,
            object_key=plan.object_key,
            status="sha256_mismatch",
            draft=draft,
            sha256=actual_sha,
            detail=(
                f"sha256 不一致：本地={actual_sha[:12]}… "
                f"元数据={(draft.original_sha256 or '')[:12]}…，已删除 .part 等待重下"
            ),
        )
    return ObjectOutcome(
        fragment_id=plan.fragment_id,
        object_key=plan.object_key,
        status="downloaded",
        draft=draft,
        sha256=actual_sha,
        part_path=part,
    )


# ── 启动 / 轮询前恢复：清理 inbox 残留 .part ───────────────────────────────
def cleanup_parts(inbox_root: Path) -> list[str]:
    """删除 inbox 下残留的 ``*.part``（崩溃残留），返回被清理的文件名（AC#6）。

    清理的是**本地** inbox 中间态文件；下一轮轮询会重新下载，不污染 fragments/。
    """
    if not inbox_root.exists():
        return []
    removed: list[str] = []
    for p in sorted(inbox_root.glob("*.part")):
        try:
            p.unlink()
            removed.append(p.name)
        except OSError:  # pragma: no cover - 并发删除等罕见情况
            continue
    return removed


# ── 一轮扫描 + 轮询循环 ────────────────────────────────────────────────────
@dataclass(frozen=True)
class ScanResult:
    """一轮扫描结果。"""

    plan: ScanPlan
    outcomes: list[ObjectOutcome] = field(default_factory=list)


def poll_once(
    source: OssSource,
    *,
    inbox_root: Path,
    fragments_root: Path,
    log: Callable[[str], None],
) -> ScanResult:
    """执行一轮：列举 → 计划 → 逐个下载校验。已 .done 的跳过（AC#1/#2）。"""
    listings = source.list_recordings()
    plan = plan_downloads(
        listings,
        done_check=lambda fid, date: done_marker_path(fragments_root, date, fid).exists(),
    )
    log(
        f"[poll] 扫描 OSS {RECORDINGS_PREFIX} 共 {len(listings)} 个对象："
        f"待下载 {len(plan.to_download)}，跳过(.done) {len(plan.skipped_done)}，"
        f"忽略 {len(plan.ignored_keys)}"
    )
    outcomes: list[ObjectOutcome] = []
    for item in plan.to_download:
        outcome = process_plan(
            item, source, inbox_root=inbox_root, fragments_root=fragments_root
        )
        if outcome.status == "downloaded":
            log(f"[poll] 下载完成并校验 sha256：{outcome.fragment_id}")
        elif outcome.status == "sha256_mismatch":
            log(f"[poll] {outcome.fragment_id} {outcome.detail}")
        else:
            log(f"[poll] {outcome.fragment_id} 处理失败：{outcome.detail}")
        outcomes.append(outcome)
    return ScanResult(plan=plan, outcomes=outcomes)


def poll_loop(
    source: OssSource,
    interval_seconds: float,
    *,
    inbox_root: Path,
    fragments_root: Path,
    log: Callable[[str], None],
    max_iterations: int | None = None,
    stop: Callable[[], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    on_scan: Callable[[float], None] | None = None,
) -> int:
    """周期轮询循环；返回实际执行的扫描轮数。

    启动先清理 inbox 残留 ``.part``（AC#6），随后每隔 ``interval_seconds`` 扫描一次。
    ``max_iterations`` / ``stop`` 用于测试与 make test-poll-interval；
    ``sleep`` / ``monotonic`` / ``on_scan`` 可注入以便确定性单测与时间戳采集。
    """
    removed = cleanup_parts(inbox_root)
    if removed:
        log(f"[poll] 启动清理 inbox 残留 .part：{', '.join(removed)}")
    iterations = 0
    while True:
        if on_scan is not None:
            on_scan(monotonic())
        try:
            poll_once(source, inbox_root=inbox_root, fragments_root=fragments_root, log=log)
        except Exception as exc:  # noqa: BLE001 - 单轮扫描失败（如 list 不可达）不杀死守护进程
            log(f"[poll] 本轮扫描失败（下一轮重试）：{type(exc).__name__}: {exc}")
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        if stop is not None and stop():
            break
        sleep(interval_seconds)
    return iterations


# ── 真实 OSS 数据源（lazy import SDK；用 config.yaml 的 OSS 只读 AK）─────────
class RealOssSource:
    """真实只读 OSS 数据源；用 config.yaml 的 OSS AK 建客户端，调用才触网。

    构造时加载 config（缺失 / 非法 config 抛 ``ConfigError``）。绝不实现删除方法。
    """

    def __init__(self, cfg: SoniScopeConfig | None = None) -> None:
        resolved = cfg if cfg is not None else load_config(config_path())
        self._bucket = resolved.oss.bucket
        self._endpoint = resolved.oss.endpoint
        self._ak_id = resolved.oss.access_key_id
        self._ak_secret = resolved.oss.access_key_secret.get_secret_value()
        self._oss: Any | None = None

    def _client(self) -> tuple[Any, Any]:
        from soniscope_worker.verify_prep import _import_oss, _oss_client

        if self._oss is None:
            self._oss = _import_oss()
        client = _oss_client(self._oss, self._endpoint, self._ak_id, self._ak_secret)
        return self._oss, client

    def list_recordings(self) -> list[OssListing]:
        oss, client = self._client()
        listings: list[OssListing] = []
        token: str | None = None
        while True:
            req = oss.ListObjectsV2Request(
                bucket=self._bucket,
                prefix=RECORDINGS_PREFIX,
                continuation_token=token,
            )
            result = client.list_objects_v2(req)
            for obj in getattr(result, "contents", None) or []:
                key = str(getattr(obj, "key", "") or "")
                if not key:
                    continue
                listings.append(OssListing(key=key, size=int(getattr(obj, "size", 0) or 0)))
            if not getattr(result, "is_truncated", False):
                break
            token = getattr(result, "next_continuation_token", None)
            if not token:
                break
        return listings

    def head_metadata(self, object_key: str) -> Mapping[str, str]:
        oss, client = self._client()
        result = client.head_object(oss.HeadObjectRequest(bucket=self._bucket, key=object_key))
        raw_meta = getattr(result, "metadata", None) or {}
        return {str(k): str(v) for k, v in dict(raw_meta).items()}

    def download(self, object_key: str, dest: Path) -> None:
        oss, client = self._client()
        dest.parent.mkdir(parents=True, exist_ok=True)
        client.get_object_to_file(
            oss.GetObjectRequest(bucket=self._bucket, key=object_key), str(dest)
        )


# ── make worker-run：真实主轮询入口 ────────────────────────────────────────
def run_worker_run(log: Callable[[str], None] = print) -> None:
    """启动真实 Worker 主轮询（make worker-run / python -m soniscope_worker run）。

    读取 config.yaml 的 ``poll.interval_seconds`` 无限轮询；config 缺失时打印诊断并返回。
    """
    try:
        cfg = load_config(config_path())
    except ConfigError as exc:
        log(f"[poll] 无法启动主轮询：{exc}")
        return
    interval = cfg.poll.interval_seconds
    log(f"[poll] Worker 主轮询启动，间隔 {interval}s，bucket={cfg.oss.bucket}")
    source = RealOssSource(cfg)
    poll_loop(
        source,
        interval,
        inbox_root=inbox_dir(),
        fragments_root=fragments_dir(),
        log=log,
    )


# ── make test-poll-interval：验证扫描间隔 ──────────────────────────────────
@dataclass(frozen=True)
class PollIntervalOptions:
    """test-poll-interval 选项。"""

    expected_interval: int | None = None  # 设了就断言 config 的 interval 等于它（AC#8）
    iterations: int = 3


def run_test_poll_interval(
    opts: PollIntervalOptions,
    *,
    source: OssSource | None = None,
    cfg: SoniScopeConfig | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[list[str], int]:
    """运行若干轮真实轮询并校验相邻扫描间隔约等于配置值（返回输出行, 退出码）。

    缺 config / 缺 OSS SDK 时优雅 SKIP（exit 0），便于本地无凭证 CI；
    有 config 时即便 OSS 不可达，每轮扫描会记错误但循环节奏仍可校验。
    """
    lines: list[str] = []
    try:
        resolved = cfg if cfg is not None else load_config(config_path())
    except ConfigError as exc:
        lines.append(f"SKIP — 未配置 config.yaml：{exc}")
        return lines, 0
    interval = resolved.poll.interval_seconds
    lines.append(f"poll.interval_seconds = {interval}")
    if opts.expected_interval is not None and interval != opts.expected_interval:
        lines.append(
            f"FAIL — 期望 poll.interval_seconds={opts.expected_interval}，"
            f"实际 {interval}（请改 config.yaml 后重试）"
        )
        return lines, 1

    used = source
    if used is None:
        try:
            used = RealOssSource(resolved)
        except ConfigError as exc:  # pragma: no cover - 已在上方加载过
            lines.append(f"SKIP — {exc}")
            return lines, 0

    timestamps: list[float] = []
    iters = poll_loop(
        used,
        interval,
        inbox_root=inbox_dir(),
        fragments_root=fragments_dir(),
        log=lines.append,
        max_iterations=max(2, opts.iterations),
        sleep=sleep,
        monotonic=monotonic,
        on_scan=timestamps.append,
    )
    ok, gaps = check_scan_intervals(timestamps, float(interval))
    gap_text = ", ".join(f"{g:.1f}s" for g in gaps)
    lines.append(f"完成 {iters} 轮扫描，相邻间隔：[{gap_text}]")
    if ok:
        lines.append(f"✅ 扫描间隔符合配置（每 ~{interval}s 一次）")
        return lines, 0
    lines.append(f"FAIL — 扫描间隔偏离配置 {interval}s（容差 {SCAN_INTERVAL_TOLERANCE_SECONDS}s）")
    return lines, 1
