"""US-022：Worker 音频格式检测、WAV 直通与非 WAV 转码（单测，不触 ffmpeg/ffprobe）。

``standardize`` 默认用真实 ``probe_media`` / ``ffmpeg_to_wav``，本测试全部注入 fake
（FakeProbe / fake transcode），不依赖系统 ffmpeg/ffprobe，保持 pytest 纯逻辑确定性。
真实端到端校验在 ``make test-wav-passthrough`` / ``test-audio-transcode-to-wav`` /
``test-transcode-fail``（用真实 fixtures + ffmpeg）中手动跑。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from soniscope_worker.audio import (
    AUDIO_FILENAME,
    STATUS_FAILED,
    STATUS_PASSTHROUGH,
    STATUS_TRANSCODED,
    WAV_TMP_SUFFIX,
    AudioToolError,
    StandardizeResult,
    format_label,
    is_wav,
    run_test_audio_transcode_to_wav,
    run_test_wav_passthrough,
    standardize,
)
from soniscope_worker.fixtures import FixtureError, MediaInfo, sha256_of

WAV_INFO = MediaInfo(duration=24.0, format_name="wav", codec_names=("pcm_s16le",))
PCM_ONLY_INFO = MediaInfo(duration=10.0, format_name="", codec_names=("pcm_mulaw",))
M4A_INFO = MediaInfo(
    duration=24.0, format_name="mov,mp4,m4a,3gp,3g2,mj2", codec_names=("aac",)
)
MP3_INFO = MediaInfo(duration=30.0, format_name="mp3", codec_names=("mp3",))

VALID_FID = "20260527T120000_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE"
EXPECTED_DATE_FROM_FID = "2026-05-27"  # 来自 fragment_id 前缀的日期解析


def _dirs(base: Path) -> tuple[Path, Path, Path]:
    inbox = base / "inbox"
    failed = inbox / "failed"
    fragments = base / "fragments"
    for d in (inbox, failed, fragments):
        d.mkdir(parents=True, exist_ok=True)
    return inbox, failed, fragments


def _make_part(inbox: Path, fid: str, data: bytes) -> Path:
    part = inbox / f"{fid}.part"
    part.write_bytes(data)
    return part


def _const_probe(info: MediaInfo) -> Callable[[Path], MediaInfo]:
    def probe(_path: Path) -> MediaInfo:
        return info

    return probe


# ── 纯逻辑 ─────────────────────────────────────────────────────────────────
def test_is_wav_by_format_name() -> None:
    assert is_wav(WAV_INFO)


def test_is_wav_by_pcm_codec() -> None:
    assert is_wav(PCM_ONLY_INFO)


def test_is_wav_false_for_m4a_and_mp3() -> None:
    assert not is_wav(M4A_INFO)
    assert not is_wav(MP3_INFO)


def test_format_label_wav() -> None:
    assert format_label(WAV_INFO) == "wav"


def test_format_label_m4a_from_aac() -> None:
    assert format_label(M4A_INFO) == "m4a"


def test_format_label_fallback_to_codec() -> None:
    assert format_label(MP3_INFO) == "mp3"


def test_format_label_fallback_to_format_name() -> None:
    info = MediaInfo(duration=1.0, format_name="amr,foo", codec_names=())
    assert format_label(info) == "amr"


# ── 直通路径（WAV）────────────────────────────────────────────────────────
def test_passthrough_renames_and_keeps_bytes(tmp_path: Path) -> None:
    inbox, failed, fragments = _dirs(tmp_path)
    data = b"RIFF....WAVEfmt fake wav bytes"
    part = _make_part(inbox, VALID_FID, data)
    original_sha = sha256_of(part)

    result = standardize(
        part,
        fragment_id=VALID_FID,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        original_format="wav",
        probe=_const_probe(WAV_INFO),
        transcode=_unexpected_transcode,
    )

    assert result.status == STATUS_PASSTHROUGH
    assert result.ok
    audio = fragments / EXPECTED_DATE_FROM_FID / VALID_FID / AUDIO_FILENAME
    assert result.audio_path == audio
    assert audio.is_file()
    assert audio.read_bytes() == data
    # 直通：bytes 不变 → audio.sha256 == upload.original_sha256，size 相等（§3.3 AC#5）
    assert result.audio_sha256 == original_sha == result.original_sha256
    assert result.audio_size_bytes == result.original_size_bytes == len(data)
    assert result.audio_format == "wav"
    assert result.original_format == "wav"
    # .part 已被 rename 走
    assert not part.exists()


def test_passthrough_original_format_falls_back_to_probe(tmp_path: Path) -> None:
    inbox, failed, fragments = _dirs(tmp_path)
    part = _make_part(inbox, VALID_FID, b"wavbytes")
    result = standardize(
        part,
        fragment_id=VALID_FID,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        original_format=None,
        probe=_const_probe(WAV_INFO),
    )
    assert result.original_format == "wav"  # 来自探测兜底


# ── 转码路径（非 WAV）──────────────────────────────────────────────────────
def _fake_transcode_writes(content: bytes) -> Callable[[Path, Path], None]:
    def transcode(src: Path, dest: Path) -> None:
        assert src.exists()
        dest.write_bytes(content)

    return transcode


def _unexpected_transcode(_src: Path, _dest: Path) -> None:  # pragma: no cover
    raise AssertionError("WAV 直通路径不应调用 transcode")


def test_transcode_produces_wav_with_distinct_sha(tmp_path: Path) -> None:
    inbox, failed, fragments = _dirs(tmp_path)
    original = b"\x00\x01\x02 fake m4a payload"
    part = _make_part(inbox, VALID_FID, original)
    original_sha = sha256_of(part)
    wav_bytes = b"RIFFtranscoded-pcm-wav-payload"

    result = standardize(
        part,
        fragment_id=VALID_FID,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        original_format="m4a",
        probe=_const_probe(M4A_INFO),
        transcode=_fake_transcode_writes(wav_bytes),
    )

    assert result.status == STATUS_TRANSCODED
    audio = fragments / EXPECTED_DATE_FROM_FID / VALID_FID / AUDIO_FILENAME
    assert audio.is_file()
    assert audio.read_bytes() == wav_bytes
    assert result.audio_format == "wav"
    assert result.original_format == "m4a"
    # 两个 sha256 都真实且不同（AC#6）
    assert result.original_sha256 == original_sha
    assert result.audio_sha256 == sha256_of(audio)
    assert result.audio_sha256 != result.original_sha256
    assert result.audio_sha256 is not None and result.original_sha256 is not None
    # 中间态清理：.part 消费、.wav.tmp 不残留
    assert not part.exists()
    assert not (inbox / f"{VALID_FID}{WAV_TMP_SUFFIX}").exists()


def test_transcode_writes_tmp_in_inbox_then_renames(tmp_path: Path) -> None:
    inbox, failed, fragments = _dirs(tmp_path)
    part = _make_part(inbox, VALID_FID, b"original")
    seen_dest: list[Path] = []

    def transcode(_src: Path, dest: Path) -> None:
        seen_dest.append(dest)
        dest.write_bytes(b"wav")

    standardize(
        part,
        fragment_id=VALID_FID,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        original_format="mp3",
        probe=_const_probe(MP3_INFO),
        transcode=transcode,
    )
    # AC#3：先写 inbox/<id>.wav.tmp
    assert seen_dest == [inbox / f"{VALID_FID}{WAV_TMP_SUFFIX}"]


# ── 失败留档 ───────────────────────────────────────────────────────────────
def test_probe_failure_archives_to_failed(tmp_path: Path) -> None:
    inbox, failed, fragments = _dirs(tmp_path)
    part = _make_part(inbox, VALID_FID, b"garbage")

    def probe(_path: Path) -> MediaInfo:
        raise FixtureError("ffprobe 探测失败")

    result = standardize(
        part,
        fragment_id=VALID_FID,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        probe=probe,
        transcode=_unexpected_transcode,
    )

    assert result.status == STATUS_FAILED
    assert not result.ok
    archived = failed / f"{VALID_FID}.part"
    assert result.failed_archive == archived
    assert archived.is_file()
    assert not part.exists()
    # 不创建 fragment 完成目录（AC#7）
    assert not (fragments / EXPECTED_DATE_FROM_FID / VALID_FID).exists()


def test_transcode_failure_archives_and_cleans_tmp(tmp_path: Path) -> None:
    inbox, failed, fragments = _dirs(tmp_path)
    part = _make_part(inbox, VALID_FID, b"broken m4a")

    def transcode(_src: Path, dest: Path) -> None:
        dest.write_bytes(b"partial")  # 写了一半的 .wav.tmp
        raise AudioToolError("ffmpeg 转码失败：broken")

    result = standardize(
        part,
        fragment_id=VALID_FID,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        original_format="m4a",
        probe=_const_probe(M4A_INFO),
        transcode=transcode,
    )

    assert result.status == STATUS_FAILED
    assert (failed / f"{VALID_FID}.part").is_file()
    assert not part.exists()
    assert not (inbox / f"{VALID_FID}{WAV_TMP_SUFFIX}").exists()  # 半成品 tmp 清理
    assert not (fragments / EXPECTED_DATE_FROM_FID / VALID_FID).exists()
    # 转码失败仍保留原始 sha256（消费前已算），便于诊断
    assert result.original_sha256 == sha256_of(failed / f"{VALID_FID}.part")


def test_missing_part_is_failed(tmp_path: Path) -> None:
    inbox, failed, fragments = _dirs(tmp_path)
    result = standardize(
        inbox / f"{VALID_FID}.part",
        fragment_id=VALID_FID,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        probe=_const_probe(WAV_INFO),
    )
    assert result.status == STATUS_FAILED
    assert "缺失" in result.detail


def test_invalid_fragment_id_is_failed(tmp_path: Path) -> None:
    inbox, failed, fragments = _dirs(tmp_path)
    bad_fid = "not-a-valid-fragment-id"
    part = inbox / f"{bad_fid}.part"
    part.write_bytes(b"x")
    result = standardize(
        part,
        fragment_id=bad_fid,
        fragments_root=fragments,
        inbox_root=inbox,
        failed_root=failed,
        probe=_const_probe(WAV_INFO),
    )
    assert result.status == STATUS_FAILED
    assert "fragment_id" in result.detail


def test_standardize_result_ok_property() -> None:
    assert StandardizeResult("f", STATUS_PASSTHROUGH).ok
    assert StandardizeResult("f", STATUS_TRANSCODED).ok
    assert not StandardizeResult("f", STATUS_FAILED).ok


# ── make test-* 入口：缺 fixture 时优雅 SKIP（不依赖 ffmpeg）─────────────────
@pytest.mark.parametrize(
    "runner",
    [run_test_wav_passthrough, run_test_audio_transcode_to_wav],
)
def test_runners_skip_when_fixture_missing(
    runner: Callable[[], tuple[list[str], int]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import soniscope_worker.audio as audio_mod

    monkeypatch.setattr(audio_mod, "_fixture_path", lambda name: Path("/no/such") / name)
    lines, code = runner()
    assert code == 0
    assert any(line.startswith("SKIP") for line in lines)
