## Context

`verify-prep` 是 US-001 人工准备产物一键校验命令，用于在真实本机环境中验证 Worker 运行环境、配置、OSS、FC、NLS 等外部依赖是否就绪。E 块的目标是通过 OSS 签名 URL 触发 NLS 文件转写，从而证明 NLS 凭证、AppKey、OSS 音频可访问性以及转写响应结构可用。

当前 E 块在 `verify_prep.py` 内部重复实现 OSS 签名 URL 生成逻辑，并调用了 `alibabacloud_oss_v2.Client.generate_presigned_url(...)`。该方法不属于 Alibaba Cloud OSS v2 Python SDK，因此真实执行时会抛出 `'Client' object has no attribute 'generate_presigned_url'`。生产转写模块 `nls_transcriber.py` 已使用正确的 `client.presign(GetObjectRequest(...), expires=...)` 路径。

## Goals / Non-Goals

**Goals:**

- 让 E 块使用 OSS v2 SDK 支持的 presign API 生成 `sample/sample-20s.wav` 的 GET 签名 URL。
- 优先复用或对齐生产转写模块已有签名 URL 逻辑，避免诊断工具与生产路径漂移。
- 增加测试覆盖，验证 E 块不会再调用不存在的 `generate_presigned_url` 方法，并能把生成的签名 URL 放入 NLS `SubmitTask` 的 `file_link`。
- 保持现有 `make verify-prep` 的 CLI 行为、块命名、配置字段和输出风格不变。

**Non-Goals:**

- 不修复 A 块 OSS 403 或 B 块部署 AK 环境变量缺失；这些属于当前机器/凭证状态问题。
- 不修改 NLS 生产转写能力、结果解析模型或任务轮询策略。
- 不新增 Alibaba Cloud SDK 依赖或更换 OSS/NLS SDK。
- 不改变 config.yaml schema 或 Makefile target。

## Decisions

1. **使用 OSS v2 `client.presign(GetObjectRequest(...), expires=...)`，而不是 `generate_presigned_url`。**
   - Rationale: 这是当前 SDK 和生产模块已使用的合法 API。
   - Alternatives considered: 继续手写 signer / 使用 S3 风格 API。前者易错且重复，后者不适用于当前 SDK。

2. **优先复用 `nls_transcriber._generate_presigned_url` 或保持同源实现。**
   - Rationale: E 块是诊断生产前置条件，签名逻辑应与生产路径一致，减少 AC 通过但诊断脚本失败的漂移。
   - Alternatives considered: 在 `verify_prep.py` 内重新实现。可行但更容易再次与生产逻辑分叉。

3. **用 mock/stub 测试 E 块签名与 NLS 提交行为，不依赖真实阿里云网络。**
   - Rationale: 单元测试需要稳定验证代码路径和 SDK 调用形状；真实连通性仍由 `make verify-prep` 在人工环境中验证。
   - Alternatives considered: 新增真实云端集成测试。该方式依赖 AK、网络、费用和外部状态，不适合作为常规测试。

## Risks / Trade-offs

- [Risk] `_generate_presigned_url` 是内部 helper，复用它会跨模块访问非公开函数。→ Mitigation: 该项目内部已将签名逻辑集中在生产模块；若需要更清晰边界，可在后续改为公开 helper，但本修复优先保持最小变更。
- [Risk] E 块仍可能因真实 OSS/NLS 权限、音频对象不存在或网络问题失败。→ Mitigation: 本变更只修复 SDK API 调用错误；失败输出仍保留现有凭证/网络修复指引。
- [Risk] mock 测试无法证明真实 NLS 服务成功。→ Mitigation: 单元测试覆盖回归缺陷；`make verify-prep` 继续承担真实外部依赖校验。
