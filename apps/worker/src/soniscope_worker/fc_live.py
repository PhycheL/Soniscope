"""issue-credential 云端联调与 STS 安全反例（US-008，`make test-fc-live`）。

对**已部署**的 FC `issue-credential` 函数做真实云端联调：伪造 code 拿 401、不在
allowlist 的 code 拿 403、allowlist 内 code 拿到单文件 STS，再用该 STS 跑越权 / 过期
反例（全部应被 OSS 拒绝），并验证 size 超限返回 SIZE_EXCEEDED。

设计沿用 ``verify_prep`` 的「纯逻辑 + IO Protocol」模式（AGENTS「单元测试 mock 云端」）：

* 纯断言逻辑（``assert_*``）只对**已取回的结构化响应**做判断，无任何 IO，直接单测；
* 一切 HTTP / OSS 调用收敛到 ``FcLiveProbes`` 协议；``RealFcLiveProbes`` lazy import
  云 SDK / 走 urllib，缺失或不可达时抛 ``ProbeError``；单测注入 ``FakeProbes`` 不触网；
* 任何路径都**绝不打印 AK Secret / SecurityToken 明文**：detail 只含状态码 / 错误码 /
  object key / 判定结果。

``wx.login`` code 是**一次性**的：每次调用 FC 都会消耗一个 code。因此成功路径、
SIZE_EXCEEDED、403 各需要独立的 code；缺失的 code 对应场景标记为 SKIP。
AC#1（部署后 curl 存活）复用 US-005 `make deploy-fc` 的 ``deploy_one``；
AC#9（fc-logs 看 openid 哈希 / fragment_id）复用 US-005 `make fc-logs`，本模块不重复实现。
"""

from __future__ import annotations

import datetime
import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from soniscope_worker.verify_prep import (
    EXPECTED_BUCKET,
    EXPECTED_REGION,
    FC_ISSUE_URL,
    STS_EXPIRY_WAIT_BUFFER_SECONDS,
    ProbeError,
    is_denied,
)

# FC issue-credential 响应 / 错误码（与 fc_shared 保持一致，避免跨包导入）。
ERR_INVALID_CODE = "INVALID_CODE"
ERR_OPENID_NOT_ALLOWED = "OPENID_NOT_ALLOWED"
ERR_SIZE_EXCEEDED = "SIZE_EXCEEDED"

# 成功响应必备字段（tech-spec §4.1，7 字段，AC#4）。
CREDENTIAL_FIELDS: tuple[str, ...] = (
    "access_key_id",
    "access_key_secret",
    "security_token",
    "expiration",
    "bucket",
    "endpoint",
    "object_key",
)

# 联调用 size（字节）：10MB 在 50MB 上限内（正常签发）；60MB 超限（SIZE_EXCEEDED）。
SIZE_OK_BYTES = 10_000_000
SIZE_EXCEEDED_BYTES = 60_000_000

# 公网匿名伪造 code：不可能换出 openid，应稳定返回 401 INVALID_CODE（AC#2）。
FAKE_CODE = "fc-live-fake-code-not-a-real-wx-login-code"

# 越权 PutObject 目标：在签发 key 同目录下的另一个 recordings key（AC#5）。
ESCAPE_KEY_SUFFIX = "-fclive-escape"

# 越权 / 过期反例的展示名与判定方式（expiry=True 接受 ExpiredToken 等过期码）。
ESCAPE_OPS: tuple[tuple[str, str, bool], ...] = (
    ("put_other_key", "越权 PutObject 到其他 recordings key", False),
    ("get_object", "越权 GetObject", False),
    ("list_objects", "越权 ListObjects（列举 Bucket）", False),
    ("delete_object", "越权 DeleteObject", False),
    ("expired_put", "等待超过 STS 有效期上限后 PutObject", True),
)


# ── 结构化探针返回值 ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class HttpResponse:
    """FC HTTP 调用结果（状态码 + 解析后的 JSON body）。"""

    status: int
    body: Mapping[str, object]


@dataclass(frozen=True)
class IssuedCredential:
    """从成功响应解析出的单文件 STS 凭证（明文只在内存内用于跑反例，不入日志）。"""

    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration: str
    bucket: str
    endpoint: str
    object_key: str


@dataclass(frozen=True)
class OssOpResult:
    """一次 STS 越权 / 过期反例的结果（``error_code`` 空串表示操作意外成功）。"""

    name: str
    error_code: str


@dataclass(frozen=True)
class LiveResult:
    """单个联调断言结果；``status`` ∈ {PASS, FAIL, SKIP}。"""

    name: str
    status: str
    detail: str = ""
    fix_hint: str = ""

    @property
    def failed(self) -> bool:
        return self.status == "FAIL"


PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


class FcLiveProbes(Protocol):
    """所有 HTTP / OSS IO 的注入点（单测用 Fake 替换）。"""

    def call_issue_credential(self, code: str, fragment_id: str, size: int) -> HttpResponse: ...

    def oss_escape_ops(
        self, cred: IssuedCredential, *, check_expiry: bool
    ) -> Sequence[OssOpResult]: ...


# ── 纯逻辑（无 IO，直接单测）──────────────────────────────────────────────────
def _body_error(resp: HttpResponse) -> str:
    err = resp.body.get("error")
    return str(err) if err is not None else ""


def assert_status_error(
    resp: HttpResponse, *, expected_status: int, expected_error: str, name: str
) -> LiveResult:
    """断言响应为指定状态码 + 稳定错误码（401 INVALID_CODE / 403 OPENID_NOT_ALLOWED）。"""
    actual_error = _body_error(resp)
    ok = resp.status == expected_status and actual_error == expected_error
    detail = (
        f"HTTP {resp.status} error={actual_error or '∅'}"
        f"（期望 {expected_status} {expected_error}）"
    )
    # 安全：成功响应字段绝不应出现在这些拒绝场景里。
    leaked = [f for f in CREDENTIAL_FIELDS if f in resp.body]
    if leaked:
        ok = False
        detail += f"；疑似泄漏 STS 字段：{', '.join(leaked)}"
    return LiveResult(
        name=name,
        status=PASS if ok else FAIL,
        detail="OK — " + detail if ok else detail,
        fix_hint="" if ok else "检查 FC 鉴权链路（jscode2session / allowlist）与错误码映射。",
    )


def assert_credential_complete(resp: HttpResponse, *, name: str) -> LiveResult:
    """断言 200 且 7 个 STS 字段齐全非空（AC#4 / AC#8 size-ok）。"""
    if resp.status != 200:
        return LiveResult(
            name=name,
            status=FAIL,
            detail=f"HTTP {resp.status} error={_body_error(resp) or '∅'}（期望 200 + STS 凭证）",
            fix_hint="确认 code 在 allowlist 内、size 未超限、RAM_ROLE_ARN / AK 已配置。",
        )
    missing = [f for f in CREDENTIAL_FIELDS if not str(resp.body.get(f, "")).strip()]
    ok = not missing
    object_key = str(resp.body.get("object_key", ""))
    return LiveResult(
        name=name,
        status=PASS if ok else FAIL,
        # 只展示 object_key（非敏感），绝不展示 access_key_secret / security_token。
        detail=f"OK — 7 字段齐全，object_key={object_key}"
        if ok
        else f"缺字段：{', '.join(missing)}",
        fix_hint="" if ok else "检查 issue-credential 成功响应字段（tech-spec §4.1）。",
    )


def assert_size_exceeded(resp: HttpResponse, *, name: str) -> LiveResult:
    """断言 size 超限返回 400 SIZE_EXCEEDED 且含 limit_bytes / actual_bytes（AC#8）。"""
    ok = (
        resp.status == 400
        and _body_error(resp) == ERR_SIZE_EXCEEDED
        and "limit_bytes" in resp.body
        and "actual_bytes" in resp.body
    )
    leaked = [f for f in CREDENTIAL_FIELDS if f in resp.body]
    if leaked:
        ok = False
    detail = (
        f"OK — HTTP 400 SIZE_EXCEEDED limit={resp.body.get('limit_bytes')} "
        f"actual={resp.body.get('actual_bytes')}"
        if ok
        else f"HTTP {resp.status} error={_body_error(resp) or '∅'}（期望 400 SIZE_EXCEEDED）"
    )
    return LiveResult(
        name=name,
        status=PASS if ok else FAIL,
        detail=detail,
        fix_hint="" if ok else "确认 MAX_UPLOAD_BYTES 与 size 校验顺序（US-007）。",
    )


def assert_escape_op(op: OssOpResult, *, display: str, expiry: bool) -> LiveResult:
    """断言一次越权 / 过期反例被 OSS 如预期拒绝。"""
    denied = is_denied(op.error_code, expiry=expiry)
    expected = "ExpiredToken/等价过期或拒绝码" if expiry else "AccessDenied"
    detail = (
        f"OK — 已被拒（{op.error_code}）"
        if denied
        else f"未被拒：error_code={op.error_code or '操作意外成功'}（期望 {expected}）"
    )
    return LiveResult(
        name=display,
        status=PASS if denied else FAIL,
        detail=detail,
        fix_hint="" if denied else (
            "收紧 STS policy 到单 object key（仅 PutObject、有效期 <= 900s），见 tech-spec §4.4。"
        ),
    )


def parse_issued_credential(body: Mapping[str, object]) -> IssuedCredential | None:
    """从成功响应 body 解析 STS 凭证；任一字段缺失返回 None。"""
    if any(not str(body.get(f, "")).strip() for f in CREDENTIAL_FIELDS):
        return None
    return IssuedCredential(
        access_key_id=str(body["access_key_id"]),
        access_key_secret=str(body["access_key_secret"]),
        security_token=str(body["security_token"]),
        expiration=str(body["expiration"]),
        bucket=str(body["bucket"]),
        endpoint=str(body["endpoint"]),
        object_key=str(body["object_key"]),
    )


def other_recordings_key(object_key: str) -> str:
    """由签发 key 推导同目录下另一个 recordings key（越权 PutObject 目标，AC#5）。"""
    if object_key.endswith(".wav"):
        return object_key[: -len(".wav")] + ESCAPE_KEY_SUFFIX + ".wav"
    return object_key + ESCAPE_KEY_SUFFIX


def make_fragment_id(now: datetime.datetime, *, device: str = "fclive") -> str:
    """构造合法 fragment_id：``<YYYYMMDDTHHMMSS>_<deviceShortId>_<26 字符 ULID>``。"""
    ts = now.strftime("%Y%m%dT%H%M%S")
    suffix = uuid.uuid4().hex[:26].upper()  # [0-9A-F] ⊂ [0-9A-Za-z]，满足 fragment_id 正则
    return f"{ts}_{device}_{suffix}"


# ── 编排：跑场景 → 汇总 ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class LiveOptions:
    """test-fc-live 运行参数。"""

    allow_code: str = ""  # allowlist 内的一次性 wx.login code（成功 + STS 反例路径）
    not_allowed_code: str = ""  # 真实但不在 allowlist 的一次性 code（403 路径）
    size_code: str = ""  # 用于 SIZE_EXCEEDED 场景的一次性 code
    check_expiry: bool = True  # 是否跑过期反例（需等待 ≥ 900s）


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def run_checks(
    probes: FcLiveProbes,
    opts: LiveOptions,
    *,
    fragment_id_factory: Callable[[], str] | None = None,
) -> list[LiveResult]:
    """执行全部联调场景，返回有序结果（网络 / 云端异常被收敛为单项 FAIL / SKIP）。"""
    make_fid = fragment_id_factory or (lambda: make_fragment_id(_now()))
    results: list[LiveResult] = []

    # A. 伪造 code → 401 INVALID_CODE（公网匿名也拿不到 STS）。
    try:
        resp = probes.call_issue_credential(FAKE_CODE, make_fid(), SIZE_OK_BYTES)
        results.append(
            assert_status_error(
                resp,
                expected_status=401,
                expected_error=ERR_INVALID_CODE,
                name="伪造 code → 401 INVALID_CODE（AC#2）",
            )
        )
    except ProbeError as exc:
        results.append(LiveResult("伪造 code → 401 INVALID_CODE（AC#2）", FAIL, str(exc)))

    # B. 真实但不在 allowlist 的 code → 403 OPENID_NOT_ALLOWED。
    name_b = "allowlist 外 code → 403 OPENID_NOT_ALLOWED（AC#3）"
    if opts.not_allowed_code:
        try:
            resp = probes.call_issue_credential(opts.not_allowed_code, make_fid(), SIZE_OK_BYTES)
            results.append(
                assert_status_error(
                    resp,
                    expected_status=403,
                    expected_error=ERR_OPENID_NOT_ALLOWED,
                    name=name_b,
                )
            )
        except ProbeError as exc:
            results.append(LiveResult(name_b, FAIL, str(exc)))
    else:
        results.append(
            LiveResult(
                name_b, SKIP, "未提供 allowlist 外 code（make test-fc-live CODE_NOT_ALLOWED=…）"
            )
        )

    # C-H. allowlist 内 code → 签发 STS → 越权 / 过期反例。
    results.extend(_run_credential_path(probes, opts, make_fid))

    # I. size 超限 → 400 SIZE_EXCEEDED。
    name_i = "size=60MB → 400 SIZE_EXCEEDED（AC#8）"
    if opts.size_code:
        try:
            resp = probes.call_issue_credential(opts.size_code, make_fid(), SIZE_EXCEEDED_BYTES)
            results.append(assert_size_exceeded(resp, name=name_i))
        except ProbeError as exc:
            results.append(LiveResult(name_i, FAIL, str(exc)))
    else:
        results.append(
            LiveResult(name_i, SKIP, "未提供 SIZE_CODE（make test-fc-live SIZE_CODE=…）")
        )

    return results


def _run_credential_path(
    probes: FcLiveProbes, opts: LiveOptions, make_fid: Callable[[], str]
) -> list[LiveResult]:
    """成功签发 + STS 越权 / 过期反例（C-H）；无 allow_code 时整体 SKIP。"""
    name_c = "allowlist 内 code + size=10MB → 完整 STS 凭证（AC#4 / AC#8 size-ok）"
    if not opts.allow_code:
        skip_msg = "未提供 allowlist 内 code（make test-fc-live CODE=…）"
        out = [LiveResult(name_c, SKIP, skip_msg)]
        out.extend(
            LiveResult(display, SKIP, "依赖成功签发的 STS（缺 CODE）")
            for _, display, _ in ESCAPE_OPS
        )
        return out

    try:
        resp = probes.call_issue_credential(opts.allow_code, make_fid(), SIZE_OK_BYTES)
    except ProbeError as exc:
        out = [LiveResult(name_c, FAIL, str(exc))]
        out.extend(
            LiveResult(display, FAIL, "无法签发 STS（FC 不可达）")
            for _, display, _ in ESCAPE_OPS
        )
        return out

    cred_result = assert_credential_complete(resp, name=name_c)
    results = [cred_result]
    cred = parse_issued_credential(resp.body)
    if cred is None:
        results.extend(
            LiveResult(display, FAIL, "未拿到完整 STS，无法跑反例") for _, display, _ in ESCAPE_OPS
        )
        return results

    try:
        ops = probes.oss_escape_ops(cred, check_expiry=opts.check_expiry)
    except ProbeError as exc:
        results.extend(LiveResult(display, FAIL, str(exc)) for _, display, _ in ESCAPE_OPS)
        return results

    ops_by_name = {op.name: op for op in ops}
    for op_name, display, expiry in ESCAPE_OPS:
        op = ops_by_name.get(op_name)
        if op is None:
            results.append(
                LiveResult(display, SKIP, "未执行（过期反例已按 --skip-expiry 跳过）")
                if op_name == "expired_put" and not opts.check_expiry
                else LiveResult(display, FAIL, "探针未返回该反例结果")
            )
            continue
        results.append(assert_escape_op(op, display=display, expiry=expiry))
    return results


def all_passed(results: Sequence[LiveResult]) -> bool:
    """没有任何 FAIL（SKIP 允许）且至少跑了一项。"""
    return bool(results) and not any(r.failed for r in results)


def format_report(results: Sequence[LiveResult]) -> list[str]:
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
        lines.append("✅ test-fc-live 通过（无 FAIL）。")
        if skipped:
            lines.append(
                "ℹ️  存在 SKIP：传入真实 wx.login code"
                "（CODE= / CODE_NOT_ALLOWED= / SIZE_CODE=）可覆盖全部反例。"
            )
        lines.append(
            "ℹ️  AC#9：运行 `make fc-logs FUNCTION=issue-credential` "
            "查看 openid 哈希 / fragment_id 日志。"
        )
    else:
        lines.append("❌ test-fc-live 未通过，请按上面修复指引处理。")
    return lines


# ── 真实探针实现（urllib + OSS SDK；缺失 / 不可达抛 ProbeError）───────────────
def _parse_body(raw: bytes) -> Mapping[str, object]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


class RealFcLiveProbes:
    """真实 HTTP / OSS 探针；构造时无副作用，调用时才触网。"""

    def call_issue_credential(self, code: str, fragment_id: str, size: int) -> HttpResponse:
        body = {"code": code, "fragment_id": fragment_id, "size": size}
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310 — 固定 https 常量 URL
            FC_ISSUE_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                return HttpResponse(int(resp.status), _parse_body(resp.read()))
        except urllib.error.HTTPError as exc:
            return HttpResponse(int(exc.code), _parse_body(exc.read()))
        except urllib.error.URLError as exc:
            raise ProbeError(f"FC issue-credential 不可达：{exc.reason}") from exc
        except OSError as exc:  # 超时等
            raise ProbeError(f"FC issue-credential 请求失败：{type(exc).__name__}") from exc

    def oss_escape_ops(
        self, cred: IssuedCredential, *, check_expiry: bool
    ) -> Sequence[OssOpResult]:
        import time

        from soniscope_worker.verify_prep import (
            _import_oss,
            _oss_sts_client,
            _run_oss_op,
            _seconds_until_expiry,
        )

        oss = _import_oss()
        sts_cred = _StsCred(cred.access_key_id, cred.access_key_secret, cred.security_token)
        try:
            client = _oss_sts_client(oss, cred.endpoint or _default_endpoint(), sts_cred)
        except Exception as exc:  # noqa: BLE001 — 收敛为 ProbeError，不泄漏明文
            raise ProbeError(f"OSS STS 客户端初始化失败：{type(exc).__name__}") from exc

        bucket = cred.bucket or EXPECTED_BUCKET
        allowed = cred.object_key
        other = other_recordings_key(allowed)
        results: list[OssOpResult] = [
            OssOpResult(
                "put_other_key",
                _run_oss_op(
                    lambda: client.put_object(
                        oss.PutObjectRequest(bucket=bucket, key=other, body=b"x")
                    )
                ),
            ),
            OssOpResult(
                "get_object",
                _run_oss_op(
                    lambda: client.get_object(oss.GetObjectRequest(bucket=bucket, key=allowed))
                ),
            ),
            OssOpResult(
                "list_objects",
                _run_oss_op(
                    lambda: client.list_objects_v2(
                        oss.ListObjectsV2Request(bucket=bucket, max_keys=1)
                    )
                ),
            ),
            OssOpResult(
                "delete_object",
                _run_oss_op(
                    lambda: client.delete_object(
                        oss.DeleteObjectRequest(bucket=bucket, key=allowed)
                    )
                ),
            ),
        ]
        if check_expiry:
            wait = _seconds_until_expiry(cred) + STS_EXPIRY_WAIT_BUFFER_SECONDS
            if wait > 0:
                time.sleep(wait)
            results.append(
                OssOpResult(
                    "expired_put",
                    _run_oss_op(
                        lambda: client.put_object(
                            oss.PutObjectRequest(bucket=bucket, key=allowed, body=b"x")
                        )
                    ),
                )
            )
        return results


def _default_endpoint() -> str:
    return f"oss-{EXPECTED_REGION}.aliyuncs.com"


@dataclass(frozen=True)
class _StsCred:
    """适配 verify_prep._seconds_until_expiry / _oss_sts_client 的最小凭证视图。"""

    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration: str = ""


# ── 顶层入口（CLI 调用）─────────────────────────────────────────────────────
def run_test_fc_live(
    opts: LiveOptions, probes: FcLiveProbes | None = None
) -> tuple[list[str], int]:
    """执行 test-fc-live，返回（报告行, 退出码）。退出码 0 表示无 FAIL。"""
    used_probes = probes or RealFcLiveProbes()
    results = run_checks(used_probes, opts)
    lines = format_report(results)
    return lines, (0 if all_passed(results) else 1)
