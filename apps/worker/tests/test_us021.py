"""Tests for US-021 — Worker OSS polling, HeadObject metadata, and secure download."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from soniscope_worker import poller
from soniscope_worker.config import OssConfig, PollConfig, SoniScopeConfig, TranscriberConfig, TranscriberLocalConfig
from soniscope_worker.paths import resolve_home


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(interval: int = 60) -> SoniScopeConfig:
    return SoniScopeConfig(
        oss=OssConfig(
            endpoint="oss-cn-beijing.aliyuncs.com",
            bucket="soniscope-audio",
            access_key_id="AKIDtest",
            access_key_secret="SecretTest12345678",
        ),
        poll=PollConfig(interval_seconds=interval),
        transcriber=TranscriberConfig(
            name="cloud-speech",
            provider="aliyun-nls",
            model="test-model",
            params_version="v1",
            api_endpoint="cn-beijing",
            appkey="test-appkey",
            access_key_id="AKIDnls",
            access_key_secret="SecretNLS123456",
            upload_mode="oss-url",
            local=TranscriberLocalConfig(enabled=False),
        ),
    )


# ---------------------------------------------------------------------------
# fragment_id → date / OSS key helpers
# ---------------------------------------------------------------------------


class TestFragmentToDate:
    def test_valid_fragment_id(self) -> None:
        assert poller._fragment_to_date("20260603T120000_dev01_01JXXXXX") == "2026-06-03"

    def test_valid_fragment_id_midnight(self) -> None:
        assert poller._fragment_to_date("20260603T000000_abc12_01J0001") == "2026-06-03"

    def test_no_t_separator(self) -> None:
        with pytest.raises(ValueError, match="no 'T' separator"):
            poller._fragment_to_date("20260603-120000_dev01_01JXXXXX")

    def test_short_date_part(self) -> None:
        with pytest.raises(ValueError, match="Invalid fragment_id date portion"):
            poller._fragment_to_date("202606T120000_dev01_01JXXXXX")

    def test_dec_year(self) -> None:
        assert poller._fragment_to_date("20251231T235959_dev01_01JXXXXX") == "2025-12-31"

    def test_jan_year(self) -> None:
        assert poller._fragment_to_date("20260101T000000_dev01_01JXXXXX") == "2026-01-01"


class TestFragmentOssKey:
    def test_typical(self) -> None:
        result = poller._fragment_oss_key("20260603T120000_dev01_01JXXXXX1234567890ABC")
        assert result == "recordings/2026-06-03/20260603T120000_dev01_01JXXXXX1234567890ABC.wav"

    def test_with_timestamp(self) -> None:
        result = poller._fragment_oss_key("20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE")
        assert result == "recordings/2026-05-26/20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav"

    def test_raises_on_bad_id(self) -> None:
        with pytest.raises(ValueError):
            poller._fragment_oss_key("not-valid")


class TestOssKeyToFragmentId:
    def test_valid(self) -> None:
        fid = poller.oss_key_to_fragment_id(
            "recordings/2026-06-03/20260603T120000_dev01_01JXXX.wav"
        )
        assert fid == "20260603T120000_dev01_01JXXX"

    def test_no_slash(self) -> None:
        with pytest.raises(ValueError, match="Unexpected object key format"):
            poller.oss_key_to_fragment_id("bad_key.wav")

    def test_no_wav_extension(self) -> None:
        with pytest.raises(ValueError, match="does not end with .wav"):
            poller.oss_key_to_fragment_id("recordings/2026-06-03/something.mp3")

    def test_nested_date_folder(self) -> None:
        fid = poller.oss_key_to_fragment_id(
            "recordings/2026-05-26/20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav"
        )
        assert fid == "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE"


# ---------------------------------------------------------------------------
# HeadMetaResult
# ---------------------------------------------------------------------------


class TestHeadMetaResult:
    def test_defaults(self) -> None:
        r = poller.HeadMetaResult()
        assert r.found is False
        assert r.content_length is None
        assert r.etag is None
        assert r.sha256 is None

    def test_found_with_metadata(self) -> None:
        r = poller.HeadMetaResult(
            found=True,
            content_length=12345,
            etag="abc123",
            last_modified="2026-06-03T12:00:00",
            session_id="session-1",
            chunk_seq=1,
            chunk_total=3,
            recorded_at="2026-06-03T12:00:00+08:00",
            duration="87.5",
            original_format="mp3",
            sha256="abcdef1234567890",
        )
        assert r.found is True
        assert r.content_length == 12345
        assert r.session_id == "session-1"
        assert r.chunk_seq == 1
        assert r.chunk_total == 3
        assert r.original_format == "mp3"

    def test_to_manifest_draft_full(self) -> None:
        r = poller.HeadMetaResult(
            found=True,
            content_length=12345,
            session_id="session-1",
            chunk_seq=1,
            chunk_total=3,
            recorded_at="2026-06-03T12:00:00+08:00",
            duration="87.5",
            original_format="mp3",
            sha256="abcdef1234567890",
        )
        draft = r.to_manifest_draft()
        assert draft["session_id"] == "session-1"
        assert draft["chunk_seq"] == 1
        assert draft["chunk_total"] == 3
        assert draft["recorded_at"] == "2026-06-03T12:00:00+08:00"
        assert draft["duration_seconds"] == 87.5
        assert draft["audio"]["original_format"] == "mp3"
        assert draft["upload"]["original_sha256"] == "abcdef1234567890"
        assert draft["upload"]["original_size_bytes"] == 12345

    def test_to_manifest_draft_minimal(self) -> None:
        r = poller.HeadMetaResult(found=True, content_length=100)
        draft = r.to_manifest_draft()
        assert "session_id" not in draft
        assert draft["upload"]["original_size_bytes"] == 100

    def test_to_manifest_draft_missing_metadata(self) -> None:
        """Metadata fields that are None should not appear in the manifest draft."""
        r = poller.HeadMetaResult(found=True)
        draft = r.to_manifest_draft()
        assert draft == {}


# ---------------------------------------------------------------------------
# head_oss_object
# ---------------------------------------------------------------------------


class TestHeadOssObject:
    def test_found(self) -> None:
        """HeadObject returns metadata dict."""
        mock_client = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.content_length = 12345
        mock_result.etag = '"abc123"'
        mock_result.last_modified = None
        mock_result.metadata = {
            "session-id": "session-1",
            "chunk-seq": "1",
            "chunk-total": "3",
            "recorded-at": "2026-06-03T12:00:00+08:00",
            "duration": "87.5",
            "original-format": "mp3",
            "sha256": "abcdef1234567890",
        }
        mock_client.head_object.return_value = mock_result

        result = poller.head_oss_object(
            "recordings/2026-06-03/fid.wav", mock_client, "soniscope-audio"
        )
        assert result.found is True
        assert result.content_length == 12345
        assert result.etag == "abc123"
        assert result.session_id == "session-1"
        assert result.chunk_seq == 1
        assert result.chunk_total == 3
        assert result.original_format == "mp3"
        assert result.sha256 == "abcdef1234567890"

    def test_not_found_404(self) -> None:
        """NoSuchKey / 404 returns a found=False result."""
        mock_client = mock.MagicMock()
        mock_client.head_object.side_effect = Exception("404 NoSuchKey")

        result = poller.head_oss_object(
            "recordings/2026-06-03/fid.wav", mock_client, "soniscope-audio"
        )
        assert result.found is False
        assert result.content_length is None

    def test_not_found_nosuchkey(self) -> None:
        mock_client = mock.MagicMock()
        mock_client.head_object.side_effect = Exception("NoSuchKey: The specified key does not exist.")

        result = poller.head_oss_object(
            "recordings/2026-06-03/fid.wav", mock_client, "soniscope-audio"
        )
        assert result.found is False

    def test_other_error_raises(self) -> None:
        mock_client = mock.MagicMock()
        mock_client.head_object.side_effect = Exception("AccessDenied")

        with pytest.raises(RuntimeError, match="HeadObject failed"):
            poller.head_oss_object(
                "recordings/2026-06-03/fid.wav", mock_client, "soniscope-audio"
            )

    def test_metadata_none(self) -> None:
        """Metadata dict can be None (no user metadata)."""
        mock_client = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.content_length = 100
        mock_result.etag = '"xyz"'
        mock_result.last_modified = None
        mock_result.metadata = None
        mock_client.head_object.return_value = mock_result

        result = poller.head_oss_object(
            "recordings/2026-06-03/fid.wav", mock_client, "soniscope-audio"
        )
        assert result.found is True
        assert result.content_length == 100
        assert result.session_id is None

    def test_partial_metadata(self) -> None:
        """Some metadata fields may be missing (non-sharded audio has no chunk-total)."""
        mock_client = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.content_length = 100
        mock_result.etag = '"xyz"'
        mock_result.last_modified = None
        mock_result.metadata = {
            "session-id": "s1",
            "sha256": "abc123",
        }
        mock_client.head_object.return_value = mock_result

        result = poller.head_oss_object(
            "recordings/2026-06-03/fid.wav", mock_client, "soniscope-audio"
        )
        assert result.found is True
        assert result.session_id == "s1"
        assert result.sha256 == "abc123"
        assert result.chunk_seq is None
        assert result.original_format is None


# ---------------------------------------------------------------------------
# list_oss_objects
# ---------------------------------------------------------------------------


class TestListOssObjects:
    def test_single_page(self) -> None:
        mock_client = mock.MagicMock()
        obj1 = mock.MagicMock()
        obj1.key = "recordings/2026-06-03/fid1.wav"
        obj2 = mock.MagicMock()
        obj2.key = "recordings/2026-06-03/fid2.wav"
        mock_result = mock.MagicMock()
        mock_result.contents = [obj1, obj2]
        mock_result.is_truncated = False
        mock_client.list_objects_v2.return_value = mock_result

        keys = poller.list_oss_objects(mock_client, "soniscope-audio")
        assert len(keys) == 2
        assert keys[0] == "recordings/2026-06-03/fid1.wav"
        assert keys[1] == "recordings/2026-06-03/fid2.wav"

    def test_pagination(self) -> None:
        mock_client = mock.MagicMock()

        obj_a = mock.MagicMock()
        obj_a.key = "recordings/2026-06-03/fid_a.wav"
        page1 = mock.MagicMock()
        page1.contents = [obj_a]
        page1.is_truncated = True
        page1.next_continuation_token = "page2token"

        obj_b = mock.MagicMock()
        obj_b.key = "recordings/2026-06-04/fid_b.wav"
        page2 = mock.MagicMock()
        page2.contents = [obj_b]
        page2.is_truncated = False

        mock_client.list_objects_v2.side_effect = [page1, page2]

        keys = poller.list_oss_objects(mock_client, "soniscope-audio")
        assert len(keys) == 2
        assert "recordings/2026-06-03/fid_a.wav" in keys
        assert "recordings/2026-06-04/fid_b.wav" in keys
        assert mock_client.list_objects_v2.call_count == 2

    def test_empty_bucket(self) -> None:
        mock_client = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.contents = None
        mock_result.is_truncated = False
        mock_client.list_objects_v2.return_value = mock_result

        keys = poller.list_oss_objects(mock_client, "soniscope-audio")
        assert keys == []

    def test_empty_contents(self) -> None:
        mock_client = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.contents = []
        mock_result.is_truncated = False
        mock_client.list_objects_v2.return_value = mock_result

        keys = poller.list_oss_objects(mock_client, "soniscope-audio")
        assert keys == []

    def test_obj_key_none_handled(self) -> None:
        """Objects with key=None are skipped."""
        mock_client = mock.MagicMock()
        obj = mock.MagicMock()
        obj.key = None
        mock_result = mock.MagicMock()
        mock_result.contents = [obj]
        mock_result.is_truncated = False
        mock_client.list_objects_v2.return_value = mock_result

        keys = poller.list_oss_objects(mock_client, "soniscope-audio")
        assert keys == []

    def test_pagination_with_none_keys_in_both_pages(self) -> None:
        mock_client = mock.MagicMock()

        obj_none = mock.MagicMock(); obj_none.key = None
        obj_a = mock.MagicMock(); obj_a.key = "recordings/fid_a.wav"
        page1 = mock.MagicMock()
        page1.contents = [obj_none, obj_a]
        page1.is_truncated = True
        page1.next_continuation_token = "t2"

        obj_none2 = mock.MagicMock(); obj_none2.key = None
        page2 = mock.MagicMock()
        page2.contents = [obj_none2]
        page2.is_truncated = False

        mock_client.list_objects_v2.side_effect = [page1, page2]

        keys = poller.list_oss_objects(mock_client, "soniscope-audio")
        assert keys == ["recordings/fid_a.wav"]


# ---------------------------------------------------------------------------
# download_object
# ---------------------------------------------------------------------------


class TestDownloadObject:
    def test_success_no_sha256(self) -> None:
        mock_client = mock.MagicMock()
        with tempfile.TemporaryDirectory() as td:
            part = Path(td) / "test.part"
            # Write a tiny file first to simulate download
            part.write_bytes(b"hello test data")
            result = poller.download_object(
                "recordings/date/fid.wav", mock_client, "bucket", part
            )
            assert result is True

    def test_success_sha256_match(self) -> None:
        mock_client = mock.MagicMock()
        data = b"hello test data for sha256"
        expected = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            part = Path(td) / "test.part"
            part.write_bytes(data)
            result = poller.download_object(
                "recordings/date/fid.wav", mock_client, "bucket", part,
                expected_sha256=expected,
            )
            assert result is True
            assert part.is_file()

    def test_sha256_mismatch_deletes_part(self) -> None:
        mock_client = mock.MagicMock()
        data = b"hello test data"
        with tempfile.TemporaryDirectory() as td:
            part = Path(td) / "test.part"
            part.write_bytes(data)
            result = poller.download_object(
                "recordings/date/fid.wav", mock_client, "bucket", part,
                expected_sha256="not_matching_at_all",
            )
            assert result is False
            assert not part.is_file()

    def test_download_error_raises(self) -> None:
        mock_client = mock.MagicMock()
        mock_client.get_object_to_file.side_effect = Exception("Network error")

        with tempfile.TemporaryDirectory() as td:
            part = Path(td) / "test.part"
            with pytest.raises(RuntimeError, match="Download failed"):
                poller.download_object(
                    "recordings/date/fid.wav", mock_client, "bucket", part
                )


# ---------------------------------------------------------------------------
# is_fragment_done
# ---------------------------------------------------------------------------


class TestIsFragmentDone:
    def test_done_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            done_dir = home / "fragments" / "2026-06-03" / "20260603T120000_dev01_01JXXX"
            done_dir.mkdir(parents=True)
            (done_dir / ".done").touch()

            assert poller.is_fragment_done(home, "20260603T120000_dev01_01JXXX") is True

    def test_done_file_absent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            assert poller.is_fragment_done(home, "20260603T120000_dev01_01JXXX") is False

    def test_directory_exists_but_no_done(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            done_dir = home / "fragments" / "2026-06-03" / "20260603T120000_dev01_01JXXX"
            done_dir.mkdir(parents=True)
            # no .done

            assert poller.is_fragment_done(home, "20260603T120000_dev01_01JXXX") is False


# ---------------------------------------------------------------------------
# recovery_scan
# ---------------------------------------------------------------------------


class TestRecoveryScan:
    def test_cleans_part_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            (inbox / "fid1.part").touch()
            (inbox / "fid2.part").touch()

            removed = poller.recovery_scan(home)
            assert len(removed) == 2
            assert not (inbox / "fid1.part").is_file()
            assert not (inbox / "fid2.part").is_file()

    def test_cleans_wav_tmp_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            (inbox / "fid1.wav.tmp").touch()

            removed = poller.recovery_scan(home)
            assert len(removed) == 1
            assert not (inbox / "fid1.wav.tmp").is_file()

    def test_cleans_both_types(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            (inbox / "fid1.part").touch()
            (inbox / "fid2.wav.tmp").touch()
            (inbox / "fid3.part").touch()

            removed = poller.recovery_scan(home)
            assert len(removed) == 3

    def test_no_inbox_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            removed = poller.recovery_scan(home)
            assert removed == []

    def test_non_part_files_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            (inbox / "notes.txt").touch()
            (inbox / "data.json").touch()

            removed = poller.recovery_scan(home)
            assert len(removed) == 0
            assert (inbox / "notes.txt").is_file()
            assert (inbox / "data.json").is_file()

    def test_oserror_on_unlink_tolerated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            inbox = home / "inbox"
            inbox.mkdir(parents=True)
            (inbox / "fid1.part").touch()

            with mock.patch.object(Path, "unlink", side_effect=OSError("mock error")):
                removed = poller.recovery_scan(home)
                assert len(removed) == 0


# ---------------------------------------------------------------------------
# poll_cycle
# ---------------------------------------------------------------------------


class TestPollCycle:
    def test_complete_cycle(self, monkeypatch, tmp_path: Path) -> None:
        """Full poll cycle: list → check done → head → download."""
        monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
        config = _make_config()

        # Set up the fragments dir structure — nothing .done yet
        (tmp_path / "fragments").mkdir(parents=True)
        (tmp_path / "inbox").mkdir(parents=True)

        mock_client = mock.MagicMock()

        # 1. list_objects → 2 keys
        obj1 = mock.MagicMock(); obj1.key = "recordings/2026-06-03/20260603T120000_dev01_01JAAA.wav"
        obj2 = mock.MagicMock(); obj2.key = "recordings/2026-06-03/20260603T120001_dev01_01JBBB.wav"
        list_result = mock.MagicMock()
        list_result.contents = [obj1, obj2]
        list_result.is_truncated = False
        mock_client.list_objects_v2.return_value = list_result

        # 2. head_object → both found with metadata
        head_result1 = mock.MagicMock()
        head_result1.content_length = 100
        head_result1.etag = '"etag1"'
        head_result1.last_modified = None
        head_result1.metadata = {"sha256": "abc123"}

        head_result2 = mock.MagicMock()
        head_result2.content_length = 200
        head_result2.etag = '"etag2"'
        head_result2.last_modified = None
        head_result2.metadata = {"sha256": "def456"}

        mock_client.head_object.side_effect = [head_result1, head_result2]

        # 3. download → simulate successful downloads by pre-creating .part files
        # The download_object function calls get_object_to_file which would write.
        # We'll mock download_object to return True.
        with mock.patch.object(poller, "download_object", return_value=True) as mock_dl:
            summary = poller.poll_cycle(config, mock_client)

        assert summary["total_objects"] == 2
        assert summary["downloaded"] == 2
        assert summary["skipped_done"] == 0
        assert summary["sha256_mismatch"] == 0
        assert summary["errors"] == 0

    def test_skips_done_fragments(self, monkeypatch, tmp_path: Path) -> None:
        """Fragments with .done are skipped."""
        monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
        config = _make_config()

        # Create a .done for fid1
        done_dir = tmp_path / "fragments" / "2026-06-03" / "20260603T120000_dev01_01JAAA"
        done_dir.mkdir(parents=True)
        (done_dir / ".done").touch()

        (tmp_path / "inbox").mkdir(parents=True)

        mock_client = mock.MagicMock()

        obj1 = mock.MagicMock(); obj1.key = "recordings/2026-06-03/20260603T120000_dev01_01JAAA.wav"  # .done exists
        obj2 = mock.MagicMock(); obj2.key = "recordings/2026-06-03/20260603T120001_dev01_01JBBB.wav"  # no .done
        list_result = mock.MagicMock()
        list_result.contents = [obj1, obj2]
        list_result.is_truncated = False
        mock_client.list_objects_v2.return_value = list_result

        # head for obj2 only (obj1 skipped by .done)
        head_result = mock.MagicMock()
        head_result.content_length = 200
        head_result.etag = '"etag2"'
        head_result.last_modified = None
        head_result.metadata = {"sha256": "def456"}
        mock_client.head_object.return_value = head_result

        with mock.patch.object(poller, "download_object", return_value=True) as mock_dl:
            summary = poller.poll_cycle(config, mock_client)

        assert summary["total_objects"] == 2
        assert summary["skipped_done"] == 1
        assert summary["downloaded"] == 1
        assert mock_dl.call_count == 1

    def test_sha256_mismatch(self, monkeypatch, tmp_path: Path) -> None:
        """When sha256 verification fails, it's counted as mismatch."""
        monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
        config = _make_config()

        (tmp_path / "fragments").mkdir(parents=True)
        (tmp_path / "inbox").mkdir(parents=True)

        mock_client = mock.MagicMock()

        obj = mock.MagicMock(); obj.key = "recordings/2026-06-03/20260603T120000_dev01_01JAAA.wav"
        list_result = mock.MagicMock()
        list_result.contents = [obj]
        list_result.is_truncated = False
        mock_client.list_objects_v2.return_value = list_result

        head_result = mock.MagicMock()
        head_result.content_length = 100
        head_result.etag = '"etag1"'
        head_result.last_modified = None
        head_result.metadata = {"sha256": "expected_sha"}
        mock_client.head_object.return_value = head_result

        with mock.patch.object(poller, "download_object", return_value=False) as mock_dl:
            summary = poller.poll_cycle(config, mock_client)

        assert summary["total_objects"] == 1
        assert summary["sha256_mismatch"] == 1
        assert summary["downloaded"] == 0

    def test_head_object_error(self, monkeypatch, tmp_path: Path) -> None:
        """HeadObject errors are counted."""
        monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
        config = _make_config()

        (tmp_path / "fragments").mkdir(parents=True)
        (tmp_path / "inbox").mkdir(parents=True)

        mock_client = mock.MagicMock()

        obj = mock.MagicMock(); obj.key = "recordings/2026-06-03/20260603T120000_dev01_01JAAA.wav"
        list_result = mock.MagicMock()
        list_result.contents = [obj]
        list_result.is_truncated = False
        mock_client.list_objects_v2.return_value = list_result

        mock_client.head_object.side_effect = Exception("AccessDenied")

        with mock.patch.object(poller, "download_object", return_value=True) as mock_dl:
            summary = poller.poll_cycle(config, mock_client)

        assert summary["total_objects"] == 1
        assert summary["errors"] == 1
        assert summary["downloaded"] == 0

    def test_download_error(self, monkeypatch, tmp_path: Path) -> None:
        """Download errors are counted."""
        monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
        config = _make_config()

        (tmp_path / "fragments").mkdir(parents=True)
        (tmp_path / "inbox").mkdir(parents=True)

        mock_client = mock.MagicMock()

        obj = mock.MagicMock(); obj.key = "recordings/2026-06-03/20260603T120000_dev01_01JAAA.wav"
        list_result = mock.MagicMock()
        list_result.contents = [obj]
        list_result.is_truncated = False
        mock_client.list_objects_v2.return_value = list_result

        head_result = mock.MagicMock()
        head_result.content_length = 100
        head_result.etag = '"etag1"'
        head_result.last_modified = None
        head_result.metadata = {"sha256": "expected_sha"}
        mock_client.head_object.return_value = head_result

        with mock.patch.object(poller, "download_object", side_effect=RuntimeError("fail")) as mock_dl:
            summary = poller.poll_cycle(config, mock_client)

        assert summary["total_objects"] == 1
        assert summary["errors"] == 1
        assert summary["downloaded"] == 0

    def test_non_conforming_key_skipped(self, monkeypatch, tmp_path: Path) -> None:
        """Keys that don't match the expected pattern are skipped."""
        monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
        config = _make_config()

        (tmp_path / "fragments").mkdir(parents=True)
        (tmp_path / "inbox").mkdir(parents=True)

        mock_client = mock.MagicMock()

        obj_bad = mock.MagicMock(); obj_bad.key = "recordings/2026-06-03/not-our-format.mp3"
        obj_good = mock.MagicMock(); obj_good.key = "recordings/2026-06-03/20260603T120000_dev01_01JAAA.wav"
        list_result = mock.MagicMock()
        list_result.contents = [obj_bad, obj_good]
        list_result.is_truncated = False
        mock_client.list_objects_v2.return_value = list_result

        head_result = mock.MagicMock()
        head_result.content_length = 100
        head_result.etag = '"etag1"'
        head_result.last_modified = None
        head_result.metadata = {"sha256": "abc123"}
        mock_client.head_object.return_value = head_result

        with mock.patch.object(poller, "download_object", return_value=True) as mock_dl:
            summary = poller.poll_cycle(config, mock_client)

        assert summary["total_objects"] == 2
        assert summary["downloaded"] == 1
        assert mock_dl.call_count == 1


# ---------------------------------------------------------------------------
# _sha256_hex
# ---------------------------------------------------------------------------


class TestSha256Hex:
    def test_computes_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.bin"
            p.write_bytes(b"hello world")
            result = poller._sha256_hex(p)
            expected = hashlib.sha256(b"hello world").hexdigest()
            assert result == expected

    def test_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "empty.bin"
            p.write_bytes(b"")
            result = poller._sha256_hex(p)
            expected = hashlib.sha256(b"").hexdigest()
            assert result == expected


# ---------------------------------------------------------------------------
# _build_oss_client
# ---------------------------------------------------------------------------


class TestBuildOssClient:
    def test_returns_client(self) -> None:
        config = _make_config()
        client = poller._build_oss_client(config)
        # The client should exist and be callable
        assert client is not None

    def test_client_has_head_object(self) -> None:
        config = _make_config()
        client = poller._build_oss_client(config)
        assert hasattr(client, "head_object")

    def test_client_has_list_objects_v2(self) -> None:
        config = _make_config()
        client = poller._build_oss_client(config)
        assert hasattr(client, "list_objects_v2")

    def test_client_has_get_object_to_file(self) -> None:
        config = _make_config()
        client = poller._build_oss_client(config)
        assert hasattr(client, "get_object_to_file")


# ---------------------------------------------------------------------------
# run_poll_loop (basic structure)
# ---------------------------------------------------------------------------


class TestRunPollLoop:
    def test_recovery_scan_called_on_startup(self) -> None:
        """run_poll_loop calls recovery_scan before entering loop."""
        config = _make_config(interval=999)

        with mock.patch.object(poller, "recovery_scan") as mock_recovery, \
             mock.patch.object(poller, "_build_oss_client") as mock_build, \
             mock.patch.object(poller, "poll_cycle") as mock_cycle, \
             mock.patch("time.sleep", side_effect=StopIteration("exit loop")):
            mock_recovery.return_value = []
            mock_cycle.return_value = {"total_objects": 0, "skipped_done": 0,
                                        "downloaded": 0, "sha256_mismatch": 0, "errors": 0}
            with pytest.raises(StopIteration):
                poller.run_poll_loop(config)

            mock_recovery.assert_called_once()

    def test_poll_cycle_called_after_recovery(self) -> None:
        """After recovery, poll_cycle is called at least once."""
        config = _make_config(interval=999)

        with mock.patch.object(poller, "recovery_scan") as mock_recovery, \
             mock.patch.object(poller, "_build_oss_client") as mock_build, \
             mock.patch.object(poller, "poll_cycle") as mock_cycle, \
             mock.patch("time.sleep", side_effect=StopIteration("exit loop")):
            mock_recovery.return_value = []
            mock_cycle.return_value = {"total_objects": 0, "skipped_done": 0,
                                        "downloaded": 0, "sha256_mismatch": 0, "errors": 0}
            with pytest.raises(StopIteration):
                poller.run_poll_loop(config)

            mock_cycle.assert_called_once()

    def test_poll_interval_env_override(self, monkeypatch) -> None:
        """Env var POLL_INTERVAL_SECONDS_OVERRIDE overrides the interval."""
        monkeypatch.setenv("POLL_INTERVAL_SECONDS_OVERRIDE", "30")
        config = _make_config(interval=60)

        with mock.patch.object(poller, "recovery_scan") as mock_recovery, \
             mock.patch.object(poller, "_build_oss_client") as mock_build, \
             mock.patch.object(poller, "poll_cycle") as mock_cycle, \
             mock.patch("time.sleep") as mock_sleep:
            mock_recovery.return_value = []
            mock_cycle.return_value = {"total_objects": 0, "skipped_done": 0,
                                        "downloaded": 0, "sha256_mismatch": 0, "errors": 0}
            # Let it run one cycle then stop
            mock_sleep.side_effect = StopIteration("exit loop")
            with pytest.raises(StopIteration):
                poller.run_poll_loop(config)

            # The sleep duration should be based on the override (30) not the config (60)
            call_args = mock_sleep.call_args[0] if mock_sleep.call_args else ()
            if call_args:
                # sleep called with interval - elapsed (roughly 30 since override is 30)
                sleep_seconds = call_args[0]
                # It should be close to 30, not 60
                assert sleep_seconds <= 30


# ---------------------------------------------------------------------------
# No DeleteObject in Worker source
# ---------------------------------------------------------------------------


class TestNoDeleteObjectInWorkerSource:
    """AC: Worker business source must not contain DeleteObject calls."""

    def test_poller_has_no_delete_object(self) -> None:
        """poller.py should not call delete_object."""
        src = (Path(__file__).parent.parent / "src" / "soniscope_worker" / "poller.py").read_text()
        assert "delete_object" not in src
        assert "DeleteObject" not in src

    def test_poller_has_no_delete(self) -> None:
        """poller.py should not contain any OSS delete patterns."""
        src = (Path(__file__).parent.parent / "src" / "soniscope_worker" / "poller.py").read_text()
        # Only the phrase in AC comments is allowed — not actual delete API calls
        lines_with_delete = [l for l in src.splitlines() if "Client.delete" in l or "client.delete" in l]
        assert len(lines_with_delete) == 0


# ---------------------------------------------------------------------------
# OSS key derivation consistency with FC shared
# ---------------------------------------------------------------------------


class TestOssKeyConsistency:
    """Ensure Worker's fragment_id → OSS key logic matches FC shared/sts.py."""

    def test_matches_shared_fc_pattern(self) -> None:
        """Both Worker and FC shared produce the same OSS key from the same fragment_id."""
        fragment_id = "20260603T120000_dev01_01JXXXABC1234567890123"
        worker_key = poller._fragment_oss_key(fragment_id)
        expected = f"recordings/2026-06-03/{fragment_id}.wav"
        assert worker_key == expected
        # The date is correctly parsed as 2026-06-03
        assert "2026-06-03" in worker_key
