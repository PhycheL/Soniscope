#!/usr/bin/env python3
"""拉取测试音频 fixture。

音频二进制不进 git，存于阿里云 OSS 私有 bucket。本脚本读取
`tests/audio/fixtures.manifest.json`，用工作目录下 `config.yaml` 中的 OSS
只读凭证，把每个 fixture 下载到本地并按 sha256 校验。

工作目录按以下优先级解析（与 scripts/gen_worker_config.sh 一致，以 runbook 为准）：
runbook §7 的 `SONISCOPE_HOME` → 环境变量 `$SONISCOPE_HOME` → `~/SoniScope`。

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
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "tests" / "audio" / "fixtures.manifest.json"
RUNBOOK_PATH = REPO_ROOT / "docs" / "runbook" / "cloud-setup.md"
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


def runbook_home() -> "str | None":
    """从 runbook §7「工作目录环境变量：`SONISCOPE_HOME=...`」读取工作目录。

    runbook（docs/runbook/cloud-setup.md）是工作目录的权威来源，与
    scripts/gen_worker_config.sh 保持一致：两个脚本必须指向同一个 config.yaml。
    """
    if not RUNBOOK_PATH.is_file():
        return None
    m = re.search(r"SONISCOPE_HOME=([^\s`]+)", RUNBOOK_PATH.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def resolve_config_path() -> Path:
    # 目录来源优先级（以 runbook 为准）：runbook §7 → $SONISCOPE_HOME → ~/SoniScope
    candidates = []
    rb = runbook_home()
    if rb:
        candidates.append(Path(rb).expanduser() / "config.yaml")
    home = os.environ.get("SONISCOPE_HOME")
    if home:
        candidates.append(Path(home).expanduser() / "config.yaml")
    candidates.append(Path("~/SoniScope/config.yaml").expanduser())

    # 去重保序
    seen: set[Path] = set()
    candidates = [p for p in candidates if not (p in seen or seen.add(p))]

    for p in candidates:
        if p.is_file():
            return p
    tried = "\n  ".join(str(p) for p in candidates)
    _fail(
        "找不到 config.yaml，已尝试以下路径：\n  "
        f"{tried}\n"
        "请先运行 scripts/gen_worker_config.sh 生成运行时配置，其中需包含 "
        "oss.access_key_id / oss.access_key_secret（soniscope-local-reader 只读凭证）。"
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


def _import_oss():
    try:
        import alibabacloud_oss_v2 as oss  # type: ignore

        return oss
    except ImportError:
        _fail(
            "缺少依赖 alibabacloud-oss-v2，请先 "
            "`pip install alibabacloud-oss-v2`（或在 worker 环境中运行）。"
        )


def build_client(manifest: dict, config_path: Path):
    oss = _import_oss()
    ak_id, ak_secret = load_oss_credentials(config_path)
    cfg = oss.config.load_default()
    cfg.credentials_provider = oss.credentials.StaticCredentialsProvider(
        access_key_id=ak_id, access_key_secret=ak_secret
    )
    cfg.region = manifest["region"]
    cfg.endpoint = manifest["endpoint"]
    return oss.Client(cfg)


def download_to(client, manifest: dict, oss_key: str, dest: Path) -> None:
    """下载单个 object 到本地文件（V2 SDK 内置 CRC64 校验）。"""
    oss = _import_oss()
    client.get_object_to_file(
        oss.GetObjectRequest(bucket=manifest["bucket"], key=oss_key),
        str(dest),
    )


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

    client = None  # 延迟构建：纯校验或全部命中时无需凭证
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

        if client is None:
            client = build_client(manifest, resolve_config_path())

        part = dest_dir / f"{name}.part"
        try:
            print(f"[fetch-fixtures] 下载：{fx['oss_key']} → {name}")
            download_to(client, manifest, fx["oss_key"], part)
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
