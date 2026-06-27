"""US-028 Worker 幂等规则与显式重转 单元测试（stub 转写器，全程不触网/不触云端）。"""

from __future__ import annotations

import json
from pathlib import Path

from soniscope_worker.recovery import DONE_MARKER
from soniscope_worker.retranscribe import (
    REASON_FORCE,
    REASON_UPGRADE_CHANGED,
    REASON_UPGRADE_SAME,
    STATUS_FAILED,
    STATUS_NOT_FOUND,
    STATUS_RETRANSCRIBED,
    STATUS_SKIPPED,
    BatchReport,
    RetranscribeOutcome,
    _make_done_fragment,
    _stub_config,
    _StubTranscriber,
    retranscribe_all_from,
    retranscribe_one,
    run_retranscribe,
    run_test_cli_retranscribe,
    run_test_cli_upgrade,
    run_test_idempotent_skip,
    run_test_no_auto_retranscribe,
    should_retranscribe,
)
from soniscope_worker.transcriber import TranscriptResult

_FID = "20260527T150000_devr01_01HZX3K8MN5PQR9TFB7AYWVCDE"
_OTHER_FID = "20260601T150000_devr09_01HZX3K8MN5PQR9TFB7AYWVCDH"


def _txt(frag: Path) -> str:
    return (frag / "transcript.txt").read_text(encoding="utf-8")


# ── should_retranscribe 决策表 ─────────────────────────────────────────────
def test_should_force_overrides_all() -> None:
    decided, reason = should_retranscribe(
        done_exists=True, manifest_model="m", manifest_params_version="v",
        config_model="m", config_params_version="v", force=True, upgrade=False,
    )
    assert decided is True
    assert reason == REASON_FORCE


def test_should_upgrade_changed() -> None:
    decided, reason = should_retranscribe(
        done_exists=True, manifest_model="m", manifest_params_version="v1",
        config_model="m", config_params_version="v2", force=False, upgrade=True,
    )
    assert decided is True
    assert reason == REASON_UPGRADE_CHANGED


def test_should_upgrade_model_changed() -> None:
    decided, _ = should_retranscribe(
        done_exists=True, manifest_model="m1", manifest_params_version="v",
        config_model="m2", config_params_version="v", force=False, upgrade=True,
    )
    assert decided is True


def test_should_upgrade_same_skips() -> None:
    decided, reason = should_retranscribe(
        done_exists=True, manifest_model="m", manifest_params_version="v",
        config_model="m", config_params_version="v", force=False, upgrade=True,
    )
    assert decided is False
    assert reason == REASON_UPGRADE_SAME


def test_should_no_flag_done_skips() -> None:
    decided, reason = should_retranscribe(
        done_exists=True, manifest_model="m", manifest_params_version="v",
        config_model="m", config_params_version="v", force=False, upgrade=False,
    )
    assert decided is False
    assert "已完成" in reason


def test_should_no_flag_no_done_retranscribes() -> None:
    decided, _ = should_retranscribe(
        done_exists=False, manifest_model="m", manifest_params_version="v",
        config_model="m", config_params_version="v", force=False, upgrade=False,
    )
    assert decided is True


# ── retranscribe_one ───────────────────────────────────────────────────────
def test_retranscribe_one_not_found(tmp_path: Path) -> None:
    out = retranscribe_one(
        _FID, _StubTranscriber(text="x"), config=_stub_config(),
        fragments_root=tmp_path / "fragments", tmp_root=tmp_path / "tmp",
    )
    assert out.status == STATUS_NOT_FOUND


def test_retranscribe_one_illegal_id(tmp_path: Path) -> None:
    out = retranscribe_one(
        "not-a-valid-id", _StubTranscriber(text="x"), config=_stub_config(),
        fragments_root=tmp_path / "fragments", tmp_root=tmp_path / "tmp",
    )
    assert out.status == STATUS_FAILED
    assert "非法" in out.reason


def test_retranscribe_one_missing_manifest(tmp_path: Path) -> None:
    fragments, tmp = tmp_path / "fragments", tmp_path / "tmp"
    frag = _make_done_fragment(
        fragments, tmp, _FID, model="m", params_version="v", transcript_text="orig"
    )
    (frag / "manifest.json").unlink()
    out = retranscribe_one(
        _FID, _StubTranscriber(text="x"), config=_stub_config(),
        fragments_root=fragments, tmp_root=tmp,
    )
    assert out.status == STATUS_FAILED
    assert "manifest" in out.reason


def test_retranscribe_one_no_flag_skips(tmp_path: Path) -> None:
    fragments, tmp = tmp_path / "fragments", tmp_path / "tmp"
    frag = _make_done_fragment(
        fragments, tmp, _FID, model="m", params_version="v", transcript_text="orig"
    )
    out = retranscribe_one(
        _FID, _StubTranscriber(text="新"), config=_stub_config(),
        fragments_root=fragments, tmp_root=tmp,
    )
    assert out.status == STATUS_SKIPPED
    assert _txt(frag) == "orig"  # 未改写


def test_retranscribe_one_force_overwrites(tmp_path: Path) -> None:
    fragments, tmp = tmp_path / "fragments", tmp_path / "tmp"
    frag = _make_done_fragment(
        fragments, tmp, _FID, model="m", params_version="v", transcript_text="orig"
    )
    out = retranscribe_one(
        _FID, _StubTranscriber(text="强制新文本", model="m2", params_version="v9"),
        config=_stub_config(), fragments_root=fragments, tmp_root=tmp, force=True,
    )
    assert out.retranscribed
    assert _txt(frag) == "强制新文本"
    tj = json.loads((frag / "transcript.json").read_text(encoding="utf-8"))
    assert tj["model"] == "m2"
    assert tj["params_version"] == "v9"
    assert "duration" not in tj  # §3.4 不落盘 duration
    manifest = json.loads((frag / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["transcription"]["model"] == "m2"
    assert manifest["transcription"]["params_version"] == "v9"
    assert manifest["transcription"]["completed_at"] is not None
    assert (frag / DONE_MARKER).is_file()
    # 临时文件已清理。
    assert not (tmp / f"{_FID}.transcript.json.tmp").exists()


def test_retranscribe_one_upgrade_same_skips(tmp_path: Path) -> None:
    fragments, tmp = tmp_path / "fragments", tmp_path / "tmp"
    frag = _make_done_fragment(
        fragments, tmp, _FID, model="m", params_version="v2", transcript_text="orig"
    )
    out = retranscribe_one(
        _FID, _StubTranscriber(text="新"),
        config=_stub_config(model="m", params_version="v2"),
        fragments_root=fragments, tmp_root=tmp, upgrade=True,
    )
    assert out.status == STATUS_SKIPPED
    assert _txt(frag) == "orig"


def test_retranscribe_one_upgrade_changed(tmp_path: Path) -> None:
    fragments, tmp = tmp_path / "fragments", tmp_path / "tmp"
    frag = _make_done_fragment(
        fragments, tmp, _FID, model="m", params_version="v1", transcript_text="orig"
    )
    out = retranscribe_one(
        _FID, _StubTranscriber(text="升级新文本", params_version="v2"),
        config=_stub_config(model="m", params_version="v2"),
        fragments_root=fragments, tmp_root=tmp, upgrade=True,
    )
    assert out.retranscribed
    assert _txt(frag) == "升级新文本"


def test_retranscribe_one_transcribe_failure(tmp_path: Path) -> None:
    fragments, tmp = tmp_path / "fragments", tmp_path / "tmp"
    frag = _make_done_fragment(
        fragments, tmp, _FID, model="m", params_version="v", transcript_text="orig"
    )

    class _Boom:
        name = "cloud-speech"

        def transcribe(
            self, fragment_id: str, audio_path: Path, oss_key: str
        ) -> TranscriptResult:
            raise RuntimeError("NLS 不可达")

    out = retranscribe_one(
        _FID, _Boom(), config=_stub_config(), fragments_root=fragments, tmp_root=tmp, force=True,
    )
    assert out.status == STATUS_FAILED
    assert _txt(frag) == "orig"  # 失败不覆盖原产物


# ── retranscribe_all_from ──────────────────────────────────────────────────
def test_all_from_filters_by_date(tmp_path: Path) -> None:
    fragments, tmp = tmp_path / "fragments", tmp_path / "tmp"
    _make_done_fragment(fragments, tmp, _FID, model="m", params_version="v", transcript_text="a")
    _make_done_fragment(
        fragments, tmp, _OTHER_FID, model="m", params_version="v", transcript_text="b"
    )
    # from_date 晚于第一个（05-27）只命中 06-01 那个。
    report = retranscribe_all_from(
        "2026-06-01", _StubTranscriber(text="新"), config=_stub_config(),
        fragments_root=fragments, tmp_root=tmp, force=True,
    )
    assert {o.fragment_id for o in report.outcomes} == {_OTHER_FID}
    assert report.retranscribed == 1


def test_all_from_continues_on_failure(tmp_path: Path) -> None:
    fragments, tmp = tmp_path / "fragments", tmp_path / "tmp"
    good = _make_done_fragment(
        fragments, tmp, _FID, model="m", params_version="v", transcript_text="orig"
    )
    bad = _make_done_fragment(
        fragments, tmp, _OTHER_FID, model="m", params_version="v", transcript_text="orig"
    )
    (bad / "manifest.json").unlink()  # 让该条 failed
    report = retranscribe_all_from(
        "2026-05-27", _StubTranscriber(text="新"), config=_stub_config(),
        fragments_root=fragments, tmp_root=tmp, force=True,
    )
    assert report.retranscribed == 1
    assert report.failed == 1
    assert _txt(good) == "新"  # 好的那条仍被处理
    assert "成功 1" in report.summary()


def test_batch_report_counts() -> None:
    report = BatchReport(
        [
            RetranscribeOutcome("a", STATUS_RETRANSCRIBED),
            RetranscribeOutcome("b", STATUS_SKIPPED),
            RetranscribeOutcome("c", STATUS_FAILED),
            RetranscribeOutcome("d", STATUS_NOT_FOUND),
        ]
    )
    assert report.retranscribed == 1
    assert report.skipped == 1
    assert report.failed == 2


# ── run_retranscribe 入口 ──────────────────────────────────────────────────
def test_run_retranscribe_no_args_errors() -> None:
    lines, code = run_retranscribe(fragment_id=None, all_from=None, upgrade=False, force=False)
    assert code == 1
    assert any("必须提供" in line for line in lines)


def test_run_retranscribe_config_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from soniscope_worker import retranscribe as mod
    from soniscope_worker.config import ConfigError

    def _boom(_path: object) -> object:
        raise ConfigError("config.yaml 不存在")

    monkeypatch.setattr("soniscope_worker.config.load_config", _boom)
    lines, code = run_retranscribe(
        fragment_id=_FID, all_from=None, upgrade=False, force=False
    )
    assert code == 1
    assert any("config.yaml" in line for line in lines)
    assert mod  # 引用以示模块可导入


# ── make test-* 自包含入口 ─────────────────────────────────────────────────
def test_make_idempotent_skip() -> None:
    lines, code = run_test_idempotent_skip()
    assert code == 0, lines
    assert any("✅" in line for line in lines)


def test_make_no_auto_retranscribe() -> None:
    lines, code = run_test_no_auto_retranscribe()
    assert code == 0, lines


def test_make_cli_retranscribe() -> None:
    lines, code = run_test_cli_retranscribe()
    assert code == 0, lines


def test_make_cli_upgrade() -> None:
    lines, code = run_test_cli_upgrade()
    assert code == 0, lines
