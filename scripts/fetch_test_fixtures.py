#!/usr/bin/env python3
"""拉取测试音频 fixture。

音频二进制不进 git，存于阿里云 OSS 私有 bucket。本脚本读取
`tests/audio/fixtures.manifest.json`，用 `$SONISCOPE_HOME/config.yaml`
（或 `~/SoniScope/config.yaml`）中的 OSS 只读凭证，把每个 fixture 下载到
本地并按 sha256 校验。

下载遵循项目三段式协议：先写 `<name>.part` → 校验 size + sha256 → 原子
rename 为最终文件。已存在且 sha256 匹配的文件直接跳过（幂等）。

用法：
    python scripts/fetch_test_fixtures.py            # 拉取缺失/损坏的 fixture
    python scripts/fetch_test_fixtures.py --force    # 强制重新下载全部
    python scripts/fetch_test_fixtures.py --check     # 只校验本地，不下载
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "tests" / "audio" / "fixtures.manifest.json"
_CHUNK = 1024 * 1024


def _fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"[fetch-fixtures] 错误：{msg}", file=sys.stderr)
    sys.exit(1)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(_CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def resolve_config_path() -> Path:
    home = os.environ.get("SONISCOPE_HOME")
    candidates = []
    if home:
        candidates.append(Path(home).expanduser() / "config.yaml")
    candidates.append(Path("~/SoniScope/config.yaml").expanduser())
    for p in candidates:
        if p.is_file():
            return p
    tried = "\n  ".join(str(p) for p in candidates)
    _fail(
        "找不到 config.yaml，已尝试以下路径：\n  "
        f"{tried}\n"
        "请参考 PRD US-001 (H) 准备运行时配置，其中需包含 oss.access_key_id / "
        "oss.access_key_secret（soniscope-local-reader 只读凭证）。"
    )


def load_oss_credentials(config_path: Path) -> tuple[str, str]:
    try:
        import yaml  # type: ignore
    except ImportError:
        _fail("缺少依赖 PyYAML，请先 `pip install pyyaml`（或在 worker 环境中运行）。")
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        _fail(f"解析 {config_path} 失败：{exc}")
    oss = data.get("oss") or {}
    missing = [k for k in ("access_key_id", "access_key_secret") if not oss.get(k)]
    if missing:
        _fail(
            f"{config_path} 的 oss 段缺少字段：{', '.join(missing)}。"
            "需要 soniscope-local-reader 的只读 AK。"
        )
    return str(oss["access_key_id"]), str(oss["access_key_secret"])


def build_bucket(manifest: dict, config_path: Path):
    try:
        import oss2  # type: ignore
    except ImportError:
        _fail("缺少依赖 oss2，请先 `pip install oss2`（或在 worker 环境中运行）。")
    ak_id, ak_secret = load_oss_credentials(config_path)
    auth = oss2.Auth(ak_id, ak_secret)
    return oss2.Bucket(auth, manifest["endpoint"], manifest["bucket"])


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        _fail(f"找不到清单文件：{MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="拉取并校验测试音频 fixture")
    parser.add_argument("--force", action="store_true", help="强制重新下载全部 fixture")
    parser.add_argument("--check", action="store_true", help="只校验本地文件，不下载")
    args = parser.parse_args()

    manifest = load_manifest()
    dest_dir = REPO_ROOT / manifest["dest_dir"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    fixtures = manifest["fixtures"]

    bucket = None  # 延迟构建：纯校验或全部命中时无需凭证
    ok = downloaded = skipped = 0

    for fx in fixtures:
        name = fx["name"]
        dest = dest_dir / name
        expected_sha = fx["sha256"]

        if dest.is_file() and not args.force:
            actual = sha256_of(dest)
            if actual == expected_sha:
                print(f"[fetch-fixtures] 跳过（已存在且校验通过）：{name}")
                ok += 1
                skipped += 1
                continue
            if args.check:
                print(
                    f"[fetch-fixtures] 校验失败：{name} sha256 不匹配\n"
                    f"  期望 {expected_sha}\n  实际 {actual}",
                    file=sys.stderr,
                )
                continue
            print(f"[fetch-fixtures] sha256 不匹配，重新下载：{name}")

        if args.check:
            print(f"[fetch-fixtures] 缺失：{name}", file=sys.stderr)
            continue

        if bucket is None:
            bucket = build_bucket(manifest, resolve_config_path())

        part = dest_dir / f"{name}.part"
        try:
            print(f"[fetch-fixtures] 下载：{fx['oss_key']} → {name}")
            bucket.get_object_to_file(fx["oss_key"], str(part))
            size = part.stat().st_size
            if size != fx["size_bytes"]:
                _fail(
                    f"{name} 大小不符：期望 {fx['size_bytes']} 字节，实际 {size} 字节"
                )
            actual = sha256_of(part)
            if actual != expected_sha:
                _fail(
                    f"{name} sha256 不匹配：\n  期望 {expected_sha}\n  实际 {actual}"
                )
            os.replace(part, dest)
            print(f"[fetch-fixtures] 完成：{name}")
            ok += 1
            downloaded += 1
        finally:
            if part.exists():
                part.unlink()

    total = len(fixtures)
    print(
        f"[fetch-fixtures] 汇总：{ok}/{total} 就绪"
        f"（下载 {downloaded}，跳过 {skipped}）"
    )
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
