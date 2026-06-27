"""US-030：E2E 完整性、sha256 与 manifest 关键字段校验脚本。

针对真实 ``$SONISCOPE_HOME/fragments`` 落盘产物做只读验收校验，**不使用 mock、不修改
OSS 或本地产物**，失败时以非零退出便于 Ralph / CI 判断（tech-spec §4.1 / §3.3）：

- ``verify-e2e-integrity DATE=<YYYY-MM-DD> EXPECTED=100``：确认目标日期有 ``EXPECTED`` 个
  Fragment 目录，且每个目录同时包含 ``audio.wav`` / ``manifest.json`` / ``transcript.json``
  / ``transcript.txt`` / ``.done`` 五个产物（AC#1）。
- ``verify-e2e-sha256 [DATE=<YYYY-MM-DD>]``：读每条 manifest 按 §3.3 一致性规则校验——WAV
  直通（``audio.sha256 == upload.original_sha256`` 且 size 相等）与非 WAV 转码（两 sha256
  均真实非空、不允许 null）两种路径（AC#2）。
- ``verify-e2e-fields [DATE=<YYYY-MM-DD>]``：确认每条 ``manifest.upload.verified_at`` 与
  ``manifest.transcription.completed_at`` 非空（AC#3）。

沿用既有「纯逻辑（无 IO，可直接单测）」分层：扫描 / 校验逻辑只对已读入的目录结构与 manifest
dict 做判断，单测在 ``tmp_path`` 下构造**真实** Fragment 目录（非 mock）即可覆盖。所有输出
只含 ``fragment_id`` / 字段路径 / 文件名，绝不打印 AK Secret（manifest 本就不含密钥）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from soniscope_worker.paths import fragments_dir
from soniscope_worker.poller import fragment_id_from_key
from soniscope_worker.recovery import (
    AUDIO_FILENAME,
    DONE_MARKER,
    MANIFEST_FILENAME,
    TRANSCRIPT_JSON_FILENAME,
    TRANSCRIPT_TXT_FILENAME,
)

DEFAULT_EXPECTED_COUNT = 100

# 完整 Fragment 必须同时存在的五个产物（tech-spec §2.2）。
REQUIRED_FILES = (
    AUDIO_FILENAME,
    MANIFEST_FILENAME,
    TRANSCRIPT_JSON_FILENAME,
    TRANSCRIPT_TXT_FILENAME,
    DONE_MARKER,
)

_WAV_FORMAT = "wav"


# ── 公共：发现 Fragment 目录 + 读取 manifest ────────────────────────────────
@dataclass(frozen=True)
class FragmentDir:
    """一条已发现的 Fragment 目录。"""

    date: str
    fragment_id: str
    path: Path


def _fragment_id_valid(name: str) -> bool:
    """校验 fragment_id 自洽（用其自身日期前缀构造 key 往返）。"""
    prefix = name.split("_", 1)[0]  # <YYYYMMDDTHHMMSS>
    if len(prefix) < 8:
        return False
    iso_date = f"{prefix[0:4]}-{prefix[4:6]}-{prefix[6:8]}"
    return fragment_id_from_key(f"recordings/{iso_date}/{name}.wav") == name


def discover_fragments(
    fragments_root: Path, *, date: str | None = None
) -> list[FragmentDir]:
    """扫描 ``fragments/<date>/<fragment_id>/`` 目录（只读）。

    ``date`` 给定时只扫该日期目录，否则扫所有日期。仅纳入目录名为合法 fragment_id 的子目录，
    按 (date, fragment_id) 排序。
    """
    found: list[FragmentDir] = []
    if not fragments_root.exists():
        return found
    date_dirs = (
        [fragments_root / date]
        if date is not None
        else sorted(d for d in fragments_root.iterdir() if d.is_dir())
    )
    for date_dir in date_dirs:
        if not date_dir.is_dir():
            continue
        for frag_dir in sorted(date_dir.iterdir(), key=lambda p: p.name):
            if frag_dir.is_dir() and _fragment_id_valid(frag_dir.name):
                found.append(
                    FragmentDir(
                        date=date_dir.name, fragment_id=frag_dir.name, path=frag_dir
                    )
                )
    return found


def _read_manifest(frag_dir: Path) -> dict[str, Any]:
    """读取并解析 ``manifest.json``；缺失 / 非法 / 非对象抛 :class:`E2eError`。"""
    path = frag_dir / MANIFEST_FILENAME
    if not path.is_file():
        raise E2eError(f"缺少 {MANIFEST_FILENAME}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise E2eError(f"{MANIFEST_FILENAME} 解析失败：{type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise E2eError(f"{MANIFEST_FILENAME} 顶层不是对象")
    return data


def _get_path(manifest: dict[str, Any], *keys: str) -> Any:
    """按嵌套键路径取值；任一层缺失或非 dict 返回 ``None``。"""
    cur: Any = manifest
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _is_empty(value: Any) -> bool:
    """字段是否「空」（None 或去空白后空串）。"""
    return value is None or (isinstance(value, str) and not value.strip())


class E2eError(Exception):
    """单条 Fragment 的 manifest 读取 / 校验输入错误。"""


# ── 通用失败汇总 ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CheckResult:
    """单条 Fragment 的校验结果。``problems`` 空表示通过。"""

    fragment_id: str
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _summarize(
    title: str, results: list[CheckResult], *, header_lines: list[str] | None = None
) -> tuple[list[str], int]:
    """渲染统一 pass/fail 汇总：通过数、失败数、逐条失败 fragment_id + 失败路径。"""
    lines = list(header_lines or [])
    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    for r in failed:
        for problem in r.problems:
            lines.append(f"FAIL — {r.fragment_id}：{problem}")
    lines.append(f"{title}：通过 {len(passed)} 条，失败 {len(failed)} 条，共 {len(results)} 条")
    return lines, 0 if not failed else 1


# ── verify-e2e-integrity（AC#1）─────────────────────────────────────────────
def check_integrity(frag: FragmentDir) -> CheckResult:
    """校验单条 Fragment 目录含五个产物文件。"""
    problems = [
        f"缺少产物 {name}"
        for name in REQUIRED_FILES
        if not (frag.path / name).is_file()
    ]
    return CheckResult(fragment_id=frag.fragment_id, problems=problems)


def run_verify_e2e_integrity(
    *,
    fragments_root: Path | None = None,
    date: str | None = None,
    expected: int = DEFAULT_EXPECTED_COUNT,
) -> tuple[list[str], int]:
    """校验目标日期 Fragment 目录数 == ``expected`` 且每条五产物齐全（AC#1）。

    ``expected <= 0`` 时跳过数量断言（仅报告实际数）。任一不满足以非零退出。
    """
    root = fragments_root if fragments_root is not None else fragments_dir()
    frags = discover_fragments(root, date=date)
    scope = f"日期 {date}" if date is not None else "全部日期"
    header = [f"扫描 {root}（{scope}）：发现 {len(frags)} 个 Fragment 目录"]
    results = [check_integrity(f) for f in frags]
    lines, code = _summarize("完整性校验", results, header_lines=header)
    if expected > 0 and len(frags) != expected:
        lines.append(
            f"FAIL — Fragment 目录数 {len(frags)} 不等于期望 {expected}（{scope}）"
        )
        code = 1
    if code == 0:
        lines.append("✅ E2E 完整性校验通过：每条 Fragment 五产物齐全")
    return lines, code


# ── verify-e2e-sha256（AC#2，§3.3）──────────────────────────────────────────
def check_sha256(manifest: dict[str, Any], fragment_id: str) -> CheckResult:
    """按 §3.3 一致性规则校验单条 manifest 的 sha256 / size。

    - WAV 直通（``audio.original_format == 'wav'``）：``audio.sha256 ==
      upload.original_sha256`` 且 ``audio.size_bytes == upload.original_size_bytes``。
    - 非 WAV 转码：``audio.sha256`` 与 ``upload.original_sha256`` 均真实非空（允许不同）。
    两路径均要求两个 sha256 与两个 size 字段非空（不允许 null）。
    """
    problems: list[str] = []
    original_format = _get_path(manifest, "audio", "original_format")
    audio_sha = _get_path(manifest, "audio", "sha256")
    audio_size = _get_path(manifest, "audio", "size_bytes")
    orig_sha = _get_path(manifest, "upload", "original_sha256")
    orig_size = _get_path(manifest, "upload", "original_size_bytes")

    for path, value in (
        ("audio.sha256", audio_sha),
        ("audio.size_bytes", audio_size),
        ("upload.original_sha256", orig_sha),
        ("upload.original_size_bytes", orig_size),
    ):
        if _is_empty(value):
            problems.append(f"{path} 为空（§3.3 不允许 null）")
    # 字段缺失时不再做一致性比较（已记为空）。
    if problems:
        return CheckResult(fragment_id=fragment_id, problems=problems)

    if original_format == _WAV_FORMAT:
        if audio_sha != orig_sha:
            problems.append(
                "WAV 直通规则违反：audio.sha256 != upload.original_sha256"
            )
        if audio_size != orig_size:
            problems.append(
                "WAV 直通规则违反：audio.size_bytes != upload.original_size_bytes"
            )
    # 非 WAV：两 sha256 已确认非空即可（§3.3「通常不同」，不强制不等）。
    return CheckResult(fragment_id=fragment_id, problems=problems)


def run_verify_e2e_sha256(
    *, fragments_root: Path | None = None, date: str | None = None
) -> tuple[list[str], int]:
    """按 §3.3 校验每条 Fragment 的 WAV 直通 / 非 WAV 转码 sha256 一致性（AC#2）。"""
    root = fragments_root if fragments_root is not None else fragments_dir()
    frags = discover_fragments(root, date=date)
    scope = f"日期 {date}" if date is not None else "全部日期"
    header = [f"扫描 {root}（{scope}）：{len(frags)} 个 Fragment"]
    results: list[CheckResult] = []
    for frag in frags:
        try:
            manifest = _read_manifest(frag.path)
        except E2eError as exc:
            results.append(CheckResult(frag.fragment_id, [str(exc)]))
            continue
        results.append(check_sha256(manifest, frag.fragment_id))
    lines, code = _summarize("sha256 校验", results, header_lines=header)
    if code == 0:
        lines.append("✅ E2E sha256 一致性校验通过（§3.3 WAV 直通 + 非 WAV 转码规则）")
    return lines, code


# ── verify-e2e-fields（AC#3）────────────────────────────────────────────────
# 每条 manifest 必须非空的关键字段（字段路径 → 嵌套键）。
REQUIRED_NONEMPTY_FIELDS = (
    ("upload.verified_at", ("upload", "verified_at")),
    ("transcription.completed_at", ("transcription", "completed_at")),
)


def check_fields(manifest: dict[str, Any], fragment_id: str) -> CheckResult:
    """校验 manifest 关键字段非空（upload.verified_at / transcription.completed_at）。"""
    problems: list[str] = []
    for label, keys in REQUIRED_NONEMPTY_FIELDS:
        if _is_empty(_get_path(manifest, *keys)):
            problems.append(f"{label} 为空")
    return CheckResult(fragment_id=fragment_id, problems=problems)


def run_verify_e2e_fields(
    *, fragments_root: Path | None = None, date: str | None = None
) -> tuple[list[str], int]:
    """确认每条 manifest.upload.verified_at 与 transcription.completed_at 非空（AC#3）。"""
    root = fragments_root if fragments_root is not None else fragments_dir()
    frags = discover_fragments(root, date=date)
    scope = f"日期 {date}" if date is not None else "全部日期"
    header = [f"扫描 {root}（{scope}）：{len(frags)} 个 Fragment"]
    results: list[CheckResult] = []
    for frag in frags:
        try:
            manifest = _read_manifest(frag.path)
        except E2eError as exc:
            results.append(CheckResult(frag.fragment_id, [str(exc)]))
            continue
        results.append(check_fields(manifest, frag.fragment_id))
    lines, code = _summarize("关键字段校验", results, header_lines=header)
    if code == 0:
        lines.append("✅ E2E 关键字段校验通过（verified_at / completed_at 均非空）")
    return lines, code
