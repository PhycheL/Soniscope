"""verify-upload 云端闭环测试（US-010，``make test-verify-upload``）。

对**已部署**的 FC ``verify-upload`` 函数做真实云端联调（tech-spec §4.2）：

* 上传测试对象 → ``/verify-upload`` → 断言 ``verified:true``（含 etag/size/last_modified）；
* 删除该对象（``oss-delete-obj`` 仅测试用）后再调 → 断言 ``OBJECT_NOT_FOUND``；
* 上传 100 字节对象、``expected_size=200`` → 断言 ``SIZE_MISMATCH`` 且 ``actual_size=100``；
* 不带 / 伪造 code → 400 / 401，且**不泄露任何对象信息**；
* 输出每次调用耗时与 P95（阈值 1 秒，复用 ``latency.format_latency_report``）。

设计沿用 ``fc_live`` 的「纯断言逻辑 + IO Protocol」模式：``assert_*`` 只对已取回的
结构化响应做判断（无 IO，直接单测）；HTTP / OSS IO 收敛到 ``VerifyLiveProbes``，
``RealVerifyUploadProbes`` 走 urllib + ``RealOssObjectStore``，单测注入 Fake 不触网。
``wx.login`` code 一次性：每个需要 code 的场景缺 code 即标记 SKIP（本地 CI 也能 exit 0）。
任何路径都**绝不打印 AK Secret / SecurityToken**。
"""

from __future__ import annotations

import datetime
import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from soniscope_worker.latency import format_latency_report
from soniscope_worker.oss_admin import OssAdminError, RealOssObjectStore, object_key_for
from soniscope_worker.verify_prep import FC_VERIFY_URL, ProbeError

# verify-upload 业务 reason（200 响应体字段，非 HTTP 错误码，tech-spec §4.2）。
REASON_OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
REASON_SIZE_MISMATCH = "SIZE_MISMATCH"

# 成功响应字段（verified:true 时严格 4 字段）。
VERIFIED_FIELDS: tuple[str, ...] = ("verified", "etag", "size", "last_modified")
# 鉴权失败时绝不应出现的对象信息字段（AC#6：不泄露对象信息）。
OBJECT_INFO_FIELDS: tuple[str, ...] = ("etag", "size", "last_modified", "actual_size")

# 公网匿名伪造 code：不可能换出 openid，应稳定返回 401 INVALID_CODE（AC#6）。
FAKE_CODE = "verify-live-fake-code-not-a-real-wx-login-code"

# 测试对象内容：verified 场景任意字节；size-mismatch 场景固定 100 字节。
VERIFIED_BODY = b"soniscope-verify-upload-live-test-object"
MISMATCH_BODY_SIZE = 100
MISMATCH_EXPECTED_SIZE = 200

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


@dataclass(frozen=True)
class VerifyResponse:
    """一次 ``/verify-upload`` 调用结果（状态码 + JSON body + 耗时）。"""

    status: int
    body: Mapping[str, object]
    elapsed_seconds: float


@dataclass(frozen=True)
class LiveResult:
    """单个断言结果；``status`` ∈ {PASS, FAIL, SKIP}。"""

    name: str
    status: str
    detail: str = ""
    fix_hint: str = ""

    @property
    def failed(self) -> bool:
        return self.status == FAIL


class VerifyLiveProbes(Protocol):
    """HTTP / OSS IO 注入点（单测用 Fake 替换）。"""

    def call_verify_upload(
        self, code: str, fragment_id: str, expected_size: int
    ) -> VerifyResponse: ...

    def upload_object(self, key: str, body: bytes) -> None: ...

    def delete_object(self, key: str) -> None: ...


# ── 纯断言逻辑（无 IO，直接单测）──────────────────────────────────────────────
def _body_error(body: Mapping[str, object]) -> str:
    err = body.get("error")
    return str(err) if err is not None else ""


def _leaked_object_info(body: Mapping[str, object]) -> list[str]:
    """鉴权失败响应里若混入对象信息字段或 verified==true，视为泄漏。"""
    leaked = [f for f in OBJECT_INFO_FIELDS if f in body]
    if body.get("verified") is True:
        leaked.append("verified=true")
    return leaked


def assert_auth_failure(resp: VerifyResponse, *, name: str) -> LiveResult:
    """断言伪造 code 返回 400/401 且不泄露任何对象信息（AC#6）。"""
    ok = resp.status in (400, 401)
    detail = f"HTTP {resp.status} error={_body_error(resp.body) or '∅'}（期望 400/401）"
    leaked = _leaked_object_info(resp.body)
    if leaked:
        ok = False
        detail += f"；疑似泄漏对象信息：{', '.join(leaked)}"
    return LiveResult(
        name=name,
        status=PASS if ok else FAIL,
        detail="OK — " + detail if ok else detail,
        fix_hint=""
        if ok
        else "检查 verify-upload 鉴权链路（jscode2session / allowlist）先于 HeadObject。",
    )


def assert_verified_true(
    resp: VerifyResponse, *, expected_size: int, name: str
) -> LiveResult:
    """断言 200 且 ``verified:true`` + etag/size/last_modified 齐全、size 一致（AC#3）。"""
    if resp.status != 200:
        return LiveResult(
            name, FAIL,
            f"HTTP {resp.status} error={_body_error(resp.body) or '∅'}（期望 200 verified:true）",
            "确认对象已上传、code 在 allowlist 内、ALIYUN_AK 已配置。",
        )
    missing = [f for f in VERIFIED_FIELDS if f not in resp.body]
    actual_size = resp.body.get("size")
    ok = (
        not missing
        and resp.body.get("verified") is True
        and actual_size == expected_size
    )
    detail = (
        f"OK — verified:true size={actual_size} etag={resp.body.get('etag')}"
        if ok
        else f"verified={resp.body.get('verified')} size={actual_size}"
        f"（期望 {expected_size}）缺字段={missing or '∅'}"
    )
    return LiveResult(
        name=name,
        status=PASS if ok else FAIL,
        detail=detail,
        fix_hint="" if ok else "检查 verify-upload 成功响应字段（tech-spec §4.2）。",
    )


def assert_object_not_found(resp: VerifyResponse, *, name: str) -> LiveResult:
    """断言对象缺失返回 ``verified:false`` + ``reason=OBJECT_NOT_FOUND``（AC#4）。"""
    ok = (
        resp.status == 200
        and resp.body.get("verified") is False
        and resp.body.get("reason") == REASON_OBJECT_NOT_FOUND
    )
    detail = (
        "OK — verified:false reason=OBJECT_NOT_FOUND"
        if ok
        else f"HTTP {resp.status} verified={resp.body.get('verified')} "
        f"reason={resp.body.get('reason')!r}（期望 OBJECT_NOT_FOUND）"
    )
    return LiveResult(
        name=name,
        status=PASS if ok else FAIL,
        detail=detail,
        fix_hint="" if ok else "确认对象已被删除且 HeadObject 404 映射为 OBJECT_NOT_FOUND。",
    )


def assert_size_mismatch(
    resp: VerifyResponse, *, expected_actual_size: int, name: str
) -> LiveResult:
    """断言大小不一致返回 ``SIZE_MISMATCH`` 且 ``actual_size`` 为真实大小（AC#5）。"""
    ok = (
        resp.status == 200
        and resp.body.get("verified") is False
        and resp.body.get("reason") == REASON_SIZE_MISMATCH
        and resp.body.get("actual_size") == expected_actual_size
    )
    detail = (
        f"OK — verified:false reason=SIZE_MISMATCH actual_size={resp.body.get('actual_size')}"
        if ok
        else f"HTTP {resp.status} verified={resp.body.get('verified')} "
        f"reason={resp.body.get('reason')!r} actual_size={resp.body.get('actual_size')}"
        f"（期望 SIZE_MISMATCH actual_size={expected_actual_size}）"
    )
    return LiveResult(
        name=name,
        status=PASS if ok else FAIL,
        detail=detail,
        fix_hint="" if ok else "确认 Content-Length 与 expected_size 比对逻辑（tech-spec §4.2）。",
    )


def make_fragment_id(now: datetime.datetime, *, device: str = "vrfy") -> str:
    """构造合法 fragment_id：``<YYYYMMDDTHHMMSS>_<deviceShortId>_<26 字符 ULID>``。"""
    ts = now.strftime("%Y%m%dT%H%M%S")
    suffix = uuid.uuid4().hex[:26].upper()  # [0-9A-F] ⊂ [0-9A-Za-z]，满足 fragment_id 正则
    return f"{ts}_{device}_{suffix}"


# ── 编排：跑场景 → 汇总 ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class VerifyLiveOptions:
    """test-verify-upload 运行参数（每个真实 code 一次性，缺失即 SKIP）。"""

    verified_code: str = ""  # verified:true 场景（AC#3）
    not_found_code: str = ""  # OBJECT_NOT_FOUND 场景（AC#4）
    mismatch_code: str = ""  # SIZE_MISMATCH 场景（AC#5）


@dataclass
class _RunState:
    results: list[LiveResult] = field(default_factory=list)
    latencies: list[float] = field(default_factory=list)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def run_checks(
    probes: VerifyLiveProbes,
    opts: VerifyLiveOptions,
    *,
    fragment_id_factory: Callable[[], str] | None = None,
) -> tuple[list[LiveResult], list[float]]:
    """执行全部联调场景，返回（有序结果, 每次真实调用耗时秒）。"""
    make_fid = fragment_id_factory or (lambda: make_fragment_id(_now()))
    st = _RunState()

    # A. 伪造 code → 400/401，不泄露对象信息（AC#6，始终可跑）。
    name_a = "伪造 code → 400/401 且不泄露对象信息（AC#6）"
    try:
        resp = probes.call_verify_upload(FAKE_CODE, make_fid(), len(VERIFIED_BODY))
        st.latencies.append(resp.elapsed_seconds)
        st.results.append(assert_auth_failure(resp, name=name_a))
    except ProbeError as exc:
        st.results.append(LiveResult(name_a, FAIL, str(exc)))

    # B. verified:true（AC#3）：上传对象 → verify → 断言 true → 清理删除。
    _run_verified(probes, opts, make_fid, st)

    # C. OBJECT_NOT_FOUND（AC#4）：上传后删除（构造缺失）→ verify → 断言 not found。
    _run_object_not_found(probes, opts, make_fid, st)

    # D. SIZE_MISMATCH（AC#5）：上传 100 字节、expected_size=200 → verify → 断言 mismatch。
    _run_size_mismatch(probes, opts, make_fid, st)

    return st.results, st.latencies


def _try_delete(probes: VerifyLiveProbes, key: str) -> None:
    """best-effort 清理测试对象（删除失败不影响断言结论）。"""
    try:
        probes.delete_object(key)
    except Exception:  # noqa: BLE001 - 清理失败忽略（不影响主断言）
        pass


def _run_verified(
    probes: VerifyLiveProbes,
    opts: VerifyLiveOptions,
    make_fid: Callable[[], str],
    st: _RunState,
) -> None:
    name = "上传对象 + verify → verified:true（AC#3）"
    if not opts.verified_code:
        st.results.append(LiveResult(name, SKIP, "未提供 VERIFIED_CODE（缺一次性 wx.login code）"))
        return
    try:
        key = object_key_for(fid := make_fid())
        probes.upload_object(key, VERIFIED_BODY)
    except Exception as exc:  # noqa: BLE001 - 上传/构造失败收敛为单项 FAIL
        st.results.append(LiveResult(name, FAIL, f"上传测试对象失败：{type(exc).__name__}"))
        return
    try:
        resp = probes.call_verify_upload(opts.verified_code, fid, len(VERIFIED_BODY))
        st.latencies.append(resp.elapsed_seconds)
        st.results.append(assert_verified_true(resp, expected_size=len(VERIFIED_BODY), name=name))
    except ProbeError as exc:
        st.results.append(LiveResult(name, FAIL, str(exc)))
    finally:
        _try_delete(probes, key)


def _run_object_not_found(
    probes: VerifyLiveProbes,
    opts: VerifyLiveOptions,
    make_fid: Callable[[], str],
    st: _RunState,
) -> None:
    name = "删除对象后 verify → OBJECT_NOT_FOUND（AC#4）"
    if not opts.not_found_code:
        st.results.append(
            LiveResult(name, SKIP, "未提供 NOT_FOUND_CODE（缺一次性 wx.login code）")
        )
        return
    try:
        key = object_key_for(fid := make_fid())
        probes.upload_object(key, VERIFIED_BODY)
        probes.delete_object(key)  # 仅测试用：构造对象缺失场景
    except Exception as exc:  # noqa: BLE001 - 上传/构造失败收敛为单项 FAIL
        st.results.append(LiveResult(name, FAIL, f"构造对象缺失失败：{type(exc).__name__}"))
        return
    try:
        resp = probes.call_verify_upload(opts.not_found_code, fid, len(VERIFIED_BODY))
        st.latencies.append(resp.elapsed_seconds)
        st.results.append(assert_object_not_found(resp, name=name))
    except ProbeError as exc:
        st.results.append(LiveResult(name, FAIL, str(exc)))


def _run_size_mismatch(
    probes: VerifyLiveProbes,
    opts: VerifyLiveOptions,
    make_fid: Callable[[], str],
    st: _RunState,
) -> None:
    name = "上传 100 字节、expected_size=200 → SIZE_MISMATCH（AC#5）"
    if not opts.mismatch_code:
        st.results.append(
            LiveResult(name, SKIP, "未提供 MISMATCH_CODE（缺一次性 wx.login code）")
        )
        return
    try:
        key = object_key_for(fid := make_fid())
        probes.upload_object(key, b"x" * MISMATCH_BODY_SIZE)
    except Exception as exc:  # noqa: BLE001 - 上传/构造失败收敛为单项 FAIL
        st.results.append(LiveResult(name, FAIL, f"上传测试对象失败：{type(exc).__name__}"))
        return
    try:
        resp = probes.call_verify_upload(opts.mismatch_code, fid, MISMATCH_EXPECTED_SIZE)
        st.latencies.append(resp.elapsed_seconds)
        st.results.append(
            assert_size_mismatch(resp, expected_actual_size=MISMATCH_BODY_SIZE, name=name)
        )
    except ProbeError as exc:
        st.results.append(LiveResult(name, FAIL, str(exc)))
    finally:
        _try_delete(probes, key)


def all_passed(results: Sequence[LiveResult], latencies: Sequence[float]) -> bool:
    """没有任何 FAIL（SKIP 允许）、至少跑了一项，且 P95 达标。"""
    if not results or any(r.failed for r in results):
        return False
    _, latency_ok = format_latency_report("verify-upload", latencies)
    return latency_ok


def format_report(results: Sequence[LiveResult], latencies: Sequence[float]) -> list[str]:
    """渲染人类可读汇总（含 P95 时延；绝不含 AK Secret）。"""
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
    latency_line, _ = format_latency_report("verify-upload P95", latencies)
    lines.append(latency_line)
    lines.append(f"汇总：{passed} PASS / {failed} FAIL / {skipped} SKIP")
    if all_passed(results, latencies):
        lines.append("✅ test-verify-upload 通过（无 FAIL 且 P95 达标）。")
        if skipped:
            lines.append(
                "ℹ️  存在 SKIP：传入真实 wx.login code"
                "（VERIFIED_CODE= / NOT_FOUND_CODE= / MISMATCH_CODE=）可覆盖全部路径。"
            )
        lines.append(
            "ℹ️  AC#8：运行 `make fc-logs FUNCTION=verify-upload` 查看 fragment_id / 结果 / 耗时。"
        )
    else:
        lines.append("❌ test-verify-upload 未通过，请按上面修复指引处理。")
    return lines


# ── 真实探针实现（urllib + RealOssObjectStore；缺失 / 不可达抛 ProbeError）─────
def _parse_body(raw: bytes) -> Mapping[str, object]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


class RealVerifyUploadProbes:
    """真实 HTTP / OSS 探针；构造时无副作用，调用时才触网。"""

    def __init__(self) -> None:
        self._store: RealOssObjectStore | None = None

    def _ensure_store(self) -> RealOssObjectStore:
        if self._store is None:
            try:
                self._store = RealOssObjectStore()
            except OssAdminError as exc:
                raise ProbeError(str(exc)) from exc
        return self._store

    def call_verify_upload(
        self, code: str, fragment_id: str, expected_size: int
    ) -> VerifyResponse:
        import time

        body = {"code": code, "fragment_id": fragment_id, "expected_size": expected_size}
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310 — 固定 https 常量 URL
            FC_VERIFY_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                return VerifyResponse(
                    int(resp.status), _parse_body(resp.read()), time.monotonic() - start
                )
        except urllib.error.HTTPError as exc:
            return VerifyResponse(int(exc.code), _parse_body(exc.read()), time.monotonic() - start)
        except urllib.error.URLError as exc:
            raise ProbeError(f"FC verify-upload 不可达：{exc.reason}") from exc
        except OSError as exc:  # 超时等
            raise ProbeError(f"FC verify-upload 请求失败：{type(exc).__name__}") from exc

    def upload_object(self, key: str, body: bytes) -> None:
        try:
            self._ensure_store().put_object(key, body)
        except ProbeError:
            raise
        except Exception as exc:  # noqa: BLE001 - 收敛为 ProbeError，不泄漏明文
            raise ProbeError(f"OSS put_object 失败：{type(exc).__name__}") from exc

    def delete_object(self, key: str) -> None:
        try:
            self._ensure_store().delete_object(key)
        except ProbeError:
            raise
        except Exception as exc:  # noqa: BLE001 - 收敛为 ProbeError，不泄漏明文
            raise ProbeError(f"OSS delete_object 失败：{type(exc).__name__}") from exc


# ── 顶层入口（CLI 调用）─────────────────────────────────────────────────────
def run_test_verify_upload(
    opts: VerifyLiveOptions, probes: VerifyLiveProbes | None = None
) -> tuple[list[str], int]:
    """执行 test-verify-upload，返回（报告行, 退出码）。退出码 0 表示无 FAIL 且 P95 达标。"""
    used_probes = probes or RealVerifyUploadProbes()
    results, latencies = run_checks(used_probes, opts)
    lines = format_report(results, latencies)
    return lines, (0 if all_passed(results, latencies) else 1)
