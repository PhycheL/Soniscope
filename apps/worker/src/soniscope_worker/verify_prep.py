"""US-001 人工准备产物一键校验（US-004，`make verify-prep`）。

本模块对 runbook 中已人工准备好的 OSS / RAM-STS / FC / ASR / 测试音频 / Worker
环境逐项做**真实**可用性校验，输出单项 pass/fail 汇总和可操作修复指引，全部通过时
打印 ``✅ US-001 preparation verified. Ready for US-003+``。

设计要点（便于 mypy strict + pytest 覆盖，遵循 AGENTS「单元测试 mock 云端依赖」）：

* 纯校验逻辑（`check_*`）只对**已取回的结构化数据**做判断，无任何 IO，可直接单测。
* 一切 IO / 云端调用收敛到 `Probes` 协议；`RealProbes` 用 lazy import 真实调用云 SDK，
  缺少 SDK 时抛 `ProbeError` 并给安装指引；单测注入 `FakeProbes` 不触网。
* 任何路径都**绝不打印 AK Secret 明文**：detail 只含资源名 / 区域 / 状态码 / 错误码。
"""

from __future__ import annotations

import os
import shutil
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from soniscope_worker.config import (
    ConfigError,
    SoniScopeConfig,
    config_path,
    config_permission_is_600,
    load_config,
)
from soniscope_worker.fixtures import (
    FixtureError,
    load_manifest,
    verify_fixture,
)

# ── runbook / tech-spec 登记的期望值（真实云资源，勿"修正"拼写）────────────────
EXPECTED_BUCKET = "soniscope-audio"
EXPECTED_REGION = "cn-beijing"
EXPECTED_ACL = "private"
RAM_ROLE_ARN = "acs:ram::1633875501759333:role/soniscope-uploader-role"
STS_MAX_DURATION_SECONDS = 900
MIN_PYTHON: tuple[int, int] = (3, 11)
MIN_DISK_BYTES = 50 * 1024**3  # 50 GiB
REQUIRED_TOOLS: tuple[str, ...] = ("ffmpeg", "ffprobe")
# 子域名 issue-ce**d**ential 确实少一个 r，是阿里云分配的真实 URL，禁止"修正"。
FC_ISSUE_URL = "https://issue-cedential-ottfirocds.cn-beijing.fcapp.run"
FC_VERIFY_URL = "https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run"

SAMPLE_FIXTURE = "sample-20s.wav"
SUCCESS_LINE = "✅ US-001 preparation verified. Ready for US-003+"

# transcript.json 结构必备键（tech-spec §3.4）。
NLS_RESULT_KEYS: tuple[str, ...] = ("segments", "language", "model", "params_version", "provider")


class ProbeError(Exception):
    """云端探针无法执行（如缺少 SDK、缺少部署凭证）时抛出。"""


# ── 结构化探针返回值 ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CheckResult:
    """单项校验结果。"""

    name: str
    ok: bool
    detail: str = ""
    fix_hint: str = ""


@dataclass(frozen=True)
class BucketInfo:
    """OSS Bucket 元信息。"""

    exists: bool
    region: str
    acl: str


@dataclass(frozen=True)
class StsCase:
    """一个 STS 越权反例的结果：``denied`` 表示如预期被拒。"""

    name: str
    denied: bool
    error_code: str


@dataclass(frozen=True)
class FcProbe:
    """FC 公网 URL 可达性探测结果。"""

    url: str
    reachable: bool
    status: int | None
    error: str = ""


@dataclass(frozen=True)
class EnvInfo:
    """本机环境探测结果。"""

    python_version: tuple[int, int, int]
    home_writable: bool
    disk_free_bytes: int
    tools: Mapping[str, str | None]


class Probes(Protocol):
    """所有 IO / 云端调用的注入点（单测用 Fake 替换）。"""

    def env_info(self, home: Path) -> EnvInfo: ...

    def oss_bucket_info(self, cfg: SoniScopeConfig) -> BucketInfo: ...

    def sts_escape(self, cfg: SoniScopeConfig) -> Sequence[StsCase]: ...

    def fc_curl(self, url: str) -> FcProbe: ...

    def nls_transcribe(self, cfg: SoniScopeConfig, audio: Path) -> Mapping[str, object]: ...

    def fixture_results(self, audio_dir: Path, manifest_path: Path) -> Sequence[CheckResult]: ...


# ── 纯校验逻辑（无 IO，直接单测）─────────────────────────────────────────────
def check_oss_bucket(info: BucketInfo) -> CheckResult:
    """Bucket 存在、region=cn-beijing、ACL=private。"""
    problems: list[str] = []
    if not info.exists:
        problems.append(f"Bucket {EXPECTED_BUCKET} 不存在或不可访问")
    if info.region != EXPECTED_REGION:
        problems.append(f"region={info.region!r}，期望 {EXPECTED_REGION!r}")
    if info.acl != EXPECTED_ACL:
        problems.append(f"ACL={info.acl!r}，期望 {EXPECTED_ACL!r}")
    ok = not problems
    return CheckResult(
        name="OSS Bucket（存在 / region / private ACL）",
        ok=ok,
        detail="OK" if ok else "；".join(problems),
        fix_hint=""
        if ok
        else "见 runbook §1：确认 Bucket soniscope-audio、region cn-beijing、私有读写。",
    )


def check_env(info: EnvInfo) -> list[CheckResult]:
    """Python >= 3.11、SONISCOPE_HOME 可写、磁盘 >= 50GB、ffmpeg/ffprobe 可执行。"""
    results: list[CheckResult] = []

    py_ok = info.python_version[:2] >= MIN_PYTHON
    py_str = ".".join(str(p) for p in info.python_version)
    results.append(
        CheckResult(
            name="Python 版本 >= 3.11",
            ok=py_ok,
            detail=f"当前 {py_str}",
            fix_hint="" if py_ok else "升级到 Python 3.11+（见 runbook §7）。",
        )
    )

    results.append(
        CheckResult(
            name="SONISCOPE_HOME 可写",
            ok=info.home_writable,
            detail="可写" if info.home_writable else "不可写",
            fix_hint="" if info.home_writable else "确认 $SONISCOPE_HOME 存在且当前用户可写。",
        )
    )

    disk_ok = info.disk_free_bytes >= MIN_DISK_BYTES
    free_gib = info.disk_free_bytes / 1024**3
    results.append(
        CheckResult(
            name="可用磁盘 >= 50GB",
            ok=disk_ok,
            detail=f"可用 {free_gib:.1f} GiB",
            fix_hint="" if disk_ok else "清理磁盘或更换 $SONISCOPE_HOME 到容量更大的卷。",
        )
    )

    for tool in REQUIRED_TOOLS:
        path = info.tools.get(tool)
        results.append(
            CheckResult(
                name=f"{tool} 可执行",
                ok=path is not None,
                detail=path or "未找到",
                fix_hint="" if path else f"安装 {tool}（macOS: brew install ffmpeg）。",
            )
        )
    return results


# config.yaml 中必须非空的字符串字段（dotted 路径 → 取值函数）。
def _config_required_values(cfg: SoniScopeConfig) -> dict[str, str]:
    return {
        "oss.endpoint": cfg.oss.endpoint,
        "oss.bucket": cfg.oss.bucket,
        "oss.access_key_id": cfg.oss.access_key_id,
        "oss.access_key_secret": cfg.oss.access_key_secret.get_secret_value(),
        "transcriber.name": cfg.transcriber.name,
        "transcriber.provider": cfg.transcriber.provider,
        "transcriber.model": cfg.transcriber.model,
        "transcriber.params_version": cfg.transcriber.params_version,
        "transcriber.api_endpoint": cfg.transcriber.api_endpoint,
        "transcriber.appkey": cfg.transcriber.appkey.get_secret_value(),
        "transcriber.access_key_id": cfg.transcriber.access_key_id,
        "transcriber.access_key_secret": cfg.transcriber.access_key_secret.get_secret_value(),
        "transcriber.upload_mode": cfg.transcriber.upload_mode,
    }


def check_config_security(cfg: SoniScopeConfig, path: Path, perm_is_600: bool) -> list[CheckResult]:
    """config.yaml 权限为 600 且所有必填字段非空（不打印任何字段值）。"""
    results: list[CheckResult] = []
    results.append(
        CheckResult(
            name="config.yaml 权限为 600",
            ok=perm_is_600,
            detail="600" if perm_is_600 else "权限不是 600",
            fix_hint="" if perm_is_600 else f"chmod 600 {path}",
        )
    )

    empty = [name for name, value in _config_required_values(cfg).items() if not value.strip()]
    fields_ok = not empty
    results.append(
        CheckResult(
            name="config.yaml 必填字段非空",
            ok=fields_ok,
            # 只列字段名，绝不打印字段值（含 AK Secret）。
            detail="全部非空" if fields_ok else f"空字段：{', '.join(empty)}",
            fix_hint="" if fields_ok else "在 config.yaml 中补全上述字段（见 runbook §8）。",
        )
    )
    return results


def check_sts_escape(cases: Sequence[StsCase]) -> CheckResult:
    """4 个 STS 反例必须全部如预期被拒（AccessDenied / ExpiredToken）。"""
    failed = [c.name for c in cases if not c.denied]
    ok = bool(cases) and not failed
    if not cases:
        detail = "未执行任何反例（探针无返回）"
    elif ok:
        detail = f"{len(cases)} 个反例全部如预期被拒"
    else:
        detail = "未被拒绝（疑似越权放行）：" + ", ".join(failed)
    return CheckResult(
        name="STS 单 key 越权反例（4 例全 Denied/Expired）",
        ok=ok,
        detail=detail,
        fix_hint="" if ok else (
            f"收紧 {RAM_ROLE_ARN} 的 policy 到单 object key（仅 PutObject，"
            f"有效期 <= {STS_MAX_DURATION_SECONDS}s），见 tech-spec §4.4。"
        ),
    )


def check_fc(probe: FcProbe) -> CheckResult:
    """FC 公网 URL 网络可达且响应不是 5xx。"""
    if not probe.reachable:
        ok = False
        detail = f"不可达：{probe.error}"
    elif probe.status is not None and 500 <= probe.status < 600:
        ok = False
        detail = f"HTTP {probe.status}（5xx）"
    else:
        ok = True
        detail = f"HTTP {probe.status}" if probe.status is not None else "可达"
    return CheckResult(
        name=f"FC 可达（{probe.url}）",
        ok=ok,
        detail=detail,
        fix_hint="" if ok else "确认 FC 函数已部署且公网 URL 已开启（见 runbook §3.2）。",
    )


def check_nls_result(result: Mapping[str, object]) -> CheckResult:
    """NLS 转写返回结构符合 tech-spec §3.4（segments / language / model / ...）。"""
    missing = [k for k in NLS_RESULT_KEYS if k not in result]
    segments = result.get("segments")
    seg_ok = isinstance(segments, list) and len(segments) > 0
    problems: list[str] = []
    if missing:
        problems.append(f"缺字段：{', '.join(missing)}")
    if not seg_ok:
        problems.append("segments 为空或非列表")
    ok = not problems
    return CheckResult(
        name="NLS 转写结构（tech-spec §3.4）",
        ok=ok,
        detail="结构合格，含非空 segments" if ok else "；".join(problems),
        fix_hint="" if ok else "检查 NLS appkey / AK 与 §3.4 字段映射（见 runbook §5）。",
    )


# ── 编排：拉取数据 → 跑校验 → 汇总 ──────────────────────────────────────────
@dataclass
class VerifyContext:
    """verify-prep 运行上下文（仓库内可定位的路径 + 已加载配置）。"""

    cfg: SoniScopeConfig
    config_file: Path
    perm_is_600: bool
    home: Path
    audio_dir: Path
    manifest_path: Path
    sample_audio: Path


def run_checks(probes: Probes, ctx: VerifyContext) -> list[CheckResult]:
    """执行全部校验块，返回有序结果列表（云端异常被收敛为单项 fail）。"""
    results: list[CheckResult] = []

    # B. 环境
    try:
        results.extend(check_env(probes.env_info(ctx.home)))
    except ProbeError as exc:
        results.append(CheckResult("本机环境探测", False, str(exc)))

    # C. 配置安全
    results.extend(check_config_security(ctx.cfg, ctx.config_file, ctx.perm_is_600))

    # A. OSS Bucket
    try:
        results.append(check_oss_bucket(probes.oss_bucket_info(ctx.cfg)))
    except ProbeError as exc:
        results.append(
            CheckResult(
                "OSS Bucket（存在 / region / private ACL）",
                False,
                str(exc),
                "确认已安装 alibabacloud-oss-v2 且 config.oss 凭证有效（runbook §1/§2.2）。",
            )
        )

    # D. STS 越权反例
    try:
        results.append(check_sts_escape(probes.sts_escape(ctx.cfg)))
    except ProbeError as exc:
        results.append(
            CheckResult(
                "STS 单 key 越权反例（4 例全 Denied/Expired）",
                False,
                str(exc),
                "确认部署凭证 ALIYUN_DEPLOY_AK_ID/SECRET 与 STS/OSS SDK 已就绪。",
            )
        )

    # E. FC 可达
    for url in (FC_ISSUE_URL, FC_VERIFY_URL):
        try:
            results.append(check_fc(probes.fc_curl(url)))
        except ProbeError as exc:
            results.append(CheckResult(f"FC 可达（{url}）", False, str(exc)))

    # F. NLS 转写
    try:
        results.append(check_nls_result(probes.nls_transcribe(ctx.cfg, ctx.sample_audio)))
    except ProbeError as exc:
        results.append(
            CheckResult(
                "NLS 转写结构（tech-spec §3.4）",
                False,
                str(exc),
                "确认 NLS SDK 已安装、appkey/AK 有效，且 sample-20s.wav 已就绪（runbook §5/§6）。",
            )
        )

    # G. 测试音频 fixture
    try:
        results.extend(probes.fixture_results(ctx.audio_dir, ctx.manifest_path))
    except ProbeError as exc:
        results.append(CheckResult("测试音频 fixture 校验", False, str(exc)))

    return results


def all_passed(results: Sequence[CheckResult]) -> bool:
    """是否全部通过（且至少跑了一项）。"""
    return bool(results) and all(r.ok for r in results)


def format_report(results: Sequence[CheckResult]) -> list[str]:
    """渲染人类可读的单项 pass/fail 汇总（绝不含 AK Secret）。"""
    lines: list[str] = []
    passed = sum(1 for r in results if r.ok)
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        line = f"[{mark}] {r.name}"
        if r.detail:
            line += f" — {r.detail}"
        lines.append(line)
        if not r.ok and r.fix_hint:
            lines.append(f"        ↳ 修复：{r.fix_hint}")
    lines.append("")
    lines.append(f"汇总：{passed}/{len(results)} 通过")
    if all_passed(results):
        lines.append(SUCCESS_LINE)
    else:
        lines.append("❌ US-001 准备校验未通过，请按上面修复指引处理后重跑 make verify-prep。")
    return lines


# ── 真实探针实现（lazy import 云 SDK；缺失时抛 ProbeError）───────────────────
class RealProbes:
    """真实云端 / 系统探针；构造时无副作用，调用时才触网。"""

    def env_info(self, home: Path) -> EnvInfo:
        free = shutil.disk_usage(home if home.exists() else home.anchor or Path("/")).free
        writable = home.exists() and os.access(home, os.W_OK)
        tools: dict[str, str | None] = {t: shutil.which(t) for t in REQUIRED_TOOLS}
        vi = sys.version_info
        return EnvInfo(
            python_version=(vi.major, vi.minor, vi.micro),
            home_writable=writable,
            disk_free_bytes=free,
            tools=tools,
        )

    def oss_bucket_info(self, cfg: SoniScopeConfig) -> BucketInfo:
        oss = _import_oss()
        client = _oss_client(
            oss,
            cfg.oss.endpoint,
            cfg.oss.access_key_id,
            cfg.oss.access_key_secret.get_secret_value(),
        )
        try:
            info = client.get_bucket_info(oss.GetBucketInfoRequest(bucket=cfg.oss.bucket))
            bucket = info.bucket_info
            region = getattr(bucket, "region", "") or ""
            region = region.replace("oss-", "")
            acl = str(getattr(getattr(bucket, "access_control_list", None), "grant", "") or "")
            return BucketInfo(exists=True, region=region or EXPECTED_REGION, acl=acl)
        except Exception as exc:  # noqa: BLE001 — 任意 OSS 异常都视为 Bucket 不可访问
            return BucketInfo(exists=False, region="", acl=f"error:{type(exc).__name__}")

    def sts_escape(self, cfg: SoniScopeConfig) -> Sequence[StsCase]:
        # 真实执行需部署凭证 + STS/OSS SDK + 单 key policy；此处给出明确未就绪提示，
        # 由 US-007/US-008 的 issue-credential 联调脚本承载完整反例（见 tech-spec §4.4）。
        raise ProbeError(
            "STS 越权反例需部署凭证（ALIYUN_DEPLOY_AK_ID/SECRET）与 alibabacloud-sts SDK；"
            "请在 US-007/US-008 联调环境执行，或安装 SDK 后重跑。"
        )

    def fc_curl(self, url: str) -> FcProbe:
        req = urllib.request.Request(url, method="GET")  # noqa: S310 — 固定 https 常量 URL
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                return FcProbe(url=url, reachable=True, status=int(resp.status))
        except urllib.error.HTTPError as exc:
            return FcProbe(url=url, reachable=True, status=int(exc.code))
        except urllib.error.URLError as exc:
            return FcProbe(url=url, reachable=False, status=None, error=str(exc.reason))
        except OSError as exc:  # 超时等
            return FcProbe(url=url, reachable=False, status=None, error=str(exc))

    def nls_transcribe(self, cfg: SoniScopeConfig, audio: Path) -> Mapping[str, object]:
        if not audio.is_file():
            raise ProbeError(f"测试音频缺失：{audio}（先运行 make 拉取 fixture）")
        # 真实 NLS 调用在 US-026 CloudSpeechTranscriber 落地；此处提示在该实现就绪后联调。
        raise ProbeError(
            "NLS 转写探针依赖 US-026 CloudSpeechTranscriber（alibabacloud-nls）；"
            "请在该实现就绪后通过 make test-transcribe-oss-url 联调。"
        )

    def fixture_results(self, audio_dir: Path, manifest_path: Path) -> Sequence[CheckResult]:
        try:
            manifest = load_manifest(manifest_path)
        except FixtureError as exc:
            raise ProbeError(f"读取 fixture 清单失败：{exc}") from exc
        results: list[CheckResult] = []
        for fx in manifest.fixtures:
            dest = audio_dir / fx.name
            try:
                vr = verify_fixture(fx, dest, check_media=True)
            except FixtureError as exc:
                results.append(
                    CheckResult(f"fixture {fx.name}", False, str(exc), _fixture_fix_hint())
                )
                continue
            results.append(
                CheckResult(
                    name=f"fixture {fx.name}（sha256 / duration / codec）",
                    ok=vr.ok,
                    detail="OK" if vr.ok else "；".join(vr.problems),
                    fix_hint="" if vr.ok else _fixture_fix_hint(),
                )
            )
        return results


def _fixture_fix_hint() -> str:
    from soniscope_worker.fixtures import FIX_HINT

    return FIX_HINT


def _import_oss() -> Any:
    try:
        import alibabacloud_oss_v2 as oss

        return oss
    except ImportError as exc:  # pragma: no cover - 依赖缺失路径
        raise ProbeError(
            "缺少依赖 alibabacloud-oss-v2，请 "
            "`uv add --package soniscope-worker alibabacloud-oss-v2`。"
        ) from exc


def _oss_client(oss: Any, endpoint: str, ak_id: str, ak_secret: str) -> Any:
    cfg = oss.config.load_default()
    cfg.credentials_provider = oss.credentials.StaticCredentialsProvider(
        access_key_id=ak_id, access_key_secret=ak_secret
    )
    cfg.region = EXPECTED_REGION
    cfg.endpoint = endpoint
    return oss.Client(cfg)


# ── 顶层入口（CLI 调用）─────────────────────────────────────────────────────
@dataclass
class RepoLayout:
    """仓库内可定位的固定路径（便于测试注入）。"""

    repo_root: Path
    audio_dir: Path = field(init=False)
    manifest_path: Path = field(init=False)
    sample_audio: Path = field(init=False)

    def __post_init__(self) -> None:
        self.audio_dir = self.repo_root / "tests" / "audio"
        self.manifest_path = self.audio_dir / "fixtures.manifest.json"
        self.sample_audio = self.audio_dir / SAMPLE_FIXTURE


def default_repo_root() -> Path:
    """从本文件位置推导仓库根（apps/worker/src/soniscope_worker/verify_prep.py → 上溯 4 级）。"""
    return Path(__file__).resolve().parents[4]


def build_context(layout: RepoLayout, cfg_path: Path | None = None) -> VerifyContext:
    """加载配置并组装运行上下文。"""
    path = cfg_path or config_path()
    cfg = load_config(path)
    return VerifyContext(
        cfg=cfg,
        config_file=path,
        perm_is_600=config_permission_is_600(path),
        home=path.parent,
        audio_dir=layout.audio_dir,
        manifest_path=layout.manifest_path,
        sample_audio=layout.sample_audio,
    )


def run_verify_prep(
    probes: Probes | None = None,
    layout: RepoLayout | None = None,
    cfg_path: Path | None = None,
) -> tuple[list[str], int]:
    """执行 verify-prep，返回（报告行, 退出码）。退出码 0 表示全部通过。"""
    used_layout = layout or RepoLayout(default_repo_root())
    try:
        ctx = build_context(used_layout, cfg_path)
    except ConfigError as exc:
        return (
            [
                "[FAIL] 加载 config.yaml",
                f"        ↳ {exc}",
                "",
                "❌ US-001 准备校验未通过：配置不可用。",
            ],
            1,
        )
    used_probes = probes or RealProbes()
    results = run_checks(used_probes, ctx)
    lines = format_report(results)
    return lines, (0 if all_passed(results) else 1)
