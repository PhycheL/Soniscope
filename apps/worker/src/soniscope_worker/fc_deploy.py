"""FC 3.0 函数打包 / 备份 / 部署 / 回滚 / 日志（US-005，``make deploy-fc`` 等）。

为阿里云 FC 3.0 顶级 Web 函数建立源码组织、打包、备份、部署、回滚和日志查看能力，
让后续函数代码（US-006 / US-007 / US-009）可以脚本化上线。

设计要点（与 ``verify_prep`` 一致，便于 mypy strict + pytest 覆盖，遵循 AGENTS
「单元测试 mock 云端依赖」）：

* 纯逻辑（命名映射、打包、sha256、备份/日志路径、报告渲染）无云端 IO，可直接单测。
* 一切云端 / 网络 IO 收敛到 ``FcApi`` 协议；``RealFcApi`` 用 lazy import 调用云 SDK
  （``alibabacloud-fc20230330`` 仅部署脚本使用、不随函数代码打包），缺 SDK 抛
  ``FcApiError`` 并给安装指引；单测注入 ``FakeFcApi`` 不触网。
* 部署只更新**代码包**，不改 FC 环境变量 / 触发器 / 运行时规格 / 公网 URL。
* 备份只记录环境变量**名**，绝不记录值；报告 / 日志绝不打印任何 AK Secret。
"""

from __future__ import annotations

import datetime
import hashlib
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

# ── 真实云资源登记（runbook / tech-spec，勿"修正"拼写）─────────────────────────
# 云端函数名为 kebab-case；URL 子域名 issue-ce**d**ential 确实少一个 r，是真实 URL。
FUNCTIONS: tuple[str, ...] = ("issue-credential", "verify-upload")
FUNCTION_URLS: dict[str, str] = {
    "issue-credential": "https://issue-cedential-ottfirocds.cn-beijing.fcapp.run",
    "verify-upload": "https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run",
}
REGION = "cn-beijing"
# RAM 账号 ID（来自 RAM Role ARN），用于 FC 3.0 endpoint 拼接。
ALIYUN_ACCOUNT_ID = "1633875501759333"

LOG_LOOKBACK_HOURS = 1.0
# 打包时排除的目录 / 文件名片段。
EXCLUDE_DIR_NAMES = frozenset({"__pycache__"})
EXCLUDE_SUFFIXES = (".pyc", ".pyo")
# FC 共享模块（US-006）：随每个函数代码一起 vendoring 到包根，使两函数都能 import fc_shared。
SHARED_PARENT = ("apps", "fc", "shared")  # 含 fc_shared 包
SHARED_PACKAGE = "fc_shared"


class FcDeployError(Exception):
    """部署参数错误（未知函数名、源码缺失、无备份等）。"""


class FcApiError(Exception):
    """云端 / 网络 IO 无法执行（缺 SDK、缺凭证、调用失败）时抛出。"""


# ── 结构化结果 ───────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CurlResult:
    """函数公网 URL 存活验证结果。"""

    url: str
    reachable: bool
    status: int | None
    error: str = ""


@dataclass(frozen=True)
class PackageResult:
    """单个函数打包产物。"""

    function: str
    staging_dir: Path
    zip_path: Path
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class DeployRecord:
    """单个函数一次部署（或回滚）的记录。"""

    function: str
    ok: bool
    sha256: str
    upload_seconds: float
    backup_path: Path | None
    curl: CurlResult | None
    detail: str = ""


# ── IO 注入点（单测用 Fake 替换）─────────────────────────────────────────────
class FcApi(Protocol):
    """所有 FC 云端 / 网络 IO 的注入点。"""

    def download_code(self, function: str) -> bytes: ...

    def env_var_names(self, function: str) -> list[str]: ...

    def install_deps(self, staging_dir: Path, requirements: list[str]) -> None: ...

    def update_code(self, function: str, zip_bytes: bytes) -> None: ...

    def curl(self, url: str) -> CurlResult: ...

    def fetch_logs(self, function: str, hours: float) -> list[str]: ...


# ── 纯逻辑（无 IO，直接单测）────────────────────────────────────────────────
def source_dir_name(function: str) -> str:
    """云端函数名（kebab-case）→ 代码目录名（snake_case）。"""
    return function.replace("-", "_")


def resolve_functions(function: str | None) -> list[str]:
    """``None`` / 空 → 全部函数；否则校验单个函数名（未知则报错）。"""
    if function is None or not function.strip():
        return list(FUNCTIONS)
    name = function.strip()
    if name not in FUNCTIONS:
        raise FcDeployError(f"未知 FC 函数 {name!r}；支持：{', '.join(FUNCTIONS)}")
    return [name]


def function_url(function: str) -> str:
    """返回函数公网 URL（未知函数报错）。"""
    if function not in FUNCTION_URLS:
        raise FcDeployError(f"未知 FC 函数 {function!r}；支持：{', '.join(FUNCTIONS)}")
    return FUNCTION_URLS[function]


def read_requirements(req_path: Path) -> list[str]:
    """读取 requirements.txt 的非空非注释行（缺失则空列表）。"""
    if not req_path.is_file():
        return []
    lines: list[str] = []
    for raw in req_path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def _should_copy(path: Path) -> bool:
    if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
        return False
    return path.suffix not in EXCLUDE_SUFFIXES


def _copy_tree(src: Path, dst: Path) -> None:
    for item in sorted(src.rglob("*")):
        if not item.is_file() or not _should_copy(item.relative_to(src)):
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def zip_dir(staging: Path, zip_path: Path) -> tuple[str, int]:
    """把暂存目录打成确定性 zip（按路径排序），返回（sha256, 字节数）。"""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in staging.rglob("*") if p.is_file())
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(staging).as_posix())
    data = zip_path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def fc_build_root(repo_root: Path) -> Path:
    """打包 / 备份 / 日志根目录 ``build/fc/``（已 gitignore）。"""
    return repo_root / "build" / "fc"


def backup_dir(build_root: Path, timestamp: str) -> Path:
    return build_root / "backup" / timestamp


def log_path(build_root: Path, timestamp: str) -> Path:
    return build_root / "logs" / f"deploy-{timestamp}.log"


def _vendor_shared(repo_root: Path, staging: Path) -> None:
    """把 ``apps/fc/shared/fc_shared`` vendoring 到函数包根（US-006）。

    使部署后的函数能 ``import fc_shared``。共享包不存在时静默跳过（便于单测用临时仓库）。
    """
    shared_pkg = repo_root.joinpath(*SHARED_PARENT) / SHARED_PACKAGE
    if shared_pkg.is_dir():
        _copy_tree(shared_pkg, staging / SHARED_PACKAGE)


def package_function(repo_root: Path, function: str, build_root: Path, api: FcApi) -> PackageResult:
    """打包单个函数代码及运行依赖到 ``build/fc/<function_name>/`` 与同名 zip。"""
    name = source_dir_name(function)
    src = repo_root / "apps" / "fc" / name
    if not src.is_dir():
        raise FcDeployError(f"FC 函数源码目录不存在：{src}")
    staging = build_root / name
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    _copy_tree(src, staging)
    _vendor_shared(repo_root, staging)
    reqs = read_requirements(src / "requirements.txt")
    if reqs:
        api.install_deps(staging, reqs)
    zip_path = build_root / f"{name}.zip"
    sha, size = zip_dir(staging, zip_path)
    return PackageResult(function, staging, zip_path, sha, size)


def find_latest_backup(build_root: Path, function: str) -> Path | None:
    """找指定函数最新备份 zip（按时间戳目录名字典序，即时间序）。"""
    backup_root = build_root / "backup"
    if not backup_root.is_dir():
        return None
    name = source_dir_name(function)
    existing = [
        d / f"{name}.zip"
        for d in sorted(backup_root.iterdir(), key=lambda p: p.name)
        if d.is_dir() and (d / f"{name}.zip").is_file()
    ]
    return existing[-1] if existing else None


def curl_ok(curl: CurlResult) -> bool:
    """存活验证通过：可达且响应不是 5xx。"""
    if not curl.reachable:
        return False
    return curl.status is None or not (500 <= curl.status < 600)


def format_deploy_log(records: Sequence[DeployRecord], timestamp: str, action: str) -> list[str]:
    """渲染部署日志行（含函数名、zip sha256、上传耗时、curl 存活验证结果）。"""
    lines = [f"# SoniScope FC {action} {timestamp}"]
    for r in records:
        if r.curl is None:
            curl = "n/a"
        else:
            curl = f"reachable={r.curl.reachable} status={r.curl.status}"
            if r.curl.error:
                curl += f" error={r.curl.error}"
        backup = str(r.backup_path) if r.backup_path else "none"
        line = (
            f"function={r.function} ok={r.ok} sha256={r.sha256} "
            f"upload_seconds={r.upload_seconds:.3f} backup={backup} curl=({curl})"
        )
        if r.detail:
            line += f" detail={r.detail}"
        lines.append(line)
    return lines


def format_report(records: Sequence[DeployRecord], action: str, log_file: Path) -> list[str]:
    """渲染人类可读 pass/fail 汇总（绝不含 AK Secret）。"""
    lines: list[str] = []
    passed = sum(1 for r in records if r.ok)
    for r in records:
        mark = "PASS" if r.ok else "FAIL"
        curl = ""
        if r.curl is not None:
            curl = f"，curl {'可达' if r.curl.reachable else '不可达'}"
            if r.curl.status is not None:
                curl += f" HTTP {r.curl.status}"
        line = f"[{mark}] {r.function} — sha256={r.sha256[:12]}…{curl}"
        if r.detail:
            line += f"（{r.detail}）"
        lines.append(line)
    lines.append("")
    lines.append(f"汇总：{action} {passed}/{len(records)} 成功")
    lines.append(f"部署日志：{log_file}")
    return lines


# ── 编排：备份 → 打包 → 部署 → 存活验证 ─────────────────────────────────────
def _write_backup(api: FcApi, build_root: Path, function: str, timestamp: str) -> Path:
    """下载线上代码与环境变量名快照（只记名、不记值），写入备份目录。"""
    code = api.download_code(function)
    name = source_dir_name(function)
    dest_dir = backup_dir(build_root, timestamp)
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / f"{name}.zip"
    zip_path.write_bytes(code)
    # 仅记录环境变量名，绝不写值（安全红线）。
    names = api.env_var_names(function)
    names_file = dest_dir / f"{name}.env-names.txt"
    names_file.write_text("\n".join(sorted(names)) + ("\n" if names else ""), encoding="utf-8")
    return zip_path


def deploy_one(
    api: FcApi, repo_root: Path, build_root: Path, function: str, timestamp: str
) -> DeployRecord:
    """部署单个函数：备份（best-effort）→ 打包 → 仅更新代码 → curl 存活验证。"""
    detail: list[str] = []
    backup_path: Path | None = None
    try:
        backup_path = _write_backup(api, build_root, function, timestamp)
    except FcApiError as exc:
        # 首次部署时线上可能尚无代码可备份，不阻断部署。
        detail.append(f"备份跳过：{exc}")

    pkg = package_function(repo_root, function, build_root, api)

    start = time.monotonic()
    try:
        api.update_code(function, pkg.zip_path.read_bytes())
    except FcApiError as exc:
        return DeployRecord(
            function=function,
            ok=False,
            sha256=pkg.sha256,
            upload_seconds=time.monotonic() - start,
            backup_path=backup_path,
            curl=None,
            detail="；".join([*detail, f"上传失败：{exc}"]),
        )
    upload_seconds = time.monotonic() - start

    curl = api.curl(function_url(function))
    ok = curl_ok(curl)
    if not ok:
        detail.append("curl 存活验证未通过")
    return DeployRecord(
        function=function,
        ok=ok,
        sha256=pkg.sha256,
        upload_seconds=upload_seconds,
        backup_path=backup_path,
        curl=curl,
        detail="；".join(detail),
    )


def rollback_one(
    api: FcApi, build_root: Path, function: str, timestamp: str
) -> DeployRecord:
    """从最新备份恢复单个函数代码。"""
    backup_path = find_latest_backup(build_root, function)
    if backup_path is None:
        raise FcDeployError(
            f"未找到 {function} 的备份（{build_root / 'backup'} 下无 "
            f"{source_dir_name(function)}.zip）；请先成功部署一次。"
        )
    start = time.monotonic()
    try:
        api.update_code(function, backup_path.read_bytes())
    except FcApiError as exc:
        return DeployRecord(
            function=function,
            ok=False,
            sha256="",
            upload_seconds=time.monotonic() - start,
            backup_path=backup_path,
            curl=None,
            detail=f"回滚上传失败：{exc}",
        )
    upload_seconds = time.monotonic() - start
    sha = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    curl = api.curl(function_url(function))
    ok = curl_ok(curl)
    return DeployRecord(
        function=function,
        ok=ok,
        sha256=sha,
        upload_seconds=upload_seconds,
        backup_path=backup_path,
        curl=curl,
        detail="" if ok else "curl 存活验证未通过",
    )


# ── 顶层入口（CLI 调用）─────────────────────────────────────────────────────
def default_repo_root() -> Path:
    """从本文件位置推导仓库根（apps/worker/src/soniscope_worker/fc_deploy.py → 上溯 4 级）。"""
    return Path(__file__).resolve().parents[4]


def _now_stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _write_log(
    build_root: Path, records: Sequence[DeployRecord], timestamp: str, action: str
) -> Path:
    log_file = log_path(build_root, timestamp)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(format_deploy_log(records, timestamp, action)) + "\n"
    log_file.write_text(body, encoding="utf-8")
    return log_file


def run_deploy(
    function: str | None,
    *,
    api: FcApi | None = None,
    repo_root: Path | None = None,
    timestamp: str | None = None,
) -> tuple[list[str], int]:
    """执行部署（单个或全部函数），返回（报告行, 退出码）。"""
    root = repo_root or default_repo_root()
    build_root = fc_build_root(root)
    ts = timestamp or _now_stamp()
    used_api = api or RealFcApi()
    try:
        funcs = resolve_functions(function)
    except FcDeployError as exc:
        return ([f"[FAIL] {exc}"], 1)

    records: list[DeployRecord] = []
    for fn in funcs:
        try:
            records.append(deploy_one(used_api, root, build_root, fn, ts))
        except (FcDeployError, FcApiError) as exc:
            records.append(
                DeployRecord(fn, False, "", 0.0, None, None, detail=str(exc))
            )
    log_file = _write_log(build_root, records, ts, "deploy")
    lines = format_report(records, "部署", log_file)
    return lines, (0 if all(r.ok for r in records) else 1)


def run_rollback(
    function: str,
    *,
    api: FcApi | None = None,
    repo_root: Path | None = None,
    timestamp: str | None = None,
) -> tuple[list[str], int]:
    """从最新备份回滚指定函数，返回（报告行, 退出码）。"""
    root = repo_root or default_repo_root()
    build_root = fc_build_root(root)
    ts = timestamp or _now_stamp()
    used_api = api or RealFcApi()
    if not function or not function.strip():
        return (["[FAIL] rollback-fc 需要 FUNCTION=<name> 参数"], 1)
    try:
        funcs = resolve_functions(function)
    except FcDeployError as exc:
        return ([f"[FAIL] {exc}"], 1)

    records: list[DeployRecord] = []
    for fn in funcs:
        try:
            records.append(rollback_one(used_api, build_root, fn, ts))
        except (FcDeployError, FcApiError) as exc:
            records.append(DeployRecord(fn, False, "", 0.0, None, None, detail=str(exc)))
    log_file = _write_log(build_root, records, ts, "rollback")
    lines = format_report(records, "回滚", log_file)
    return lines, (0 if all(r.ok for r in records) else 1)


def run_fc_logs(
    function: str,
    *,
    api: FcApi | None = None,
    repo_root: Path | None = None,
    hours: float = LOG_LOOKBACK_HOURS,
) -> tuple[list[str], int]:
    """拉取近 N 小时 FC 日志；日志服务未配置时输出明确诊断。"""
    used_api = api or RealFcApi()
    if not function or not function.strip():
        return (["[FAIL] fc-logs 需要 FUNCTION=<name> 参数"], 1)
    try:
        funcs = resolve_functions(function)
    except FcDeployError as exc:
        return ([f"[FAIL] {exc}"], 1)
    fn = funcs[0]
    try:
        entries = used_api.fetch_logs(fn, hours)
    except FcApiError as exc:
        return (
            [
                f"[诊断] 无法拉取 {fn} 近 {hours:g} 小时日志：{exc}",
                "        ↳ 确认 FC 函数已接入阿里云日志服务（SLS）并配置 project/logstore"
                "（见 tech-spec §6.4）。",
            ],
            1,
        )
    if not entries:
        return ([f"[空] {fn} 近 {hours:g} 小时无日志记录。"], 0)
    return ([f"# {fn} 近 {hours:g} 小时日志（{len(entries)} 行）", *entries], 0)


# ── 真实云端 IO（lazy import alibabacloud-fc20230330；缺失抛 FcApiError）──────
class RealFcApi:
    """真实 FC 云端 / 网络 IO；构造无副作用，调用时才触网。

    依赖隔离：``alibabacloud-fc20230330`` 仅在部署脚本使用、不随函数代码打包（tech-spec §6.4）。
    """

    def _client(self) -> Any:
        import os

        ak_id = os.environ.get("ALIYUN_DEPLOY_AK_ID", "").strip()
        ak_secret = os.environ.get("ALIYUN_DEPLOY_AK_SECRET", "").strip()
        if not ak_id or not ak_secret:
            raise FcApiError(
                "缺少部署凭证 ALIYUN_DEPLOY_AK_ID/ALIYUN_DEPLOY_AK_SECRET"
                "（tech-spec §6.4）；请在本地 .env 注入后重跑。"
            )
        try:
            from alibabacloud_fc20230330.client import Client as FcClient
            from alibabacloud_tea_openapi import models as open_api_models
        except ImportError as exc:  # pragma: no cover - 依赖缺失路径
            raise FcApiError(
                "缺少依赖 alibabacloud-fc20230330 / alibabacloud-tea-openapi，请 "
                "`uv add --package soniscope-worker alibabacloud-fc20230330 "
                "alibabacloud-tea-openapi`。"
            ) from exc
        cfg = open_api_models.Config(access_key_id=ak_id, access_key_secret=ak_secret)
        cfg.endpoint = f"{ALIYUN_ACCOUNT_ID}.{REGION}.fc.aliyuncs.com"
        return FcClient(cfg)

    def download_code(self, function: str) -> bytes:
        client = self._client()
        try:
            resp = client.get_function_code(function)
            url = getattr(getattr(resp, "body", None), "url", None)
            if not url:
                raise FcApiError(f"线上 {function} 无可下载代码 URL（疑似首次部署）。")
        except FcApiError:
            raise
        except Exception as exc:  # noqa: BLE001 - 任意失败收敛为 FcApiError（不泄漏明文）
            raise FcApiError(f"获取线上代码失败：{type(exc).__name__}") from exc
        try:
            req = urllib.request.Request(str(url), method="GET")  # noqa: S310
            with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
                return bytes(r.read())
        except (urllib.error.URLError, OSError) as exc:
            raise FcApiError(f"下载线上代码失败：{exc}") from exc

    def env_var_names(self, function: str) -> list[str]:
        client = self._client()
        try:
            resp = client.get_function(function)
            env = getattr(getattr(resp, "body", None), "environment_variables", None)
            if isinstance(env, dict):
                return [str(k) for k in env]
            return []
        except Exception as exc:  # noqa: BLE001
            raise FcApiError(f"读取函数环境变量名失败：{type(exc).__name__}") from exc

    def install_deps(self, staging_dir: Path, requirements: list[str]) -> None:
        # 运行依赖装入暂存目录（与代码一起打包），仅在 requirements.txt 有非注释行时调用。
        import subprocess

        cmd = [
            "uv",
            "pip",
            "install",
            "--target",
            str(staging_dir),
            *requirements,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
        except FileNotFoundError as exc:
            raise FcApiError("未找到 uv，无法安装 FC 运行依赖。") from exc
        except subprocess.CalledProcessError as exc:
            raise FcApiError(f"安装 FC 运行依赖失败（exit={exc.returncode}）。") from exc

    def update_code(self, function: str, zip_bytes: bytes) -> None:
        import base64

        client = self._client()
        try:
            from alibabacloud_fc20230330 import models as fc_models
        except ImportError as exc:  # pragma: no cover
            raise FcApiError("缺少依赖 alibabacloud-fc20230330。") from exc
        try:
            # 只更新代码，不传 environment_variables / triggers / 运行规格，保证不改这些。
            code = fc_models.InputCodeLocation(zip_file=base64.b64encode(zip_bytes).decode("ascii"))
            body = fc_models.UpdateFunctionInput(code=code)
            req = fc_models.UpdateFunctionRequest(body=body)
            client.update_function(function, req)
        except Exception as exc:  # noqa: BLE001
            raise FcApiError(f"更新函数代码失败：{type(exc).__name__}") from exc

    def curl(self, url: str) -> CurlResult:
        req = urllib.request.Request(url, method="GET")  # noqa: S310 - 固定 https 常量 URL
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                return CurlResult(url=url, reachable=True, status=int(resp.status))
        except urllib.error.HTTPError as exc:
            return CurlResult(url=url, reachable=True, status=int(exc.code))
        except urllib.error.URLError as exc:
            return CurlResult(url=url, reachable=False, status=None, error=str(exc.reason))
        except OSError as exc:
            return CurlResult(url=url, reachable=False, status=None, error=str(exc))

    def fetch_logs(self, function: str, hours: float) -> list[str]:
        # FC 运行时日志接入阿里云 SLS；未配置 project/logstore 时给明确诊断。
        client = self._client()
        try:
            resp = client.get_function(function)
            log_config = getattr(getattr(resp, "body", None), "log_config", None)
            project = getattr(log_config, "project", None)
            logstore = getattr(log_config, "logstore", None)
        except Exception as exc:  # noqa: BLE001
            raise FcApiError(f"读取函数日志配置失败：{type(exc).__name__}") from exc
        if not project or not logstore:
            raise FcApiError("函数未配置 SLS 日志服务（project/logstore 为空）。")
        raise FcApiError(
            f"已配置 SLS（project={project} logstore={logstore}），"
            "但日志拉取需 aliyun-log-python-sdk（本期未集成，US-008 联调时补全）。"
        )
