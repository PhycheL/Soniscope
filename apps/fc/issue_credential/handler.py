"""FC 3.0 顶级 Web 函数 ``issue-credential`` 占位处理器（US-005 基线）。

本文件仅建立 ``apps/fc/`` 目录约定与可部署骨架，使 ``make deploy-fc`` 的打包 / 备份 /
部署 / 存活验证链路先行打通。真实业务逻辑（微信 code 换 openid、OPENID_ALLOWLIST
校验、STS 单 object key 凭证签发）在 US-006 / US-007 实现，届时替换本占位实现。

云端函数名为 kebab-case ``issue-credential``；代码目录用 snake_case ``issue_credential``，
由部署脚本负责名称映射（见 tech-spec §2.1 约定 6）。
"""

from collections.abc import Callable, Iterable
from typing import Any

# FC 3.0 Python Web 函数为标准 WSGI 入口。
StartResponse = Callable[[str, list[tuple[str, str]]], Any]


def handler(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
    """占位 WSGI 处理器：返回函数存活探针响应（US-006 / US-007 替换为真实逻辑）。"""
    import json

    payload = {
        "function": "issue-credential",
        "status": "placeholder",
        "story": "US-005",
        "note": "real STS issuance lands in US-006/US-007",
    }
    body = json.dumps(payload).encode("utf-8")
    start_response("200 OK", [("Content-Type", "application/json")])
    return [body]
