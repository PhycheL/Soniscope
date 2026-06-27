"""US-029：OSS 与 E2E 运维辅助 make 命令的收口实现。

本模块只负责本 story 首次交付的三个命令；``show-oss-object``（US-017 首交付）与
``oss-delete-obj``（US-010 首交付）已在 :mod:`soniscope_worker.oss_admin` 实现，CLI
直接复用，**不在此重复实现**。

- ``list-oss-objects DATE=<YYYY-MM-DD>``：列出当天 ``recordings/<date>/`` 下 ``.wav``
  对象并输出总数（复用 :class:`poller.OssSource` 的 ``list_recordings``）。
- ``verify-no-stale``：检查 ``inbox/`` 顶层无 ``*.part`` / ``*.wav.tmp`` 残留、``tmp/``
  下无 ``*.transcript.json.tmp`` 残留（``inbox/failed/`` 是有意留档，不计入）。
- ``verify-oss-retention``：对比 OSS 对象数与本地 fragments 目录数（OSS ≥ 本地），并
  扫描 Worker 日志 + Worker 业务源码确认无 ``DeleteObject`` 调用记录（红线 R-07）。

沿用既有「纯逻辑（无 IO，可直接单测）+ IO 用 ``OssSource`` Protocol 注入」分层：
单测注入 Fake source / 临时目录不触网，真实运行用 ``RealOssSource``（lazy import OSS SDK）。

**安全红线**：所有输出绝不打印 AK Secret 明文，失败时只输出 object key / 路径 / 配置项名。
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

from soniscope_worker.config import ConfigError
from soniscope_worker.paths import fragments_dir, inbox_dir, soniscope_home, tmp_dir
from soniscope_worker.poller import (
    OssListing,
    OssSource,
    RealOssSource,
    fragment_id_from_key,
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WAV_SUFFIX = ".wav"

# 日志扫描：宽松匹配人类可读的删除记录（DeleteObject / delete_object 任意提及）。
_LOG_DELETE_TOKENS = ("DeleteObject", "delete_object")

# 源码扫描：只匹配**真实调用形态**（方法调用 / 请求类型 / 批量删除），避免把 docstring
# 里「绝不调用 DeleteObject」这类说明性提及误判为违规。
_SOURCE_DELETE_PATTERNS = (
    ".delete_object(",
    "DeleteObjectRequest",
    ".delete_objects(",
    "DeleteObjectsRequest",
    "DeleteMultipleObjectsRequest",
)

# 允许出现删除调用的「仅测试用」模块（与 progress.txt 记录的口径一致）+ 本运维模块自身。
_DELETE_ALLOWED_MODULES = frozenset(
    {"oss_admin.py", "verify_upload_live.py", "fc_live.py", "ops.py"}
)


class OpsError(Exception):
    """运维命令的输入 / 配置错误（非法日期等）。"""


# ── list-oss-objects ───────────────────────────────────────────────────────
def validate_date(date: str) -> str:
    """校验 ``YYYY-MM-DD`` 日期字符串合法，返回原值；非法抛 :class:`OpsError`。"""
    if not _DATE_RE.match(date):
        raise OpsError(f"非法 DATE 格式（应为 YYYY-MM-DD）：{date!r}")
    try:
        datetime.date.fromisoformat(date)
    except ValueError as exc:
        raise OpsError(f"非法日期：{date!r}") from exc
    return date


def date_listing_prefix(date: str) -> str:
    """当天 OSS 列举前缀 ``recordings/<date>/``。"""
    return f"recordings/{date}/"


def wav_objects_for_date(listings: list[OssListing], date: str) -> list[OssListing]:
    """从全量 listing 过滤出当天 ``recordings/<date>/`` 下的 ``.wav`` 对象（按 key 排序）。"""
    prefix = date_listing_prefix(date)
    matched = [
        lst
        for lst in listings
        if lst.key.startswith(prefix) and lst.key.endswith(_WAV_SUFFIX)
    ]
    return sorted(matched, key=lambda lst: lst.key)


def format_list_objects(date: str, objects: list[OssListing]) -> list[str]:
    """渲染 list-oss-objects 输出。"""
    lines = [f"recordings/{date}/ 下 .wav 对象："]
    for obj in objects:
        lines.append(f"  {obj.key}  ({obj.size} bytes)")
    if not objects:
        lines.append("  （无）")
    lines.append(f"总数：{len(objects)}")
    return lines


def run_list_oss_objects(
    date: str, *, source: OssSource | None = None
) -> tuple[list[str], int]:
    """列出指定日期 OSS ``recordings/<date>/`` 下 ``.wav`` 对象 + 计数。返回（输出行, 退出码）。

    非法日期 / OSS 不可达 / 缺依赖 → exit 1（只输出错误，绝不打印 AK Secret）。
    """
    try:
        valid = validate_date(date)
    except OpsError as exc:
        return [f"FAIL — {exc}"], 1
    used = source
    if used is None:
        try:
            used = RealOssSource()
        except ConfigError as exc:
            return [f"FAIL — 加载 config.yaml 失败：{exc}"], 1
    try:
        listings = used.list_recordings()
    except Exception as exc:  # noqa: BLE001 - 收敛为单项 fail，不泄漏明文
        return [f"FAIL — 列举 OSS recordings/{valid}/ 失败：{type(exc).__name__}"], 1
    return format_list_objects(valid, wav_objects_for_date(listings, valid)), 0


# ── verify-no-stale ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class StaleReport:
    """inbox / tmp 残留中间态文件扫描结果（顶层，不含 inbox/failed/ 留档）。"""

    inbox_parts: list[str] = field(default_factory=list)
    inbox_wav_tmp: list[str] = field(default_factory=list)
    tmp_transcript_tmp: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (self.inbox_parts or self.inbox_wav_tmp or self.tmp_transcript_tmp)


def find_stale(inbox_root: Path, tmp_root: Path) -> StaleReport:
    """扫描 inbox 顶层 ``*.part`` / ``*.wav.tmp`` 与 tmp 下 ``*.transcript.json.tmp``。

    使用 ``glob``（非递归），故 ``inbox/failed/`` 下的留档 ``.part`` 不计入残留。
    """
    parts: list[str] = []
    wav_tmp: list[str] = []
    transcript_tmp: list[str] = []
    if inbox_root.exists():
        parts = sorted(p.name for p in inbox_root.glob("*.part"))
        wav_tmp = sorted(p.name for p in inbox_root.glob("*.wav.tmp"))
    if tmp_root.exists():
        transcript_tmp = sorted(p.name for p in tmp_root.glob("*.transcript.json.tmp"))
    return StaleReport(
        inbox_parts=parts, inbox_wav_tmp=wav_tmp, tmp_transcript_tmp=transcript_tmp
    )


def format_stale_report(report: StaleReport) -> tuple[list[str], int]:
    """渲染 verify-no-stale 输出。无残留 → exit 0；有残留 → exit 1。"""
    if report.clean:
        return [
            "✅ 无残留中间态文件："
            "inbox/*.part、inbox/*.wav.tmp、tmp/*.transcript.json.tmp 均不存在"
        ], 0
    lines = ["FAIL — 发现残留中间态文件（Worker 重启恢复扫描应已清理，请检查）："]
    for name in report.inbox_parts:
        lines.append(f"  inbox/{name}")
    for name in report.inbox_wav_tmp:
        lines.append(f"  inbox/{name}")
    for name in report.tmp_transcript_tmp:
        lines.append(f"  tmp/{name}")
    return lines, 1


def run_verify_no_stale(
    *, inbox_root: Path | None = None, tmp_root: Path | None = None
) -> tuple[list[str], int]:
    """检查 inbox / tmp 无残留中间态文件。返回（输出行, 退出码）。"""
    report = find_stale(
        inbox_root if inbox_root is not None else inbox_dir(),
        tmp_root if tmp_root is not None else tmp_dir(),
    )
    return format_stale_report(report)


# ── verify-oss-retention ───────────────────────────────────────────────────
def count_oss_wav(listings: list[OssListing]) -> int:
    """统计 OSS recordings/ 下合法 ``<date>/<fragment_id>.wav`` 对象数。"""
    return sum(1 for lst in listings if fragment_id_from_key(lst.key) is not None)


def count_local_fragments(fragments_root: Path) -> int:
    """统计本地 ``fragments/<date>/<fragment_id>/`` 目录数。

    计入含 ``.done`` / ``audio.wav`` / ``manifest.json`` 之一的目录（空目录不计）。
    """
    if not fragments_root.exists():
        return 0
    count = 0
    for date_dir in fragments_root.iterdir():
        if not date_dir.is_dir():
            continue
        for frag_dir in date_dir.iterdir():
            if not frag_dir.is_dir():
                continue
            if (
                (frag_dir / ".done").exists()
                or (frag_dir / "audio.wav").exists()
                or (frag_dir / "manifest.json").exists()
            ):
                count += 1
    return count


def _scan_text(text: str, tokens: tuple[str, ...]) -> list[int]:
    """返回 ``text`` 中包含任一 token 的行号（1 起）。"""
    hits: list[int] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if any(tok in line for tok in tokens):
            hits.append(i)
    return hits


def scan_logs_for_delete(log_paths: list[Path]) -> tuple[list[str], list[str]]:
    """扫描日志文件确认无 ``DeleteObject`` 记录。返回（命中行描述, 实际扫描到的文件）。"""
    hits: list[str] = []
    scanned: list[str] = []
    for path in log_paths:
        if not path.is_file():
            continue
        scanned.append(str(path))
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:  # pragma: no cover - 罕见读权限问题
            continue
        for lineno in _scan_text(text, _LOG_DELETE_TOKENS):
            hits.append(f"{path}:{lineno}")
    return hits, scanned


def scan_business_source_for_delete(src_root: Path) -> list[str]:
    """扫描 Worker 业务源码确认无删除调用（排除仅测试用模块与本运维模块自身）。

    返回违规位置 ``<file>:<lineno>`` 列表；空列表表示业务路径无 DeleteObject（红线 R-07）。
    """
    hits: list[str] = []
    for py in sorted(src_root.glob("*.py")):
        if py.name in _DELETE_ALLOWED_MODULES:
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="replace")
        except OSError:  # pragma: no cover
            continue
        for lineno in _scan_text(text, _SOURCE_DELETE_PATTERNS):
            hits.append(f"{py.name}:{lineno}")
    return hits


def default_log_paths() -> list[Path]:
    """发现可能的 Worker 日志：``$SONISCOPE_HOME`` 与其 ``logs/`` 下的 ``*.log``。"""
    home = soniscope_home()
    paths: list[Path] = []
    if home.exists():
        paths.extend(sorted(home.glob("*.log")))
        logs_dir = home / "logs"
        if logs_dir.exists():
            paths.extend(sorted(logs_dir.rglob("*.log")))
    return paths


def _default_src_root() -> Path:
    """Worker 包源码根目录（soniscope_worker/）。"""
    return Path(__file__).resolve().parent


@dataclass(frozen=True)
class RetentionReport:
    """verify-oss-retention 汇总。"""

    local_count: int
    oss_count: int | None  # None 表示 OSS 不可用（缺 config / 不可达），该维度 SKIP
    source_delete_hits: list[str] = field(default_factory=list)
    log_delete_hits: list[str] = field(default_factory=list)
    log_files_scanned: list[str] = field(default_factory=list)
    oss_skip_reason: str = ""

    @property
    def count_ok(self) -> bool:
        # OSS 不可用时不判定数量（SKIP）；可用时要求 OSS ≥ 本地。
        return self.oss_count is None or self.oss_count >= self.local_count

    @property
    def no_delete(self) -> bool:
        return not self.source_delete_hits and not self.log_delete_hits

    @property
    def passed(self) -> bool:
        return self.count_ok and self.no_delete


def format_retention_report(report: RetentionReport) -> tuple[list[str], int]:
    """渲染 verify-oss-retention 输出。"""
    lines = [f"本地 fragments 目录数：{report.local_count}"]
    if report.oss_count is None:
        lines.append(f"OSS 对象数：SKIP（{report.oss_skip_reason}）")
    else:
        symbol = "≥" if report.count_ok else "<"
        lines.append(f"OSS 对象数：{report.oss_count}（OSS {symbol} 本地）")

    if report.source_delete_hits:
        lines.append("FAIL — Worker 业务源码出现 DeleteObject 调用（红线 R-07 违规）：")
        for hit in report.source_delete_hits:
            lines.append(f"  {hit}")
    else:
        lines.append("✅ Worker 业务源码无 DeleteObject 调用")

    if report.log_files_scanned:
        if report.log_delete_hits:
            lines.append("FAIL — Worker 日志出现 DeleteObject 记录：")
            for hit in report.log_delete_hits:
                lines.append(f"  {hit}")
        else:
            scanned_n = len(report.log_files_scanned)
            lines.append(f"✅ Worker 日志无 DeleteObject 记录（已扫描 {scanned_n} 个日志文件）")
    else:
        lines.append("ℹ️  未发现 Worker 日志文件（无 DeleteObject 记录可扫描）")

    if not report.count_ok:
        lines.append(
            f"FAIL — OSS 对象数 {report.oss_count} 少于本地 fragments {report.local_count}"
            "（OSS 应永不删除，至少与本地持平）"
        )

    if report.passed:
        lines.append("✅ OSS 留存校验通过：OSS 永不删除")
    return lines, 0 if report.passed else 1


def run_verify_oss_retention(
    *,
    source: OssSource | None = None,
    fragments_root: Path | None = None,
    src_root: Path | None = None,
    log_paths: list[Path] | None = None,
) -> tuple[list[str], int]:
    """对比 OSS 对象数与本地 fragments 目录数 + 扫描日志/源码确认无 DeleteObject。

    OSS 不可用（缺 config / 不可达）时该维度 SKIP（不致命）；源码红线 / 日志命中致命。
    返回（输出行, 退出码）。
    """
    frag_root = fragments_root if fragments_root is not None else fragments_dir()
    code_root = src_root if src_root is not None else _default_src_root()
    logs = log_paths if log_paths is not None else default_log_paths()

    local_count = count_local_fragments(frag_root)
    source_hits = scan_business_source_for_delete(code_root)
    log_hits, scanned = scan_logs_for_delete(logs)

    oss_count: int | None = None
    skip_reason = ""
    used = source
    if used is None:
        try:
            used = RealOssSource()
        except ConfigError as exc:
            skip_reason = f"加载 config.yaml 失败：{exc}"
    if used is not None:
        try:
            oss_count = count_oss_wav(used.list_recordings())
        except Exception as exc:  # noqa: BLE001 - OSS 不可达不致命，记 SKIP，不泄漏明文
            skip_reason = f"OSS 不可达：{type(exc).__name__}"

    report = RetentionReport(
        local_count=local_count,
        oss_count=oss_count,
        source_delete_hits=source_hits,
        log_delete_hits=log_hits,
        log_files_scanned=scanned,
        oss_skip_reason=skip_reason,
    )
    return format_retention_report(report)
