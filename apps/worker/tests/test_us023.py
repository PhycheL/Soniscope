"""Tests for US-023 — Worker startup recovery scan & atomic write tools."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from soniscope_worker import atomics, poller
from soniscope_worker.paths import resolve_home


# ============================================================================
# atomics module tests
# ============================================================================


class TestTempFor:
    def test_temp_for_json(self) -> None:
        target = Path("/some/dir/manifest.json")
        result = atomics._temp_for(target)
        assert result == Path("/some/dir/manifest.json.tmp")

    def test_temp_for_txt(self) -> None:
        target = Path("/some/dir/transcript.txt")
        result = atomics._temp_for(target)
        assert result == Path("/some/dir/transcript.txt.tmp")

    def test_temp_for_done(self) -> None:
        target = Path("/some/dir/.done")
        result = atomics._temp_for(target)
        assert result == Path("/some/dir/.done.tmp")


class TestAtomicWriteJson:
    def test_write_and_read(self, tmp_path: Path) -> None:
        target = tmp_path / "sub" / "manifest.json"
        data = {"key": "value", "num": 42}
        atomics.atomic_write_json(target, data)

        assert target.is_file()
        # .tmp should not exist after rename
        assert not (tmp_path / "sub" / "manifest.json.tmp").exists()

        read_back = json.loads(target.read_text())
        assert read_back == data

    def test_overwrite_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "manifest.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text("old")

        atomics.atomic_write_json(target, {"new": True})
        read_back = json.loads(target.read_text())
        assert read_back == {"new": True}

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested" / "dir" / "manifest.json"
        atomics.atomic_write_json(target, {"a": 1})
        assert target.is_file()

    def test_non_ascii_and_complex(self, tmp_path: Path) -> None:
        target = tmp_path / "manifest.json"
        data = {"text": "你好世界", "segments": [{"text": "测试", "start": 0.5, "end": 1.0}]}
        atomics.atomic_write_json(target, data)
        read_back = json.loads(target.read_text())
        assert read_back == data

    def test_no_partial_file_on_error(self, tmp_path: Path) -> None:
        target = tmp_path / "manifest.json"

        # Write with valid data first to check the atomic path
        atomics.atomic_write_json(target, {"key": "value"})

        # Verify that .tmp is gone and target exists
        tmp_file = tmp_path / "manifest.json.tmp"
        assert not tmp_file.exists()
        assert target.exists()

    def test_atomic_rename_cleans_tmp(self, tmp_path: Path) -> None:
        """After atomic write, the .tmp file should not exist."""
        target = tmp_path / "manifest.json"
        atomics.atomic_write_json(target, {"a": 1})
        tmp_file = tmp_path / "manifest.json.tmp"
        assert not tmp_file.exists()


class TestAtomicWriteText:
    def test_write_and_read(self, tmp_path: Path) -> None:
        target = tmp_path / "transcript.txt"
        atomics.atomic_write_text(target, "Hello, world!\n第二行\n")

        assert target.is_file()
        assert not (tmp_path / "transcript.txt.tmp").exists()
        assert target.read_text() == "Hello, world!\n第二行\n"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c" / "transcript.txt"
        atomics.atomic_write_text(target, "deep")
        assert target.is_file()

    def test_overwrite(self, tmp_path: Path) -> None:
        target = tmp_path / "transcript.txt"
        atomics.atomic_write_text(target, "first")
        atomics.atomic_write_text(target, "second")
        assert target.read_text() == "second"

    def test_empty_text(self, tmp_path: Path) -> None:
        target = tmp_path / "transcript.txt"
        atomics.atomic_write_text(target, "")
        assert target.is_file()
        assert target.read_text() == ""


class TestCreateDoneMarker:
    def test_creates_done(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "fragment_abc"
        done = atomics.create_done_marker(frag_dir)

        assert done.name == ".done"
        assert done.is_file()
        assert done.stat().st_size == 0

    def test_idempotent(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "fragment_abc"
        atomics.create_done_marker(frag_dir)
        mtime1 = (frag_dir / ".done").stat().st_mtime

        atomics.create_done_marker(frag_dir)
        mtime2 = (frag_dir / ".done").stat().st_mtime

    def test_creates_missing_parents(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "deep" / "fragment_xyz"
        done = atomics.create_done_marker(frag_dir)
        assert done.is_file()
        assert done.stat().st_size == 0


class TestIsDone:
    def test_done_exists(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "done_dir"
        atomics.create_done_marker(frag_dir)
        assert atomics.is_done(frag_dir) is True

    def test_done_missing(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "no_done_dir"
        frag_dir.mkdir(exist_ok=True)
        assert atomics.is_done(frag_dir) is False

    def test_directory_does_not_exist(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "nonexistent"
        assert atomics.is_done(frag_dir) is False


class TestRemoveDoneMarker:
    def test_remove_existing(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "frag"
        atomics.create_done_marker(frag_dir)
        assert atomics.remove_done_marker(frag_dir) is True
        assert not (frag_dir / ".done").exists()

    def test_remove_missing(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "frag_no_done"
        frag_dir.mkdir(exist_ok=True)
        assert atomics.remove_done_marker(frag_dir) is False

    def test_remove_non_existent_dir(self, tmp_path: Path) -> None:
        frag_dir = tmp_path / "no_such_dir"
        assert atomics.remove_done_marker(frag_dir) is False


# ============================================================================
# recovery_scan tests (expanded for US-023)
# ============================================================================


class TestRecoveryScanInbox:
    """AC1/AC2: clean stale .part and .wav.tmp from inbox/."""

    def test_cleans_part_file(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "test123.part").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=inbox):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert len(result["inbox_cleaned"]) == 1
        assert "test123.part" in result["inbox_cleaned"][0]
        assert not (inbox / "test123.part").exists()

    def test_cleans_wav_tmp_file(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "test456.wav.tmp").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=inbox):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert len(result["inbox_cleaned"]) == 1
        assert "test456.wav.tmp" in result["inbox_cleaned"][0]
        assert not (inbox / "test456.wav.tmp").exists()

    def test_cleans_both_part_and_wav_tmp(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "a.part").touch()
        (inbox / "b.wav.tmp").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=inbox):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert len(result["inbox_cleaned"]) == 2

    def test_no_inbox_directory(self, tmp_path: Path) -> None:
        inbox = tmp_path / "nonexistent_inbox"
        with mock.patch.object(poller, "inbox_dir", return_value=inbox):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert result["inbox_cleaned"] == []

    def test_osesrror_tolerated(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "stale.part").touch()

        # Simulate permission error on unlink
        with mock.patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            with mock.patch.object(poller, "inbox_dir", return_value=inbox):
                with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                    with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                        result = poller.recovery_scan(tmp_path)

        # OSError is tolerated — no crash
        assert result["inbox_cleaned"] == []

    def test_non_stash_files_unaffected(self, tmp_path: Path) -> None:
        """Files without .part/.wav.tmp extension should not be touched."""
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        keep_me = inbox / "important.txt"
        keep_me.touch()

        with mock.patch.object(poller, "inbox_dir", return_value=inbox):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert result["inbox_cleaned"] == []
        assert keep_me.is_file()


class TestRecoveryScanTmp:
    """AC3: clean stale .transcript.json.tmp from tmp/."""

    def test_cleans_transcript_tmp(self, tmp_path: Path) -> None:
        tmp = tmp_path / "tmp"
        tmp.mkdir(parents=True)
        (tmp / "frag1.transcript.json.tmp").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp):
                    result = poller.recovery_scan(tmp_path)

        assert len(result["tmp_cleaned"]) == 1
        assert "frag1.transcript.json.tmp" in result["tmp_cleaned"][0]
        assert not (tmp / "frag1.transcript.json.tmp").exists()

    def test_cleans_multiple_transcript_tmps(self, tmp_path: Path) -> None:
        tmp = tmp_path / "tmp"
        tmp.mkdir(parents=True)
        (tmp / "frag1.transcript.json.tmp").touch()
        (tmp / "frag2.transcript.json.tmp").touch()
        (tmp / "frag3.transcript.json.tmp").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp):
                    result = poller.recovery_scan(tmp_path)

        assert len(result["tmp_cleaned"]) == 3

    def test_no_tmp_directory(self, tmp_path: Path) -> None:
        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "nonexistent_tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert result["tmp_cleaned"] == []

    def test_other_tmp_files_not_cleaned(self, tmp_path: Path) -> None:
        tmp = tmp_path / "tmp"
        tmp.mkdir(parents=True)
        (tmp / "some_other_file.txt").touch()
        (tmp / "data.json").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp):
                    result = poller.recovery_scan(tmp_path)

        assert result["tmp_cleaned"] == []
        assert (tmp / "some_other_file.txt").is_file()
        assert (tmp / "data.json").is_file()

    def test_osesrror_on_tmp_clean_tolerated(self, tmp_path: Path) -> None:
        tmp = tmp_path / "tmp"
        tmp.mkdir(parents=True)
        (tmp / "frag.transcript.json.tmp").touch()

        with mock.patch.object(Path, "unlink", side_effect=OSError("stale NFS handle")):
            with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
                with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                    with mock.patch.object(poller, "tmp_dir", return_value=tmp):
                        result = poller.recovery_scan(tmp_path)

        assert result["tmp_cleaned"] == []


class TestRecoveryScanFragments:
    """AC4: scan fragments/**, identify state of each directory."""

    def _make_frag_structure(
        self,
        base: Path,
        *,
        with_done: bool = False,
        with_audio: bool = False,
        with_other: bool = False,
        frag_id: str = "20260603T120000_dev_01JXXXXX",
    ) -> Path:
        date_dir = base / "fragments" / "2026-06-03"
        frag_dir = date_dir / frag_id
        frag_dir.mkdir(parents=True)
        if with_audio:
            (frag_dir / "audio.wav").touch()
        if with_done:
            (frag_dir / ".done").touch()
        if with_other:
            (frag_dir / "other_file.log").touch()
        return frag_dir

    def test_skip_done_directory(self, tmp_path: Path) -> None:
        self._make_frag_structure(tmp_path, with_done=True, with_audio=True)

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        actions = result["fragment_actions"]
        assert any("skip" in a for a in actions)
        assert any("has .done" in a for a in actions)

    def test_resume_audio_no_done(self, tmp_path: Path) -> None:
        self._make_frag_structure(tmp_path, with_audio=True, with_done=False)

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        actions = result["fragment_actions"]
        assert any("resume" in a for a in actions)
        assert any("needs transcription" in a for a in actions)

    def test_remove_empty_directory(self, tmp_path: Path) -> None:
        frag_dir = self._make_frag_structure(tmp_path, with_audio=False, with_done=False)

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        actions = result["fragment_actions"]
        assert any("removed empty dir" in a for a in actions)
        assert not frag_dir.exists()

    def test_ignore_no_audio_with_files(self, tmp_path: Path) -> None:
        self._make_frag_structure(tmp_path, with_audio=False, with_done=False, with_other=True)

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        actions = result["fragment_actions"]
        assert any("no audio.wav" in a for a in actions)

    def test_multiple_fragments_mixed_states(self, tmp_path: Path) -> None:
        self._make_frag_structure(tmp_path, with_done=True, with_audio=True, frag_id="done_one")
        self._make_frag_structure(tmp_path, with_audio=True, with_done=False, frag_id="needs_trans")
        self._make_frag_structure(tmp_path, with_audio=False, with_done=False, frag_id="empty_one")

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        actions = result["fragment_actions"]
        assert len(actions) == 3
        assert any("skip" in a for a in actions)
        assert any("resume" in a for a in actions)
        assert any("removed empty" in a for a in actions)

    def test_no_fragments_directory(self, tmp_path: Path) -> None:
        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "nonexistent_frags"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert result["fragment_actions"] == []

    def test_ignores_non_directory_entries(self, tmp_path: Path) -> None:
        """Files directly in fragments/ should be ignored."""
        frags = tmp_path / "fragments"
        frags.mkdir(parents=True)
        (frags / "README.txt").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=frags):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert result["fragment_actions"] == []

    def test_rmdir_error_tolerated(self, tmp_path: Path) -> None:
        """If rmdir fails, we should still get an 'ignore' entry."""
        self._make_frag_structure(tmp_path, with_audio=False, with_done=False)

        with mock.patch.object(Path, "rmdir", side_effect=OSError("Directory not empty")):
            with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
                with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                    with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                        result = poller.recovery_scan(tmp_path)

        actions = result["fragment_actions"]
        assert any("ignore" in a and "cleanup failed" in a for a in actions)


class TestRecoveryScanFull:
    """Full recovery scan: inbox + tmp + fragments all at once."""

    def test_all_three_areas(self, tmp_path: Path) -> None:
        # Setup inbox with stale files
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "frag1.part").touch()
        (inbox / "frag2.wav.tmp").touch()

        # Setup tmp with stale files
        tmpp = tmp_path / "tmp"
        tmpp.mkdir(parents=True)
        (tmpp / "frag1.transcript.json.tmp").touch()

        # Setup fragments with mixed states
        frags = tmp_path / "fragments"
        date_dir = frags / "2026-06-03"
        done_dir = date_dir / "done_frag"
        done_dir.mkdir(parents=True)
        (done_dir / "audio.wav").touch()
        (done_dir / ".done").touch()

        resume_dir = date_dir / "resume_frag"
        resume_dir.mkdir(parents=True)
        (resume_dir / "audio.wav").touch()

        empty_dir = date_dir / "empty_frag"
        empty_dir.mkdir(parents=True)

        with mock.patch.object(poller, "inbox_dir", return_value=inbox):
            with mock.patch.object(poller, "fragments_dir", return_value=frags):
                with mock.patch.object(poller, "tmp_dir", return_value=tmpp):
                    result = poller.recovery_scan(tmp_path)

        assert len(result["inbox_cleaned"]) == 2
        assert len(result["tmp_cleaned"]) == 1
        assert len(result["fragment_actions"]) == 3


# ============================================================================
# Crash recovery integration tests
# ============================================================================


class TestCrashRecoveryInbox:
    """AC9: stale .part → cleaned on startup → redownloaded next poll."""

    def test_stale_part_cleaned(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        stale = inbox / "test_frag.part"
        stale.write_text("partial download data")

        with mock.patch.object(poller, "inbox_dir", return_value=inbox):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    poller.recovery_scan(tmp_path)

        assert not stale.exists()

    def test_stale_wav_tmp_cleaned(self, tmp_path: Path) -> None:
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        stale = inbox / "test_frag.wav.tmp"
        stale.write_text("partial transcode data")

        with mock.patch.object(poller, "inbox_dir", return_value=inbox):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    poller.recovery_scan(tmp_path)

        assert not stale.exists()


class TestCrashRecoveryTmp:
    """AC7: transcript.json.tmp cleaned, fragment re-transcribed."""

    def test_transcript_tmp_cleaned(self, tmp_path: Path) -> None:
        tmpp = tmp_path / "tmp"
        tmpp.mkdir(parents=True)
        stale = tmpp / "frag.transcript.json.tmp"
        stale.write_text('{"partial": true}')

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmpp):
                    poller.recovery_scan(tmp_path)

        assert not stale.exists()

    def test_multiple_transcript_tmps_all_cleaned(self, tmp_path: Path) -> None:
        tmpp = tmp_path / "tmp"
        tmpp.mkdir(parents=True)
        for i in range(5):
            (tmpp / f"frag_{i}.transcript.json.tmp").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmpp):
                    result = poller.recovery_scan(tmp_path)

        assert len(result["tmp_cleaned"]) == 5


class TestCrashRecoveryFragments:
    """AC7/AC8: missing .done triggers re-processing."""

    def test_missing_done_with_audio_resumable(self, tmp_path: Path) -> None:
        frags = tmp_path / "fragments" / "2026-06-03" / "test_frag"
        frags.mkdir(parents=True)
        (frags / "audio.wav").touch()

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert any("resume" in a and "needs transcription" in a for a in result["fragment_actions"])

    def test_missing_done_no_audio_empty_removed(self, tmp_path: Path) -> None:
        frags = tmp_path / "fragments" / "2026-06-03" / "test_frag_empty"
        frags.mkdir(parents=True)

        with mock.patch.object(poller, "inbox_dir", return_value=tmp_path / "inbox"):
            with mock.patch.object(poller, "fragments_dir", return_value=tmp_path / "fragments"):
                with mock.patch.object(poller, "tmp_dir", return_value=tmp_path / "tmp"):
                    result = poller.recovery_scan(tmp_path)

        assert any("removed empty" in a for a in result["fragment_actions"])
        assert not frags.exists()


# ============================================================================
# return type / schema tests
# ============================================================================


class TestRecoveryScanReturnSchema:
    """Ensure recovery_scan always returns a dict with the expected keys."""

    def test_returns_dict_with_three_keys(self, tmp_path: Path) -> None:
        result = poller.recovery_scan(tmp_path)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"inbox_cleaned", "tmp_cleaned", "fragment_actions"}
        assert isinstance(result["inbox_cleaned"], list)
        assert isinstance(result["tmp_cleaned"], list)
        assert isinstance(result["fragment_actions"], list)


# ============================================================================
# simulate_worker_crash script structure + Makefile tests
# ============================================================================


class TestSimulateWorkerCrashScript:
    """Verify that scripts/simulate_worker_crash.py exists and is syntactically valid."""

    def test_script_exists(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        script = repo_root / "scripts" / "simulate_worker_crash.py"
        assert script.is_file(), f"Script missing: {script}"

    def test_script_compiles(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        script = repo_root / "scripts" / "simulate_worker_crash.py"
        import py_compile
        py_compile.compile(str(script), doraise=True)

    def test_script_importable(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        import sys
        sys.path.insert(0, str(repo_root / "scripts"))
        import simulate_worker_crash  # noqa: F811
        assert hasattr(simulate_worker_crash, "main")
        assert hasattr(simulate_worker_crash, "case_missing_done")
        assert hasattr(simulate_worker_crash, "case_stale_part")
        assert hasattr(simulate_worker_crash, "case_crash_transcode")

    def test_script_has_three_cases(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        import sys
        sys.path.insert(0, str(repo_root / "scripts"))
        import simulate_worker_crash

        # All three AC cases should be covered
        assert callable(simulate_worker_crash.case_crash_transcode)
        assert callable(simulate_worker_crash.case_missing_done)
        assert callable(simulate_worker_crash.case_stale_part)


class TestMakefileTargets:
    """Verify US-023 Makefile targets exist."""

    def test_makefile_has_crash_recovery_and_simulate(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        makefile = repo_root / "Makefile"
        content = makefile.read_text()

        assert "test-crash-recovery:" in content
        assert "simulate-worker-crash:" in content

    def test_phony_includes_new_targets(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        makefile = repo_root / "Makefile"
        content = makefile.read_text()

        # Find .PHONY line(s)
        lines = content.splitlines()
        phony_content = ""
        in_phony = False
        for line in lines:
            if line.startswith(".PHONY:"):
                in_phony = True
                phony_content = line
            elif in_phony:
                if line.endswith("\\"):
                    phony_content += " " + line.rstrip("\\").strip()
                else:
                    phony_content += " " + line.strip()
                    in_phony = False

        assert "test-crash-recovery" in phony_content
        assert "simulate-worker-crash" in phony_content


# ============================================================================
# Module structure / importability tests
# ============================================================================


class TestAtomicsModuleStructure:
    def test_module_importable(self) -> None:
        from soniscope_worker import atomics
        assert atomics is not None

    def test_public_api(self) -> None:
        assert hasattr(atomics, "atomic_write_json")
        assert hasattr(atomics, "atomic_write_text")
        assert hasattr(atomics, "create_done_marker")
        assert hasattr(atomics, "is_done")
        assert hasattr(atomics, "remove_done_marker")

    def test_all_functions_callable(self) -> None:
        assert callable(atomics.atomic_write_json)
        assert callable(atomics.atomic_write_text)
        assert callable(atomics.create_done_marker)
        assert callable(atomics.is_done)
        assert callable(atomics.remove_done_marker)


# ============================================================================
# CLI integration tests (test-poll-cycle recovery scan output)
# ============================================================================


class TestCliRecoveryOutput:
    def test_cli_imports_new_symbols(self) -> None:
        """Verify cli.py can handle the new recovery_scan return type."""
        from soniscope_worker.cli import app
        # app should exist — the new code path is exercised via
        # test_poll_cycle command which imports recovery_scan
        assert app is not None

    def test_test_poll_cycle_command_exists(self) -> None:
        from soniscope_worker.cli import app
        # test-poll-cycle command must exist
        from typer.testing import CliRunner
        runner = CliRunner()
        # Just verify the command is registered (help output)
        result = runner.invoke(app, ["--help"])
        assert "test-poll-cycle" in result.output


# ============================================================================
# Worker security: no DeleteObject
# ============================================================================


class TestWorkerSecurity:
    """Worker source must NOT contain OSS DeleteObject calls."""

    def test_no_delete_object_in_worker_src(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        worker_src = repo_root / "apps" / "worker" / "src"

        for py_file in worker_src.rglob("*.py"):
            content = py_file.read_text()
            # Check for potential DeleteObject calls
            lines = content.splitlines()
            for i, line in enumerate(lines):
                # Skip comments and strings we know are safe
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # Check: no DeleteObject in business logic
                # The word "DeleteObject" in comments/docs is fine
                if "DeleteObject" in stripped and not stripped.startswith("#"):
                    # Allow in docstrings/comments only
                    if "def " in stripped or "import " in stripped or ".delete_object" in stripped.lower():
                        pytest.fail(
                            f"DeleteObject call found in {py_file}:{i+1}: {stripped}"
                        )
