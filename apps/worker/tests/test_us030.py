"""Tests for US-030 — E2E integrity, sha256, and field validation scripts.

Covers:
- AC1: make verify-e2e-integrity — 100 Fragment dirs, 5 files each
- AC2: make verify-e2e-sha256 — WAV passthrough vs non-WAV transcode rules
- AC3: make verify-e2e-fields — verified_at / completed_at non-empty
- AC4: Output includes pass/fail counts and per-failure fragment_id + field
- AC5: Scripts use no mocks, don't modify OSS or local artifacts
- AC6: Non-zero exit on failure
- AC7: Typecheck/lint/test pass
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
MAKEFILE_PATH = REPO_ROOT / "Makefile"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _makefile_has_target(target: str) -> bool:
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    for line in content.split("\n"):
        if line.strip().startswith(f"{target}:"):
            return True
    return False


def _makefile_has_phony(target: str) -> bool:
    """Check target appears anywhere in .PHONY block (handles continuations)."""
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    in_phony = False
    phony_lines: list[str] = []
    for line in content.split("\n"):
        if line.strip().startswith(".PHONY:"):
            in_phony = True
            phony_lines.append(line.strip())
        elif in_phony and (line.startswith("\t") or line.startswith("        ")):
            phony_lines.append(line.strip())
        elif in_phony and not (line.startswith("\t") or line.startswith("        ")):
            in_phony = False
    combined = " ".join(phony_lines)
    return target in combined


def _script_source(script_name: str) -> str:
    path = SCRIPTS_DIR / script_name
    return path.read_text(encoding="utf-8")


def _script_syntax_valid(script_name: str) -> bool:
    """Compile the script to check Python syntax."""
    path = SCRIPTS_DIR / script_name
    try:
        compile(path.read_text(encoding="utf-8"), script_name, "exec")
        return True
    except SyntaxError:
        return False


# ── AC7: Typecheck / lint / test ──────────────────────────────────────────────


class TestMakefile:
    """Verify Makefile targets for all three commands."""

    def test_verify_e2e_integrity_target(self) -> None:
        assert _makefile_has_target("verify-e2e-integrity"), (
            "Makefile missing verify-e2e-integrity target"
        )

    def test_verify_e2e_integrity_phony(self) -> None:
        assert _makefile_has_phony("verify-e2e-integrity"), (
            "verify-e2e-integrity not in .PHONY"
        )

    def test_verify_e2e_sha256_target(self) -> None:
        assert _makefile_has_target("verify-e2e-sha256"), (
            "Makefile missing verify-e2e-sha256 target"
        )

    def test_verify_e2e_sha256_phony(self) -> None:
        assert _makefile_has_phony("verify-e2e-sha256"), (
            "verify-e2e-sha256 not in .PHONY"
        )

    def test_verify_e2e_fields_target(self) -> None:
        assert _makefile_has_target("verify-e2e-fields"), (
            "Makefile missing verify-e2e-fields target"
        )

    def test_verify_e2e_fields_phony(self) -> None:
        assert _makefile_has_phony("verify-e2e-fields"), (
            "verify-e2e-fields not in .PHONY"
        )


# ── Script syntax ─────────────────────────────────────────────────────────────


class TestScriptSyntax:
    def test_verify_e2e_integrity_python_syntax(self) -> None:
        assert _script_syntax_valid("verify_e2e_integrity.py"), (
            "verify_e2e_integrity.py has syntax errors"
        )

    def test_verify_e2e_sha256_python_syntax(self) -> None:
        assert _script_syntax_valid("verify_e2e_sha256.py"), (
            "verify_e2e_sha256.py has syntax errors"
        )

    def test_verify_e2e_fields_python_syntax(self) -> None:
        assert _script_syntax_valid("verify_e2e_fields.py"), (
            "verify_e2e_fields.py has syntax errors"
        )


# ── Script module structure ───────────────────────────────────────────────────


class TestScriptStructure:
    """Verify each script has the expected functions and constants."""

    def test_verify_e2e_integrity_has_required_files(self) -> None:
        source = _script_source("verify_e2e_integrity.py")
        assert "REQUIRED_FILES" in source, "Missing REQUIRED_FILES constant"
        assert "audio.wav" in source
        assert "manifest.json" in source
        assert "transcript.json" in source
        assert "transcript.txt" in source
        assert ".done" in source

    def test_verify_e2e_integrity_has_resolve_home(self) -> None:
        source = _script_source("verify_e2e_integrity.py")
        assert "def resolve_home()" in source, "Missing resolve_home()"

    def test_verify_e2e_integrity_has_main(self) -> None:
        source = _script_source("verify_e2e_integrity.py")
        assert "def main()" in source, "Missing main()"

    def test_verify_e2e_sha256_has_resolve_home(self) -> None:
        source = _script_source("verify_e2e_sha256.py")
        assert "def resolve_home()" in source, "Missing resolve_home()"

    def test_verify_e2e_sha256_has_consistency_function(self) -> None:
        source = _script_source("verify_e2e_sha256.py")
        assert "_sha256_consistency" in source, "Missing _sha256_consistency()"

    def test_verify_e2e_sha256_has_main(self) -> None:
        source = _script_source("verify_e2e_sha256.py")
        assert "def main()" in source, "Missing main()"

    def test_verify_e2e_fields_has_resolve_home(self) -> None:
        source = _script_source("verify_e2e_fields.py")
        assert "def resolve_home()" in source, "Missing resolve_home()"

    def test_verify_e2e_fields_has_check_fields(self) -> None:
        source = _script_source("verify_e2e_fields.py")
        assert "_check_fields" in source, "Missing _check_fields()"

    def test_verify_e2e_fields_has_required_fields(self) -> None:
        source = _script_source("verify_e2e_fields.py")
        assert "REQUIRED_FIELDS" in source, "Missing REQUIRED_FIELDS constant"
        assert "verified_at" in source
        assert "completed_at" in source


# ── AC1: verify-e2e-integrity core logic ──────────────────────────────────────


class TestIntegrityLogic:
    """Test the integrity verification logic directly."""

    @pytest.fixture
    def script_module(self):
        """Import verify_e2e_integrity as a module."""
        import importlib

        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            mod = importlib.import_module("verify_e2e_integrity")
            return mod
        finally:
            sys.path.pop(0)
            if "verify_e2e_integrity" in sys.modules:
                del sys.modules["verify_e2e_integrity"]

    def test_required_files_list(self, script_module) -> None:
        assert len(script_module.REQUIRED_FILES) == 5
        assert "audio.wav" in script_module.REQUIRED_FILES
        assert "manifest.json" in script_module.REQUIRED_FILES
        assert "transcript.json" in script_module.REQUIRED_FILES
        assert "transcript.txt" in script_module.REQUIRED_FILES
        assert ".done" in script_module.REQUIRED_FILES

    def test_all_files_present_single_dir(self, tmp_path, script_module) -> None:
        """With all 5 files present, main reports pass and exits 0."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_0123456789ABCDEFGHJKMNPQ"
        frag_dir.mkdir(parents=True)
        for f in script_module.REQUIRED_FILES:
            (frag_dir / f).touch()

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 0, f"Expected exit 0, got {exc.code}"

    def test_missing_file(self, tmp_path, script_module) -> None:
        """One file missing → non-zero exit."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_0123456789ABCDEFGHJKMNPQ"
        frag_dir.mkdir(parents=True)
        for f in script_module.REQUIRED_FILES:
            (frag_dir / f).touch()
        # Remove .done
        (frag_dir / ".done").unlink()

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_missing_date_env(self, tmp_path, script_module) -> None:
        """No DATE env → exit non-zero."""
        home = tmp_path / "SoniScope"
        home.mkdir(parents=True)
        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_home_not_exists(self, tmp_path, script_module) -> None:
        """SONISCOPE_HOME doesn't exist → exit non-zero."""
        home = tmp_path / "nonexistent"
        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": "2026-06-02"}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_date_dir_not_exists(self, tmp_path, script_module) -> None:
        """Target date directory doesn't exist → exit non-zero."""
        home = tmp_path / "SoniScope"
        home.mkdir(parents=True)
        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": "2099-01-01"}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_empty_date_dir(self, tmp_path, script_module) -> None:
        """Date dir exists but has no fragment dirs → exit 0."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date
        frag_dir.mkdir(parents=True)

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 0, f"Expected exit 0, got {exc.code}"

    def test_multiple_fragments_mixed(self, tmp_path, script_module) -> None:
        """3 fragments, 2 pass, 1 missing .done → exit 1."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_base = home / "fragments" / date

        for i in range(1, 4):
            d = frag_base / f"20260602T12000{i}_abc123_ULID_{i}"
            d.mkdir(parents=True)
            for f in script_module.REQUIRED_FILES:
                (d / f).touch()

        # Break fragment 2 (remove .done)
        (frag_base / "20260602T120002_abc123_ULID_2" / ".done").unlink()

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_non_dir_files_ignored(self, tmp_path, script_module) -> None:
        """Files (not dirs) in fragments/<date>/ are ignored."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_date_dir = home / "fragments" / date
        frag_date_dir.mkdir(parents=True)
        # Create a stray file (not a directory)
        (frag_date_dir / "README.txt").touch()
        # Also create a valid fragment
        frag_dir = frag_date_dir / "20260602T120000_abc123_ULID_ok"
        frag_dir.mkdir()
        for f in script_module.REQUIRED_FILES:
            (frag_dir / f).touch()

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 0, f"Expected exit 0, got {exc.code}"


# ── AC2: verify-e2e-sha256 core logic ─────────────────────────────────────────


class TestSha256Logic:
    """Test the SHA-256 verification logic directly."""

    @pytest.fixture
    def script_module(self):
        import importlib

        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            mod = importlib.import_module("verify_e2e_sha256")
            return mod
        finally:
            sys.path.pop(0)
            if "verify_e2e_sha256" in sys.modules:
                del sys.modules["verify_e2e_sha256"]

    def test_consistency_wav_passthrough_match(self, script_module) -> None:
        """WAV passthrough with matching sha256s → pass (None)."""
        manifest = {
            "audio": {"sha256": "abc123def456", "format": "wav", "original_format": "wav"},
            "upload": {"original_sha256": "abc123def456"},
        }
        result = script_module._sha256_consistency(manifest, "frag1")
        assert result is None, f"Expected None (pass), got: {result}"

    def test_consistency_wav_passthrough_mismatch(self, script_module) -> None:
        """WAV passthrough with different sha256s → error message."""
        manifest = {
            "audio": {"sha256": "aaa111bbb222", "format": "wav", "original_format": "wav"},
            "upload": {"original_sha256": "ccc333ddd444"},
        }
        result = script_module._sha256_consistency(manifest, "frag2")
        assert result is not None
        assert "不一致" in result
        assert "frag2" in result

    def test_consistency_non_wav_transcode_both_present(self, script_module) -> None:
        """Non-WAV transcode with both sha256 values present → pass."""
        manifest = {
            "audio": {
                "sha256": "aaa111bbb222333444",
                "format": "wav",
                "original_format": "m4a",
            },
            "upload": {"original_sha256": "ccc333ddd444555666"},
        }
        result = script_module._sha256_consistency(manifest, "frag3")
        assert result is None, f"Expected None (pass), got: {result}"

    def test_consistency_non_wav_short_sha256(self, script_module) -> None:
        """Non-WAV transcode with too-short sha256s → error."""
        manifest = {
            "audio": {"sha256": "abc", "format": "wav", "original_format": "m4a"},
            "upload": {"original_sha256": "def"},
        }
        result = script_module._sha256_consistency(manifest, "frag4")
        assert result is not None

    def test_consistency_missing_audio_sha256(self, script_module) -> None:
        """audio.sha256 is empty → error."""
        manifest = {
            "audio": {"sha256": "", "format": "wav", "original_format": ""},
            "upload": {"original_sha256": "abc123def456"},
        }
        result = script_module._sha256_consistency(manifest, "frag5")
        assert result is not None
        assert "audio.sha256" in result

    def test_consistency_missing_upload_sha256(self, script_module) -> None:
        """upload.original_sha256 is empty → error."""
        manifest = {
            "audio": {"sha256": "abc123def456", "format": "wav", "original_format": ""},
            "upload": {"original_sha256": ""},
        }
        result = script_module._sha256_consistency(manifest, "frag6")
        assert result is not None
        assert "upload.original_sha256" in result

    def test_consistency_original_format_empty_treated_as_passthrough(
        self, script_module
    ) -> None:
        """Empty original_format + wav format → passthrough (match check)."""
        manifest = {
            "audio": {"sha256": "xxx111yyy222", "format": "wav", "original_format": ""},
            "upload": {"original_sha256": "xxx111yyy222"},
        }
        result = script_module._sha256_consistency(manifest, "frag7")
        assert result is None

    def test_full_script_non_zero_exit_on_failure(self, tmp_path, script_module) -> None:
        """A fragment with sha256 mismatch → script exits 1."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_MISMATCH01ABCDEFGHJK"
        frag_dir.mkdir(parents=True)
        manifest = {
            "audio": {"sha256": "aaa111bbb222", "format": "wav", "original_format": "wav"},
            "upload": {"original_sha256": "ccc333ddd444"},
        }
        (frag_dir / "manifest.json").write_text(json.dumps(manifest))

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_full_script_pass(self, tmp_path, script_module) -> None:
        """All sha256s consistent → exit 0."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_MATCH01ABCDEFGHJK"
        frag_dir.mkdir(parents=True)
        manifest = {
            "audio": {"sha256": "aaa111bbb222", "format": "wav", "original_format": "wav"},
            "upload": {"original_sha256": "aaa111bbb222"},
        }
        (frag_dir / "manifest.json").write_text(json.dumps(manifest))

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 0, f"Expected exit 0, got {exc.code}"

    def test_missing_manifest_json(self, tmp_path, script_module) -> None:
        """Fragment dir without manifest.json → reported as failure."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_NOMANIFESTABCDEFGH"
        frag_dir.mkdir(parents=True)
        # No manifest.json

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_invalid_manifest_json(self, tmp_path, script_module) -> None:
        """Corrupt manifest.json → reported as failure."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_BADJSON01ABCDEFGH"
        frag_dir.mkdir(parents=True)
        (frag_dir / "manifest.json").write_text("{not valid json")

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_empty_date_dir_exit_zero(self, tmp_path, script_module) -> None:
        """Empty date dir → exit 0."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        (home / "fragments" / date).mkdir(parents=True)

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 0, f"Expected exit 0, got {exc.code}"


# ── AC3: verify-e2e-fields core logic ─────────────────────────────────────────


class TestFieldsLogic:
    """Test the fields verification logic directly."""

    @pytest.fixture
    def script_module(self):
        import importlib

        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            mod = importlib.import_module("verify_e2e_fields")
            return mod
        finally:
            sys.path.pop(0)
            if "verify_e2e_fields" in sys.modules:
                del sys.modules["verify_e2e_fields"]

    def test_required_fields_constant(self, script_module) -> None:
        """REQUIRED_FIELDS includes verified_at and completed_at."""
        field_paths = [f[0] for f in script_module.REQUIRED_FIELDS]
        assert "upload.verified_at" in field_paths
        assert "transcription.completed_at" in field_paths

    def test_get_nested(self, script_module) -> None:
        """_get_nested retrieves nested values correctly."""
        manifest = {
            "upload": {"verified_at": "2026-06-02T12:00:00Z"},
            "transcription": {"completed_at": "2026-06-02T12:01:00Z"},
        }
        val1 = script_module._get_nested(manifest, "upload.verified_at")
        assert val1 == "2026-06-02T12:00:00Z"
        val2 = script_module._get_nested(manifest, "transcription.completed_at")
        assert val2 == "2026-06-02T12:01:00Z"

    def test_get_nested_missing_path(self, script_module) -> None:
        """_get_nested returns None for nonexistent path."""
        manifest = {"upload": {}}
        result = script_module._get_nested(manifest, "upload.verified_at")
        assert result is None

    def test_get_nested_missing_top_key(self, script_module) -> None:
        """_get_nested returns None for missing top-level key."""
        manifest = {"upload": {"verified_at": "abc"}}
        result = script_module._get_nested(manifest, "transcription.completed_at")
        assert result is None

    def test_check_fields_all_present(self, script_module) -> None:
        """When all required fields are populated → empty failures."""
        manifest = {
            "upload": {"verified_at": "2026-06-02T12:00:00Z"},
            "transcription": {"completed_at": "2026-06-02T12:01:00Z"},
        }
        failures = script_module._check_fields(manifest, "frag1")
        assert failures == [], f"Expected empty list, got: {failures}"

    def test_check_fields_verified_at_missing(self, script_module) -> None:
        """verified_at is None → failure reported."""
        manifest = {
            "upload": {"verified_at": None},
            "transcription": {"completed_at": "2026-06-02T12:01:00Z"},
        }
        failures = script_module._check_fields(manifest, "frag2")
        assert len(failures) == 1
        assert "verified_at" in failures[0]
        assert "frag2" in failures[0]

    def test_check_fields_verified_at_empty(self, script_module) -> None:
        """verified_at is empty string → failure reported."""
        manifest = {
            "upload": {"verified_at": ""},
            "transcription": {"completed_at": "2026-06-02T12:01:00Z"},
        }
        failures = script_module._check_fields(manifest, "frag3")
        assert len(failures) == 1
        assert "verified_at" in failures[0]

    def test_check_fields_completed_at_missing(self, script_module) -> None:
        """completed_at is None → failure reported."""
        manifest = {
            "upload": {"verified_at": "2026-06-02T12:00:00Z"},
            "transcription": {"completed_at": None},
        }
        failures = script_module._check_fields(manifest, "frag4")
        assert len(failures) == 1
        assert "completed_at" in failures[0]

    def test_check_fields_completed_at_empty(self, script_module) -> None:
        """completed_at is empty string → failure reported."""
        manifest = {
            "upload": {"verified_at": "2026-06-02T12:00:00Z"},
            "transcription": {"completed_at": ""},
        }
        failures = script_module._check_fields(manifest, "frag5")
        assert len(failures) == 1
        assert "completed_at" in failures[0]

    def test_check_fields_both_missing(self, script_module) -> None:
        """Both fields missing → 2 failures."""
        manifest = {
            "upload": {"verified_at": None},
            "transcription": {"completed_at": None},
        }
        failures = script_module._check_fields(manifest, "frag6")
        assert len(failures) == 2

    def test_full_script_exit_zero_all_pass(self, tmp_path, script_module) -> None:
        """All fields populated → exit 0."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_FIELDS01ABCDEFGH"
        frag_dir.mkdir(parents=True)
        manifest = {
            "upload": {"verified_at": "2026-06-02T12:00:00Z"},
            "transcription": {"completed_at": "2026-06-02T12:01:00Z"},
        }
        (frag_dir / "manifest.json").write_text(json.dumps(manifest))

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 0, f"Expected exit 0, got {exc.code}"

    def test_full_script_exit_one_on_failure(self, tmp_path, script_module) -> None:
        """Missing verified_at → exit 1."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_FAIL01ABCDEFGHJK"
        frag_dir.mkdir(parents=True)
        manifest = {
            "upload": {"verified_at": None},
            "transcription": {"completed_at": "2026-06-02T12:01:00Z"},
        }
        (frag_dir / "manifest.json").write_text(json.dumps(manifest))

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_full_script_missing_manifest_json(self, tmp_path, script_module) -> None:
        """No manifest.json → reported as failure."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_NOMAN01ABCDEFGH"
        frag_dir.mkdir(parents=True)
        # no manifest

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 1, f"Expected exit 1, got {exc.code}"

    def test_full_script_empty_date_dir(self, tmp_path, script_module) -> None:
        """Empty date dir → exit 0."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        (home / "fragments" / date).mkdir(parents=True)

        with mock.patch.object(script_module, "resolve_home", return_value=home):
            with mock.patch.dict(os.environ, {"DATE": date}, clear=True):
                try:
                    script_module.main()
                except SystemExit as exc:
                    assert exc.code == 0, f"Expected exit 0, got {exc.code}"


# ── AC4: Output format — pass/fail counts and per-failure fragment_id + field ──


class TestOutputFormat:
    """Verify that scripts output pass/fail counts and per-failure details."""

    def _capture_output(self, script_name: str, env: dict) -> tuple[str, str, int]:
        """Run a script and capture stdout, stderr, and exit code."""
        import subprocess

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script_name)],
            capture_output=True,
            text=True,
            env={**os.environ, **env},
        )
        return result.stdout, result.stderr, result.returncode

    def test_integrity_output_has_counts(self, tmp_path) -> None:
        """Integration test: output contains pass/fail counts."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_OUT01ABCDEFGHJK"
        frag_dir.mkdir(parents=True)
        for f in ["audio.wav", "manifest.json", "transcript.json", "transcript.txt", ".done"]:
            (frag_dir / f).touch()

        stdout, stderr, rc = self._capture_output("verify_e2e_integrity.py", {
            "SONISCOPE_HOME": str(home),
            "DATE": date,
        })
        assert rc == 0, f"Expected exit 0, got {rc}. stderr: {stderr}"
        assert "通过: 1/1" in stdout, f"Expected '通过: 1/1' in output, got:\n{stdout}"
        assert "失败: 0/1" in stdout, f"Expected '失败: 0/1' in output"

    def test_integrity_output_has_failure_details(self, tmp_path) -> None:
        """Failed fragment shows fragment_id and missing field names."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_id = "20260602T120000_abc123_FAILTESTABCDEFGH"
        frag_dir = home / "fragments" / date / frag_id
        frag_dir.mkdir(parents=True)
        # Only create audio.wav — missing manifest.json, transcript.json, transcript.txt, .done
        (frag_dir / "audio.wav").touch()

        stdout, stderr, rc = self._capture_output("verify_e2e_integrity.py", {
            "SONISCOPE_HOME": str(home),
            "DATE": date,
        })
        assert rc == 1, f"Expected exit 1, got {rc}. stdout: {stdout}"
        assert frag_id in stdout, f"Expected fragment_id {frag_id} in output:\n{stdout}"
        assert "不完整的 Fragment 目录" in stdout or "FAIL" in stdout

    def test_sha256_output_has_fragment_id_on_failure(self, tmp_path) -> None:
        """SHA-256 failure output includes fragment_id."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_SHAFAILABCDEFGH"
        frag_dir.mkdir(parents=True)
        manifest = {
            "audio": {"sha256": "", "format": "wav", "original_format": ""},
            "upload": {"original_sha256": ""},
        }
        (frag_dir / "manifest.json").write_text(json.dumps(manifest))

        stdout, stderr, rc = self._capture_output("verify_e2e_sha256.py", {
            "SONISCOPE_HOME": str(home),
            "DATE": date,
        })
        assert rc == 1, f"Expected exit 1, got {rc}. stdout: {stdout}"
        assert "20260602T120000_abc123_SHAFAILABCDEFGH" in stdout

    def test_fields_output_has_fragment_id_on_failure(self, tmp_path) -> None:
        """Fields verification failure output includes fragment_id."""
        date = "2026-06-02"
        home = tmp_path / "SoniScope"
        frag_dir = home / "fragments" / date / "20260602T120000_abc123_FLDFAILABCDEF"
        frag_dir.mkdir(parents=True)
        manifest = {
            "upload": {"verified_at": None},
            "transcription": {"completed_at": "2026-06-02T12:01:00Z"},
        }
        (frag_dir / "manifest.json").write_text(json.dumps(manifest))

        stdout, stderr, rc = self._capture_output("verify_e2e_fields.py", {
            "SONISCOPE_HOME": str(home),
            "DATE": date,
        })
        assert rc == 1, f"Expected exit 1, got {rc}. stdout: {stdout}"
        assert "20260602T120000_abc123_FLDFAILABCDEF" in stdout


# ── AC5: Scripts do not modify OSS or local artifacts ─────────────────────────


class TestNoSideEffects:
    """Verify scripts are read-only — no OSS/network calls, no local writes."""

    def test_integrity_script_no_network_imports(self) -> None:
        """verify_e2e_integrity.py does not import network libraries."""
        source = _script_source("verify_e2e_integrity.py")
        assert "urllib" not in source, "Should not import urllib"
        assert "requests" not in source, "Should not import requests"
        assert "boto3" not in source, "Should not import boto3"
        assert "alibabacloud" not in source, "Should not import alibabacloud"

    def test_sha256_script_no_network_imports(self) -> None:
        """verify_e2e_sha256.py does not import network libraries."""
        source = _script_source("verify_e2e_sha256.py")
        assert "urllib" not in source, "Should not import urllib"
        assert "requests" not in source, "Should not import requests"
        assert "boto3" not in source, "Should not import boto3"
        assert "alibabacloud" not in source, "Should not import alibabacloud"

    def test_fields_script_no_network_imports(self) -> None:
        """verify_e2e_fields.py does not import network libraries."""
        source = _script_source("verify_e2e_fields.py")
        assert "urllib" not in source, "Should not import urllib"
        assert "requests" not in source, "Should not import requests"
        assert "boto3" not in source, "Should not import boto3"
        assert "alibabacloud" not in source, "Should not import alibabacloud"

    def test_scripts_do_not_write_files(self) -> None:
        """Scripts use open only for reading (manifest.json reading via json.loads)."""
        for script_name in [
            "verify_e2e_integrity.py",
            "verify_e2e_sha256.py",
            "verify_e2e_fields.py",
        ]:
            source = _script_source(script_name)
            # Check for write-mode patterns
            assert '"w"' not in source, f"{script_name} should not open files for writing"
            assert "'w'" not in source, f"{script_name} should not open files for writing"
            # Check for write_text
            assert ".write_text(" not in source, f"{script_name} should not write files"


# ── AC6: Non-zero exit on failure ─────────────────────────────────────────────

class TestNonZeroExit:
    """Verify non-zero exit codes on failures (covered in logic tests above)."""

    def test_integrity_exit_one_on_date_missing(self, tmp_path) -> None:
        """DATE not set → exit non-zero."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "verify_e2e_integrity.py")],
            capture_output=True, text=True,
            env={**os.environ, "DATE": ""},
        )
        assert result.returncode != 0

    def test_sha256_exit_one_on_date_missing(self, tmp_path) -> None:
        """DATE not set → exit non-zero."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "verify_e2e_sha256.py")],
            capture_output=True, text=True,
            env={**os.environ, "DATE": ""},
        )
        assert result.returncode != 0

    def test_fields_exit_one_on_date_missing(self, tmp_path) -> None:
        """DATE not set → exit non-zero."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "verify_e2e_fields.py")],
            capture_output=True, text=True,
            env={**os.environ, "DATE": ""},
        )
        assert result.returncode != 0


# ── Security: No AK Secret leakage ────────────────────────────────────────────


class TestSecurityNoSecretLeakage:
    """Verify scripts do not output AK Secret plaintext."""

    def test_integrity_no_ak_in_source(self) -> None:
        source = _script_source("verify_e2e_integrity.py")
        assert "LTAI" not in source, "Should not hardcode Aliyun AK ID prefix"
        assert "access_key_secret" not in source.lower(), "Should not reference secret key"

    def test_sha256_no_ak_in_source(self) -> None:
        source = _script_source("verify_e2e_sha256.py")
        assert "LTAI" not in source, "Should not hardcode Aliyun AK ID prefix"
        assert "access_key_secret" not in source.lower(), "Should not reference secret key"

    def test_fields_no_ak_in_source(self) -> None:
        source = _script_source("verify_e2e_fields.py")
        assert "LTAI" not in source, "Should not hardcode Aliyun AK ID prefix"
        assert "access_key_secret" not in source.lower(), "Should not reference secret key"


# ── Path / env resolution ─────────────────────────────────────────────────────


class TestResolveHome:
    """Test SONISCOPE_HOME resolution across all three scripts."""

    @pytest.mark.parametrize("script_name", [
        "verify_e2e_integrity.py",
        "verify_e2e_sha256.py",
        "verify_e2e_fields.py",
    ])
    def test_resolve_home_from_env(self, script_name: str) -> None:
        """resolve_home picks up SONISCOPE_HOME env var."""
        import importlib

        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            mod = importlib.import_module(script_name.replace(".py", ""))
            with mock.patch.dict(os.environ, {"SONISCOPE_HOME": "/custom/path"}):
                result = mod.resolve_home()
                assert str(result) == "/custom/path"
        finally:
            sys.path.pop(0)
            mod_name = script_name.replace(".py", "")
            if mod_name in sys.modules:
                del sys.modules[mod_name]

    @pytest.mark.parametrize("script_name", [
        "verify_e2e_integrity.py",
        "verify_e2e_sha256.py",
        "verify_e2e_fields.py",
    ])
    def test_resolve_home_default(self, script_name: str) -> None:
        """resolve_home defaults to ~/SoniScope when env not set."""
        import importlib

        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            mod = importlib.import_module(script_name.replace(".py", ""))
            with mock.patch.dict(os.environ, {}, clear=True):
                result = mod.resolve_home()
                assert "SoniScope" in str(result)
        finally:
            sys.path.pop(0)
            mod_name = script_name.replace(".py", "")
            if mod_name in sys.modules:
                del sys.modules[mod_name]


# ── completeness: Non-zero exit code is 1 ─────────────────────────────────────


class TestExitCodeIsOne:
    """Verify non-zero exit is exactly 1 (convention for verification scripts)."""

    @pytest.mark.parametrize("script_name", [
        "verify_e2e_integrity",
        "verify_e2e_sha256",
        "verify_e2e_fields",
    ])
    def test_exit_code_one_on_missing_date(self, script_name: str) -> None:
        """Each script exits with code 1 when DATE is missing."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / f"{script_name}.py")],
            capture_output=True, text=True,
            env={**os.environ, "DATE": "", "SONISCOPE_HOME": "/tmp/nonexistent"},
        )
        assert result.returncode == 1, (
            f"{script_name}.py exited with {result.returncode}, expected 1"
        )
