"""响应时延统计工具（US-009，tech-spec §4.2 / PRD §9 P-03）。

verify-upload 等云端联调脚本需要在输出中展示每次调用耗时与 P95，并按阈值（默认 1 秒）
判定 pass/fail。把分位数计算与报告渲染抽成纯函数，便于单测，并供 US-010 的
``make test-verify-upload`` 等 live 脚本复用。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# tech-spec §4.2 / PRD §9 P-03：verify-upload P95 目标阈值（秒）。
P95_THRESHOLD_SECONDS = 1.0


def percentile(samples: Sequence[float], pct: float) -> float:
    """返回 ``samples`` 的第 ``pct`` 百分位（0–100，线性插值）；空序列返回 0.0。

    采用 NIST 线性插值法（与 numpy 默认 ``linear`` 一致），便于与基线对齐。
    """
    if not samples:
        return 0.0
    if pct <= 0:
        return float(min(samples))
    if pct >= 100:
        return float(max(samples))
    ordered = sorted(samples)
    rank = (pct / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * frac)


@dataclass(frozen=True)
class LatencyStats:
    """一组调用耗时（秒）的统计摘要。"""

    count: int
    p50_seconds: float
    p95_seconds: float
    max_seconds: float
    mean_seconds: float


def summarize(samples: Sequence[float]) -> LatencyStats:
    """把耗时样本（秒）汇总为 ``LatencyStats``（空样本全 0）。"""
    if not samples:
        return LatencyStats(0, 0.0, 0.0, 0.0, 0.0)
    return LatencyStats(
        count=len(samples),
        p50_seconds=percentile(samples, 50),
        p95_seconds=percentile(samples, 95),
        max_seconds=max(samples),
        mean_seconds=sum(samples) / len(samples),
    )


def format_latency_report(
    label: str,
    samples: Sequence[float],
    *,
    threshold_seconds: float = P95_THRESHOLD_SECONDS,
) -> tuple[str, bool]:
    """渲染 P95 时延报告行并返回 (报告文本, 是否达标)。

    无样本视为不达标（无法证明性能）。P95 <= 阈值标记 PASS，否则 FAIL。
    """
    stats = summarize(samples)
    passed = stats.count > 0 and stats.p95_seconds <= threshold_seconds
    mark = "PASS" if passed else "FAIL"
    line = (
        f"[{mark}] {label}: n={stats.count} "
        f"p50={stats.p50_seconds * 1000:.1f}ms "
        f"p95={stats.p95_seconds * 1000:.1f}ms "
        f"max={stats.max_seconds * 1000:.1f}ms "
        f"(P95 阈值 {threshold_seconds * 1000:.0f}ms)"
    )
    return line, passed
