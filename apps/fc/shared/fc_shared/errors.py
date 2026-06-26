"""FC 共享错误模型与稳定错误码（US-006）。

两个 FC 函数（``issue-credential`` / ``verify-upload``）复用同一套 HTTP 错误码，
保证鉴权 / 校验失败的响应稳定一致。错误对象只携带稳定错误码与**安全**的提示信息
（绝不含 code / session_key / AK Secret / SecurityToken 明文）。
"""

from __future__ import annotations

from collections.abc import Iterable

# ── 稳定错误码（响应 body 的 "error" 字段；前端按此分支处理）─────────────────
INVALID_CODE = "INVALID_CODE"  # 401：jscode2session 换 openid 失败
OPENID_NOT_ALLOWED = "OPENID_NOT_ALLOWED"  # 403：openid 不在 allowlist
INVALID_REQUEST = "INVALID_REQUEST"  # 400：JSON 解析失败 / 非对象 / 字段缺失
SIZE_EXCEEDED = "SIZE_EXCEEDED"  # 400：size 超过 MAX_UPLOAD_BYTES（US-007）
SERVER_MISCONFIGURED = "SERVER_MISCONFIGURED"  # 500：缺必填运行时环境变量
STS_ISSUE_FAILED = "STS_ISSUE_FAILED"  # 500：AssumeRole 签发 STS 失败（不泄漏明文，US-007）
HEAD_OBJECT_FAILED = "HEAD_OBJECT_FAILED"  # 500：HeadObject 调用失败（不泄漏明文，US-009）

# ── verify-upload 校验结果 reason（verified:false 时的 "reason" 字段，US-009）─────
# 这些不是 HTTP 错误码，而是 200 响应体内的业务结果原因（tech-spec §4.2）。
OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"  # 对象不存在
SIZE_MISMATCH = "SIZE_MISMATCH"  # 对象存在但 Content-Length 与 expected_size 不一致


class FcHttpError(Exception):
    """映射为某个 HTTP 状态码 + 稳定错误码的请求级错误。

    ``payload`` 是直接序列化给客户端的 JSON 字典，固定含 ``error`` 字段；
    ``message`` 与任意 ``extra`` 字段都必须是开发者自定义的安全文案，不得携带敏感值。
    """

    def __init__(self, status: int, error_code: str, *, message: str = "", **extra: object) -> None:
        self.status = status
        self.error_code = error_code
        self.message = message
        payload: dict[str, object] = {"error": error_code}
        payload.update(extra)
        if message:
            payload["message"] = message
        self.payload = payload
        super().__init__(f"{status} {error_code}: {message}".rstrip(": "))


class FcConfigError(Exception):
    """FC 运行时缺少必填环境变量（启动 / 请求时报明确错误，只列变量名不列值）。"""

    def __init__(self, missing: Iterable[str]) -> None:
        self.missing = list(missing)
        super().__init__("缺少 FC 运行时环境变量：" + ", ".join(self.missing))
