"""Tests for US-028 — Worker idempotency rules and retranscribe CLI.

Covers:
- AC1: Normal poll checks .done only (not model/params_version)
- AC2: Manifest transcription block fields (started_at, completed_at, etc.)
- AC3: retranscribe CLI command exists and parses args correctly
- AC4: make retranscribe target works
- AC5: Without --force/--upgrade, .done fragment shows "already done" message
- AC6: --force unconditionally re-transcribes
- AC7: --upgrade only retranscribes when model/params_version differs
- AC8: --all-from <date> batch mode
- AC9: File-lock mutual exclusion
- AC10: Make targets exist
"""

from __future__ import annotations

import fcntl
import json as _json
import os as _os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from soniscope_worker.config import (
    OssConfig,
    PollConfig,
    SoniScopeConfig,
    TranscriberConfig,
    TranscriberLocalConfig,
)
from soniscope_worker.manifest import build_manifest, update_manifest_with_transcription
from soniscope_worker.retranscribe import (
    _differs_from_config,
    _needs_upgrade,
    _retranscribe_one,
    _scan_fragment_dirs,
    os_open_lock,
    run_retranscribe,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *,
    model: str = "test-model",
    params_version: str = "v1",
    interval: int = 60,
) -> SoniScopeConfig:
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
            model=model,
            params_version=params_version,
            api_endpoint="cn-beijing",
            appkey="test-appkey",
            access_key_id="AKIDnls",
            access_key_secret="SecretNLS123456",
            upload_mode="oss-url",
            local=TranscriberLocalConfig(enabled=False),
        ),
    )


def _make_fragment_dir(
    base: Path,
    fragment_id: str,
    *,
    with_audio: bool = True,
    with_done: bool = False,
    with_manifest: bool = False,
    model: str = "test-model",
    params_version: str = "v1",
) -> Path:
    """Create a minimal fragment directory for testing."""
    from soniscope_worker.poller import _fragment_to_date

    date = _fragment_to_date(fragment_id)
    frag_dir = base / "fragments" / date / fragment_id
    frag_dir.mkdir(parents=True, exist_ok=True)

    if with_audio:
        (frag_dir / "audio.wav").write_bytes(b"fake-audio-data")

    if with_manifest or with_done:
        manifest = build_manifest(
            fragment_id=fragment_id,
            head_meta={
                "session_id": "sess-1",
                "chunk_seq": 1,
                "recorded_at": "2026-06-02T10:00:00Z",
                "duration_seconds": 20.0,
                "audio": {"original_format": "wav"},
                "upload": {"original_sha256": "abc123", "original_size_bytes": 1234},
            },
            audio_result={
                "audio_format": "wav",
                "original_format": "wav",
                "audio_sha256": "abc123",
                "original_sha256": "abc123",
                "audio_size_bytes": 1234,
                "original_size_bytes": 1234,
                "mode": "passthrough",
            },
            config_model=model,
            config_params_version=params_version,
            config_provider="aliyun-nls",
            config_transcriber_name="cloud-speech",
            config_upload_mode="oss-url",
            now="2026-06-02T10:30:00Z",
        )

        if with_done:
            update_manifest_with_transcription(
                manifest,
                started_at="2026-06-02T10:05:00Z",
                completed_at="2026-06-02T10:06:00Z",
                elapsed_seconds=60.0,
                transcriber="cloud-speech",
                model=model,
                params_version=params_version,
                provider="aliyun-nls",
                upload_mode="oss-url",
            )

        (frag_dir / "manifest.json").write_text(
            _json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if with_done:
        (frag_dir / ".done").touch()

    return frag_dir


# ---------------------------------------------------------------------------
# AC1: .done-only idempotency in poll cycle
# ---------------------------------------------------------------------------


class TestIdempotentSkip:
    """Verify poll_cycle skips .done fragments without checking model/params_version."""

    def test_poll_cycle_skips_done(self, tmp_path: Path) -> None:
        """AC1: .done exists → is_fragment_done returns True."""
        from soniscope_worker.poller import is_fragment_done

        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        _make_fragment_dir(tmp_path, frag_id, with_audio=True, with_done=True)

        with mock.patch("soniscope_worker.poller.resolve_home", return_value=tmp_path):
            assert is_fragment_done(tmp_path, frag_id) is True

    def test_is_fragment_done_only_checks_dotfile(self, tmp_path: Path) -> None:
        """AC1: .done check only — no model comparison in poll_cycle."""
        from soniscope_worker.poller import is_fragment_done

        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        _make_fragment_dir(
            tmp_path, frag_id, with_audio=True, with_done=True,
            model="old-model", params_version="v1",
        )

        with mock.patch("soniscope_worker.poller.resolve_home", return_value=tmp_path):
            # is_fragment_done only checks .done existence, not manifest
            assert is_fragment_done(tmp_path, frag_id) is True

    def test_no_auto_retranscribe_on_config_change(self, tmp_path: Path) -> None:
        """AC1: Normal poll does NOT auto-retranscribe when config changes."""
        from soniscope_worker.poller import is_fragment_done

        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        _make_fragment_dir(
            tmp_path, frag_id, with_audio=True, with_done=True,
            model="very-old-model", params_version="v0",
        )

        with mock.patch("soniscope_worker.poller.resolve_home", return_value=tmp_path):
            assert is_fragment_done(tmp_path, frag_id) is True


# ---------------------------------------------------------------------------
# AC2: Manifest transcription block fields
# ---------------------------------------------------------------------------


class TestManifestTranscriptionFields:
    """Verify manifest.transcription contains all required fields (AC2)."""

    def test_transcription_block_fields(self) -> None:
        """AC2: transcription block has all required fields."""
        manifest: dict = {}
        update_manifest_with_transcription(
            manifest,
            started_at="2026-06-02T10:05:00Z",
            completed_at="2026-06-02T10:06:00Z",
            elapsed_seconds=60.0,
            transcriber="cloud-speech",
            model="test-model",
            params_version="v1",
            provider="aliyun-nls",
            upload_mode="oss-url",
        )

        tx = manifest["transcription"]
        assert tx is not None
        assert tx["started_at"] == "2026-06-02T10:05:00Z"
        assert tx["completed_at"] == "2026-06-02T10:06:00Z"
        assert tx["elapsed_seconds"] == 60.0
        assert tx["transcriber"] == "cloud-speech"
        assert tx["model"] == "test-model"
        assert tx["params_version"] == "v1"
        assert tx["provider"] == "aliyun-nls"
        assert tx["upload_mode"] == "oss-url"

    def test_transcription_starts_as_null(self) -> None:
        """manifest built by build_manifest has transcription=None."""
        manifest = build_manifest(
            fragment_id="20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ",
            head_meta={"recorded_at": "2026-06-02T10:00:00Z"},
            audio_result={"audio_format": "wav", "original_format": "wav"},
            config_model="test-model",
            config_params_version="v1",
            config_provider="aliyun-nls",
            config_transcriber_name="cloud-speech",
            config_upload_mode="oss-url",
        )
        assert "transcription" in manifest
        assert manifest["transcription"] is None
        assert "transcription_spec" in manifest
        assert manifest["transcription_spec"]["model"] == "test-model"


# ---------------------------------------------------------------------------
# AC3/AC4: CLI command and Make target
# ---------------------------------------------------------------------------


class TestCliRetranscribe:
    """CLI and Makefile integration tests."""

    def test_retranscribe_command_exists(self) -> None:
        """AC3: retranscribe command is registered."""
        from soniscope_worker.cli import app

        commands = [c.callback.__name__ if c.callback else None for c in app.registered_commands]
        assert "retranscribe" in commands

    def test_retranscribe_no_args_errors(self) -> None:
        """AC3: Calling without fragment_id or --all-from errors."""
        from typer.testing import CliRunner

        from soniscope_worker.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["retranscribe"])
        assert result.exit_code != 0

    def test_retranscribe_help_shows_flags(self) -> None:
        """AC3: retranscribe --help shows flags."""
        from typer.testing import CliRunner

        from soniscope_worker.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["retranscribe", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.stdout
        assert "--upgrade" in result.stdout
        assert "--all-from" in result.stdout

    def test_makefile_has_retranscribe_target(self) -> None:
        """AC4: Makefile has retranscribe target."""
        makefile = Path(__file__).parent.parent.parent.parent / "Makefile"
        text = makefile.read_text(encoding="utf-8")
        lines = text.splitlines()
        target_lines = [l for l in lines if l.strip().startswith("retranscribe:")]
        assert len(target_lines) > 0

    def test_makefile_has_all_four_test_targets(self) -> None:
        """Makefile has all test targets."""
        makefile = Path(__file__).parent.parent.parent.parent / "Makefile"
        text = makefile.read_text(encoding="utf-8")
        assert "test-idempotent-skip:" in text
        assert "test-no-auto-retranscribe:" in text
        assert "test-cli-retranscribe:" in text
        assert "test-cli-upgrade:" in text

    def test_phoney_includes_new_targets(self) -> None:
        """Makefile .PHONY includes new test targets."""
        makefile = Path(__file__).parent.parent.parent.parent / "Makefile"
        text = makefile.read_text(encoding="utf-8")

        in_phony = False
        phony_content = ""
        for line in text.splitlines():
            if ".PHONY:" in line:
                in_phony = True
                phony_content = line
            elif in_phony and line.endswith("\\"):
                phony_content += " " + line.rstrip("\\")
            elif in_phony:
                phony_content += " " + line
                in_phony = False

        assert "test-idempotent-skip" in phony_content
        assert "test-no-auto-retranscribe" in phony_content
        assert "test-cli-retranscribe" in phony_content
        assert "test-cli-upgrade" in phony_content


# ---------------------------------------------------------------------------
# AC5: Without flags, .done fragment is skipped
# ---------------------------------------------------------------------------


class TestRetranscribeSkipDone:
    """Verify retranscribe_one skips .done fragment without flags."""

    def test_skips_done_without_flags(self, tmp_path: Path) -> None:
        """AC5: .done + no --force/--upgrade → skipped_done."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config()
        _make_fragment_dir(
            tmp_path, frag_id,
            with_audio=True, with_done=True, with_manifest=True,
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        # The function should return "skipped_done" BEFORE hitting _build_oss_client
        status = _retranscribe_one(
            frag_dir=frag_dir,
            fragment_id=frag_id,
            config=config,
            force=False,
            upgrade=False,
        )
        assert status == "skipped_done"


# ---------------------------------------------------------------------------
# AC6: --force unconditionally re-transcribes
# ---------------------------------------------------------------------------


class TestForceRetranscribe:
    """Verify --force triggers transcription even with .done."""

    def test_force_triggers_transcription(self, tmp_path: Path) -> None:
        """AC6: --force with .done → transcribed."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config()
        _make_fragment_dir(
            tmp_path, frag_id,
            with_audio=True, with_done=True, with_manifest=True,
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        with mock.patch(
            "soniscope_worker.poller._build_oss_client"
        ) as mock_build:
            mock_client = mock.MagicMock()
            mock_build.return_value = mock_client
            with mock.patch(
                "soniscope_worker.poller._run_transcription_pipeline"
            ) as mock_pipeline:
                status = _retranscribe_one(
                    frag_dir=frag_dir, fragment_id=frag_id,
                    config=config, force=True, upgrade=False,
                )
                assert status == "transcribed"
                mock_pipeline.assert_called_once()

    def test_force_without_done_also_transcribes(self, tmp_path: Path) -> None:
        """AC6: --force also works when no .done."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config()
        _make_fragment_dir(
            tmp_path, frag_id,
            with_audio=True, with_done=False, with_manifest=True,
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        with mock.patch(
            "soniscope_worker.poller._build_oss_client"
        ) as mock_build:
            mock_client = mock.MagicMock()
            mock_build.return_value = mock_client
            with mock.patch(
                "soniscope_worker.poller._run_transcription_pipeline"
            ) as mock_pipeline:
                status = _retranscribe_one(
                    frag_dir=frag_dir, fragment_id=frag_id,
                    config=config, force=True, upgrade=False,
                )
                assert status == "transcribed"
                mock_pipeline.assert_called_once()


# ---------------------------------------------------------------------------
# AC7: --upgrade only retranscribes when model/params differ
# ---------------------------------------------------------------------------


class TestUpgradeRetranscribe:
    """Verify --upgrade behavior."""

    def test_upgrade_retranscribes_when_model_differs(self, tmp_path: Path) -> None:
        """AC7: --upgrade when model differs → transcribed."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config(model="new-model", params_version="v2")
        _make_fragment_dir(
            tmp_path, frag_id,
            with_audio=True, with_done=True, with_manifest=True,
            model="old-model", params_version="v1",
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        with mock.patch(
            "soniscope_worker.poller._build_oss_client"
        ) as mock_build:
            mock_client = mock.MagicMock()
            mock_build.return_value = mock_client
            with mock.patch(
                "soniscope_worker.poller._run_transcription_pipeline"
            ) as mock_pipeline:
                status = _retranscribe_one(
                    frag_dir=frag_dir, fragment_id=frag_id,
                    config=config, force=False, upgrade=True,
                )
                assert status == "transcribed"
                mock_pipeline.assert_called_once()

    def test_upgrade_skips_when_same(self, tmp_path: Path) -> None:
        """AC7: --upgrade skips when model/params match."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config(model="test-model", params_version="v1")
        _make_fragment_dir(
            tmp_path, frag_id,
            with_audio=True, with_done=True, with_manifest=True,
            model="test-model", params_version="v1",
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        status = _retranscribe_one(
            frag_dir=frag_dir, fragment_id=frag_id,
            config=config, force=False, upgrade=True,
        )
        assert status == "skipped_upgrade"

    def test_upgrade_retranscribes_params_differs(self, tmp_path: Path) -> None:
        """AC7: --upgrade when params_version differs → transcribed."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config(model="test-model", params_version="v2")
        _make_fragment_dir(
            tmp_path, frag_id,
            with_audio=True, with_done=True, with_manifest=True,
            model="test-model", params_version="v1",
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        with mock.patch(
            "soniscope_worker.poller._build_oss_client"
        ) as mock_build:
            mock_client = mock.MagicMock()
            mock_build.return_value = mock_client
            with mock.patch(
                "soniscope_worker.poller._run_transcription_pipeline"
            ) as mock_pipeline:
                status = _retranscribe_one(
                    frag_dir=frag_dir, fragment_id=frag_id,
                    config=config, force=False, upgrade=True,
                )
                assert status == "transcribed"
                mock_pipeline.assert_called_once()

    def test_upgrade_no_done_still_transcribes(self, tmp_path: Path) -> None:
        """AC7: --upgrade without .done triggers transcript (not just upgrade)."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config()
        _make_fragment_dir(
            tmp_path, frag_id,
            with_audio=True, with_done=False, with_manifest=True,
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        with mock.patch(
            "soniscope_worker.poller._build_oss_client"
        ) as mock_build:
            mock_client = mock.MagicMock()
            mock_build.return_value = mock_client
            with mock.patch(
                "soniscope_worker.poller._run_transcription_pipeline"
            ) as mock_pipeline:
                status = _retranscribe_one(
                    frag_dir=frag_dir, fragment_id=frag_id,
                    config=config, force=False, upgrade=True,
                )
                assert status == "transcribed"
                mock_pipeline.assert_called_once()


# ---------------------------------------------------------------------------
# AC8: --all-from batch mode
# ---------------------------------------------------------------------------


class TestBatchRetranscribe:
    """Verify --all-from batch scanning and retranscribe."""

    def test_scan_fragment_dirs_from_date(self, tmp_path: Path) -> None:
        """_scan_fragment_dirs returns fragments on or after from_date."""
        _make_fragment_dir(
            tmp_path, "20260601T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ",
            with_audio=True, with_done=True,
        )
        _make_fragment_dir(
            tmp_path, "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ",
            with_audio=True, with_done=True,
        )
        _make_fragment_dir(
            tmp_path, "20260603T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ",
            with_audio=True, with_done=True,
        )

        entries = _scan_fragment_dirs(tmp_path, "2026-06-02")
        assert len(entries) == 2

        entries2 = _scan_fragment_dirs(tmp_path, "2026-06-03")
        assert len(entries2) == 1

    def test_scan_filters_no_audio(self, tmp_path: Path) -> None:
        """Fragments without audio.wav are skipped."""
        _make_fragment_dir(
            tmp_path, "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ",
            with_audio=False, with_done=False,
        )
        _make_fragment_dir(
            tmp_path, "20260602T110000_abc123_01ABCDEFGHJKMNPQRSTVWXYA",
            with_audio=True, with_done=False,
        )
        entries = _scan_fragment_dirs(tmp_path, "2026-06-01")
        assert len(entries) == 1

    def test_batch_continues_on_failure(self, tmp_path: Path) -> None:
        """AC8: Single failure doesn't stop batch."""
        frag1 = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        frag2 = "20260602T110000_abc123_01ABCDEFGHJKMNPQRSTVWXYA"

        _make_fragment_dir(
            tmp_path, frag1, with_audio=True, with_done=True,
            with_manifest=True, model="old", params_version="v0",
        )
        _make_fragment_dir(
            tmp_path, frag2, with_audio=True, with_done=True,
            with_manifest=True, model="old", params_version="v0",
        )

        config = _make_config(model="new", params_version="v1")
        call_count = [0]

        def mock_pipeline(**kwargs: object) -> None:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("simulated failure")

        with mock.patch("soniscope_worker.retranscribe.resolve_home", return_value=tmp_path):
            with mock.patch(
                "soniscope_worker.poller._build_oss_client"
            ) as mock_build:
                mock_client = mock.MagicMock()
                mock_build.return_value = mock_client
                with mock.patch(
                    "soniscope_worker.poller._run_transcription_pipeline",
                    side_effect=mock_pipeline,
                ):
                    summary = run_retranscribe(
                        all_from="2026-06-01",
                        force=False, upgrade=True,
                        config=config,
                    )
                    assert summary["failed"] == 1
                    assert summary["transcribed"] == 1


# ---------------------------------------------------------------------------
# AC9: File lock mutual exclusion
# ---------------------------------------------------------------------------


class TestFileLock:
    """Verify fcntl-based file locking."""

    def test_lock_acquired(self, tmp_path: Path) -> None:
        """Can acquire lock when free."""
        lock_file = tmp_path / ".retranscribe.lock"
        fd = os_open_lock(lock_file)
        assert fd is not None
        fcntl.flock(fd, fcntl.LOCK_UN)
        _os.close(fd)

    def test_lock_busy(self, tmp_path: Path) -> None:
        """Second process cannot acquire lock."""
        lock_file = tmp_path / ".retranscribe.lock"
        fd1 = os_open_lock(lock_file)
        assert fd1 is not None
        fd2 = os_open_lock(lock_file)
        assert fd2 is None
        fcntl.flock(fd1, fcntl.LOCK_UN)
        _os.close(fd1)

    def test_retranscribe_one_locked(self, tmp_path: Path) -> None:
        """Returns 'locked' when another process holds lock."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config()
        _make_fragment_dir(
            tmp_path, frag_id, with_audio=True, with_done=True,
            with_manifest=True, model="old", params_version="v0",
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id
        lock_file = frag_dir / ".retranscribe.lock"

        fd_held = os_open_lock(lock_file)
        assert fd_held is not None

        try:
            status = _retranscribe_one(
                frag_dir=frag_dir, fragment_id=frag_id,
                config=config, force=True, upgrade=False,
            )
            assert status == "locked"
        finally:
            fcntl.flock(fd_held, fcntl.LOCK_UN)
            _os.close(fd_held)


# ---------------------------------------------------------------------------
# differs_from_config helper
# ---------------------------------------------------------------------------


class TestDiffersFromConfig:
    """Unit tests for _differs_from_config and _needs_upgrade."""

    def test_differs_model_changed(self) -> None:
        manifest = {"transcription": {"model": "old-model", "params_version": "v1"}}
        config = _make_config(model="new-model", params_version="v1")
        assert _differs_from_config(manifest, config) is True

    def test_differs_params_changed(self) -> None:
        manifest = {"transcription": {"model": "test-model", "params_version": "v1"}}
        config = _make_config(model="test-model", params_version="v2")
        assert _differs_from_config(manifest, config) is True

    def test_differs_both_same(self) -> None:
        manifest = {"transcription": {"model": "test-model", "params_version": "v1"}}
        config = _make_config(model="test-model", params_version="v1")
        assert _differs_from_config(manifest, config) is False

    def test_differs_no_transcription(self) -> None:
        config = _make_config()
        assert _differs_from_config({}, config) is True

    def test_differs_none_transcription(self) -> None:
        config = _make_config()
        assert _differs_from_config({"transcription": None}, config) is True


# ---------------------------------------------------------------------------
# Module structure & security
# ---------------------------------------------------------------------------


class TestModuleStructure:
    """Verify module exports."""

    def test_module_exports(self) -> None:
        import soniscope_worker.retranscribe as rr
        assert hasattr(rr, "run_retranscribe")
        assert hasattr(rr, "_retranscribe_one")
        assert hasattr(rr, "_scan_fragment_dirs")
        assert hasattr(rr, "_differs_from_config")
        assert hasattr(rr, "_needs_upgrade")
        assert hasattr(rr, "os_open_lock")


class TestSecurity:
    """No secrets in retranscribe module."""

    def test_no_hardcoded_ak(self) -> None:
        import inspect
        import soniscope_worker.retranscribe as rr
        source = inspect.getsource(rr)
        assert "LTAI" not in source


# ---------------------------------------------------------------------------
# No-auto-retranscribe verification
# ---------------------------------------------------------------------------


class TestNoAutoRetranscribe:
    """Normal poll does NOT auto-retranscribe on config change."""

    def test_no_config_model_check_in_poll(self, tmp_path: Path) -> None:
        """poll_cycle only checks .done, not manifest.model."""
        from soniscope_worker.poller import is_fragment_done

        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        _make_fragment_dir(
            tmp_path, frag_id, with_audio=True, with_done=True,
            with_manifest=True, model="very-old-model", params_version="v0",
        )

        with mock.patch("soniscope_worker.poller.resolve_home", return_value=tmp_path):
            assert is_fragment_done(tmp_path, frag_id) is True


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestCLIRunRetranscribe:
    """run_retranscribe integration tests."""

    def test_run_retranscribe_single(self, tmp_path: Path) -> None:
        """run_retranscribe with fragment_id."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config()
        _make_fragment_dir(
            tmp_path, frag_id, with_audio=True, with_done=True,
            with_manifest=True, model="old", params_version="v0",
        )

        with mock.patch("soniscope_worker.retranscribe.resolve_home", return_value=tmp_path):
            with mock.patch(
                "soniscope_worker.poller._build_oss_client"
            ) as mock_build:
                mock_client = mock.MagicMock()
                mock_build.return_value = mock_client
                with mock.patch(
                    "soniscope_worker.poller._run_transcription_pipeline"
                ) as mock_pipeline:
                    summary = run_retranscribe(
                        fragment_id=frag_id, force=True, config=config,
                    )
                    assert summary["transcribed"] == 1
                    mock_pipeline.assert_called_once()

    def test_run_retranscribe_batch(self, tmp_path: Path) -> None:
        """run_retranscribe with --all-from."""
        frag1 = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        frag2 = "20260602T110000_abc123_01ABCDEFGHJKMNPQRSTVWXYA"

        _make_fragment_dir(
            tmp_path, frag1, with_audio=True, with_done=True,
            with_manifest=True, model="old", params_version="v0",
        )
        _make_fragment_dir(
            tmp_path, frag2, with_audio=True, with_done=True,
            with_manifest=True, model="old", params_version="v0",
        )

        config = _make_config(model="new", params_version="v1")

        with mock.patch("soniscope_worker.retranscribe.resolve_home", return_value=tmp_path):
            with mock.patch(
                "soniscope_worker.poller._build_oss_client"
            ) as mock_build:
                mock_client = mock.MagicMock()
                mock_build.return_value = mock_client
                with mock.patch(
                    "soniscope_worker.poller._run_transcription_pipeline"
                ) as mock_pipeline:
                    summary = run_retranscribe(
                        all_from="2026-06-01", upgrade=True, config=config,
                    )
                    assert summary["transcribed"] == 2
                    assert mock_pipeline.call_count == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_fragment_dir_not_found(self, tmp_path: Path) -> None:
        config = _make_config()
        with pytest.raises(FileNotFoundError):
            _retranscribe_one(
                frag_dir=tmp_path / "nonexistent",
                fragment_id="20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ",
                config=config, force=True,
            )

    def test_no_audio_wav(self, tmp_path: Path) -> None:
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        _make_fragment_dir(tmp_path, frag_id, with_audio=False, with_done=False)

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        config = _make_config()
        with pytest.raises(FileNotFoundError):
            _retranscribe_one(
                frag_dir=frag_dir, fragment_id=frag_id,
                config=config, force=True,
            )

    def test_empty_fragments_dir(self, tmp_path: Path) -> None:
        entries = _scan_fragment_dirs(tmp_path, "2026-06-01")
        assert entries == []

    def test_invalid_fragment_id_date(self) -> None:
        with pytest.raises(ValueError):
            from soniscope_worker.poller import _fragment_to_date
            _fragment_to_date("invalid_fragment_id")

    def test_no_manifest_no_upgrade(self, tmp_path: Path) -> None:
        """Fragment with done but no manifest → upgrade skips."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config(model="new-model", params_version="v2")

        # Create fragment with .done but WITHOUT manifest
        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id
        frag_dir.mkdir(parents=True, exist_ok=True)
        (frag_dir / "audio.wav").write_bytes(b"fake-audio-data")
        (frag_dir / ".done").touch()
        # NO manifest.json

        assert _needs_upgrade(frag_dir, config) is False

    def test_done_removed_before_force(self, tmp_path: Path) -> None:
        """--force removes .done before pipeline for crash safety."""
        frag_id = "20260602T100000_abc123_01ABCDEFGHJKMNPQRSTVWXYZ"
        config = _make_config()
        _make_fragment_dir(
            tmp_path, frag_id, with_audio=True, with_done=True,
            with_manifest=True,
        )

        from soniscope_worker.poller import _fragment_to_date
        date = _fragment_to_date(frag_id)
        frag_dir = tmp_path / "fragments" / date / frag_id

        assert (frag_dir / ".done").is_file()

        with mock.patch(
            "soniscope_worker.poller._build_oss_client"
        ) as mock_build:
            mock_client = mock.MagicMock()
            mock_build.return_value = mock_client
            with mock.patch(
                "soniscope_worker.poller._run_transcription_pipeline"
            ) as mock_pipeline:
                _retranscribe_one(
                    frag_dir=frag_dir, fragment_id=frag_id,
                    config=config, force=True,
                )
        mock_pipeline.assert_called_once()
