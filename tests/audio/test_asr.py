#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SoniScope · US-001 E-6 云端语音识别可用性自检脚本.

用途
----
针对 ``docs/runbook/us-001-manual.html`` 中 E 块（云端 ASR 服务）的 E-4 / E-5 / E-6
任务做一次真实联调：把一个 OSS 上的样例录音 URL 提交给阿里云 NLS「录音文件识别」
（极速版 / 录音文件转写），轮询拿到结构化结果，并打印关键字段，方便贴入 runbook
作为基线参考。

这是一个**手动联调脚本**，不是单元测试（单元测试一律 mock，不打真实云端）。

调用方式
--------
录音文件识别是 RPC 风格的 POP API：
  1. POST  SubmitTask     提交任务，拿 TaskId
  2. GET   GetTaskResult  用 TaskId 轮询，直到 SUCCESS / 失败状态

依赖
----
    pip install 'aliyun-python-sdk-core==2.16.0'
（官方 Python Demo 推荐版本；也可 ``uv pip install aliyun-python-sdk-core`` 安装。）

凭证（绝不写进代码 / git，从环境变量或命令行传入；变量名与官方 Demo 对齐）
--------------------------------------------------------------------
    export ALIYUN_AK_ID=<调用 NLS 的 RAM 子账号 AccessKey ID>
    export ALIYUN_AK_SECRET=<对应 AccessKey Secret>
    export NLS_APP_KEY=<E 块创建的项目 AppKey>

运行
----
    # 用脚本内置的样例 URL（华北2 北京）
    python test/test_asr.py

    # 指定自己的文件 / region / 开启返回词信息
    python test/test_asr.py \\
        --file-link 'https://soniscope-audio.oss-cn-beijing.aliyuncs.com/sample/sample-20s.wav?...' \\
        --region cn-beijing \\
        --enable-words

退出码
------
    0  识别成功（拿到非空文本）—— E-4 / E-6 通过
    2  缺少凭证 / 依赖等使用错误
    3  提交任务失败（4xx，立即失败不重试）
    4  识别任务返回失败状态 / 超时 / 结果为空
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

# --- region → POP 调用参数（见 api-reference-2 §各地域POP调用参数）---
REGION_ENDPOINTS: dict[str, str] = {
    "cn-shanghai": "filetrans.cn-shanghai.aliyuncs.com",
    "cn-beijing": "filetrans.cn-beijing.aliyuncs.com",
    "cn-shenzhen": "filetrans.cn-shenzhen.aliyuncs.com",
}

PRODUCT = "nls-filetrans"
API_VERSION = "2018-08-17"
POST_ACTION = "SubmitTask"
GET_ACTION = "GetTaskResult"

# 录音文件识别状态码（见 api-reference-2 §服务状态码）
STATUS_SUCCESS = "SUCCESS"
STATUS_RUNNING = "RUNNING"
STATUS_QUEUEING = "QUEUEING"
# 识别成功但 VAD 未检测到有效语音（21050003）——也是终止态，链路其实是通的
STATUS_NO_VALID_FRAGMENT = "SUCCESS_WITH_NO_VALID_FRAGMENT"

# 本项目北京样例文件（注意：OSS 签名 URL 会过期，过期后请用 --file-link 传新链接）
DEFAULT_FILE_LINK = (
    "https://soniscope-audio.oss-cn-beijing.aliyuncs.com/sample/sample-20s.wav?Expires=1780035733&OSSAccessKeyId=TMP.3KuQrr9ih9veyriVdkVqNaFg15d6qbTPhKQEbhiHXFxAkg5KkGzyBfw5hq5wqnM8J5nvCzTyDUn7vi7dsqhEXWHuz9PLFd&Signature=Bp2nxy21THPHxav9yd3Czjtcqc8%3D"
)


def _mask(secret: str) -> str:
    """脱敏：只显示前后 4 位（遵循 tech-spec §2.3 约定）。"""
    if not secret:
        return "<空>"
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}...{secret[-4:]}"


def _print_raw_response(title: str, raw: bytes | str) -> None:
    """打印阿里云返回的原始 JSON 响应（不做任何字段裁剪）。"""
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    print(f"\n----- {title} -----")
    try:
        # 尝试格式化，便于阅读；失败则原样输出
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
    except (ValueError, TypeError):
        print(raw)
    print("-" * (len(title) + 12))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="阿里云 NLS 录音文件识别可用性自检（US-001 E-6）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--file-link",
        default=os.getenv("NLS_FILE_LINK", DEFAULT_FILE_LINK),
        help="待识别录音文件的可公网访问 URL（默认用脚本内置北京样例）",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("NLS_REGION", "cn-beijing"),
        choices=sorted(REGION_ENDPOINTS),
        help="NLS region（必须与 OSS 同区，默认 cn-beijing）",
    )
    parser.add_argument(
        "--appkey",
        default=os.getenv("NLS_APP_KEY") or os.getenv("NLS_APPKEY"),
        help="NLS 项目 AppKey（默认读环境变量 NLS_APP_KEY）",
    )
    parser.add_argument(
        "--ak-id",
        default=os.getenv("ALIYUN_AK_ID") or os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
        help="调用 NLS 的 RAM 子账号 AccessKey ID（默认读 ALIYUN_AK_ID）",
    )
    parser.add_argument(
        "--ak-secret",
        default=os.getenv("ALIYUN_AK_SECRET") or os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
        help="对应 AccessKey Secret（默认读 ALIYUN_AK_SECRET）",
    )
    parser.add_argument(
        "--enable-words",
        action="store_true",
        help="返回词级时间戳信息（version 自动锁 4.0）",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="轮询识别结果的间隔秒数（默认 5s，注意查询接口有 QPS 限制）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="轮询总超时秒数（默认 300s）",
    )
    return parser.parse_args()


def _build_client(ak_id: str, ak_secret: str, region: str) -> Any:
    try:
        from aliyunsdkcore.client import AcsClient
    except ImportError:
        print(
            "✗ 缺少依赖 aliyun-python-sdk-core。请先安装：\n"
            "    pip install 'aliyun-python-sdk-core==2.16.0'",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return AcsClient(ak_id, ak_secret, region)


def _submit_task(
    client: Any, domain: str, appkey: str, file_link: str, enable_words: bool
) -> str:
    """提交识别任务，返回 TaskId；失败则抛 SystemExit。"""
    from aliyunsdkcore.request import CommonRequest

    task: dict[str, Any] = {
        "appkey": appkey,
        "file_link": file_link,
        "version": "4.0",
        "enable_words": enable_words,
        # 大于 16kHz 自动降采样，避免采样率不匹配（41050008）
        "enable_sample_rate_adaptive": True,
    }

    request = CommonRequest()
    request.set_domain(domain)
    request.set_version(API_VERSION)
    request.set_product(PRODUCT)
    request.set_action_name(POST_ACTION)
    request.set_method("POST")
    request.add_body_params("Task", json.dumps(task, ensure_ascii=False))

    print("→ 提交识别任务 (SubmitTask) ...")
    try:
        raw = client.do_action_with_exception(request)
    except Exception as exc:  # noqa: BLE001 - POP SDK 抛通用异常
        print(f"✗ 提交任务请求失败（鉴权 / 网络 / 参数错误，立即失败不重试）：\n  {exc}", file=sys.stderr)
        raise SystemExit(3) from exc

    _print_raw_response("SubmitTask 原始响应", raw)
    resp = json.loads(raw)
    status = resp.get("StatusText")
    if status != STATUS_SUCCESS:
        print("✗ 提交任务未成功，服务端返回：", file=sys.stderr)
        print(json.dumps(resp, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(3)

    task_id = resp["TaskId"]
    print(f"✓ 任务已提交，TaskId = {task_id}")
    return task_id


def _poll_result(
    client: Any, domain: str, task_id: str, interval: float, timeout: float
) -> dict[str, Any]:
    """轮询识别结果，返回最终响应 dict。"""
    from aliyunsdkcore.request import CommonRequest

    request = CommonRequest()
    request.set_domain(domain)
    request.set_version(API_VERSION)
    request.set_product(PRODUCT)
    request.set_action_name(GET_ACTION)
    request.set_method("GET")
    request.add_query_param("TaskId", task_id)

    deadline = time.monotonic() + timeout
    print(f"→ 轮询识别结果 (GetTaskResult)，每 {interval:g}s 一次，最多等 {timeout:g}s ...")
    while True:
        try:
            raw = client.do_action_with_exception(request)
        except Exception as exc:  # noqa: BLE001
            print(f"✗ 查询结果请求失败：{exc}", file=sys.stderr)
            raise SystemExit(4) from exc

        _print_raw_response("GetTaskResult 原始响应", raw)
        resp = json.loads(raw)
        status = resp.get("StatusText")

        if status in (STATUS_RUNNING, STATUS_QUEUEING):
            if time.monotonic() >= deadline:
                print(f"✗ 超时：{timeout:g}s 内任务仍处于 {status} 状态。", file=sys.stderr)
                raise SystemExit(4)
            print(f"  … 状态 {status}，等待中")
            time.sleep(interval)
            continue

        return resp


def _render_result(resp: dict[str, Any], enable_words: bool) -> str:
    """打印结构化结果，返回终止结果：'ok' / 'no_valid' / 'fail'。"""
    status = resp.get("StatusText")
    print("\n" + "=" * 60)
    print("识别任务最终状态：", status)
    print("关键字段（可贴入 runbook 作为 E-6 基线）：")
    baseline = {
        "TaskId": resp.get("TaskId"),
        "StatusCode": resp.get("StatusCode"),
        "StatusText": status,
        "BizDuration_ms": resp.get("BizDuration"),
        "SolveTime": resp.get("SolveTime"),
    }
    print(json.dumps(baseline, ensure_ascii=False, indent=2))

    if status == STATUS_NO_VALID_FRAGMENT:
        print(
            "\n⚠ 服务正常响应，但未检测到有效语音（21050003）。"
            "\n  ASR 链路是通的，但该音频可能是纯静音 / 无人声，请换一段含清晰人声的录音重试。",
            file=sys.stderr,
        )
        return "no_valid"

    if status != STATUS_SUCCESS:
        print("\n✗ 识别未成功。请对照 api-reference-2 §服务状态码 排查 StatusCode。", file=sys.stderr)
        return "fail"

    sentences = (resp.get("Result") or {}).get("Sentences") or []
    full_text = "".join(s.get("Text", "") for s in sentences).strip()

    print("\n--- 逐句结果（含时间戳，单位 ms）---")
    if not sentences:
        print("  （无句子，可能是纯静音或无有效语音，见状态码 21050003 / ASR_RESPONSE_HAVE_NO_WORDS）")
    for idx, s in enumerate(sentences, 1):
        print(
            f"  [{idx}] {s.get('BeginTime')}–{s.get('EndTime')} "
            f"ch{s.get('ChannelId')}: {s.get('Text')}"
        )

    if enable_words:
        words = (resp.get("Result") or {}).get("Words") or []
        if words:
            print(f"\n--- 词级信息（共 {len(words)} 个词，仅展示前 20）---")
            for w in words[:20]:
                print(f"  {w.get('BeginTime')}–{w.get('EndTime')}: {w.get('Word')}")

    print("\n--- 完整转写文本 ---")
    print(full_text if full_text else "（空）")
    print("=" * 60)

    return "ok" if full_text else "no_valid"


def main() -> int:
    args = _parse_args()

    missing = [
        name
        for name, value in (
            ("AccessKey ID (--ak-id / ALIYUN_AK_ID)", args.ak_id),
            ("AccessKey Secret (--ak-secret / ALIYUN_AK_SECRET)", args.ak_secret),
            ("AppKey (--appkey / NLS_APP_KEY)", args.appkey),
        )
        if not value
    ]
    if missing:
        print("✗ 缺少以下必填凭证：", file=sys.stderr)
        for m in missing:
            print(f"    - {m}", file=sys.stderr)
        print("\n请通过环境变量或命令行参数提供后重试。", file=sys.stderr)
        return 2

    domain = REGION_ENDPOINTS[args.region]
    print("SoniScope · US-001 E-6 云端 ASR 可用性自检")
    print("-" * 60)
    print(f"region      : {args.region}")
    print(f"domain      : {domain}")
    print(f"appkey      : {args.appkey}")
    print(f"ak_id       : {_mask(args.ak_id)}")
    print(f"ak_secret   : {_mask(args.ak_secret)}")
    print(f"enable_words: {args.enable_words}")
    print(f"file_link   : {args.file_link[:80]}{'…' if len(args.file_link) > 80 else ''}")
    print("-" * 60)

    client = _build_client(args.ak_id, args.ak_secret, args.region)
    task_id = _submit_task(client, domain, args.appkey, args.file_link, args.enable_words)
    resp = _poll_result(client, domain, task_id, args.poll_interval, args.timeout)
    outcome = _render_result(resp, args.enable_words)

    if outcome == "ok":
        print("\n✓ 结论：云端语音识别可用（E-4 / E-6 通过）。")
        return 0
    if outcome == "no_valid":
        print(
            "\n⚠ 结论：ASR 链路可用，但本次音频无有效语音文本。"
            "请换含清晰人声的样例重测后再确认 E-6。",
            file=sys.stderr,
        )
        return 4
    print("\n✗ 结论：识别任务失败，ASR 链路不通，请按上方状态码排查。", file=sys.stderr)
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
