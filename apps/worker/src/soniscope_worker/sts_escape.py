"""STS 单 key policy 越权验证（US-017 AC#8，``make test-sts-escape``）。

用小程序上传链路获得的单文件 STS（或**等价测试凭证**：部署凭证 AssumeRole 出的
单 key STS）尝试 PutObject 到**另一个** object key，断言 OSS 返回 ``AccessDenied``。
这是「STS policy 精确到单 object key」红线（tech-spec §4.4 / AGENTS 安全红线）的反例校验。

设计沿用 ``fc_live`` / ``verify_prep`` 的「纯断言逻辑 + IO Protocol」模式：

* 纯断言 ``assert_escape_denied`` 只对已取回的 error_code 判断，无 IO，直接单测；
* 所有 STS 签发 / OSS PutObject 收敛到 ``StsEscapeProbes``；``RealStsEscapeProbes``
  lazy import 云 SDK / 走部署凭证或 FC，缺失 / 不可达抛 ``ProbeError``；
* 任何路径都**绝不打印 AK Secret / SecurityToken 明文**：detail 只含 key 与错误码。

无凭证（本地 CI）时整体 SKIP，exit 0；真实环境（部署 AK + OSS SDK）跑真实越权反例。
"""

from __future__ import annotations

import datetime
import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from soniscope_worker.fc_live import (
    CREDENTIAL_FIELDS,
    IssuedCredential,
    make_fragment_id,
    other_recordings_key,
    parse_issued_credential,
)
from soniscope_worker.verify_prep import (
    DEPLOY_AK_ID_ENV,
    DEPLOY_AK_SECRET_ENV,
    EXPECTED_BUCKET,
    EXPECTED_REGION,
    FC_ISSUE_URL,
    ProbeError,
    is_denied,
)

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

# 联调用 size（字节）：10MB 在 50MB 上限内（正常签发）。
SIZE_OK_BYTES = 10_000_000


@dataclass(frozen=True)
class EscapeResult:
    name: str
    status: str
    detail: str = ""
    fix_hint: str = ""

    @property
    def failed(self) -> bool:
        return self.status == FAIL


@dataclass(frozen=True)
class StsEscapeOptions:
    """test-sts-escape 运行参数。"""

    code: str = ""  # 可选：allowlist 内一次性 wx.login code（走 FC 真实签发链路）


class StsEscapeProbes(Protocol):
    """STS 签发 + OSS PutObject 的注入点（单测用 Fake 替换）。"""

    def mint_single_key_credential(self, allowed_key: str, *, code: str) -> IssuedCredential: ...

    def put_object(self, cred: IssuedCredential, key: str) -> str: ...


# ── 纯断言逻辑（无 IO，直接单测）──────────────────────────────────────────────
def assert_escape_denied(error_code: str, *, name: str) -> EscapeResult:
    """断言越权 PutObject 被 OSS 拒绝（AccessDenied 等）。"""
    denied = is_denied(error_code, expiry=False)
    detail = (
        f"OK — 已被拒（{error_code}）"
        if denied
        else f"未被拒：error_code={error_code or '操作意外成功'}（期望 AccessDenied）"
    )
    return EscapeResult(
        name=name,
        status=PASS if denied else FAIL,
        detail=detail,
        fix_hint="" if denied else (
            "收紧 STS policy 到单 object key（仅 PutObject、有效期 <= 900s），见 tech-spec §4.4。"
        ),
    )


# ── 编排 ─────────────────────────────────────────────────────────────────────
def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def run_checks(
    probes: StsEscapeProbes,
    opts: StsEscapeOptions,
    *,
    allowed_key: str | None = None,
) -> list[EscapeResult]:
    """签发单 key STS → 越权写另一个 key → 断言被拒。凭证缺失 / 不可达收敛为 SKIP / FAIL。"""
    name = "STS 单 key 越权 PutObject 到其他 key → AccessDenied（AC#8）"
    allowed = allowed_key or _default_allowed_key()
    try:
        cred = probes.mint_single_key_credential(allowed, code=opts.code)
    except ProbeError as exc:
        return [EscapeResult(name, SKIP, str(exc))]
    # 用签发凭证里的真实 object_key（FC 可能与请求 key 不同）推导越权目标。
    base_key = cred.object_key or allowed
    other = other_recordings_key(base_key)
    try:
        error_code = probes.put_object(cred, other)
    except ProbeError as exc:
        return [EscapeResult(name, FAIL, str(exc))]
    return [assert_escape_denied(error_code, name=name)]


def _default_allowed_key() -> str:
    fid = make_fragment_id(_now(), device="stsesc")
    return f"recordings/{_now():%Y-%m-%d}/{fid}.wav"


def all_passed(results: Sequence[EscapeResult]) -> bool:
    return bool(results) and not any(r.failed for r in results)


def format_report(results: Sequence[EscapeResult]) -> list[str]:
    """渲染人类可读汇总（绝不含 AK Secret / SecurityToken）。"""
    lines: list[str] = []
    passed = sum(1 for r in results if r.status == PASS)
    failed = sum(1 for r in results if r.status == FAIL)
    skipped = sum(1 for r in results if r.status == SKIP)
    for r in results:
        line = f"[{r.status}] {r.name}"
        if r.detail:
            line += f" — {r.detail}"
        lines.append(line)
        if r.failed and r.fix_hint:
            lines.append(f"        ↳ 修复：{r.fix_hint}")
    lines.append("")
    lines.append(f"汇总：{passed} PASS / {failed} FAIL / {skipped} SKIP")
    if all_passed(results):
        lines.append("✅ test-sts-escape 通过（无 FAIL）。")
        if skipped:
            lines.append(
                "ℹ️  存在 SKIP：在部署主机配置 ALIYUN_DEPLOY_AK_ID/SECRET + 安装 OSS SDK "
                "可跑真实越权反例。"
            )
    else:
        lines.append("❌ test-sts-escape 未通过：STS policy 可能未精确到单 object key。")
    return lines


# ── 真实探针（部署凭证 AssumeRole 或 FC 签发；缺失 / 不可达抛 ProbeError）───────
class RealStsEscapeProbes:
    """真实 STS 签发 + OSS PutObject；构造无副作用，调用时才触网。"""

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env if env is not None else os.environ

    def mint_single_key_credential(self, allowed_key: str, *, code: str) -> IssuedCredential:
        if code:
            return self._mint_via_fc(allowed_key, code)
        return self._mint_via_deploy_assume_role(allowed_key)

    def _mint_via_fc(self, allowed_key: str, code: str) -> IssuedCredential:
        # 用一次性 wx.login code 走真实 FC issue-credential 签发链路。
        fid = _fragment_id_from_key(allowed_key)
        body = {"code": code, "fragment_id": fid, "size": SIZE_OK_BYTES}
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310 — 固定 https 常量 URL
            FC_ISSUE_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raise ProbeError(f"FC issue-credential 返回 {exc.code}（无法签发 STS）") from exc
        except urllib.error.URLError as exc:
            raise ProbeError(f"FC issue-credential 不可达：{exc.reason}") from exc
        except OSError as exc:
            raise ProbeError(f"FC issue-credential 请求失败：{type(exc).__name__}") from exc
        data = _parse_body(raw)
        cred = parse_issued_credential(data)
        if cred is None:
            raise ProbeError(f"FC 响应缺少 STS 字段（需 {len(CREDENTIAL_FIELDS)} 项）")
        return cred

    def _mint_via_deploy_assume_role(self, allowed_key: str) -> IssuedCredential:
        ak_id = self._env.get(DEPLOY_AK_ID_ENV, "")
        ak_secret = self._env.get(DEPLOY_AK_SECRET_ENV, "")
        if not ak_id or not ak_secret:
            raise ProbeError(
                f"未提供 {DEPLOY_AK_ID_ENV} / {DEPLOY_AK_SECRET_ENV}（无法 AssumeRole 签发"
                "等价测试凭证；或传 CODE= 走 FC）。"
            )
        from soniscope_worker.verify_prep import _assume_role_single_key, _import_sts

        try:
            sts = _import_sts()
            raw_cred = _assume_role_single_key(
                sts, ak_id, ak_secret, EXPECTED_REGION, allowed_key
            )
        except ProbeError:
            raise
        except Exception as exc:  # noqa: BLE001 - 收敛为 ProbeError，不泄漏明文
            raise ProbeError(f"AssumeRole 签发失败：{type(exc).__name__}") from exc
        return IssuedCredential(
            access_key_id=str(getattr(raw_cred, "access_key_id", "")),
            access_key_secret=str(getattr(raw_cred, "access_key_secret", "")),
            security_token=str(getattr(raw_cred, "security_token", "")),
            expiration=str(getattr(raw_cred, "expiration", "")),
            bucket=EXPECTED_BUCKET,
            endpoint=f"oss-{EXPECTED_REGION}.aliyuncs.com",
            object_key=allowed_key,
        )

    def put_object(self, cred: IssuedCredential, key: str) -> str:
        from soniscope_worker.verify_prep import _import_oss, _oss_sts_client, _run_oss_op

        oss = _import_oss()
        try:
            client = _oss_sts_client(
                oss, cred.endpoint or f"oss-{EXPECTED_REGION}.aliyuncs.com", cred
            )
        except Exception as exc:  # noqa: BLE001 - 收敛为 ProbeError，不泄漏明文
            raise ProbeError(f"OSS STS 客户端初始化失败：{type(exc).__name__}") from exc
        bucket = cred.bucket or EXPECTED_BUCKET
        return _run_oss_op(
            lambda: client.put_object(oss.PutObjectRequest(bucket=bucket, key=key, body=b"x"))
        )


def _parse_body(raw: bytes) -> Mapping[str, object]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _fragment_id_from_key(object_key: str) -> str:
    name = object_key.rsplit("/", 1)[-1]
    return name[: -len(".wav")] if name.endswith(".wav") else name


# ── 顶层入口（CLI 调用）─────────────────────────────────────────────────────
def run_test_sts_escape(
    opts: StsEscapeOptions, probes: StsEscapeProbes | None = None
) -> tuple[list[str], int]:
    """执行 test-sts-escape，返回（报告行, 退出码）。退出码 0 表示无 FAIL。"""
    used = probes or RealStsEscapeProbes()
    results = run_checks(used, opts)
    return format_report(results), (0 if all_passed(results) else 1)
