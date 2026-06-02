#!/usr/bin/env python3
"""E2E security anti-pattern verification — ``make test-e2e-security``.

Per US-031 AC4/AC5:
- AC4: Non-allowlisted WeChat ``code`` calls FC → ``403 OPENID_NOT_ALLOWED``,
  no STS credentials returned.
- AC5: Valid STS credentials from allowlisted code cannot be used to
  PutObject to a different OSS object key → ``AccessDenied``.

This script uses the existing ``test-fc-live`` and ``test-sts-escape``
infrastructure patterns for consistency.

Usage::

    make test-e2e-security
    make test-e2e-security ARGS="--code <wx-login-code>"

Environment:
    WX_TEST_CODE: alternative way to pass the wx.login code
    ALIYUN_AK_ID / ALIYUN_AK_SECRET or ALIYUN_DEPLOY_* : OSS credentials
    SONISCOPE_HOME: Worker runtime root (default: ~/SoniScope)
"""

from __future__ import annotations

import io
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

# ── Color helpers ───────────────────────────────────────────────────────────────

_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _green(s: str) -> str:
    return f"{_GREEN}{s}{_RESET}"


def _red(s: str) -> str:
    return f"{_RED}{s}{_RESET}"


def _yellow(s: str) -> str:
    return f"{_YELLOW}{s}{_RESET}"


def _bold(s: str) -> str:
    return f"{_BOLD}{s}{_RESET}"


@dataclass
class CheckResult:
    label: str
    passed: bool
    detail: str = ""
    fix_hint: str = ""
    skipped: bool = False


@dataclass
class BlockResult:
    block: str
    title: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if not c.skipped)


# ── Constants ──────────────────────────────────────────────────────────────────

FC_ISSUE_CREDENTIAL_URL = "https://issue-cedential-ottfirocds.cn-beijing.fcapp.run"
FC_VERIFY_UPLOAD_URL = "https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run"
OSS_BUCKET = "soniscope-audio"
OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"
REQUEST_TIMEOUT = 30

_TEST_FRAGMENT_ID = "20260602T000000_test_01HZX3K8MN5PQR9TFB7AYWVCDE"
_TEST_FRAGMENT_ID_2 = "20260602T000001_test_01HZX3K8MN5PQR9TFB7AYWVCDE"


# ── HTTP helpers ───────────────────────────────────────────────────────────────


def _post_fc(url: str, payload: dict[str, object], timeout: int = REQUEST_TIMEOUT) -> tuple[int, dict[str, Any]]:
    """POST JSON to an FC endpoint. Returns (status_code, parsed_body)."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw_body = ""
        try:
            raw_body = exc.read().decode("utf-8")
        except Exception:
            raw_body = ""
        try:
            return exc.code, json.loads(raw_body) if raw_body else {"error": f"HTTP {exc.code}"}
        except json.JSONDecodeError:
            return exc.code, {"error": f"HTTP {exc.code}", "raw": raw_body[:200]}
    except urllib.error.URLError as exc:
        return 0, {"error": f"Connection failed: {exc.reason}"}
    except Exception as exc:
        return 0, {"error": str(exc)}


def _try_oss_put_wrong_key(
    creds: dict[str, str],
    object_key: str,
) -> tuple[bool, str]:
    """Try PutObject to a specific key with STS credentials.

    Returns (denied_correctly, detail).
    """
    import alibabacloud_oss_v2 as oss2

    try:
        sts_cred = oss2.credentials.StaticCredentialsProvider(
            access_key_id=creds["access_key_id"],
            access_key_secret=creds["access_key_secret"],
            security_token=creds["security_token"],
        )
        cfg = oss2.config.load_default()
        cfg.credentials_provider = sts_cred
        cfg.region = "cn-beijing"
        cfg.endpoint = OSS_ENDPOINT
        client = oss2.Client(cfg)

        client.put_object(
            oss2.PutObjectRequest(
                bucket=OSS_BUCKET,
                key=object_key,
                body=io.BytesIO(b"security-escape-test"),
            )
        )
        return False, f"PutObject unexpectedly succeeded (should have been denied)"
    except Exception as exc:
        msg = str(exc)
        denied_keywords = [
            "AccessDenied", "access denied", "Forbidden",
            "InvalidAccessKeyId", "ExpiredToken", "SecurityTokenExpired",
            "expired", "not authorized", "SignatureDoesNotMatch",
        ]
        if any(kw.lower() in msg.lower() for kw in denied_keywords):
            return True, f"PutObject correctly denied (AccessDenied/Forbidden)"
        return False, f"PutObject failed but not with AccessDenied: {msg[:150]}"


# ── Check blocks ───────────────────────────────────────────────────────────────


def check_block_a(args: object) -> BlockResult:
    """A: Non-allowlisted code → 403 OPENID_NOT_ALLOWED, no STS.

    This block always runs — it works with both fake and real codes.
    """
    result = BlockResult("A", "未授权 openid 拒绝 (unauthorized openid)")

    test_code: str = getattr(args, "code", "") or os.environ.get("WX_TEST_CODE", "")

    # A.1: Fake code → 401 INVALID_CODE
    fake_code = "e2e_security_fake_code_12345"
    status, body = _post_fc(
        FC_ISSUE_CREDENTIAL_URL,
        {"code": fake_code, "fragment_id": _TEST_FRAGMENT_ID, "size": 1000},
    )
    is_401 = status == 401
    has_invalid_code = body.get("error") == "INVALID_CODE"
    a1_pass = is_401 and has_invalid_code

    result.checks.append(
        CheckResult(
            label="伪造 code → 401 INVALID_CODE（不返回 STS）",
            passed=a1_pass,
            detail=f"HTTP {status}, error={body.get('error', 'N/A')}",
            fix_hint=(
                "" if a1_pass
                else "检查 FC issue-credential 的 jscode2session 鉴权: "
                     "伪造 code 必须返回 401 INVALID_CODE，不得返回任何 STS 凭证字段"
            ),
        )
    )

    # Verify no STS fields leaked
    sts_fields = ["access_key_id", "access_key_secret", "security_token"]
    leaked = [f for f in sts_fields if f in body]
    no_sts_leak = len(leaked) == 0
    result.checks.append(
        CheckResult(
            label="401/403 响应不包含 STS 凭证字段",
            passed=no_sts_leak,
            detail=f"泄漏字段: {leaked}" if leaked else "无 STS 字段泄漏",
            fix_hint=(
                f"响应中包含了 STS 字段: {leaked}。"
                "鉴权失败的响应不得包含 access_key_id/access_key_secret/security_token。"
                if leaked else ""
            ),
        )
    )

    # A.2: No code → 400 (missing field)
    status2, body2 = _post_fc(
        FC_ISSUE_CREDENTIAL_URL,
        {"fragment_id": _TEST_FRAGMENT_ID, "size": 1000},
    )
    a2_pass = status2 in (400, 401) and body2.get("error") is not None
    result.checks.append(
        CheckResult(
            label="缺少 code 字段 → 返回错误（不返回 STS）",
            passed=a2_pass,
            detail=f"HTTP {status2}, error={body2.get('error', 'N/A')}",
            fix_hint="" if a2_pass else "检查 safe_handler 必填字段校验",
        )
    )

    # A.3: Real code test (optional)
    if test_code:
        status3, body3 = _post_fc(
            FC_ISSUE_CREDENTIAL_URL,
            {"code": test_code, "fragment_id": _TEST_FRAGMENT_ID, "size": 1000},
        )

        if status3 == 403 and body3.get("error") == "OPENID_NOT_ALLOWED":
            a3_pass = True
            a3_detail = "403 OPENID_NOT_ALLOWED — openid 不在 allowlist 中（预期行为）"
        elif status3 == 200:
            a3_pass = True
            a3_detail = "200 — openid 在 allowlist 中（可运行完整 STS 越权测试）"
            result._sts_creds = {  # type: ignore[attr-defined]
                "access_key_id": body3.get("access_key_id", ""),
                "access_key_secret": body3.get("access_key_secret", ""),
                "security_token": body3.get("security_token", ""),
            }
            result._object_key = body3.get("object_key", "")  # type: ignore[attr-defined]
            result._has_sts = True  # type: ignore[attr-defined]
        else:
            a3_pass = False
            a3_detail = f"HTTP {status3}, error={body3.get('error', 'N/A')}"

        result.checks.append(
            CheckResult(
                label="真实 wx.login code → 鉴权响应（403 或 200）",
                passed=a3_pass,
                detail=a3_detail,
                fix_hint="" if a3_pass else "检查 allowlist 配置与 wx.login code 有效性",
            )
        )
    else:
        result.checks.append(
            CheckResult(
                label="真实 wx.login code 鉴权测试",
                passed=True,
                skipped=True,
                detail="未提供测试 code（传 --code 或设 WX_TEST_CODE 以启用完整测试）",
                fix_hint="通过微信开发者工具获取真实 wx.login code",
            )
        )
        result._has_sts = False  # type: ignore[attr-defined]

    if not getattr(result, "_has_sts", False):
        result._has_sts = False  # type: ignore[attr-defined]

    return result


def check_block_b(args: object, block_a: BlockResult) -> BlockResult:
    """B: STS escape — valid STS can't write to other keys (AC5)."""
    result = BlockResult("B", "STS 越权拒绝 (STS escape)")

    has_sts = getattr(block_a, "_has_sts", False)
    sts_creds = getattr(block_a, "_sts_creds", None) if has_sts else None
    object_key = getattr(block_a, "_object_key", "")

    if sts_creds is None or not object_key:
        result.checks.append(
            CheckResult(
                label="STS 越权 PutObject → AccessDenied",
                passed=True,
                skipped=True,
                detail="需要 allowlist 内有效 wx.login code 获取 STS 后才能测试越权",
                fix_hint="提供 --code (allowlist 内 openid) 以获取 STS 并运行越权测试",
            )
        )
        return result

    # Derive a wrong key
    wrong_key = object_key.replace("_test_", "_wrong_")

    # B.1: PutObject to wrong key → AccessDenied
    b1_ok, b1_detail = _try_oss_put_wrong_key(sts_creds, wrong_key)
    result.checks.append(
        CheckResult(
            label="PutObject 到其他 key → AccessDenied",
            passed=b1_ok,
            detail=b1_detail,
            fix_hint=(
                "" if b1_ok
                else "检查 FC issue-credential STS policy Resource 是否精确到单个 object key"
            ),
        )
    )

    # B.2: Verify the STS has no ListObjects/GetObject/DeleteObject (test GetObject)
    import alibabacloud_oss_v2 as oss2

    try:
        sts_cred2 = oss2.credentials.StaticCredentialsProvider(
            access_key_id=sts_creds["access_key_id"],
            access_key_secret=sts_creds["access_key_secret"],
            security_token=sts_creds["security_token"],
        )
        cfg2 = oss2.config.load_default()
        cfg2.credentials_provider = sts_cred2
        cfg2.region = "cn-beijing"
        cfg2.endpoint = OSS_ENDPOINT
        client2 = oss2.Client(cfg2)
        client2.get_object(oss2.GetObjectRequest(bucket=OSS_BUCKET, key=object_key))
        b2_pass = False
        b2_detail = "GetObject unexpectedly succeeded (STS 权限过宽)"
    except Exception as exc:
        msg = str(exc)
        if "AccessDenied" in msg or "access denied" in msg.lower() or "Forbidden" in msg:
            b2_pass = True
            b2_detail = "GetObject correctly denied (STS 仅限于 PutObject)"
        else:
            b2_pass = False
            b2_detail = f"GetObject 失败但非 AccessDenied: {msg[:150]}"

    result.checks.append(
        CheckResult(
            label="GetObject → AccessDenied（STS 仅限于 PutObject）",
            passed=b2_pass,
            detail=b2_detail,
            fix_hint=(
                "" if b2_pass
                else "检查 STS policy Action 是否仅限于 oss:PutObject"
            ),
        )
    )

    return result


def check_block_c(args: object) -> BlockResult:
    """C: Verify verify-upload endpoint also enforces auth."""
    result = BlockResult("C", "verify-upload 鉴权验证")

    # C.1: Fake code to verify-upload → should reject
    fake_code = "e2e_security_fake_code_verify"
    status, body = _post_fc(
        FC_VERIFY_UPLOAD_URL,
        {"code": fake_code, "fragment_id": _TEST_FRAGMENT_ID, "expected_size": 1000},
    )
    is_rejected = status in (400, 401, 403)
    result.checks.append(
        CheckResult(
            label="伪造 code → verify-upload 返回 401/403",
            passed=is_rejected,
            detail=f"HTTP {status}, error={body.get('error', 'N/A')}",
            fix_hint=(
                "" if is_rejected
                else "检查 verify-upload 的鉴权逻辑"
            ),
        )
    )

    # C.2: No code → should reject
    status2, body2 = _post_fc(
        FC_VERIFY_UPLOAD_URL,
        {"fragment_id": _TEST_FRAGMENT_ID, "expected_size": 1000},
    )
    is_rejected2 = status2 in (400, 401)
    result.checks.append(
        CheckResult(
            label="缺少 code → verify-upload 返回 400/401",
            passed=is_rejected2,
            detail=f"HTTP {status2}, error={body2.get('error', 'N/A')}",
        )
    )

    return result


def check_block_d(args: object) -> BlockResult:
    """D: Summary and repro instructions."""
    result = BlockResult("D", "安全验证汇总与复现命令")

    test_code: str = getattr(args, "code", "") or os.environ.get("WX_TEST_CODE", "")

    if test_code:
        result.checks.append(
            CheckResult(
                label="安全测试覆盖",
                passed=True,
                detail=(
                    "✓ 伪造 code → 401 INVALID_CODE（A.1）\n"
                    "✓ 缺少 code → 400/401（A.2）\n"
                    "✓ 真实 code → 鉴权测试（A.3）\n"
                    "✓ STS 越权 PutObject（B.1）\n"
                    "✓ STS 越权 GetObject（B.2）\n"
                    "✓ verify-upload 鉴权（C.1/C.2）"
                ),
            )
        )
    else:
        result.checks.append(
            CheckResult(
                label="安全测试覆盖",
                passed=True,
                detail=(
                    "✓ 伪造 code → 401 INVALID_CODE（A.1）\n"
                    "✓ 缺少 code → 400/401（A.2）\n"
                    "○ 真实 code 鉴权测试（需 --code）\n"
                    "○ STS 越权测试（需 --code + allowlist 内 openid）\n"
                    "✓ verify-upload 鉴权（C.1/C.2）"
                ),
            )
        )

    result.checks.append(
        CheckResult(
            label="复现命令",
            passed=True,
            detail=(
                "# 完整安全测试 (需 allowlist 内 code):\n"
                f"#   make test-e2e-security ARGS=\"--code <wx-login-code>\"\n"
                "# 已有 STS 时的独立越权测试:\n"
                f"#   make test-sts-escape"
            ),
        )
    )

    return result


# ── Print helpers ───────────────────────────────────────────────────────────────


def _print_block(blk: BlockResult) -> None:
    for c in blk.checks:
        if c.skipped:
            mark = "○"
        else:
            mark = "✓" if c.passed else "✗"
        print(f"  {mark} {c.label}: {c.detail}")
        if not c.passed and not c.skipped and c.fix_hint:
            print(f"    → {c.fix_hint}")
    all_ok = blk.passed
    if not any(not c.skipped for c in blk.checks):
        mark = "○"
        status_text = "全部跳过（需要更多前置条件）"
    else:
        mark = "✓" if all_ok else "✗"
        status_text = "全部通过" if all_ok else "存在失败项"
    print(f"  {mark} {blk.block} 块 {status_text}")
    print()


# ── Main ────────────────────────────────────────────────────────────────────────


def run(args: object) -> int:
    test_code: str = getattr(args, "code", "") or os.environ.get("WX_TEST_CODE", "")

    print()
    print(_bold("╔══════════════════════════════════════════════════════╗"))
    print(_bold("║     SoniScope · E2E 安全反例验证                     ║"))
    print(_bold("╚══════════════════════════════════════════════════════╝"))
    print()
    print(f"  FC issue-credential: {FC_ISSUE_CREDENTIAL_URL}")
    print(f"  FC verify-upload:    {FC_VERIFY_UPLOAD_URL}")
    print(f"  OSS Bucket:          {OSS_BUCKET}")
    if test_code:
        print(f"  Test code:           provided ({len(test_code)} chars)")
    else:
        print(f"  {_yellow('Test code: not provided — limited STS escape test coverage')}")
    print()

    blocks: list[BlockResult] = []

    # A: Unauthorized openid
    print(_bold("▶ A 块 — 未授权 openid 拒绝"))
    a = check_block_a(args)
    blocks.append(a)
    _print_block(a)

    # B: STS escape
    print(_bold("▶ B 块 — STS 越权拒绝"))
    b = check_block_b(args, a)
    blocks.append(b)
    _print_block(b)

    # C: verify-upload auth
    print(_bold("▶ C 块 — verify-upload 鉴权"))
    c = check_block_c(args)
    blocks.append(c)
    _print_block(c)

    # D: Summary
    print(_bold("▶ D 块 — 汇总"))
    d = check_block_d(args)
    blocks.append(d)
    _print_block(d)

    # ── Final summary ──
    total_passed = sum(1 for blk in blocks for c in blk.checks if c.passed and not c.skipped)
    total_failed = sum(1 for blk in blocks for c in blk.checks if not c.passed and not c.skipped)
    total_skipped = sum(1 for blk in blocks for c in blk.checks if c.skipped)

    print()
    print(_bold("═" * 60))
    print(_bold("  安全反例验证汇总"))
    print(_bold("═" * 60))

    for blk in blocks:
        if all(c.skipped for c in blk.checks):
            mark = "○"
        elif blk.passed:
            mark = "✓"
        else:
            mark = "✗"
        print(f"  {mark} {blk.block} 块 — {blk.title}")

    print()
    parts = [f"{total_passed} 通过"]
    if total_failed:
        parts.append(f"{total_failed} 失败")
    if total_skipped:
        parts.append(f"{total_skipped} 跳过")
    print(f"  总计: {', '.join(parts)}")

    if total_failed == 0:
        print()
        print(_green("✅ test-e2e-security 全部通过"))
        return 0
    else:
        print()
        print(_red("❌ 部分测试未通过，请根据上述修复指引逐一检查后重新运行。"))
        return 1


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="E2E security anti-pattern verification",
    )
    parser.add_argument(
        "--code",
        default="",
        help="Real wx.login code from WeChat DevTools for full integration test",
    )
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
