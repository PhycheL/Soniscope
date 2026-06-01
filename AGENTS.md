# AGENTS.md

该文件用于指导 AI 编码代理在本仓库中开发 **日观声记 / SoniScope**。它不是 PRD 或技术规格的替代品；遇到细节冲突时，按下列优先级处理：

1. 产品范围与验收：`docs/PRD_v1.md`
2. 技术实现、协议、数据模型：`docs/tech-spec.md`
3. 真实云资源、域名、运行环境登记：`docs/runbook/cloud-setup.md`
4. 本文件：开发时的快捷规则与红线

---

## 项目概览

SoniScope 是个人语音流水账记录工具。本期 MVP 只闭环一条链路：

**微信小程序录音 → 草稿确认 → FC 签发单文件 STS → 小程序直传 OSS → FC verify → Python Worker 轮询 OSS → 下载/标准化音频 → 调云端 ASR 转写 → 本地落盘。**

本期核心承诺：**音频与转写不丢、不重、不虚构**。本期不做 LLM 润色、不做日稿展示、不做本地 Whisper 推理、不做多用户登录系统。

---

## 项目类型

- **Monorepo**：小程序、阿里云 FC 函数、Python Worker、脚本和文档放在同一仓库。
- 当前仓库仍处于 MVP 初期：部分目标目录会随 US-002+ 逐步创建，未出现的目录不要视为异常。

---

## 架构与数据流

四层架构：

| 层 | 组件 | 职责 |
|---|---|---|
| 手机端 | 微信小程序 | 录音、中断保护、草稿、本地缓存、静默登录、STS 上传、verify、上传列表 |
| 云端计算 | 阿里云 FC 3.0 顶级 Web 函数 | `issue-credential` 签发单 object key STS；`verify-upload` HeadObject 校验 |
| 云端存储 | 阿里云 OSS 私有 Bucket | 长期音频备份，Bucket：`soniscope-audio`，region：`cn-beijing` |
| 后端进程 | Python Worker | 轮询 OSS、下载、格式标准化、云端 ASR、文件状态机落盘 |

关键原则：

- **OSS object 是小程序 / FC / Worker 的唯一数据契约**：音频 body + `x-oss-meta-*` 用户自定义元数据。
- **本地硬盘状态机是 Worker 权威状态**：以 `manifest.json`、中间态文件、`.done` 判断进度，不引入数据库。
- **FC 3.0 无 service 层级**：只操作顶级 Web 函数 `issue-credential` / `verify-upload`，不要创建或引用 `soniscope-svc`。

---

## 技术栈

| 组件 | 技术 / 依赖 | 说明 |
|---|---|---|
| 小程序 | 微信小程序 API | `wx.getRecorderManager()`、`wx.login()`、`wx.uploadFile()`、本地 storage、音频播放 |
| 小程序 sha256 | `wasm-crypto` 或同类 wasm 库 | 前端计算原始音频 sha256，避免主线程卡顿 |
| FC 运行时 | Python 3.12（或 FC 支持的 3.10/3.11） | 两个顶级 Web 函数 |
| FC SDK | `alibabacloud-sts20150401`、`alibabacloud-oss-v2` | STS AssumeRole、HeadObject verify |
| FC 部署 | `alibabacloud-fc20230330` | 仅部署脚本使用，不随函数打包 |
| Worker | Python 3.11+；当前主机 Python 3.13.2 | 包名 `soniscope-worker`，CLI：`python -m soniscope_worker` |
| Worker 依赖 | `alibabacloud-oss-v2`、`pyyaml`、`pydantic>=2`、`typer`、`alibabacloud-nls20180628` | 配置、OSS、云端 ASR、CLI |
| 系统工具 | `git`、`make`、`curl`、`ffmpeg`、`ffprobe` | Worker 音频检测/转码必须依赖 ffmpeg/ffprobe |
| 包管理 | uv workspace | 根 `pyproject.toml` 不直接装业务依赖 |
| 质量工具 | mypy strict、ruff、pytest | 顶层 Makefile 统一入口 |

禁止在本期引入 `faster-whisper` / `whisper.cpp` 作为实际依赖；本地 Whisper 只保留占位骨架。

---

## 目标仓库结构

目标结构以 `docs/tech-spec.md` §2.1 为准：

```text
my_soniscope/
├── apps/
│   ├── miniprogram/            # 微信小程序前端
│   ├── fc/<function>/          # 阿里云 FC 函数源码
│   └── worker/                 # Python Worker（包名 soniscope-worker）
├── scripts/                    # 跨组件运维与验证脚本
├── tests/
│   └── audio/                  # 共享测试音频 fixture（音频二进制不进 git；本地可拉取）
├── docs/
│   ├── PRD_v1.md               # 产品需求与 US 验收
│   ├── tech-spec.md            # 技术实现唯一权威
│   └── runbook/                # 人工准备和真实资源登记
├── pyproject.toml              # 根 uv workspace
├── Makefile                    # 唯一命令入口
└── AGENTS.md
```

当前已存在的重要目录：`docs/`、`scripts/`、`tests/audio/`、`.agents/`、`.cursor/`。`apps/`、`Makefile`、`pyproject.toml` 等会在对应 story 中创建。

---

## 运行时目录与配置

代码仓库与 Worker 运行时数据必须分离。

实际 Worker 运行时根目录：

```text
/Volumes/Data/software/SoniScope/        # $SONISCOPE_HOME
├── inbox/                                # 下载和转码中间态
├── fragments/<YYYY-MM-DD>/<fragment_id>/ # 完成态 Fragment 目录
├── tmp/                                  # 转写中间态
└── config.yaml                           # Worker 明文配置，不进 repo
```

配置加载顺序：

1. `$SONISCOPE_HOME/config.yaml`
2. 未设置 `SONISCOPE_HOME` 时回退 `~/SoniScope/config.yaml`

`config.yaml` 用 Pydantic v2 schema 校验，权限必须为 `chmod 600`。敏感字段日志只允许前后 4 位脱敏显示。

---

## 常用命令

顶层 Makefile 是唯一入口；用户不需要 `cd` 到子目录。以下命令会随 story 分阶段实现：

```bash
# 安装 / 初始化
make install
make check-config
make init-dirs
make verify-prep

# 质量门
make typecheck
make lint
make test

# Worker
make worker-run
make retranscribe FRAGMENT_ID=<id>
make retranscribe ARGS="--all-from <YYYY-MM-DD> --upgrade"

# FC 部署 / 运维
make deploy-fc FUNCTION=issue-credential
make deploy-fc FUNCTION=verify-upload
make deploy-fc
make rollback-fc FUNCTION=issue-credential
make fc-logs FUNCTION=verify-upload

# 云端联调 / 验收
make test-fc-live
make test-verify-upload
make test-sts-escape
make test-transcribe
make test-crash-recovery
make verify-e2e-integrity
make verify-e2e-sha256
make verify-e2e-fields
make verify-no-stale
make verify-oss-retention
```

新增命令时遵循 `docs/tech-spec.md` §6.5 的 target 命名，不要创建多个互相绕开的入口。

---

## 实施顺序

按 PRD user stories 与 tech-spec 里程碑推进：

| 里程碑 | 范围 | 完成标志 |
|---|---|---|
| M0 | US-001 人工准备 | `make verify-prep` 全绿 |
| M1 | US-002 + US-003 + US-005 | 骨架、配置、FC 两函数、部署联调全绿 |
| M2 | US-007 ~ US-014 | 小程序录音 → 上传 → verify，DevTools + 真机验证 |
| M3 | US-015 ~ US-019 | Worker 轮询 → 下载 → 转写 → 落盘，崩溃恢复成功 |
| M4 | Feature E2E | PRD §4 自动脚本 + 真机 checklist 全部通过 |

从 M1 开始，**不要让用户回阿里云 / 微信控制台手工配置**。需要写代码、脚本或配置读取的事情应自动化为 `make` 命令；唯一的人工动作是 US-001 准备、真机 UI 验证、必要的真实 `wx.login` code 获取。

---

## 关键业务与协议约定

### Fragment ID

格式：

```text
<YYYYMMDDTHHMMSS>_<deviceShortId>_<ulid>
```

长录音分片共享 `session_id`，每片独立 `fragment_id`，`chunk_seq` 从 1 递增。分片阈值：`CHUNK_MAX_DURATION_SECONDS = 600`。

### OSS Key

```text
recordings/<YYYY-MM-DD>/<fragment_id>.wav
```

即使前端实际录到的是 `mp3` / `aac` / `m4a` / `amr`，OSS object key 也使用 `.wav` 扩展名，表示 Worker 侧最终标准化目标。

### OSS 用户自定义元数据

前端上传时必须附带：

- `x-oss-meta-session-id`
- `x-oss-meta-chunk-seq`
- `x-oss-meta-chunk-total`（非分片用 `0`）
- `x-oss-meta-recorded-at`
- `x-oss-meta-duration`
- `x-oss-meta-original-format`
- `x-oss-meta-sha256`

Worker 用 HeadObject 读回这些字段并写入 `manifest.json`。

### Worker 完成态

每个完成 Fragment 目录必须包含 5 个文件：

```text
audio.wav
manifest.json
transcript.json
transcript.txt
.done
```

当且仅当 `.done` 存在时视为完整完成。正常轮询中，`.done` 存在即跳过，不因模型或 `params_version` 变化自动重转。

---

## FC API 约定

### `POST /issue-credential`

请求：

```json
{ "code": "<wx.login code>", "fragment_id": "<id>", "size": 1234567 }
```

流程：

1. 用 code 调微信 `jscode2session` 换 openid；失败返回 `401 INVALID_CODE`
2. 检查 `OPENID_ALLOWLIST`；不在列表返回 `403 OPENID_NOT_ALLOWED`
3. 检查 `size <= MAX_UPLOAD_BYTES`；超限返回 `400 SIZE_EXCEEDED`
4. AssumeRole 签发仅允许 `oss:PutObject` 到单个 object key 的 STS，有效期 ≤ 900 秒

### `POST /verify-upload`

请求：

```json
{ "code": "<wx.login code>", "fragment_id": "<id>", "expected_size": 1234567 }
```

返回：

- 对象不存在：`{ "verified": false, "reason": "OBJECT_NOT_FOUND" }`
- 大小不一致：`{ "verified": false, "reason": "SIZE_MISMATCH", "actual_size": ... }`
- 校验通过：`{ "verified": true, "etag": "...", "size": ..., "last_modified": "..." }`

鉴权同 `issue-credential`。

---

## 真实云资源速查

来自 `docs/runbook/cloud-setup.md`，如有变更以 runbook 为准。

| 项 | 实际值 |
|---|---|
| OSS Bucket | `soniscope-audio` |
| Region | `cn-beijing` |
| OSS Endpoint | `oss-cn-beijing.aliyuncs.com` |
| 上传域名 | `https://soniscope-audio.oss-cn-beijing.aliyuncs.com` |
| RAM Role ARN | `acs:ram::1633875501759333:role/soniscope-uploader-role` |
| FC `issue-credential` URL | `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run` |
| FC `verify-upload` URL | `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run` |
| 小程序 AppID | `wx3f973c7297728b0c` |
| ASR Provider | 阿里云智能语音交互 NLS |
| ASR 项目 / endpoint | `soniscope` / `cn-beijing` |
| ASR 模型 | `中文普通话（识音石 V1 - 端到端模型)` |
| Worker 主机 | Mac Studio M4 Max，macOS 26.5，Python 3.13.2 |
| `$SONISCOPE_HOME` | `/Volumes/Data/software/SoniScope` |

注意：`issue-credential` 的 FC URL 子域名确实是 `issue-cedential-...`（少一个 `r`）。这是阿里云分配的真实 URL，**不要“修正”拼写**。

---

## 安全红线

- 小程序源码中绝不能出现长期 AccessKey、Secret、AppSecret、业务密钥。
- 明文 AK / Secret / Token / AppSecret 不进 git，不写入示例配置，不完整打印到日志。
- FC 运行时凭证只能从环境变量读取；部署期凭证用 `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET`，来源为本地 `.env` 或 CI secret。
- Worker 凭证只放 `$SONISCOPE_HOME/config.yaml`，权限 `600`，与 repo 分离。
- STS policy 必须精确到单个 object key，只允许 `oss:PutObject`，不能带通配符放宽。
- Worker 业务路径绝不调用 OSS `DeleteObject`。测试脚本 `oss-delete-obj` 只可用于构造验证场景，必须标注“仅测试用”。
- FC 日志可以记录 openid 哈希、fragment_id、结果、耗时；不要记录完整 openid、AK、Secret、security token。
- FC HTTP 触发器认证方式为 anonymous，但业务层必须用 openid allowlist 兜底；直接匿名 curl 或伪造 code 不得拿到凭证。

---

## 错误处理与重试

统一策略：

| 错误类型 | 策略 |
|---|---|
| 网络错误 / 5xx | 指数退避重试 3 次：5s → 15s → 45s |
| 4xx 鉴权 / 配额 / 参数错误 | 立即失败，不重试，展示明确错误码 |
| 小程序离线 | 切为 `待上传（离线排队）`，恢复网络后自动上传 |
| 上传重试 3 次仍失败 | 切为 `待人工重传` 红色提示 |
| verify 重试 3 次仍失败 | 切为 `待人工 verify` 红色提示 |
| Worker 下载失败 | 删除 `.part`，下一轮自动重下 |

---

## 小程序开发约定

- 前端保持极薄：只做采集、草稿、本地缓存、上传、状态展示；不做业务鉴权、不保存长期密钥。
- 前端不转码音频，必须记录真实 `audio.original_format`。
- 保存并上传前先生成草稿；用户显式确认后才成为 Fragment。
- 录音中断（锁屏、来电、切后台、杀进程）必须自动 stop 并保存草稿。
- verify 通过后本地音频仍保留至少 48 小时；verify 未通过永不自动删除。用户手动删除未通过录音时必须二次确认。
- 上传列表维护 8 种状态：`draft`、`queued`、`uploading`、`pending_verify`、`verified`、`upload_failed`、`manual_retry`、`manual_verify`。
- 开发环境提供故障注入菜单：`mock-fc-url-broken`、`mock-network-offline`、`mock-verify-fail`；生产环境不可见。
- UI 验证不能用普通浏览器替代；用微信开发者工具模拟器 + 真机预览。

---

## Worker 开发约定

- Worker 包名：`soniscope-worker`；模块目录：`apps/worker/src/soniscope_worker/`。
- 初始模块至少包含：`__init__.py`、`__main__.py`、`cli.py`、`config.py`、`paths.py`；后续按 story 扩展。
- 所有写文件流程必须遵守三段式协议：先临时文件 → 原子 rename → 最后写 `.done`。
- `inbox/`、`tmp/`、`fragments/` 必须位于同一文件系统，保证 rename 原子性。
- 启动时执行恢复扫描：清理 `inbox/*.part`、`inbox/*.wav.tmp`、`tmp/*.transcript.json.tmp`，再按 fragment 目录状态恢复。
- 格式检测用 `ffprobe`；非 WAV 或不合规 WAV 用 `ffmpeg` 标准化为 `audio.wav`。
- 转码失败移动到 `inbox/failed/` 留档，不污染 `fragments/`。
- 云端 ASR 默认走 OSS 签名 URL（`upload_mode=oss-url`），降级才直传本地 `audio.wav`。
- 转写抽象接口按 `docs/tech-spec.md` §5.3；`whisper-local` 本期只允许 `NotImplementedError` 占位。
- ASR 调用后输出成本可观测结构化日志，字段见 tech-spec §6.8。
- `retranscribe` 是唯一自动幂等规则之外的存量重转入口；支持 `--force`、`--upgrade`、`--all-from`。

---

## FC 开发与部署约定

- 代码目录可用 snake_case（如 `apps/fc/issue_credential/`），但 `make deploy-fc FUNCTION=`、`make rollback-fc FUNCTION=`、`make fc-logs FUNCTION=` 参数统一用云端 kebab-case 名称。
- `make deploy-fc` 必须：独立打包每个函数、部署前备份线上代码、写部署日志、上传后 curl 存活验证。
- 部署不应改动 FC 环境变量、触发器、运行时配置；这些由 US-001 人工准备。
- 打包产物放 `build/fc/<function_name>/`；备份放 `build/fc/backup/<timestamp>/`；日志放 `build/fc/logs/`；`build/` 必须 gitignore。
- `alibabacloud-fc20230330` 只在部署脚本中使用，不随函数代码打包。

---

## 测试与验证规则

- 每个 story 的 AC 尽量提供自动脚本；除微信 DevTools / 真机验证外，不要求用户手工点控制台。
- 单元测试必须 mock 云端依赖（OSS、FC、NLS、微信接口），真实云端调用只放到明确命名的 live / e2e target 中。
- 涉及云端真实调用的脚本要输出 pass/fail 汇总和修复指引。
- 提交前最低质量门：

```bash
make typecheck
make lint
make test
```

- 完成 FC 相关 story 时，还要跑对应 live 验证：

```bash
make deploy-fc FUNCTION=<function-name>
make test-fc-live          # issue-credential
make test-verify-upload    # verify-upload
```

- 完成 Worker 相关 story 时，至少覆盖：下载中断、转码失败、WAV 直通、多格式转 WAV、崩溃恢复、幂等跳过、显式重转。
- 最终 MVP 验收按 `docs/PRD_v1.md` §4：100 条真机录音 + 自动完整性脚本 + 异常路径 + 安全反例 + OSS 保留。

---

## 测试音频 fixture

测试音频二进制不应作为新增内容进 git；权威清单在 runbook §6 与 tech-spec §6.3.1。

本地获取 / 校验：

```bash
python3 scripts/fetch_test_fixtures.py
python3 scripts/fetch_test_fixtures.py --check
```

当前 fixture：

| 文件 | 用途 | sha256 |
|---|---|---|
| `sample-20s.wav` | ASR 联调 + US-017 | `b07dee76f9cab9cf4ed9ba482e7a6287409180fc05e476365bd9a92f665b7828` |
| `sample-54s.wav` | P-01 性能基线 | `9c454b212654f8948557123d9bc16d78ea6b2cf425484fca195b60fe9c7c9cde` |
| `sample-25min.wav` | 长录音分片 | `34db505eb44f93fd092e868664979c155ebbbb6c0a61019dd840b30d276cdb27` |
| `sample-20s.m4a` | m4a/AAC 转 WAV 验证 | `d3d2866128efe258ff95e841a16e7abb4d783fd37536692932a875f9fb5380fd` |

---

## 关键文件

| 文件 | 用途 |
|---|---|
| `docs/PRD_v1.md` | 产品需求、User Stories、最终验收、Non-goals |
| `docs/tech-spec.md` | 架构、数据模型、API、文件状态机、依赖、make target、ADR 的技术权威 |
| `docs/runbook/cloud-setup.md` | 真实云资源、URL、openid、ASR、测试素材、Worker 主机登记 |
| `docs/runbook/us-001-manual.html` | 唯一人工准备 story 的操作手册 |

---

## 按需查阅

| 需要了解 | 查阅位置 |
|---|---|
| User Story 具体 AC | `docs/PRD_v1.md` §3 |
| Feature 最终验收 | `docs/PRD_v1.md` §4 |
| Non-goals / 范围红线 | `docs/PRD_v1.md` §6 |
| Fragment / manifest / transcript schema | `docs/tech-spec.md` §3 |
| FC API 协议 | `docs/tech-spec.md` §4 |
| 音频格式与 ASR 策略 | `docs/tech-spec.md` §5 |
| Make target 清单 | `docs/tech-spec.md` §6.5 |
| 前端 8 状态上传状态机 | `docs/tech-spec.md` §6.7 |
| 架构决策记录 | `docs/tech-spec.md` §8 |
| 真实 URL / 域名白名单 / openid | `docs/runbook/cloud-setup.md` §3-4 |
| ASR 联调基线与成本 | `docs/runbook/cloud-setup.md` §5 |

---

## 开发代理工作方式

- 开始实现前先确认当前 story 编号和依赖是否满足；不要跨 story 偷做大量后续功能。
- 优先把可验证动作做成顶层 `make` target，减少用户手工步骤。
- 写代码时匹配项目约定：Python 使用类型注解、Pydantic v2、mypy strict、ruff；部署/运维脚本输出清晰 pass/fail。
- 修改协议、schema、状态机或云资源时，必须同步检查 PRD、tech-spec、runbook 三处是否需要更新；技术细节以 tech-spec 为唯一权威。
- 不要把“看起来像 typo”的真实云资源值自动纠正；尤其是 `issue-cedential-ottfirocds`。
- 不确定真实云端状态时，写脚本验证并报告结果；不要凭记忆假设控制台配置。
- 完成工作时明确说明跑过哪些验证、哪些没跑、失败输出是什么。不要声称未验证的内容已通过。
