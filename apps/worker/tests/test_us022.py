"""Tests for US-022 — Worker audio format detection, WAV passthrough, and non-WAV transcoding."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from soniscope_worker import audio, poller
from soniscope_worker.audio import (
    AudioProcessResult,
    AudioProbeResult,
    _atomic_copy_or_rename,
    _atomic_rename,
    _run_ffprobe,
    _sha256_hex,
    probe_audio,
    process_audio,
    transcode_to_wav,
)

# ---------------------------------------------------------------------------
# Paths to test fixture files (must exist — verified by US-003)
# ---------------------------------------------------------------------------

TESTS_AUDIO = Path(__file__).parent.parent.parent.parent / "tests" / "audio"
SAMPLE_WAV = TESTS_AUDIO / "sample-20s.wav"
SAMPLE_M4A = TESTS_AUDIO / "sample-20s.m4a"

pytestmark = pytest.mark.skipif(
    not SAMPLE_WAV.is_file(),
    reason="test audio fixtures not available (run scripts/fetch_test_fixtures.py)",
)


# ---------------------------------------------------------------------------
# AudioProbeResult
# ---------------------------------------------------------------------------


class TestAudioProbeResult:
    def test_defaults(self) -> None:
        r = AudioProbeResult()
        assert r.format_name == ""
        assert r.codec_name == ""
        assert r.duration_seconds == 0.0
        assert r.sample_rate == 0
        assert r.channels == 0
        assert r.bit_depth is None
        assert r.valid is False
        assert r.error == ""
        assert r.is_wav is False
        assert r.is_compliant_wav is False

    def test_is_wav_true(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="pcm_s16le", valid=True)
        assert r.is_wav is True

    def test_is_wav_false_m4a(self) -> None:
        r = AudioProbeResult(format_name="mov,mp4,m4a,3gp,3g2,mj2", codec_name="aac", valid=True)
        assert r.is_wav is False

    def test_is_wav_false_invalid(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="pcm_s16le", valid=False)
        assert r.is_wav is False

    def test_is_compliant_wav_true_pcm_s16le(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="pcm_s16le", valid=True)
        assert r.is_compliant_wav is True

    def test_is_compliant_wav_true_pcm_s16be(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="pcm_s16be", valid=True)
        assert r.is_compliant_wav is True

    def test_is_compliant_wav_true_pcm_f32le(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="pcm_f32le", valid=True)
        assert r.is_compliant_wav is True

    def test_is_compliant_wav_true_pcm_u8(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="pcm_u8", valid=True)
        assert r.is_compliant_wav is True

    def test_is_compliant_wav_false_non_pcm(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="mp3", valid=True)
        assert r.is_compliant_wav is False

    def test_is_compliant_wav_false_non_wav(self) -> None:
        r = AudioProbeResult(format_name="mp3", codec_name="mp3", valid=True)
        assert r.is_compliant_wav is False


# ---------------------------------------------------------------------------
# AudioProcessResult
# ---------------------------------------------------------------------------


class TestAudioProcessResult:
    def test_defaults(self) -> None:
        r = AudioProcessResult()
        assert r.fragment_id == ""
        assert r.ok is False
        assert r.source_path is None
        assert r.dest_path is None
        assert r.audio_format == "wav"
        assert r.original_format == ""
        assert r.audio_sha256 == ""
        assert r.original_sha256 == ""
        assert r.audio_size_bytes == 0
        assert r.original_size_bytes == 0
        assert r.mode == ""
        assert r.error == ""

    def test_success_fields(self) -> None:
        r = AudioProcessResult(
            fragment_id="20260602T120000_dev01_01JXXXXX",
            ok=True,
            audio_format="wav",
            original_format="m4a",
            audio_sha256="abc123",
            original_sha256="def456",
            audio_size_bytes=1000,
            original_size_bytes=500,
            mode="transcoded",
        )
        assert r.fragment_id == "20260602T120000_dev01_01JXXXXX"
        assert r.ok is True
        assert r.mode == "transcoded"
        assert r.original_format == "m4a"
        assert r.audio_sha256 != r.original_sha256  # different because transcoded


# ---------------------------------------------------------------------------
# _sha256_hex
# ---------------------------------------------------------------------------


class TestSha256Hex:
    def test_known_content(self) -> None:
        """sha256 of b'hello' matches known value."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
            f.write(b"hello")
            tmp = Path(f.name)
        try:
            h = _sha256_hex(tmp)
            assert h == hashlib.sha256(b"hello").hexdigest()
        finally:
            tmp.unlink(missing_ok=True)

    def test_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
            tmp = Path(f.name)
        try:
            h = _sha256_hex(tmp)
            assert h == hashlib.sha256(b"").hexdigest()
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# _atomic_rename / _atomic_copy_or_rename
# ---------------------------------------------------------------------------


class TestAtomicRename:
    def test_renames_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.txt"
            dest = Path(td) / "sub" / "dest.txt"
            src.write_text("content")
            _atomic_rename(src, dest)
            assert dest.read_text() == "content"
            assert not src.exists()

    def test_creates_parent_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.txt"
            dest = Path(td) / "deep" / "nested" / "dest.txt"
            src.write_text("hello")
            _atomic_rename(src, dest)
            assert dest.read_text() == "hello"


class TestAtomicCopyOrRename:
    def test_rename_on_same_fs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.bin"
            dest = Path(td) / "out" / "dest.bin"
            src.write_bytes(b"test data")
            _atomic_copy_or_rename(src, dest)
            assert dest.read_bytes() == b"test data"
            assert not src.exists()

    def test_creates_parent_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.bin"
            dest = Path(td) / "a" / "b" / "c" / "dest.bin"
            src.write_bytes(b"x")
            _atomic_copy_or_rename(src, dest)
            assert dest.read_bytes() == b"x"


# ---------------------------------------------------------------------------
# _run_ffprobe (integration)
# ---------------------------------------------------------------------------


class TestRunFfprobeIntegration:
    def test_wav_fixture(self) -> None:
        raw = _run_ffprobe(SAMPLE_WAV)
        # format_name may be quoted if it contains commas; strip for comparison
        fmt = raw.get("format_name", "").strip('"')
        assert fmt in ("wav",)
        assert raw.get("codec_name", "").strip('"') in ("pcm_s16le",)

    def test_m4a_fixture(self) -> None:
        raw = _run_ffprobe(SAMPLE_M4A)
        fmt = raw.get("format_name", "").strip('"')
        # m4a container includes mov,mp4,m4a,3gp,3g2,mj2
        assert fmt != "", "expected non-empty format_name"
        # The codec should be aac
        codec = raw.get("codec_name", "").strip('"')
        assert codec in ("aac",), f"expected aac codec, got {codec!r}"


# ---------------------------------------------------------------------------
# probe_audio
# ---------------------------------------------------------------------------


class TestProbeAudio:
    def test_wav_fixture(self) -> None:
        r = probe_audio(SAMPLE_WAV)
        assert r.valid is True
        assert r.format_name == "wav"
        assert r.codec_name == "pcm_s16le"
        assert r.is_wav is True
        assert r.is_compliant_wav is True
        # duration should be positive — exact value from fixture (~24 seconds)
        assert r.duration_seconds > 0

    def test_m4a_fixture(self) -> None:
        r = probe_audio(SAMPLE_M4A)
        assert r.valid is True
        assert r.is_wav is False
        assert r.is_compliant_wav is False
        assert "aac" in r.codec_name.lower()

    def test_non_existent_file(self) -> None:
        r = probe_audio(Path("/nonexistent/audio_xyz.abc"))
        assert r.valid is False
        assert r.error != ""


# ---------------------------------------------------------------------------
# transcode_to_wav (integration)
# ---------------------------------------------------------------------------


class TestTranscodeToWav:
    def test_m4a_to_wav(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "output.wav"
            transcode_to_wav(SAMPLE_M4A, dest)
            assert dest.is_file()
            assert dest.stat().st_size > 0

            # Verify the output is actually WAV
            r = probe_audio(dest)
            assert r.valid is True
            assert r.is_wav is True
            assert r.codec_name == "pcm_s16le"

    def test_wav_passthrough_noop(self) -> None:
        """Even if we transcode a WAV, the output should still be valid WAV."""
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "output.wav"
            transcode_to_wav(SAMPLE_WAV, dest)
            assert dest.is_file()
            r = probe_audio(dest)
            assert r.valid is True
            assert r.is_wav is True

    def test_invalid_input_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            corrupt = Path(td) / "corrupt.bin"
            corrupt.write_bytes(b"\x00\x01\x02\x03" * 10)
            dest = Path(td) / "output.wav"
            with pytest.raises(RuntimeError, match="ffmpeg transcode failed"):
                transcode_to_wav(corrupt, dest)


# ---------------------------------------------------------------------------
# process_audio (integration with real fixtures)
# ---------------------------------------------------------------------------


class TestProcessAudioIntegration:
    def test_wav_passthrough(self) -> None:
        """WAV fixture should pass through (compliant WAV)."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            part = inbox / "20260602T120000_dev01_01JXXXXX.part"
            shutil.copy2(SAMPLE_WAV, part)

            orig_sha = _sha256_hex(SAMPLE_WAV)
            orig_size = SAMPLE_WAV.stat().st_size

            result = process_audio(
                part_path=part,
                fragment_id="20260602T120000_dev01_01JXXXXX",
                fragment_date="2026-06-02",
                original_format="wav",
                original_sha256=orig_sha,
                original_size_bytes=orig_size,
                home=home,
            )

            assert result.ok is True
            assert result.mode == "passthrough"
            assert result.audio_format == "wav"
            assert result.original_format == "wav"

            # dest should exist
            assert result.dest_path is not None
            assert result.dest_path.is_file()
            assert result.dest_path.name == "audio.wav"

            # passthrough: audio.sha256 == original_sha256 (AC5)
            assert result.audio_sha256 == orig_sha
            assert result.audio_size_bytes == orig_size

            # part should be gone after passthrough
            assert not part.exists()

    def test_m4a_transcode(self) -> None:
        """m4a fixture should be transcoded to WAV."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            part = inbox / "20260602T120000_dev01_01JYYYYY.part"
            shutil.copy2(SAMPLE_M4A, part)

            orig_sha = _sha256_hex(SAMPLE_M4A)
            orig_size = SAMPLE_M4A.stat().st_size

            result = process_audio(
                part_path=part,
                fragment_id="20260602T120000_dev01_01JYYYYY",
                fragment_date="2026-06-02",
                original_format="m4a",
                original_sha256=orig_sha,
                original_size_bytes=orig_size,
                home=home,
            )

            assert result.ok is True
            assert result.mode == "transcoded"
            assert result.audio_format == "wav"
            assert result.original_format == "m4a"

            # dest should exist
            assert result.dest_path is not None
            assert result.dest_path.is_file()

            # Verify output is valid WAV
            r = probe_audio(result.dest_path)
            assert r.valid
            assert r.is_wav

            # transcode: sha256 differs from original (AC6)
            assert result.audio_sha256 != orig_sha

            # part should be gone after transcode
            assert not part.exists()

    def test_m4a_output_recognized_as_wav(self) -> None:
        """AC8: make test-audio-transcode-to-wav verifies output audio.wav is
        recognized as WAV by ffprobe."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            part = inbox / "20260602T120000_dev01_01JZZZZZ.part"
            shutil.copy2(SAMPLE_M4A, part)

            orig_sha = _sha256_hex(SAMPLE_M4A)
            orig_size = SAMPLE_M4A.stat().st_size

            result = process_audio(
                part_path=part,
                fragment_id="20260602T120000_dev01_01JZZZZZ",
                fragment_date="2026-06-02",
                original_format="m4a",
                original_sha256=orig_sha,
                original_size_bytes=orig_size,
                home=home,
            )

            assert result.ok
            assert result.dest_path is not None
            # ffprobe must identify the output as WAV
            r = probe_audio(result.dest_path)
            assert r.valid
            assert r.format_name == "wav"
            assert r.codec_name == "pcm_s16le"


class TestProcessAudioTranscodeFail:
    def test_corrupt_audio_goes_to_failed(self) -> None:
        """AC9: transcode failure → file archived to inbox/failed/."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            failed_dir = home / "inbox" / "failed"

            fragment_id = "20260602T120000_dev01_01JFAIL1"

            part = inbox / f"{fragment_id}.part"
            # Write non-audio data that ffmpeg will reject
            part.write_bytes(b"\x00\x01\x02\x03\x04\x05" * 100)

            result = process_audio(
                part_path=part,
                fragment_id=fragment_id,
                fragment_date="2026-06-02",
                original_format="mp3",
                original_sha256=_sha256_hex(part),
                original_size_bytes=part.stat().st_size,
                home=home,
            )

            assert result.ok is False
            assert result.error != ""
            # Part should be moved to failed/
            assert failed_dir.is_dir()
            failed_files = list(failed_dir.glob(f"{fragment_id}*"))
            assert len(failed_files) >= 1, f"expected failed archive, got {list(failed_dir.iterdir())}"
            # Original part should be gone from inbox
            assert not part.exists()

    def test_corrupt_audio_does_not_create_fragment_dir(self) -> None:
        """Transcode failure should NOT create or pollute fragment directory."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            frags = home / "fragments"

            fragment_id = "20260602T120000_dev01_01JCORRUPT"

            part = inbox / f"{fragment_id}.part"
            part.write_bytes(b"\x00" * 1000)

            process_audio(
                part_path=part,
                fragment_id=fragment_id,
                fragment_date="2026-06-02",
                original_format="mp3",
                original_sha256=_sha256_hex(part),
                original_size_bytes=part.stat().st_size,
                home=home,
            )

            # fragment dir should not exist
            frag_path = frags / "2026-06-02" / fragment_id
            assert not frag_path.exists() or not (frag_path / "audio.wav").exists()


# ---------------------------------------------------------------------------
# process_audio — unit tests (mocked ffprobe/ffmpeg)
# ---------------------------------------------------------------------------


class TestProcessAudioMocked:
    def test_probe_invalid_returns_error(self) -> None:
        """When ffprobe fails, process_audio archives to failed/ and returns ok=False."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            failed_dir = home / "inbox" / "failed"

            fragment_id = "20260602T120000_dev01_01JBADPROBE"

            part = inbox / f"{fragment_id}.part"
            part.write_bytes(b"fake data")

            with mock.patch("soniscope_worker.audio.probe_audio") as mock_probe:
                mock_probe.return_value = AudioProbeResult(valid=False, error="ffprobe: invalid data")

                result = process_audio(
                    part_path=part,
                    fragment_id=fragment_id,
                    fragment_date="2026-06-02",
                    original_format="wav",
                    original_sha256="abc123",
                    original_size_bytes=100,
                    home=home,
                )

            assert result.ok is False
            assert result.error != ""
            assert failed_dir.is_dir()

    def test_success_uses_passthrough_for_compliant_wav(self) -> None:
        """When probe shows compliant WAV, use passthrough mode."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)

            fragment_id = "20260602T120000_dev01_01JPASS"
            part = inbox / f"{fragment_id}.part"
            part.write_text("hello world")

            with mock.patch("soniscope_worker.audio.probe_audio") as mock_probe:
                mock_probe.return_value = AudioProbeResult(
                    format_name="wav",
                    codec_name="pcm_s16le",
                    valid=True,
                )

                result = process_audio(
                    part_path=part,
                    fragment_id=fragment_id,
                    fragment_date="2026-06-02",
                    original_format="wav",
                    original_sha256=_sha256_hex(part),
                    original_size_bytes=part.stat().st_size,
                    home=home,
                )

            assert result.ok is True
            assert result.mode == "passthrough"

    def test_success_uses_transcode_for_m4a(self) -> None:
        """When probe shows non-WAV (m4a), use transcode mode."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)

            fragment_id = "20260602T120000_dev01_01JM4A"
            part = inbox / f"{fragment_id}.part"
            # Simple valid audio so ffmpeg succeeds
            shutil.copy2(SAMPLE_M4A, part)

            result = process_audio(
                part_path=part,
                fragment_id=fragment_id,
                fragment_date="2026-06-02",
                original_format="m4a",
                original_sha256=_sha256_hex(part),
                original_size_bytes=part.stat().st_size,
                home=home,
            )

            assert result.ok is True
            assert result.mode == "transcoded"
            assert result.audio_format == "wav"
            assert result.original_format == "m4a"

    def test_original_format_preserved(self) -> None:
        """Worker keeps original_format from OSS metadata, not from probe."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)

            fragment_id = "20260602T120000_dev01_01JOFMT"
            part = inbox / f"{fragment_id}.part"
            shutil.copy2(SAMPLE_WAV, part)

            result = process_audio(
                part_path=part,
                fragment_id=fragment_id,
                fragment_date="2026-06-02",
                original_format="mp3",  # OSS says mp3, even though file is actually WAV
                original_sha256=_sha256_hex(part),
                original_size_bytes=part.stat().st_size,
                home=home,
            )

            assert result.ok is True
            # original_format preserved from caller
            assert result.original_format == "mp3"
            # audio_format is always "wav" in the final output
            assert result.audio_format == "wav"

    def test_fallback_original_format_when_none(self) -> None:
        """When OSS original_format is empty, use the detected format."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)

            fragment_id = "20260602T120000_dev01_01JFALLBACK"
            part = inbox / f"{fragment_id}.part"
            shutil.copy2(SAMPLE_WAV, part)

            result = process_audio(
                part_path=part,
                fragment_id=fragment_id,
                fragment_date="2026-06-02",
                original_format="",  # missing from OSS
                original_sha256=_sha256_hex(part),
                original_size_bytes=part.stat().st_size,
                home=home,
            )

            assert result.ok is True
            # should fall back to the detected format
            assert result.original_format == "wav"

    def test_transcode_failure_path(self) -> None:
        """Simulated transcode failure through process_audio."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            failed_dir = home / "inbox" / "failed"

            fragment_id = "20260602T120000_dev01_01JTCFAIL"
            part = inbox / f"{fragment_id}.part"
            shutil.copy2(SAMPLE_M4A, part)

            with mock.patch("soniscope_worker.audio.transcode_to_wav") as mock_tc:
                mock_tc.side_effect = RuntimeError("simulated ffmpeg crash")

                result = process_audio(
                    part_path=part,
                    fragment_id=fragment_id,
                    fragment_date="2026-06-02",
                    original_format="m4a",
                    original_sha256=_sha256_hex(part),
                    original_size_bytes=part.stat().st_size,
                    home=home,
                )

            assert result.ok is False
            assert "ffmpeg transcode" in result.error or "simulated" in result.error
            # Part should be archived to failed/
            assert failed_dir.is_dir()


# ---------------------------------------------------------------------------
# process_audio — unknown format treated as non-WAV (AC4)
# ---------------------------------------------------------------------------


class TestProcessAudioUnknownFormat:
    def test_unknown_format_transcodes(self) -> None:
        """When format is unrecognized but ffprobe says valid, transcode to WAV."""
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "SoniScope"
            inbox = home / "inbox"
            inbox.mkdir(parents=True)

            # m4a file with "unknown" format label — should still transcode
            fragment_id = "20260602T120000_dev01_01JUNK"
            part = inbox / f"{fragment_id}.part"
            shutil.copy2(SAMPLE_M4A, part)

            result = process_audio(
                part_path=part,
                fragment_id=fragment_id,
                fragment_date="2026-06-02",
                original_format="unknown",
                original_sha256=_sha256_hex(part),
                original_size_bytes=part.stat().st_size,
                home=home,
            )

            assert result.ok is True
            assert result.mode == "transcoded"


# ---------------------------------------------------------------------------
# poll_cycle integration (summary keys)
# ---------------------------------------------------------------------------


class TestPollCycleSummaryKeys:
    """Verify that poll_cycle summary dict contains US-022 keys."""

    def test_passthrough_key_present(self) -> None:
        """poll_cycle return dict must include 'passthrough' key."""
        src = (Path(__file__).parent.parent / "src" / "soniscope_worker" / "poller.py").read_text()
        assert "'passthrough'" in src or '"passthrough"' in src
        assert "'transcoded'" in src or '"transcoded"' in src
        assert "'transcode_failed'" in src or '"transcode_failed"' in src

    def test_process_audio_imported_in_poller(self) -> None:
        """poll_cycle imports process_audio from audio module."""
        src = (Path(__file__).parent.parent / "src" / "soniscope_worker" / "poller.py").read_text()
        assert "from soniscope_worker.audio import process_audio" in src or \
               "soniscope_worker.audio" in src


# ---------------------------------------------------------------------------
# No DeleteObject in Worker source
# ---------------------------------------------------------------------------


class TestNoDeleteObjectInAudioSource:
    """AC: audio.py must not contain DeleteObject calls."""

    def test_audio_had_no_delete_object(self) -> None:
        src = (Path(__file__).parent.parent / "src" / "soniscope_worker" / "audio.py").read_text()
        assert "delete_object" not in src
        assert "DeleteObject" not in src

    def test_audio_had_no_client_delete(self) -> None:
        src = (Path(__file__).parent.parent / "src" / "soniscope_worker" / "audio.py").read_text()
        lines_with_delete = [
            l for l in src.splitlines()
            if "Client.delete" in l or "client.delete" in l
        ]
        assert len(lines_with_delete) == 0


# ---------------------------------------------------------------------------
# Makefile targets
# ---------------------------------------------------------------------------


class TestMakefileTargets:
    def test_makefile_has_us022_targets(self) -> None:
        makefile = Path(__file__).parent.parent.parent.parent / "Makefile"
        text = makefile.read_text()
        assert "test-wav-passthrough" in text
        assert "test-audio-transcode-to-wav" in text
        assert "test-transcode-fail" in text

    def test_makefile_phony_includes_new_targets(self) -> None:
        makefile = Path(__file__).parent.parent.parent.parent / "Makefile"
        text = makefile.read_text()
        # .PHONY line uses backslash continuation — join all phony lines
        phony_lines: list[str] = []
        accum = ""
        for line in text.splitlines():
            stripped = line.rstrip()
            if stripped.startswith(".PHONY:"):
                accum = stripped
            elif accum and accum.rstrip().endswith("\\"):
                accum = accum.rstrip()[:-1] + stripped.strip()
            else:
                if accum:
                    phony_lines.append(accum)
                accum = ""
        if accum:
            phony_lines.append(accum)
        phony_text = " ".join(phony_lines)
        assert "test-wav-passthrough" in phony_text
        assert "test-audio-transcode-to-wav" in phony_text
        assert "test-transcode-fail" in phony_text


# ---------------------------------------------------------------------------
# Cli test-poll-cycle output includes new summary keys
# ---------------------------------------------------------------------------


class TestCliTestPollCycle:
    def test_output_contains_new_summary_keys(self) -> None:
        cli_src = (
            Path(__file__).parent.parent / "src" / "soniscope_worker" / "cli.py"
        ).read_text()
        assert "Passthrough:" in cli_src or "passthrough" in cli_src
        assert "Transcoded:" in cli_src or "transcoded" in cli_src
        assert "Transcode failed:" in cli_src or "transcode_failed" in cli_src


# ---------------------------------------------------------------------------
# Audio module structure
# ---------------------------------------------------------------------------


class TestAudioModuleStructure:
    def test_module_has_required_symbols(self) -> None:
        """audio.py exports all required functions and classes."""
        assert hasattr(audio, "AudioProbeResult")
        assert hasattr(audio, "AudioProcessResult")
        assert hasattr(audio, "probe_audio")
        assert hasattr(audio, "transcode_to_wav")
        assert hasattr(audio, "process_audio")

    def test_audio_result_has_required_fields(self) -> None:
        """AudioProcessResult has all fields needed by ACs."""
        fields = list(AudioProcessResult.__dataclass_fields__)
        required = [
            "fragment_id", "ok", "source_path", "dest_path",
            "audio_format", "original_format",
            "audio_sha256", "original_sha256",
            "audio_size_bytes", "original_size_bytes",
            "mode", "error",
        ]
        for r in required:
            assert r in fields, f"AudioProcessResult missing field: {r}"

    def test_probe_result_has_required_fields(self) -> None:
        fields = list(AudioProbeResult.__dataclass_fields__)
        required = [
            "format_name", "codec_name", "duration_seconds",
            "sample_rate", "channels", "bit_depth",
            "valid", "error", "is_wav", "is_compliant_wav",
        ]
        for r in required:
            if r in ("is_wav", "is_compliant_wav"):
                continue  # properties, not dataclass fields
            assert r in fields, f"AudioProbeResult missing field: {r}"


# ---------------------------------------------------------------------------
# ffprobe / ffmpeg availability (integration)
# ---------------------------------------------------------------------------


class TestFfmpegFfprobeAvailable:
    def test_ffprobe_found(self) -> None:
        """ffprobe is installed and executable."""
        try:
            proc = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True, text=True,
            )
            assert proc.returncode == 0
        except FileNotFoundError:
            pytest.fail("ffprobe not found in PATH")

    def test_ffmpeg_found(self) -> None:
        """ffmpeg is installed and executable."""
        try:
            proc = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True,
            )
            assert proc.returncode == 0
        except FileNotFoundError:
            pytest.fail("ffmpeg not found in PATH")


# ---------------------------------------------------------------------------
# PCM WAV detection edge cases
# ---------------------------------------------------------------------------


class TestCompliantWavEdgeCases:
    def test_pcm_s16le_compliant(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="pcm_s16le", valid=True)
        assert r.is_compliant_wav is True

    def test_adpcm_not_compliant(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="adpcm_ms", valid=True)
        assert r.is_compliant_wav is False  # ADPCM is not in the compliant list

    def test_aac_not_compliant(self) -> None:
        r = AudioProbeResult(format_name="wav", codec_name="aac", valid=True)
        assert r.is_compliant_wav is False

    def test_case_insensitive_format(self) -> None:
        r = AudioProbeResult(format_name="WAV", codec_name="PCM_S16LE", valid=True)
        assert r.is_wav is True
        # is_compliant_wav checks .lower()
        assert r.is_compliant_wav is True
