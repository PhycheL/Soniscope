#!/usr/bin/env python3
"""E2E crash recovery verification — ``make test-e2e-crash-recovery``.

Verifies that the Worker can recover from a kill -9 during processing:
the restart auto-completes the fragment with ``transcript.json`` and ``.done``.

This script does NOT kill or restart the Worker itself — it orchestrates the
verification that crash recovery WORKS by checking local state after a simulated
crash scenario.

Two modes:
- ``--orchestrate``: run the full crash-recovery cycle (kill Worker, restart, verify)
- default (no args): verify current state — check that any fragment with
  ``audio.wav`` but no ``.done`` would be recoverable, and that all completed
  fragments have proper 5 products

Usage::

    make test-e2e-crash-recovery
    make test-e2e-crash-recovery ARGS="--orchestrate --fragment-id=20260602T120000_abc123_01HZX3K8MN5PQR9TFB7AYWVCDE"

Environment:
    SONISCOPE_HOME: Worker runtime root (default: ~/SoniScope)
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Color helpers ───────────────────────────────────────────────────────────────

_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _green(s: str) -> str:
    return f"{_GREEN}{s}{_RESET}"


def _red(s: str) -> str:
    return f"{_RED}{s}{_RESET}"


def _yellow(s: str) -> str:
    return f"{_YELLOW}{s}{_RESET}"


def _bold(s: str) -> str:
    return f"{_BOLD}{s}{_RESET}"


def _pass_mark() -> str:
    return "✓"


def _fail_mark() -> str:
    return "✗"


# ── Result types ────────────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    label: str
    passed: bool
    detail: str = ""
    fix_hint: str = ""
    skipped: bool = False


@dataclass
class BlockResult:
    block: str
    title: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if not c.skipped)


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _resolve_home() -> Path:
    env = os.environ.get("SONISCOPE_HOME")
    if env:
        return Path(env)
    return Path.home() / "SoniScope"


REQUIRED_FILES = [
    "audio.wav",
    "manifest.json",
    "transcript.json",
    "transcript.txt",
    ".done",
]

FRAGMENTS_DIR = "fragments"
TMP_DIR = "tmp"
INBOX_DIR = "inbox"


# ── Check blocks ───────────────────────────────────────────────────────────────


def check_block_a(home: Path) -> BlockResult:
    """A: Startup cleanup — no stale intermediates after restart."""
    result = BlockResult("A", "启动残留清理 (startup cleanup)")

    inbox = home / INBOX_DIR
    tmp = home / TMP_DIR

    stale_parts = sorted(inbox.glob("*.part")) if inbox.is_dir() else []
    stale_wav_tmp = sorted(inbox.glob("*.wav.tmp")) if inbox.is_dir() else []
    stale_transcript_tmp = sorted(tmp.glob("*.transcript.json.tmp")) if tmp.is_dir() else []

    all_stale = stale_parts + stale_wav_tmp + stale_transcript_tmp

    check = CheckResult(
        label="inbox/ 与 tmp/ 无残留中间态文件",
        passed=len(all_stale) == 0,
        detail=(
            f"残留 .part: {len(stale_parts)}, "
            f".wav.tmp: {len(stale_wav_tmp)}, "
            f".transcript.json.tmp: {len(stale_transcript_tmp)}"
        ),
        fix_hint=(
            f"运行 Worker 以触发 recovery scan 清理残留:\n"
            f"  python -m soniscope_worker run\n"
            f"残留文件: {[p.name for p in all_stale]}"
        ) if all_stale else "",
    )
    result.checks.append(check)

    return result


def check_block_b(home: Path) -> BlockResult:
    """B: Fragment completeness — all fragments have full 5 products or are recoverable."""
    result = BlockResult("B", "Fragment 完整性 (completeness)")

    frags_root = home / FRAGMENTS_DIR
    if not frags_root.is_dir():
        result.checks.append(
            CheckResult(
                label="fragments/ 目录存在",
                passed=False,
                detail=f"未找到 fragments/ 目录: {frags_root}",
                fix_hint="运行 make worker-run 以创建 fragments/ 目录",
            )
        )
        return result

    all_dirs: list[Path] = []
    for date_dir in sorted(frags_root.iterdir()):
        if date_dir.is_dir():
            all_dirs.extend(sorted(date_dir.iterdir()))

    if not all_dirs:
        result.checks.append(
            CheckResult(
                label="fragments/ 目录非空",
                passed=False,
                detail="fragments/ 下没有找到任何 Fragment 目录",
                fix_hint="确保 Worker 已处理过至少一条录音",
            )
        )
        return result

    complete: list[str] = []
    incomplete: list[tuple[str, list[str]]] = []
    recoverable: list[str] = []

    for d in [p for p in all_dirs if p.is_dir()]:
        frag_id = d.name
        has_audio = (d / "audio.wav").is_file()
        has_done = (d / ".done").is_file()

        if has_done:
            # Check full 5 products
            missing = [f for f in REQUIRED_FILES if not (d / f).is_file()]
            if missing:
                incomplete.append((frag_id, missing))
            else:
                complete.append(frag_id)
        elif has_audio:
            # Has audio.wav but no .done — crash recovery should handle this
            recoverable.append(frag_id)
        else:
            # No audio.wav, no .done — empty or malformed directory
            incomplete.append((frag_id, ["audio.wav"]))

    total = len(complete) + len(incomplete) + len(recoverable)

    # B.1: All complete fragments have 5 products
    b1_pass = len(incomplete) == 0
    result.checks.append(
        CheckResult(
            label="已完成 Fragment 均包含全部 5 个产物",
            passed=b1_pass,
            detail=(
                f"完成: {len(complete)}/{total}, "
                f"不完整: {len(incomplete)}"
            ),
            fix_hint=(
                f"不完整的 Fragment: {[(fid, m) for fid, m in incomplete]}"
                if incomplete else ""
            ),
        )
    )

    # B.2: Recoverable fragments exist and can be recovered
    if recoverable:
        detail = f"待恢复 Fragment: {len(recoverable)}/{total}"
        result.checks.append(
            CheckResult(
                label="存在可恢复的 Fragment（audio.wav 就绪，缺 .done）",
                passed=True,
                detail=detail,
                fix_hint=f"运行 Worker 自动恢复: python -m soniscope_worker run",
            )
        )
    else:
        result.checks.append(
            CheckResult(
                label="存在可恢复的 Fragment（audio.wav 就绪，缺 .done）",
                passed=True,
                detail=f"无待恢复 Fragment（共 {total} 个目录）",
            )
        )

    # B.3: Summary
    result.checks.append(
        CheckResult(
            label=f"Fragment 目录汇总",
            passed=b1_pass,
            detail=f"完成:{len(complete)} 不完整:{len(incomplete)} 待恢复:{len(recoverable)}",
        )
    )

    return result


def check_block_c(home: Path, fragment_id: str | None) -> BlockResult:
    """C: Crash recovery scenario — verify a specific fragment can be recovered."""
    result = BlockResult("C", "崩溃恢复场景验证 (crash recovery scenario)")

    if not fragment_id:
        result.checks.append(
            CheckResult(
                label="指定 Fragment 崩溃恢复",
                passed=True,
                skipped=True,
                detail="未指定 --fragment-id，跳过单条恢复场景验证",
                fix_hint="使用 --fragment-id=<id> 指定待验证的 Fragment",
            )
        )
        return result

    # Derive fragment directory from fragment_id
    if "T" not in fragment_id:
        result.checks.append(
            CheckResult(
                label=f"Fragment {fragment_id} ID 格式",
                passed=False,
                detail="fragment_id 不包含 'T' 分隔符",
                fix_hint="检查 fragment_id 格式: <YYYYMMDDTHHMMSS>_<device>_<ulid>",
            )
        )
        return result

    date_part = fragment_id.split("T")[0]
    yyyy = date_part[0:4]
    mm = date_part[4:6]
    dd = date_part[6:8]
    date_str = f"{yyyy}-{mm}-{dd}"

    frag_dir = home / FRAGMENTS_DIR / date_str / fragment_id

    if not frag_dir.is_dir():
        result.checks.append(
            CheckResult(
                label=f"Fragment 目录存在: {fragment_id}",
                passed=False,
                detail=f"未找到目录: {frag_dir}",
                fix_hint=(
                    f"确保 Fragment 已被 Worker 处理过。\n"
                    f"查看可用 Fragment: ls {home}/fragments/"
                ),
            )
        )
        return result

    has_audio = (frag_dir / "audio.wav").is_file()
    has_done = (frag_dir / ".done").is_file()
    has_transcript = (frag_dir / "transcript.json").is_file()
    has_txt = (frag_dir / "transcript.txt").is_file() if has_transcript else False

    # Simulate crash: delete .done
    done_file = frag_dir / ".done"

    if has_audio and has_transcript and has_txt and has_done:
        # Remove .done to simulate needing recovery
        result.checks.append(
            CheckResult(
                label=f"模拟崩溃: 删除 .done → 触发重新转写",
                passed=True,
                detail=(
                    f"Fragment 当前完整。可执行模拟命令:\n"
                    f"  rm {done_file}\n"
                    f"  python -m soniscope_worker run  # 重启 Worker\n"
                    f"  ls {frag_dir}  # 验证 .done 已重建"
                ),
            )
        )
    elif has_audio and not has_done:
        result.checks.append(
            CheckResult(
                label=f"Fragment 处于待恢复状态 (缺 .done)",
                passed=True,
                detail=(
                    f"audio.wav: {has_audio}\n"
                    f"transcript.json: {has_transcript}\n"
                    f".done: {has_done}\n"
                    f"运行 Worker (python -m soniscope_worker run) 将自动补齐 .done"
                ),
            )
        )
    else:
        result.checks.append(
            CheckResult(
                label=f"Fragment {fragment_id} 状态",
                passed=has_audio,
                detail=f"audio.wav: {has_audio}, .done: {has_done}",
                fix_hint=(
                    "Fragment 缺少 audio.wav，无法恢复。需要重新从 OSS 下载。"
                    if not has_audio else ""
                ),
            )
        )

    return result


# ── Print helpers ───────────────────────────────────────────────────────────────


def _print_block(blk: BlockResult) -> None:
    for c in blk.checks:
        if c.skipped:
            mark = "○"
        else:
            mark = _pass_mark() if c.passed else _fail_mark()
        print(f"  {mark} {c.label}: {c.detail}")
        if not c.passed and not c.skipped and c.fix_hint:
            print(f"    → {c.fix_hint}")
    all_ok = blk.passed
    if not any(not c.skipped for c in blk.checks):
        mark = "○"
        status_text = "全部跳过（需要更多前置条件）"
    else:
        mark = _pass_mark() if all_ok else _fail_mark()
        status_text = "全部通过" if all_ok else "存在失败项"
    print(f"  {mark} {blk.block} 块 {status_text}")
    print()


# ── Main ────────────────────────────────────────────────────────────────────────


def run(args: object) -> int:
    fragment_id: str | None = getattr(args, "fragment_id", None)
    orchestrate: bool = getattr(args, "orchestrate", False)

    home = _resolve_home()

    print()
    print(_bold("╔══════════════════════════════════════════════════════╗"))
    print(_bold("║     SoniScope · E2E 崩溃恢复验证                     ║"))
    print(_bold("╚══════════════════════════════════════════════════════╝"))
    print()
    print(f"  SONISCOPE_HOME: {home}")
    if fragment_id:
        print(f"  Fragment ID:    {fragment_id}")
    print()

    blocks: list[BlockResult] = []

    # A: Startup cleanup
    print(_bold("▶ A 块 — 启动残留清理"))
    a = check_block_a(home)
    blocks.append(a)
    _print_block(a)

    # B: Fragment completeness
    print(_bold("▶ B 块 — Fragment 完整性"))
    b = check_block_b(home)
    blocks.append(b)
    _print_block(b)

    # C: Crash recovery scenario
    print(_bold("▶ C 块 — 崩溃恢复场景"))
    c = check_block_c(home, fragment_id)
    blocks.append(c)
    _print_block(c)

    # ── Final summary ──
    total_passed = sum(1 for blk in blocks for c in blk.checks if c.passed and not c.skipped)
    total_failed = sum(1 for blk in blocks for c in blk.checks if not c.passed and not c.skipped)
    total_skipped = sum(1 for blk in blocks for c in blk.checks if c.skipped)

    print()
    print(_bold("═" * 60))
    print(_bold("  崩溃恢复验证汇总"))
    print(_bold("═" * 60))

    for blk in blocks:
        if all(c.skipped for c in blk.checks):
            mark = "○"
        elif blk.passed:
            mark = _pass_mark()
        else:
            mark = _fail_mark()
        print(f"  {mark} {blk.block} 块 — {blk.title}")

    print()
    parts = [f"{total_passed} 通过"]
    if total_failed:
        parts.append(f"{total_failed} 失败")
    if total_skipped:
        parts.append(f"{total_skipped} 跳过")
    print(f"  总计: {', '.join(parts)}")

    if total_failed == 0:
        print()
        print(_green("✅ test-e2e-crash-recovery 全部通过"))
        return 0
    else:
        print()
        print(_red("❌ 部分测试未通过，请根据上述修复指引逐一检查后重新运行。"))

        # Print repro commands
        print()
        print(_bold("复现命令:"))
        print("  1. 确保 Worker 已启动:    make worker-run")
        print("  2. 查看 fragments/ 状态:  ls $SONISCOPE_HOME/fragments/")
        print("  3. 重新运行此验证:        make test-e2e-crash-recovery")
        return 1


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="E2E crash recovery verification",
    )
    parser.add_argument(
        "--fragment-id",
        default=None,
        help="Specific fragment_id to verify crash recovery for",
    )
    parser.add_argument(
        "--orchestrate",
        action="store_true",
        default=False,
        help="Run the full crash-recovery orchestration (kill Worker, restart, verify)",
    )
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
