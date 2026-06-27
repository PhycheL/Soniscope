"""US-027 Worker 轮询到落盘完整流水线 单元测试（全程不触网/不触 ffprobe/不触云端）。

用注入的 fake probe（返回 WAV → 直通，无需 ffprobe）+ stub 转写器 + 内存 OssSource，
覆盖完整流水线、幂等跳过、同 key 去重、失败不创建 .done、启动恢复重转写等。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from soniscope_worker import pipeline
from soniscope_worker.config import TranscriberConfig
from soniscope_worker.fixtures import FixtureError, MediaInfo
from soniscope_worker.oss_admin import object_key_for
from soniscope_worker.pipeline import (
    STAGE_DONE,
    STAGE_MANIFEST_DRAFT,
    STAGE_STANDARDIZE,
    STAGE_TRANSCRIBE,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_SKIPPED,
    process_part,
    process_pending,
    run_pipeline_loop,
    run_pipeline_once,
)
from soniscope_worker.poller import OssListing, metadata_to_draft
from soniscope_worker.recovery import (
    AUDIO_FILENAME,
    DONE_MARKER,
    MANIFEST_FILENAME,
    TRANSCRIPT_JSON_FILENAME,
    TRANSCRIPT_TXT_FILENAME,
    FragmentState,
)
from soniscope_worker.transcriber import Segment, TranscriptResult

FID = "20260627T101500_dev01_0123456789ABCDEFGHJKMNPQRS"
KEY = object_key_for(FID)
DATE = KEY.split("/")[1]


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _meta(sha: str, **overrides: str) -> dict[str, str]:
    base = {
        "session-id": "SESSION01XYZ",
        "chunk-seq": "1",
        "chunk-total": "0",
        "recorded-at": "2026-06-27T10:15:00+08:00",
        "duration": "3.2",
        "original-format": "wav",
        "sha256": sha,
    }
    base.update(overrides)
    return base


def _config() -> TranscriberConfig:
    return TranscriberConfig.model_validate(
        {
            "name": "cloud-speech",
            "provider": "aliyun-nls",
            "model": "中文普通话（识音石 V1 - 端到端模型)",
            "params_version": "v1",
            "api_endpoint": "cn-beijing",
            "appkey": "stub-appkey-0000",
            "access_key_id": "stub-ak-id",
            "access_key_secret": "stub-ak-secret-0000",
            "upload_mode": "oss-url",
        }
    )


def _wav_probe(_path: Path) -> MediaInfo:
    """伪 ffprobe：永远判定为 WAV（直通），不依赖系统 ffprobe。"""
    return MediaInfo(duration=3.2, format_name="wav", codec_names=("pcm_s16le",))


class _StubTranscriber:
    name = "cloud-speech"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def transcribe(self, fragment_id: str, audio_path: Path, oss_key: str) -> TranscriptResult:
        self.calls.append((fragment_id, oss_key))
        return TranscriptResult(
            segments=[Segment(0.0, 1.5, "你好"), Segment(1.5, 3.0, "世界")],
            language="zh",
            model="中文普通话（识音石 V1 - 端到端模型)",
            params_version="v1",
            provider="aliyun-nls",
            duration=3.2,
        )


class _RaisingTranscriber:
    name = "cloud-speech"

    def transcribe(self, fragment_id: str, audio_path: Path, oss_key: str) -> TranscriptResult:
        raise RuntimeError("NLS 不可达")


class _FakeSource:
    """内存 OssSource：dict(key→(body, meta))，可注入重复 listing 与下载计数。"""

    def __init__(
        self,
        objects: Mapping[str, tuple[bytes, Mapping[str, str]]],
        *,
        duplicate_listing: bool = False,
    ) -> None:
        self._objects = dict(objects)
        self._duplicate = duplicate_listing
        self.download_calls: list[str] = []
        self.list_calls = 0

    def list_recordings(self) -> list[OssListing]:
        self.list_calls += 1
        out = [OssListing(key=k, size=len(v[0])) for k, v in self._objects.items()]
        if self._duplicate:
            out = out + list(out)  # 同 key 出现两次（AC#4）
        return out

    def head_metadata(self, object_key: str) -> Mapping[str, str]:
        return dict(self._objects[object_key][1])

    def download(self, object_key: str, dest: Path) -> None:
        self.download_calls.append(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self._objects[object_key][0])


def _runtime(base: Path) -> tuple[Path, Path, Path, Path]:
    inbox = base / "inbox"
    failed = inbox / "failed"
    fragments = base / "fragments"
    tmp = base / "tmp"
    for d in (inbox, failed, fragments, tmp):
        d.mkdir(parents=True, exist_ok=True)
    return inbox, failed, fragments, tmp


def _seed_part(inbox: Path, fragment_id: str, body: bytes) -> Path:
    part = inbox / f"{fragment_id}.part"
    part.write_bytes(body)
    return part


# ── process_part：完整成功路径 ─────────────────────────────────────────────
def test_process_part_completes_all_products(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)
    body = b"RIFF....WAVEdata...."
    part = _seed_part(inbox, FID, body)
    draft = metadata_to_draft(FID, _meta(_sha(body)))
    tr = _StubTranscriber()
    result = process_part(
        fragment_id=FID, object_key=KEY, part=part, draft=draft, transcriber=tr,
        config=_config(), fragments_root=fragments, inbox_root=inbox,
        failed_root=failed, tmp_root=tmp, probe=_wav_probe,
    )
    assert result.status == STATUS_COMPLETED
    assert result.stage == STAGE_DONE
    frag_dir = fragments / DATE / FID
    for name in (
        AUDIO_FILENAME, MANIFEST_FILENAME, TRANSCRIPT_JSON_FILENAME,
        TRANSCRIPT_TXT_FILENAME, DONE_MARKER,
    ):
        assert (frag_dir / name).is_file(), name
    # .done 0 字节
    assert (frag_dir / DONE_MARKER).stat().st_size == 0
    # transcript.txt = segments[].text 顺序拼接
    assert (frag_dir / TRANSCRIPT_TXT_FILENAME).read_text(encoding="utf-8") == "你好世界"
    # transcript.json 不含 duration（§3.4）
    tj = json.loads((frag_dir / TRANSCRIPT_JSON_FILENAME).read_text(encoding="utf-8"))
    assert "duration" not in tj
    assert tj["provider"] == "aliyun-nls"
    # transcribe 收到的 oss_key 是 object_key（AC：oss-url 拉取用）
    assert tr.calls == [(FID, KEY)]


def test_process_part_manifest_transcription_filled(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)
    body = b"WAVE-bytes"
    part = _seed_part(inbox, FID, body)
    draft = metadata_to_draft(FID, _meta(_sha(body)))
    process_part(
        fragment_id=FID, object_key=KEY, part=part, draft=draft, transcriber=_StubTranscriber(),
        config=_config(), fragments_root=fragments, inbox_root=inbox,
        failed_root=failed, tmp_root=tmp, probe=_wav_probe,
        now_iso=lambda: "2026-06-27T10:16:00+08:00",
        monotonic=iter([100.0, 112.5]).__next__,
    )
    manifest = json.loads((fragments / DATE / FID / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    tx = manifest["transcription"]
    assert tx["transcriber"] == "cloud-speech"
    assert tx["model"] == "中文普通话（识音石 V1 - 端到端模型)"
    assert tx["params_version"] == "v1"
    assert tx["provider"] == "aliyun-nls"
    assert tx["upload_mode"] == "oss-url"
    assert tx["started_at"] == "2026-06-27T10:16:00+08:00"
    assert tx["completed_at"] == "2026-06-27T10:16:00+08:00"
    assert tx["elapsed_seconds"] == pytest.approx(12.5)
    # 直通：audio.sha256 == upload.original_sha256
    assert manifest["audio"]["sha256"] == manifest["upload"]["original_sha256"] == _sha(body)


# ── process_part：失败路径不创建 .done（AC#2）──────────────────────────────
def test_process_part_transcribe_failure_no_done(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)
    body = b"WAVE-bytes"
    part = _seed_part(inbox, FID, body)
    draft = metadata_to_draft(FID, _meta(_sha(body)))
    result = process_part(
        fragment_id=FID, object_key=KEY, part=part, draft=draft, transcriber=_RaisingTranscriber(),
        config=_config(), fragments_root=fragments, inbox_root=inbox,
        failed_root=failed, tmp_root=tmp, probe=_wav_probe,
    )
    assert result.status == STATUS_FAILED
    assert result.stage == STAGE_TRANSCRIBE
    frag_dir = fragments / DATE / FID
    # manifest 初稿已写、audio.wav 已落，但无 transcript / .done
    assert (frag_dir / MANIFEST_FILENAME).is_file()
    assert (frag_dir / AUDIO_FILENAME).is_file()
    assert not (frag_dir / DONE_MARKER).exists()
    assert not (frag_dir / TRANSCRIPT_JSON_FILENAME).exists()
    # 初稿 transcription.completed_at 为空
    manifest = json.loads((frag_dir / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["transcription"]["started_at"] is not None
    assert manifest["transcription"]["completed_at"] is None


def test_process_part_standardize_failure_archives(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)
    body = b"not-audio"
    part = _seed_part(inbox, FID, body)
    draft = metadata_to_draft(FID, _meta(_sha(body)))

    def _bad_probe(_path: Path) -> MediaInfo:
        raise FixtureError("ffprobe 无法识别")

    result = process_part(
        fragment_id=FID, object_key=KEY, part=part, draft=draft, transcriber=_StubTranscriber(),
        config=_config(), fragments_root=fragments, inbox_root=inbox,
        failed_root=failed, tmp_root=tmp, probe=_bad_probe,
    )
    assert result.status == STATUS_FAILED
    assert result.stage == STAGE_STANDARDIZE
    # 留档到 inbox/failed/，未创建 fragment 目录
    assert (failed / f"{FID}.part").is_file()
    assert not (fragments / DATE / FID).exists()


# ── run_pipeline_once：幂等跳过 + 同 key 去重 ──────────────────────────────
def test_run_pipeline_once_skips_done_no_redownload(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)
    body = b"WAVE-bytes"
    source = _FakeSource({KEY: (body, _meta(_sha(body)))})
    kwargs = dict(
        config=_config(), fragments_root=fragments, inbox_root=inbox,
        failed_root=failed, tmp_root=tmp, probe=_wav_probe,
    )
    first = run_pipeline_once(source, _StubTranscriber(), **kwargs)  # type: ignore[arg-type]
    second = run_pipeline_once(source, _StubTranscriber(), **kwargs)  # type: ignore[arg-type]
    assert len(first) == 1 and first[0].ok
    assert second == []  # 已 .done → 跳过
    assert source.download_calls == [KEY]  # 仅下载一次（AC#7）


def test_run_pipeline_once_dedups_same_key(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)
    body = b"WAVE-bytes"
    source = _FakeSource({KEY: (body, _meta(_sha(body)))}, duplicate_listing=True)
    results = run_pipeline_once(
        source, _StubTranscriber(), config=_config(), fragments_root=fragments,
        inbox_root=inbox, failed_root=failed, tmp_root=tmp, probe=_wav_probe,
    )
    # 同 key 出现两次，只处理一次（AC#4：不产生重复目录）
    assert len(results) == 1 and results[0].ok
    assert source.download_calls == [KEY]
    assert len(list((fragments / DATE).iterdir())) == 1


def test_run_pipeline_once_sha_mismatch_no_done(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)
    body = b"WAVE-bytes"
    source = _FakeSource({KEY: (body, _meta("d" * 64))})  # 错误 sha256
    results = run_pipeline_once(
        source, _StubTranscriber(), config=_config(), fragments_root=fragments,
        inbox_root=inbox, failed_root=failed, tmp_root=tmp, probe=_wav_probe,
    )
    assert len(results) == 1 and results[0].status == STATUS_FAILED
    assert not (fragments / DATE / FID / DONE_MARKER).exists()
    assert not (inbox / f"{FID}.part").exists()  # sha 不符已删 .part


# ── process_pending：启动恢复重新转写 ──────────────────────────────────────
def _seed_pending(fragments: Path, fragment_id: str, *, with_manifest: bool) -> FragmentState:
    frag_dir = fragments / DATE / fragment_id
    frag_dir.mkdir(parents=True, exist_ok=True)
    (frag_dir / AUDIO_FILENAME).write_bytes(b"RIFF....WAVE")
    if with_manifest:
        (frag_dir / MANIFEST_FILENAME).write_text(
            json.dumps(
                {
                    "fragment_id": fragment_id,
                    "session_id": "SESSION01XYZ",
                    "transcription": {"started_at": "2026-06-27T10:16:00+08:00"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return FragmentState(fragment_id=fragment_id, date=DATE, path=frag_dir, status="pending")


def test_process_pending_retranscribes_and_finalizes(tmp_path: Path) -> None:
    _, _, fragments, tmp = _runtime(tmp_path)
    state = _seed_pending(fragments, FID, with_manifest=True)
    result = process_pending(state, _StubTranscriber(), config=_config(), tmp_root=tmp)
    assert result.status == STATUS_COMPLETED
    frag_dir = state.path
    assert (frag_dir / DONE_MARKER).is_file()
    assert (frag_dir / TRANSCRIPT_JSON_FILENAME).is_file()
    manifest = json.loads((frag_dir / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["transcription"]["completed_at"] is not None
    assert manifest["transcription"]["provider"] == "aliyun-nls"
    # 保留原 manifest 初稿字段
    assert manifest["session_id"] == "SESSION01XYZ"


def test_process_pending_missing_manifest_skips(tmp_path: Path) -> None:
    _, _, fragments, tmp = _runtime(tmp_path)
    state = _seed_pending(fragments, FID, with_manifest=False)
    result = process_pending(state, _StubTranscriber(), config=_config(), tmp_root=tmp)
    assert result.status == STATUS_SKIPPED
    assert result.stage == STAGE_MANIFEST_DRAFT
    assert not (state.path / DONE_MARKER).exists()  # 不补 .done，留待 OSS 重下


def test_process_pending_transcribe_failure_no_done(tmp_path: Path) -> None:
    _, _, fragments, tmp = _runtime(tmp_path)
    state = _seed_pending(fragments, FID, with_manifest=True)
    result = process_pending(state, _RaisingTranscriber(), config=_config(), tmp_root=tmp)
    assert result.status == STATUS_FAILED
    assert result.stage == STAGE_TRANSCRIBE
    assert not (state.path / DONE_MARKER).exists()


# ── run_pipeline_loop：启动恢复 pending + 周期扫描 ─────────────────────────
def test_run_pipeline_loop_recovers_pending_and_scans(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)
    # 预置一个 pending（有 audio.wav + manifest 初稿、无 .done）
    pending_fid = FID
    _seed_pending(fragments, pending_fid, with_manifest=True)
    # 残留 .part（应被恢复清理）
    (inbox / "stale.part").write_bytes(b"x")
    source = _FakeSource({})  # 无新对象
    iters = run_pipeline_loop(
        source, _StubTranscriber(), 30, config=_config(), fragments_root=fragments,
        inbox_root=inbox, failed_root=failed, tmp_root=tmp, log=lambda _m: None,
        max_iterations=1, sleep=lambda _s: None,
    )
    assert iters == 1
    # pending 已恢复转写补回 .done
    assert (fragments / DATE / pending_fid / DONE_MARKER).is_file()
    # 残留 .part 被恢复扫描清理
    assert not (inbox / "stale.part").exists()


def test_run_pipeline_loop_continues_on_scan_error(tmp_path: Path) -> None:
    inbox, failed, fragments, tmp = _runtime(tmp_path)

    class _BoomSource:
        def list_recordings(self) -> list[OssListing]:
            raise RuntimeError("OSS 不可达")

        def head_metadata(self, object_key: str) -> Mapping[str, str]:
            return {}

        def download(self, object_key: str, dest: Path) -> None:  # pragma: no cover
            pass

    iters = run_pipeline_loop(
        _BoomSource(), _StubTranscriber(), 30, config=_config(), fragments_root=fragments,
        inbox_root=inbox, failed_root=failed, tmp_root=tmp, log=lambda _m: None,
        recover_first=False, max_iterations=2, sleep=lambda _s: None,
    )
    assert iters == 2  # 单轮 list 异常不杀死循环


# ── make test-* 入口：缺 fixture 时优雅 SKIP（exit 0）──────────────────────
def test_make_targets_skip_without_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "_fixture_path", lambda name: Path("/nonexistent") / name)
    for fn in (
        pipeline.run_test_download_interrupt,
        pipeline.run_test_no_redownload,
        pipeline.run_test_transcribe,
    ):
        lines, code = fn()
        assert code == 0
        assert any("SKIP" in line for line in lines)
