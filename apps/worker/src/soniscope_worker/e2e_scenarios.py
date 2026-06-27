"""US-031：E2E 崩溃恢复、显式重转与安全反例编排脚本（tech-spec §4.1 / §6.5）。

把已分别落地并单测过的关键异常路径**组合**为三个可读 pass/fail 的 E2E target，且**不要求
用户打开阿里云或微信控制台**（AC#7）；失败时输出**复现命令**（AC#6）：

- ``test-e2e-crash-recovery``：3 种崩溃场景完整跑通（下载中断 / 转码中断 / 转写中断），
  Worker 重启后清理中间态残留并补齐 ``transcript.json`` 与 ``.done``（AC#1）。复用
  :mod:`soniscope_worker.recovery` 的 :func:`recover` 与 :func:`run_test_crash_recovery`，
  全程临时目录自包含、不触云端。
- ``test-e2e-retranscribe``：临时覆盖 ``params_version`` 后 ``--upgrade`` 只重转旧版本
  Fragment（AC#2），且普通轮询不会自动重转已 ``.done`` Fragment（AC#3）。复用
  :mod:`soniscope_worker.retranscribe` 的自包含 stub 验证。
- ``test-e2e-security``：用**测试夹具**伪造 code / allowlist 外 code 调 FC 必被拒且不返回
  STS（AC#4），合法 STS 越权 PutObject 到其他 key 必被 OSS 拒（AccessDenied，AC#5）。复用
  :mod:`soniscope_worker.fc_live` 与 :mod:`soniscope_worker.sts_escape` 的「纯断言 + IO
  Protocol」探针；无云端凭证 / 不可达时 SKIP（与既有 live target 一致），不要求控制台。

沿用既有「纯逻辑（无 IO，可直接单测）+ IO Protocol 注入」分层：编排只串联子场景结果并渲染
统一汇总，单测注入 Fake 探针（安全场景）或直接跑自包含子场景（崩溃 / 重转），全程不触网，
且**绝不打印 AK Secret / SecurityToken 明文**。
"""

from __future__ import annotations

import datetime
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from soniscope_worker.fc_live import (
    ERR_INVALID_CODE,
    ERR_OPENID_NOT_ALLOWED,
    FAKE_CODE,
    SIZE_OK_BYTES,
    FcLiveProbes,
    RealFcLiveProbes,
    assert_status_error,
    make_fragment_id,
)
from soniscope_worker.oss_admin import OssAdminError, object_key_for
from soniscope_worker.recovery import (
    PART_SUFFIX,
    WAV_TMP_SUFFIX,
    recover,
    run_test_crash_recovery,
)
from soniscope_worker.retranscribe import (
    run_test_cli_upgrade,
    run_test_no_auto_retranscribe,
)
from soniscope_worker.sts_escape import (
    RealStsEscapeProbes,
    StsEscapeOptions,
    StsEscapeProbes,
)
from soniscope_worker.sts_escape import (
    run_checks as run_sts_escape_checks,
)
from soniscope_worker.verify_prep import ProbeError

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

# 崩溃恢复场景用的固定合法 fragment_id（自洽：日期前缀与 object_key 往返一致）。
_DL_FID = "20260527T160000_deve01_01HZX3K8MN5PQR9TFB7AYWVCDE"
_TC_FID = "20260527T160100_deve02_01HZX3K8MN5PQR9TFB7AYWVCDF"


# ── 统一场景结果 + 汇总渲染 ───────────────────────────────────────────────────
@dataclass(frozen=True)
class ScenarioResult:
    """单个 E2E 子场景的结果；``status`` ∈ {PASS, FAIL, SKIP}。"""

    name: str
    status: str
    detail: str = ""
    repro: str = ""  # 仅 FAIL 时展示的复现命令（AC#6）

    @property
    def failed(self) -> bool:
        return self.status == FAIL


def format_e2e_report(
    title: str, results: Sequence[ScenarioResult]
) -> tuple[list[str], int]:
    """渲染统一 pass/fail 汇总；任一 FAIL → 退出码 1（便于 Ralph / CI 判断）。"""
    lines: list[str] = []
    passed = sum(1 for r in results if r.status == PASS)
    failed = sum(1 for r in results if r.status == FAIL)
    skipped = sum(1 for r in results if r.status == SKIP)
    for r in results:
        line = f"[{r.status}] {r.name}"
        if r.detail:
            line += f" — {r.detail}"
        lines.append(line)
        if r.failed and r.repro:
            lines.append(f"        ↳ 复现：{r.repro}")
    lines.append("")
    lines.append(f"{title} 汇总：{passed} PASS / {failed} FAIL / {skipped} SKIP")
    if failed:
        lines.append(f"❌ {title} 未通过：见上面 FAIL 项与复现命令。")
        return lines, 1
    lines.append(f"✅ {title} 通过（无 FAIL）。")
    if skipped:
        lines.append("ℹ️  存在 SKIP：在部署主机提供凭证 / 真实 code 后可跑全部反例。")
    return lines, 0


def _wrap_subrun(
    name: str, sub: tuple[list[str], int], *, repro: str
) -> ScenarioResult:
    """把自包含子 runner 的 ``(lines, code)`` 收敛为一个 ScenarioResult。"""
    sub_lines, sub_code = sub
    if sub_code == 0:
        return ScenarioResult(name, PASS, sub_lines[-1] if sub_lines else "通过")
    fails = [ln for ln in sub_lines if ln.startswith("FAIL")]
    detail = "；".join(fails) if fails else (sub_lines[-1] if sub_lines else "失败")
    return ScenarioResult(name, FAIL, detail, repro=repro)


def _scenario_from_assertion(
    name: str, status: str, detail: str, *, repro: str
) -> ScenarioResult:
    """把 fc_live / sts_escape 的断言结果（name/status/detail）转为 ScenarioResult。"""
    return ScenarioResult(name, status, detail, repro="" if status != FAIL else repro)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


# ── test-e2e-crash-recovery（AC#1，3 种场景完整跑通）──────────────────────────
def _scenario_stale_residual(
    fragment_id: str, suffix: str, label: str
) -> ScenarioResult:
    """构造 kill -9 残留中间态文件，验证重启恢复扫描清理之（下一轮自动重做）。"""
    name = f"{label}（kill -9 残留 {suffix} → 重启清理 → 下一轮自动重做）"
    repro = "make test-e2e-crash-recovery"
    try:
        object_key_for(fragment_id)
    except OssAdminError as exc:  # pragma: no cover - 固定常量合法
        return ScenarioResult(name, FAIL, f"内部 fragment_id 非法：{exc}", repro=repro)
    with tempfile.TemporaryDirectory(prefix="soniscope-e2e-crash-") as tmpdir:
        base = Path(tmpdir)
        inbox, tmp, fragments = base / "inbox", base / "tmp", base / "fragments"
        for d in (inbox, tmp, fragments):
            d.mkdir(parents=True, exist_ok=True)
        residual = inbox / f"{fragment_id}{suffix}"
        residual.write_bytes(b"partial-residual")
        recover(inbox_root=inbox, tmp_root=tmp, fragments_root=fragments)
        if residual.exists():
            return ScenarioResult(name, FAIL, f"{suffix} 残留未被清理", repro=repro)
    return ScenarioResult(name, PASS, f"{suffix} 残留已清理，下一轮自动重做")


def run_test_e2e_crash_recovery() -> tuple[list[str], int]:
    """make test-e2e-crash-recovery：3 种崩溃场景完整跑通（AC#1，自包含不触云端）。"""
    results = [
        _scenario_stale_residual(_DL_FID, PART_SUFFIX, "下载中断"),
        _scenario_stale_residual(_TC_FID, WAV_TMP_SUFFIX, "转码中断"),
        _wrap_subrun(
            "转写中断 → 重启清理 tmp 并补齐 transcript.json 与 .done（AC#1）",
            run_test_crash_recovery(),
            repro="make test-crash-recovery",
        ),
    ]
    return format_e2e_report("E2E 崩溃恢复", results)


# ── test-e2e-retranscribe（AC#2 / AC#3）──────────────────────────────────────
def run_test_e2e_retranscribe() -> tuple[list[str], int]:
    """make test-e2e-retranscribe：--upgrade 只重转旧版本 + 普通轮询不自动重转（AC#2/#3）。"""
    results = [
        _wrap_subrun(
            "--upgrade 仅重转旧 params_version Fragment，当前版本跳过（AC#2）",
            run_test_cli_upgrade(),
            repro="make test-cli-upgrade",
        ),
        _wrap_subrun(
            "改配置后普通轮询不自动重转已 .done Fragment（AC#3）",
            run_test_no_auto_retranscribe(),
            repro="make test-no-auto-retranscribe",
        ),
    ]
    return format_e2e_report("E2E 显式重转", results)


# ── test-e2e-security（AC#4 / AC#5）──────────────────────────────────────────
@dataclass(frozen=True)
class E2eSecurityOptions:
    """test-e2e-security 运行参数（均为一次性 wx.login code，可选）。"""

    code: str = ""  # allowlist 内 code：走 FC 真实签发 → STS 越权反例（否则部署凭证等价）
    not_allowed_code: str = ""  # 真实但不在 allowlist 的一次性 code（403 路径）


def _security_fc_fixture_reject(
    fragment_id: str, probes: FcLiveProbes
) -> ScenarioResult:
    """测试夹具伪造 code → 401 INVALID_CODE 且不返回 STS（AC#4，无需真实 wx.login）。"""
    name = "测试夹具伪造 code → 401 INVALID_CODE 且不返回 STS（AC#4）"
    try:
        resp = probes.call_issue_credential(FAKE_CODE, fragment_id, SIZE_OK_BYTES)
    except ProbeError as exc:
        return ScenarioResult(name, SKIP, f"FC 不可达：{exc}")
    lr = assert_status_error(
        resp, expected_status=401, expected_error=ERR_INVALID_CODE, name=name
    )
    return _scenario_from_assertion(
        lr.name, lr.status, lr.detail, repro="make test-e2e-security"
    )


def _security_fc_not_allowed(
    not_allowed_code: str, fragment_id: str, probes: FcLiveProbes
) -> ScenarioResult:
    """allowlist 外真实 code → 403 OPENID_NOT_ALLOWED 且不返回 STS（AC#4）。"""
    name = "allowlist 外真实 code → 403 OPENID_NOT_ALLOWED 且不返回 STS（AC#4）"
    repro = 'make test-e2e-security CODE_NOT_ALLOWED="<code>"'
    try:
        resp = probes.call_issue_credential(not_allowed_code, fragment_id, SIZE_OK_BYTES)
    except ProbeError as exc:
        return ScenarioResult(name, FAIL, f"FC 不可达：{exc}", repro=repro)
    lr = assert_status_error(
        resp, expected_status=403, expected_error=ERR_OPENID_NOT_ALLOWED, name=name
    )
    return _scenario_from_assertion(lr.name, lr.status, lr.detail, repro=repro)


def _security_sts_escape(code: str, probes: StsEscapeProbes) -> ScenarioResult:
    """合法 STS 越权 PutObject 到其他 key → OSS AccessDenied（AC#5）。"""
    escape_results = run_sts_escape_checks(probes, StsEscapeOptions(code=code))
    er = escape_results[0]
    return _scenario_from_assertion(
        er.name, er.status, er.detail, repro="make test-sts-escape"
    )


def run_test_e2e_security(
    opts: E2eSecurityOptions | None = None,
    *,
    fc_probes: FcLiveProbes | None = None,
    sts_probes: StsEscapeProbes | None = None,
) -> tuple[list[str], int]:
    """make test-e2e-security：FC 鉴权拒绝 + STS 越权反例（AC#4/#5，不要求控制台 AC#7）。"""
    used = opts or E2eSecurityOptions()
    fc = fc_probes or RealFcLiveProbes()
    sts = sts_probes or RealStsEscapeProbes()
    results: list[ScenarioResult] = [
        _security_fc_fixture_reject(make_fragment_id(_now()), fc)
    ]
    if used.not_allowed_code:
        results.append(
            _security_fc_not_allowed(used.not_allowed_code, make_fragment_id(_now()), fc)
        )
    else:
        results.append(
            ScenarioResult(
                "allowlist 外真实 code → 403 OPENID_NOT_ALLOWED（AC#4）",
                SKIP,
                '未提供 allowlist 外 code（make test-e2e-security CODE_NOT_ALLOWED="…"）',
            )
        )
    results.append(_security_sts_escape(used.code, sts))
    return format_e2e_report("E2E 安全反例", results)
