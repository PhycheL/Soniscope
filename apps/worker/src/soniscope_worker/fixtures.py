"""测试音频 fixture 校验逻辑（US-003）。

纯逻辑放 Worker 包内，便于 mypy strict + pytest 覆盖；
``scripts/fetch_test_fixtures.py`` 作为薄 CLI 复用本模块。

校验分三层：

1. **文件存在**。
2. **sha256** 与 manifest（= ``docs/runbook/cloud-setup.md`` §6 登记值）精确匹配 ——
   sha256 是唯一权威校验源（runbook §6）。
3. **ffprobe 探测**：真实 duration 在 manifest 期望值 ±2s 内，且容器/编码与
   声明的 ``codec`` 一致（``m4a`` 容器内识别为 ``aac``，``wav`` 识别为
   ``wav``/``pcm_*``）。不信任文件扩展名或 OSS object key 的 ``.wav`` 后缀。

sha256 / duration / codec 任一不匹配时，调用方应输出指向 runbook §6 的修复提示
（见 :data:`FIX_HINT`）。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

#: duration 校验容差（秒），见 US-003 AC「容差为 ±2 秒」。
DURATION_TOLERANCE_SECONDS = 2.0

#: 修复提示统一指向 runbook 第 6 节（测试基线音频素材，sha256 唯一权威校验源）。
FIX_HINT = (
    "修复提示：请重新运行 `python3 scripts/fetch_test_fixtures.py` 拉取正确文件，"
    "并核对 docs/runbook/cloud-setup.md 第 6 节（测试基线音频素材）"
    "登记的 sha256 / duration / codec。"
)

_CHUNK_SIZE = 1024 * 1024


class FixtureError(RuntimeError):
    """fixture 清单解析或 ffprobe 探测异常（区别于「fixture 内容不合格」）。"""


@dataclass(frozen=True)
class Fixture:
    """单个测试音频 fixture 的期望元数据。"""

    name: str
    oss_key: str
    sha256: str
    size_bytes: int
    codec: str
    duration_seconds: float


@dataclass(frozen=True)
class Manifest:
    """``tests/audio/fixtures.manifest.json`` 的结构化视图。"""

    bucket: str
    endpoint: str
    region: str
    dest_dir: str
    fixtures: tuple[Fixture, ...]


@dataclass(frozen=True)
class MediaInfo:
    """ffprobe 探测到的真实容器/编码/时长。"""

    duration: float
    format_name: str
    codec_names: tuple[str, ...]


@dataclass(frozen=True)
class VerifyResult:
    """单个 fixture 的校验结果；``ok`` 为 False 时 ``problems`` 非空。"""

    name: str
    ok: bool
    problems: tuple[str, ...]


def load_manifest(path: Path) -> Manifest:
    """读取并结构化 fixture 清单；文件缺失或字段非法抛 :class:`FixtureError`。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FixtureError(f"找不到 fixture 清单：{path}") from exc
    except json.JSONDecodeError as exc:
        raise FixtureError(f"解析 fixture 清单失败：{path}：{exc}") from exc
    try:
        fixtures = tuple(
            Fixture(
                name=str(fx["name"]),
                oss_key=str(fx["oss_key"]),
                sha256=str(fx["sha256"]),
                size_bytes=int(fx["size_bytes"]),
                codec=str(fx["codec"]),
                duration_seconds=float(fx["duration_seconds"]),
            )
            for fx in raw["fixtures"]
        )
        return Manifest(
            bucket=str(raw["bucket"]),
            endpoint=str(raw["endpoint"]),
            region=str(raw["region"]),
            dest_dir=str(raw["dest_dir"]),
            fixtures=fixtures,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FixtureError(f"fixture 清单字段不完整或非法：{path}：{exc}") from exc


def sha256_of(path: Path) -> str:
    """流式计算文件 sha256（大文件不一次性读入内存）。"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(_CHUNK_SIZE), b""):
            h.update(block)
    return h.hexdigest()


def probe_media(path: Path) -> MediaInfo:
    """用 ffprobe 探测真实容器/编码/时长，不信任文件扩展名。

    ffprobe 缺失或探测失败抛 :class:`FixtureError`。
    """
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise FixtureError(
            "未找到 ffprobe，请先安装 ffmpeg（macOS：brew install ffmpeg）。"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise FixtureError(f"ffprobe 探测失败：{path}：{exc.stderr.strip()}") from exc

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise FixtureError(f"ffprobe 输出非 JSON：{path}：{exc}") from exc

    fmt = data.get("format") or {}
    streams = data.get("streams") or []

    duration_raw = fmt.get("duration")
    if duration_raw is None:
        for stream in streams:
            if stream.get("duration") is not None:
                duration_raw = stream["duration"]
                break
    if duration_raw is None:
        raise FixtureError(f"ffprobe 未返回有效 duration：{path}")
    try:
        duration = float(duration_raw)
    except (TypeError, ValueError) as exc:
        raise FixtureError(f"ffprobe 未返回有效 duration：{path}") from exc

    codec_names = tuple(
        str(stream["codec_name"]) for stream in streams if stream.get("codec_name")
    )
    return MediaInfo(
        duration=duration,
        format_name=str(fmt.get("format_name", "")),
        codec_names=codec_names,
    )


def codec_matches(fixture: Fixture, info: MediaInfo) -> bool:
    """容器/编码是否匹配声明的 ``codec``。

    - ``wav``：ffprobe format_name 含 ``wav`` 或流编码为 ``pcm_*``。
    - ``m4a``：format_name 含 ``m4a``/``mp4``（容器为 ``mov,mp4,m4a,...``）
      或任一流编码为 ``aac``（m4a 容器内通常为 AAC）。
    """
    fmt = info.format_name.lower()
    codecs = [c.lower() for c in info.codec_names]
    if fixture.codec == "wav":
        return "wav" in fmt or any(c.startswith("pcm") for c in codecs)
    if fixture.codec == "m4a":
        return "m4a" in fmt or "mp4" in fmt or "aac" in codecs
    return fixture.codec.lower() in fmt


def verify_fixture(fixture: Fixture, path: Path, *, check_media: bool = True) -> VerifyResult:
    """校验单个本地 fixture，只读，不下载、不修改文件。

    ``check_media=False`` 时跳过 ffprobe 探测（仅校验存在性与 sha256）。
    """
    problems: list[str] = []

    if not path.is_file():
        problems.append(f"{fixture.name}：文件缺失（{path}）")
        return VerifyResult(name=fixture.name, ok=False, problems=tuple(problems))

    actual_sha = sha256_of(path)
    if actual_sha != fixture.sha256:
        problems.append(
            f"{fixture.name}：sha256 不匹配（期望 {fixture.sha256}，实际 {actual_sha}）"
        )

    if check_media:
        info = probe_media(path)
        delta = abs(info.duration - fixture.duration_seconds)
        if delta > DURATION_TOLERANCE_SECONDS:
            problems.append(
                f"{fixture.name}：duration 超出容差 "
                f"±{DURATION_TOLERANCE_SECONDS:.0f}s"
                f"（期望 ≈{fixture.duration_seconds:.0f}s，实际 {info.duration:.2f}s）"
            )
        if not codec_matches(fixture, info):
            problems.append(
                f"{fixture.name}：codec/容器不匹配（期望 {fixture.codec}，"
                f"实际 format={info.format_name} codecs={','.join(info.codec_names)}）"
            )

    return VerifyResult(name=fixture.name, ok=not problems, problems=tuple(problems))
