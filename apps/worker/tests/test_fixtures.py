"""US-003 测试音频 fixture 校验逻辑单元测试。

ffprobe 探测通过 monkeypatch :func:`soniscope_worker.fixtures.probe_media`
打桩，不依赖真实音频文件，也不调用真实 ffprobe / OSS。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from soniscope_worker import fixtures
from soniscope_worker.fixtures import (
    FIX_HINT,
    Fixture,
    FixtureError,
    Manifest,
    MediaInfo,
    codec_matches,
    load_manifest,
    sha256_of,
    verify_fixture,
)

_WAV_MEDIA = MediaInfo(duration=24.02, format_name="wav", codec_names=("pcm_s16le",))
_M4A_MEDIA = MediaInfo(
    duration=24.02,
    format_name="mov,mp4,m4a,3gp,3g2,mj2",
    codec_names=("aac",),
)


def _make_fixture(
    tmp_path: Path,
    *,
    name: str = "sample-20s.wav",
    codec: str = "wav",
    duration: float = 24.0,
    content: bytes = b"audio-bytes",
) -> tuple[Fixture, Path]:
    """落一个内容已知的文件，并返回与之 sha256 一致的 Fixture。"""
    dest = tmp_path / name
    dest.write_bytes(content)
    sha = hashlib.sha256(content).hexdigest()
    fx = Fixture(
        name=name,
        oss_key=f"sample/{name}",
        sha256=sha,
        size_bytes=len(content),
        codec=codec,
        duration_seconds=duration,
    )
    return fx, dest


def _patch_media(monkeypatch: pytest.MonkeyPatch, info: MediaInfo) -> None:
    monkeypatch.setattr(fixtures, "probe_media", lambda _path: info)


# --------------------------------------------------------------------------- #
# load_manifest
# --------------------------------------------------------------------------- #


def test_load_manifest_parses_repo_manifest() -> None:
    """仓库真实 manifest 能被解析出 4 个 fixture 与正确云资源。"""
    repo_root = Path(__file__).resolve().parents[3]
    manifest = load_manifest(repo_root / "tests" / "audio" / "fixtures.manifest.json")
    assert isinstance(manifest, Manifest)
    assert manifest.bucket == "soniscope-audio"
    assert manifest.region == "cn-beijing"
    names = [f.name for f in manifest.fixtures]
    assert names == [
        "sample-20s.wav",
        "sample-54s.wav",
        "sample-25min.wav",
        "sample-20s.m4a",
    ]
    m4a = next(f for f in manifest.fixtures if f.name == "sample-20s.m4a")
    assert m4a.codec == "m4a"
    assert m4a.sha256 == (
        "d3d2866128efe258ff95e841a16e7abb4d783fd37536692932a875f9fb5380fd"
    )


def test_load_manifest_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FixtureError):
        load_manifest(tmp_path / "nope.json")


def test_load_manifest_malformed(tmp_path: Path) -> None:
    bad = tmp_path / "m.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(FixtureError):
        load_manifest(bad)


def test_load_manifest_missing_fields(tmp_path: Path) -> None:
    bad = tmp_path / "m.json"
    bad.write_text(
        json.dumps({"bucket": "b", "endpoint": "e", "region": "r", "dest_dir": "d"}),
        encoding="utf-8",
    )
    with pytest.raises(FixtureError):
        load_manifest(bad)


# --------------------------------------------------------------------------- #
# sha256_of
# --------------------------------------------------------------------------- #


def test_sha256_of_matches_hashlib(tmp_path: Path) -> None:
    p = tmp_path / "f.bin"
    p.write_bytes(b"hello world")
    assert sha256_of(p) == hashlib.sha256(b"hello world").hexdigest()


# --------------------------------------------------------------------------- #
# codec_matches
# --------------------------------------------------------------------------- #


def test_codec_matches_wav_by_format() -> None:
    fx = Fixture("x", "k", "s", 1, "wav", 1.0)
    assert codec_matches(fx, _WAV_MEDIA)


def test_codec_matches_wav_by_pcm_codec() -> None:
    fx = Fixture("x", "k", "s", 1, "wav", 1.0)
    info = MediaInfo(duration=1.0, format_name="something", codec_names=("pcm_s24le",))
    assert codec_matches(fx, info)


def test_codec_matches_m4a_by_aac_codec() -> None:
    """m4a 容器内 codec=aac 被识别为 m4a/aac 路径（AC：容器或 codec 识别）。"""
    fx = Fixture("x", "k", "s", 1, "m4a", 1.0)
    assert codec_matches(fx, _M4A_MEDIA)


def test_codec_matches_m4a_by_container_name() -> None:
    fx = Fixture("x", "k", "s", 1, "m4a", 1.0)
    info = MediaInfo(duration=1.0, format_name="mov,mp4,m4a", codec_names=("alac",))
    assert codec_matches(fx, info)


def test_codec_mismatch() -> None:
    fx = Fixture("x", "k", "s", 1, "wav", 1.0)
    info = MediaInfo(duration=1.0, format_name="mp3", codec_names=("mp3",))
    assert not codec_matches(fx, info)


# --------------------------------------------------------------------------- #
# verify_fixture
# --------------------------------------------------------------------------- #


def test_verify_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fx, dest = _make_fixture(tmp_path, duration=24.0)
    _patch_media(monkeypatch, _WAV_MEDIA)
    result = verify_fixture(fx, dest)
    assert result.ok
    assert result.problems == ()


def test_verify_missing_file(tmp_path: Path) -> None:
    fx = Fixture("sample-20s.wav", "k", "s" * 64, 1, "wav", 24.0)
    result = verify_fixture(fx, tmp_path / "absent.wav")
    assert not result.ok
    assert any("缺失" in p for p in result.problems)


def test_verify_sha256_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fx, dest = _make_fixture(tmp_path, duration=24.0)
    # 篡改期望 sha256 使其不匹配，但 duration/codec 仍 OK
    bad = Fixture(fx.name, fx.oss_key, "0" * 64, fx.size_bytes, fx.codec, fx.duration_seconds)
    _patch_media(monkeypatch, _WAV_MEDIA)
    result = verify_fixture(bad, dest)
    assert not result.ok
    assert any("sha256" in p for p in result.problems)


def test_verify_duration_outside_tolerance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fx, dest = _make_fixture(tmp_path, duration=20.0)  # 期望 20s
    _patch_media(monkeypatch, MediaInfo(24.02, "wav", ("pcm_s16le",)))  # 实测 24s
    result = verify_fixture(fx, dest)
    assert not result.ok
    assert any("duration" in p for p in result.problems)


def test_verify_duration_within_tolerance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fx, dest = _make_fixture(tmp_path, duration=54.0)
    _patch_media(monkeypatch, MediaInfo(53.78, "wav", ("pcm_s16le",)))  # 差 0.22s
    assert verify_fixture(fx, dest).ok


def test_verify_m4a_codec_accepted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fx, dest = _make_fixture(tmp_path, name="sample-20s.m4a", codec="m4a", duration=24.0)
    _patch_media(monkeypatch, _M4A_MEDIA)
    assert verify_fixture(fx, dest).ok


def test_verify_codec_mismatch_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fx, dest = _make_fixture(tmp_path, codec="wav", duration=24.0)
    _patch_media(monkeypatch, MediaInfo(24.02, "mp3", ("mp3",)))
    result = verify_fixture(fx, dest)
    assert not result.ok
    assert any("codec" in p for p in result.problems)


def test_verify_check_media_false_skips_ffprobe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """check_media=False 时不应调用 probe_media（即使会抛错也不触发）。"""
    fx, dest = _make_fixture(tmp_path, duration=24.0)

    def _boom(_path: Path) -> MediaInfo:
        raise AssertionError("probe_media 不应被调用")

    monkeypatch.setattr(fixtures, "probe_media", _boom)
    assert verify_fixture(fx, dest, check_media=False).ok


# --------------------------------------------------------------------------- #
# FIX_HINT
# --------------------------------------------------------------------------- #


def test_fix_hint_points_to_runbook_section_6() -> None:
    assert "cloud-setup.md" in FIX_HINT
    assert "第 6 节" in FIX_HINT
