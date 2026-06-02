## Why

`make verify-prep` 的 E 块（NLS 云端 ASR 转写验证）当前在生成 OSS 签名 URL 时调用了 `alibabacloud_oss_v2.Client` 不存在的 `generate_presigned_url` 方法，导致真实环境校验报错 `'Client' object has no attribute 'generate_presigned_url'`。这会让 US-001 人工准备产物一键校验误报失败，即使生产转写路径已通过 AC。

## What Changes

- 修复 E 块 OSS 签名 URL 生成逻辑，改用 OSS v2 SDK 支持的 `client.presign(GetObjectRequest(...))` 路径，或复用生产模块中已有的签名 URL 生成实现。
- 为 verify-prep 的 NLS ASR 校验路径增加覆盖，确保不会再次使用不存在的 SDK 方法。
- 保持 E 块现有目标不变：使用 OSS 签名 URL 调用 NLS 文件转写，并在失败时输出可操作的修复指引。
- 不改变生产 NLS 转写 API、配置格式、CLI 命令或验收块定义。

## Capabilities

### New Capabilities
- `worker-prep-verification`: Worker 准备环境校验命令应可靠验证 NLS ASR 准备状态，并使用与 OSS v2 SDK 兼容的签名 URL 生成方式。

### Modified Capabilities

## Impact

- Affected code: `apps/worker/src/soniscope_worker/verify_prep.py` and related worker tests.
- Affected command: `make verify-prep` / `uv run --directory apps/worker python -m soniscope_worker verify-prep`.
- No external API, dependency, database, or config schema changes.
