"""US-009 响应时延统计单测：percentile / summarize / P95 报告与阈值判定。"""

from __future__ import annotations

import pytest

from soniscope_worker import latency


def test_percentile_empty_is_zero() -> None:
    assert latency.percentile([], 95) == 0.0


def test_percentile_bounds() -> None:
    samples = [0.1, 0.2, 0.3, 0.4]
    assert latency.percentile(samples, 0) == pytest.approx(0.1)
    assert latency.percentile(samples, 100) == pytest.approx(0.4)


def test_percentile_linear_interpolation() -> None:
    # 10 个均匀样本 0.1..1.0；P95 线性插值落在 0.955。
    samples = [i / 10 for i in range(1, 11)]
    assert latency.percentile(samples, 95) == pytest.approx(0.955)
    assert latency.percentile(samples, 50) == pytest.approx(0.55)


def test_summarize_empty() -> None:
    stats = latency.summarize([])
    assert stats.count == 0
    assert stats.p95_seconds == 0.0


def test_summarize_basic() -> None:
    stats = latency.summarize([0.2, 0.4, 0.6])
    assert stats.count == 3
    assert stats.max_seconds == pytest.approx(0.6)
    assert stats.mean_seconds == pytest.approx(0.4)


def test_report_pass_under_threshold() -> None:
    line, passed = latency.format_latency_report("verify-upload", [0.2, 0.3, 0.5])
    assert passed is True
    assert "[PASS]" in line
    assert "p95=" in line


def test_report_fail_over_threshold() -> None:
    line, passed = latency.format_latency_report("verify-upload", [0.5, 1.5, 2.0])
    assert passed is False
    assert "[FAIL]" in line


def test_report_empty_samples_fail() -> None:
    line, passed = latency.format_latency_report("verify-upload", [])
    assert passed is False
    assert "n=0" in line


def test_report_custom_threshold() -> None:
    line, passed = latency.format_latency_report(
        "verify-upload", [0.05, 0.08], threshold_seconds=0.1
    )
    assert passed is True
    assert "阈值 100ms" in line
