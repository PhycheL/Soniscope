# PRD: 日观声记 MVP（SoniScope）

> 本 PRD 定义产品需求（WHAT + WHY），**仅覆盖本期 MVP 范围**（录音 → 草稿 → 上传 OSS → 上传确认 → 本地下载 → **云端 API 转写** → 落盘）。**本期不部署本地 Whisper**，转写走公共云端语音转文字 API；本地模型推迟到流程跑通后再评估。下一阶段计划见 §7 Future Roadmap。
>
> **技术实现细节**（架构、API 协议、数据模型、文件状态机、依赖清单、ADR 等）的权威定义在 `docs/tech-spec.md`。本 PRD 中 User Story 的 AC 仍包含必要的技术描述以便 AI 编程，但当两者冲突时以 tech-spec.md 为准。

---

## 1. Introduction / 概述

「日观声记」是一款个人语音流水账记录工具。用户在微信小程序里随手按一下就开始录音，松手再按一下结束；录音被自动保存到云端 OSS 作为长期备份，并由一个独立的 **Python Worker 后端进程**（与平台 / 宿主机无关，能跑 Python 3.11+ 即可）拉取后**调用云端语音转文字 API**转写成结构化文本。

> **重要决策（v1）**：本期 MVP **优先用公共云端语音转文字 API**（如阿里云智能语音交互 NLS / 通义听悟 / OpenAI Whisper API 等）跑通整条链路；**本地 Whisper large-v3 部署推迟到流程跑通后再评估**。这样能尽快闭环，避免把模型部署的复杂度引入 MVP。`Transcriber` 抽象接口仍然预留，方便后续切换到本地实现。

本 MVP 的核心承诺是：**只要用户说出口的话，必须 100% 落到云端音频 + 本地文本，绝对不丢、不重、不虚构**。本期不做 LLM 润色、不做日稿展现，只把"声音 → 云端备份 → 本地转写文件"这条链路跑通且稳定。

整个系统分四层：
- **微信小程序**：极薄前端，只做录音、草稿管理、上传、上传列表展示
- **阿里云函数计算 FC**：签发单 object key 级别的 STS 临时凭证 + 上传完整性校验
- **阿里云 OSS（私有 Bucket）**：长期音频备份，**永不删除**
- **Python Worker（后端进程）**：可配置频率轮询 OSS、下载、**调用云端语音转文字 API 转写**、按文件状态机落盘；运行环境与操作系统无关，可部署在 Linux 服务器 / Docker / 个人电脑 / NAS 等任意位置（本期不做本地模型推理）

---

## 2. Goals / 目标

- **G-1（数据零丢失）**：从录音到本地落盘的整链路成功率达到 100%；任何环节中断都能自动恢复或显式提示人工重传。
- **G-2（极低摩擦）**：日常记录场景下，从打开小程序到开始录音 ≤ 2 次点击；停止后默认进入草稿确认态，避免误传。
- **G-3（云端长期备份）**：每条 Fragment 在 OSS 上都有完整对象，FC `/verify-upload` HeadObject 通过；OSS 文件永不被Worker删除。
- **G-4（转写幂等）**：Worker 以 `.done` 标记判等——`.done` 存在即跳过，不因配置变更自动重转（避免重复消耗云端 API 额度）；存量重转**只能**通过 `retranscribe` CLI 显式触发（见 tech-spec §3.7）。
- **G-5（安全可控）**：小程序代码内不含任何长期 AccessKey；STS 临时凭证只能写本次指定的那一个 object key；FC 接口拒绝匿名调用。
- **G-6（可验证）**：本期所有验收项（§9 Success Metrics R-01 ~ U-03）均能通过明确的人工或脚本步骤验证通过。

---

## 3. User Stories

> 拆分顺序：**基础设施 → 后端 FC → 前端小程序 → Worker → Feature 最终验收 AC（见 §4）**。前置 story 完成后下游 story 才能真实联调；每个 story 的 acceptance criteria 都写成可观测、可验证的结果，而不是实现描述。

### 3.0 人 vs AI 分工说明

为了把"需要人在控制台 / 浏览器 / 真机上动手"的事情和"AI 写代码"的事情彻底切开，本 PRD 采用如下分工：

| 分工类型 | 范围 | 谁来做 |
|---|---|---|
| **US-001（唯一的人工准备 story）** | 所有需要人工在控制台 / 浏览器 / 真机操作的一次性准备工作：阿里云账号 / OSS / RAM / FC 服务槽位 / 微信小程序账号 / 域名白名单 / 云端 ASR 注册 / 测试音频素材准备 / Worker 运行环境就绪 / 凭证注入 / runbook 登记。 | **人工**：用户在控制台/浏览器/终端按 checklist 完成，每项给出"检查方法"。 |
| **US-002 ~ US-019（全部由 AI 编程完成）** | 所有需要写代码、写脚本、写配置的工作：项目骨架 / FC 函数代码 / 部署脚本 / 小程序代码 / Worker 代码 / 集成测试脚本 / 文档。 | **AI 编程**：基于 US-001 已准备好的资源和凭证，写代码 + 写一键运行的脚本；用户只需 `git pull` → 跑脚本 → 看结果，无需再回控制台手工操作。 |
| **§4 Feature 最终验收 AC（由 AI 提供脚本 + 用户在真机执行）** | E2E 验收的自动验证脚本（`make verify-e2e-*`、`make test-e2e-*` 等）由 AI 实现；真机录音、中断、长录音、故障注入这些只能人工执行的环节由用户跑。 | **AI**：提供所有 `make` 验收脚本；**用户**：按 §4.2 真机 checklist 操作。 |

**关键约定**：
- 从 US-002 开始的所有 stories **不再要求用户回控制台做任何手工配置**。所有可自动化的事情（部署 FC、推送代码、初始化目录、跑测试），AI 必须提供脚本/命令；用户只跑命令、不点控制台。
- **唯一需要用户手动跑的环节**是：① 真机操作小程序进行 UI 验证（这是测试本身，不是准备工作）；② US-001 中的反例验证（如尝试 AccessDenied 场景）。
- 如果某个 story 的 AC 要求"环境变量 / API 凭证 / 真机 openid"等数据，AI **必须假设这些已由 US-001 准备好**，并在代码中通过环境变量 / 配置文件读取。AI 不应让用户在实施 US-002+ 时再回控制台填值。

### 3.1 验证说明

> **UI 验证**：本项目前端是微信小程序，无法使用 agent-browser。所有 UI stories 用"**微信开发者工具（DevTools）模拟器 + 真机预览**"双重验证，并明确写出：打开哪个页面、执行什么操作、看到什么状态/文案、控制台是否报错。

> **AC 验证脚本化**：从 US-002 开始，每个 story 的 AC 验证步骤要么能通过 AI 提供的脚本/命令一键完成（如 `make test-fc-live`、`make test-verify-upload`，完整 make 清单见 tech-spec §6.5），要么是用户在真机/DevTools 上的标准化操作（如"录音 5 秒"）。不允许出现"请到 X 控制台手工配置 Y"这种步骤。

### 3.2 仓库结构约定

> 完整的 Monorepo 结构、运行时目录布局、关键约定见 `docs/tech-spec.md` §2.1 / §2.2。

本仓库采用 **monorepo**，微信小程序、FC 函数、Worker 进程放在同一 git 仓库，便于协议与数据契约同步演进。核心目录：`apps/miniprogram/` · `apps/fc/` · `apps/worker/` · `scripts/` · `tests/` · `docs/`。

---

> **编号说明**：US-004、US-006 在需求整理过程中被合并到相邻 story 中，编号保留缺口以避免重编号引发的交叉引用混乱。

### 阶段 1：基础设施 (Infrastructure)

#### US-001: 人工准备：账号 / 资源 / 凭证 / 测试素材 / 运行环境

> **本 story 是整个 MVP 唯一的人工准备 story**，全部在控制台 / 浏览器 / 终端手工完成，不写业务代码。完成后所有后续 stories（US-002 ~ US-019）才能由 AI 编程接手。
>
> **详细操作手册**：`docs/runbook/us-001-manual.html`（含分步操作、验收清单、CLI 命令）。
> **资源登记表**：`docs/runbook/cloud-setup.md`（完成后的实际值记录）。

**描述：** 作为开发者，我需要一次性把阿里云（OSS / RAM / FC）、微信小程序、云端语音转文字 API、测试音频素材、Worker 运行环境、凭证注入这六类外部依赖全部准备就绪，让 AI 从 US-002 开始可以纯靠代码 + 脚本完成剩余工作，不再回控制台。

**Acceptance Criteria：**

| 块 | 需要完成的事项 | 技术参考 |
|---|---|---|
| **(A) OSS** | 阿里云实名 + 充值 + 创建私有 Bucket（ACL = private） | — |
| **(B) RAM** | 创建两个 RAM 子账号（`soniscope-fc` + `soniscope-local-reader`）+ 一个角色（`soniscope-uploader-role`）；STS 正例/反例验证通过 | tech-spec §4.4 |
| **(C) FC** | 开通 FC 3.0 + 创建 `issue-credential` / `verify-upload` 两个 Web 函数 + HTTP 触发器（anonymous） | — |
| **(D) 微信小程序** | 注册小程序 + 配置服务器域名白名单 + 安装开发者工具 + 获取真机 openid | — |
| **(E) ASR** | 开通云端 ASR 服务 + 创建项目 + 用测试音频完成一次真实联调基线 | — |
| **(F) 测试音频** | 准备 4 段标准测试音频到 `tests/fixtures/audio/`，sha256 登记到 runbook | — |
| **(G) Worker 环境** | 选定 Worker 主机 + Python ≥ 3.11 + 系统工具 + 工作目录 | — |
| **(H) 凭证注入** | FC 环境变量填入 tech-spec §4.0 定义的变量 + Worker `config.yaml` 按 tech-spec §2.3 schema 填入 | tech-spec §4.0 / §2.3 |
| **(I) 文档登记** | `docs/runbook/cloud-setup.md` 包含全部非敏感资源信息（无明文 AK） | — |

**完成判据**：
- [ ] 操作手册（`docs/runbook/us-001-manual.html`）中所有 checkbox 全部勾选
- [ ] 登记表（`docs/runbook/cloud-setup.md`）自检命令全部通过（§9 节）
- [ ] 无明文 AK / Secret 进入 git 仓库

---

**最终验收命令（一行跑完所有可自动化的检查项）**：

完成后，AI 将在 US-002 中提供一个 `make verify-prep` 脚本，执行下面这些检查并汇总 pass/fail 报告：
- 跑 `aliyun oss stat oss://soniscope-audio` 验证 Bucket 私有
- 跑 4 条 STS 反例（PutObject 越界 / ListBucket / GetObject / Expired）
- `curl` 两个 FC URL 返回 200
- `ls tests/fixtures/audio/` 4 个文件存在（3 mp3 + 1 aac）+ sha256 匹配
- `make check-config` 读取 `~/SoniScope/config.yaml` 通过

> ⚠️ `make verify-prep` 脚本本身由 AI 在 US-002 提供；US-001 完成时只需手工跑过反例验证 + 把信息记入 runbook 即可。

#### US-002: Python 项目骨架 + 配置 schema + `make verify-prep` 准备校验脚本

> **AI 编程任务**：写 Python 项目骨架、配置 schema、CLI 入口、`make verify-prep` 一键校验脚本。
>
> **前置假设（来自 US-001）**：用户已按 US-001 H 块填好 `~/SoniScope/config.yaml`，已按 F 块准备好 `tests/fixtures/audio/*.mp3`。本 story 不要求用户做任何额外手工操作。

**描述：** 作为开发者，我需要 AI 搭好 **monorepo 骨架**（顶层 uv workspace + `apps/worker/` Python 子项目 + 顶层 Makefile），实现 Worker 的配置 schema 与 CLI 入口，并提供 `make verify-prep` 脚本验证 US-001 准备的全部产物（OSS / RAM / FC / 测试音频 / config.yaml）真实可用。本 story **不**创建 `apps/miniprogram/` 与 `apps/fc/`（它们分别由 US-007+ 和 US-003+ 创建对应代码），但顶层 workspace 配置要为后续 member 留好位置。

> **技术规范参考**：Monorepo 结构见 `docs/tech-spec.md` §2.1，配置 Schema 见 §2.3。

**Acceptance Criteria：**

**(A) monorepo + uv workspace 骨架**
- [ ] monorepo workspace 配置符合 tech-spec §2.1（根 pyproject 不直接装业务依赖，`apps/fc` 在 US-003 时追加）
- [ ] Makefile 提供 tech-spec §6.5 列出的所有 target，用户不需要 cd 进子目录
- [ ] Worker 子项目依赖符合 tech-spec §6.3
- [ ] Worker 模块清单符合 tech-spec §2.1 Worker 子项目约定；CLI 入口可通过 `make` 别名调用
- [ ] 跑 `make install` → 在干净环境中能在 5 分钟内安装完成所有 Python 依赖；lock 文件已生成并已 commit
- [ ] **目录合规**：存在 `apps/worker/` 子项目；`apps/miniprogram/` 与 `apps/fc/` 本 story 不要求存在

**(B) 配置 schema + 加载器**
- [ ] 配置 schema 与加载器符合 tech-spec §2.3（字段定义、加载顺序、脱敏规则）；缺失必填字段时 raise 明确异常 + 列出所有缺失字段名

**(C) CLI 命令**
- [ ] `make check-config` → 读取配置 → 打印脱敏摘要 → 对缺失字段报错并退出非零
- [ ] `make init-dirs` → 在 `SONISCOPE_HOME`（默认 `~/SoniScope/`）下创建 `inbox/` / `fragments/` / `tmp/`，已存在时幂等不报错

**(D) `make verify-prep` 一键校验 US-001 全部产物（本 story 最关键的产出）**
- [ ] `make verify-prep` 依次执行下列检查，并输出汇总 pass/fail 报告：
  1. **(A 块)** 读取 `config.yaml` → 用只读 AK 验证 Bucket 存在且 ACL = private
  2. **(B 块)** 用 FC 部署凭证（来源由实现决定，**仅本机测试用**）调 STS AssumeRole，policy 限定到单个 object key → 拿到临时凭证 → 跑 4 个反例（越界 PutObject / ListBucket / GetObject / 等待超过 tech-spec §4.1 有效期上限后 ExpiredToken）→ 全部如预期失败才算 pass
  3. **(C 块)** `curl` FC 两个 URL → HTTP 状态码 200~499（不是 5xx / 网络错误）
  4. **(E 块)** 用 config 中的 NLS AppKey + AK，上传 `tests/fixtures/audio/sample-10s.mp3` → 拿到结构化转写结果 → 验证结构符合 tech-spec §3.4
  5. **(F 块)** `tests/fixtures/audio/sample-{10s,1min,25min}.mp3` + `sample-aac.aac` 四个文件存在 + sha256 与 runbook 中记录的一致 + ffprobe duration 与文件名标注的时长在 ±2s 内；额外检查 `sample-aac.aac` 的 codec=aac（验证 OQ-1 转码 fixture 就绪）
  6. **(G 块)** Python 版本 ≥ 3.11；`SONISCOPE_HOME` 路径可写；可用磁盘 ≥ 50GB；`ffmpeg` + `ffprobe` 可用（**OQ-1 决议依赖**）
  7. **(H 块)** `~/SoniScope/config.yaml` 权限为 600；所有必填字段非空
- [ ] 单项失败时，输出中包含**修复指引**（如 "请重做 US-001 (B) 反例 3"，附 runbook 中对应章节锚点）
- [ ] 全部通过时，最后一行打印 `✅ US-001 preparation verified. Ready for US-003+`
- [ ] **runbook 中 sha256 校验失败**时（用户改动了 fixture）→ 明确提示并指向 US-001 (F) 块的更新步骤

**(E) 质量门**
- [ ] `make typecheck` 通过（mypy strict 模式）
- [ ] `make lint` 通过
- [ ] `make test` 覆盖配置 schema 的合法 / 非法场景（至少 5 个测试用例）；对涉及云端的检查项（OSS / FC / NLS）使用 mock 而非真实 API

**(F) 用户操作清单（用户只需要做这两步，不回控制台）**
- [ ] 用户跑 `make install` 一次
- [ ] 用户跑 `make verify-prep` 一次 → 看到 `✅ US-001 preparation verified. Ready for US-003+`

---

### 阶段 2：后端 FC（阿里云函数计算）

#### US-003: FC `/issue-credential` 完整交付（openid 校验 + STS 签发 + 部署 + 云端 verify）

> **AI 编程任务**：写 `/issue-credential` 的 handler 代码 + FC 部署能力首版（`make deploy-fc`）+ 在云端真实联调全部 AC。
>
> **前置假设（来自 US-001）**：FC 服务 `soniscope-svc` 已开通、两个函数槽位已建好（hello world 状态）、HTTP 触发器已配置、微信合法域名白名单已配置、FC 环境变量已注入。本 story 不要求用户回控制台做任何配置。
>
> **本 story 完整闭环**：写完即部署到云端真实 FC、云端 AC 全部 verify 通过，故事独立可交付。

**描述：** 作为系统所有者，我需要 FC `/issue-credential` 接口在云端真实可用，能 (1) 用 wx.login code 换 openid 校验是否在 allowlist，(2) 给合法用户签发精确到单 object key 的 STS 临时凭证（有效期与大小上限见 tech-spec §4.1），(3) 拒绝越权 / 过期 / 超限请求。

> **技术规范参考**：API 协议完整定义见 `docs/tech-spec.md` §4.1 / §4.4 / §4.5。

**Acceptance Criteria：**

**(A) handler 代码 — openid 校验 + allowlist**
- [ ] FC 函数 `/issue-credential` 请求/响应字段与错误码严格符合 tech-spec §4.1 定义
- [ ] FC 通过微信开放接口换 openid → 检查 allowlist → 签发 STS，鉴权流程三步走（tech-spec §4.1 鉴权流程）
- [ ] FC 环境变量 `OPENID_ALLOWLIST` 中硬编码 openid 列表（逗号分隔，支持多设备测试）
- [ ] FC 日志记录每次调用的 openid（哈希后）、fragment_id、判定结果

**(B) handler 代码 — STS 签发 + 大小校验**
- [ ] STS 签发协议（object key 规则、Policy 模板、有效期、返回字段）严格符合 `docs/tech-spec.md` §4.1 / §4.4 定义
- [ ] **上传大小上限校验**：FC 检查请求 `size` 字段，超限时按 tech-spec §4.1 定义的错误格式返回 400；上限值通过 FC 环境变量 `MAX_UPLOAD_BYTES` 可调

**(C) FC 部署能力首版（含工程化基线）**
- [ ] FC 函数源码组织符合 tech-spec §2.1
- [ ] 仓库新增部署脚本和顶层 `make deploy-fc` target
- [ ] `make deploy-fc` 的打包、上传、备份、回滚、日志机制严格符合 tech-spec §6.4；接收 `FUNCTION=<name>` 参数（不传时默认部署所有函数）；部署**不动**环境变量 / 触发器 / 运行时配置（US-001 已配好）；部署完成后自动 `curl` 做存活验证
- [ ] 部署脚本读取 FC 部署所需的 AK 来源按 tech-spec §6.4 部署期环境变量定义注入，**不写死到代码里**
- [ ] **工程化基线（必须在首次部署就具备，US-005 直接复用）**：备份 + 回滚 + 部署日志能力符合 tech-spec §6.4；`build/` 目录已加入 `.gitignore`

**(D) 云端联调（必须在云端真实 FC 上 verify）**

> 下列 AC 中的错误码字面值（如 `INVALID_CODE`、`SIZE_EXCEEDED`）用于观测验证，权威定义见 tech-spec §4.1 / §4.2。

- [ ] 跑 `make deploy-fc FUNCTION=issue_credential` 把 (A)(B) 代码推到云端，部署日志显示 200 + curl 存活验证通过
- [ ] **公网 curl 拒绝匿名验证**：从任意可访问公网的终端用 `curl` 直接调用 FC 公网 URL（不带 code 或带伪造 code）**必须**被拒（400/401/403），不会拿到任何凭证
- [ ] **wx-login 失败验证**：跑 `make test-fc-live` → 用 `tests/fixtures/wx-login-fixture.json` 中的伪造 code 调 `/issue-credential` → 验证返回 401 `INVALID_CODE`（证明 (A) 代码生效）
- [ ] **allowlist 拒绝验证**：用真实 wx.login code（由用户在 DevTools 中临时获取并传入）调 `/issue-credential` → 验证 openid 不在 allowlist 时返回 403 `OPENID_NOT_ALLOWED`（**不需要用户回控制台**，只需 DevTools 跑 `wx.login` 一次）
- [ ] **STS 签发成功验证**：用 allowlist 内 openid 的 code 调 `/issue-credential` 返回有效 STS 凭证（字段符合 tech-spec §4.1 成功响应定义）
- [ ] **安全反例验证（拿到 STS 后越权）**：拿到的凭证尝试上传到 `recordings/<其他日期>/<其他 id>.mp3` → OSS 返回 `AccessDenied`
- [ ] **安全反例验证**：拿到的凭证尝试 `GetObject` / `ListObjects` / `DeleteObject` → 全部返回 `AccessDenied`
- [ ] **安全反例验证**：等待超过 tech-spec §4.1 有效期上限后用同一凭证再 PutObject → 返回 `ExpiredToken` 或等价错误
- [ ] **大小反例验证**：用 `size=60000000` 调 `/issue-credential` → 返回 400 `SIZE_EXCEEDED`；用 `size=10000000` → 返回正常 STS 凭证
- [ ] **日志拉取验证**：跑 `make fc-logs FUNCTION=issue-credential` 能拉到上述请求的日志（含 openid 哈希、fragment_id、判定结果），**用户无需打开 FC 控制台**

**(E) 质量门 + 本地测试**
- [ ] Typecheck（mypy strict）通过
- [ ] Lint（ruff）通过
- [ ] 单元测试覆盖：handler 字段校验、鉴权逻辑、allowlist 判定、STS 签发、大小上限边界、部署脚本打包与错误重试（mock 云端依赖）

**(F) 用户操作清单（用户只需跑命令，不回控制台）**
- [ ] 用户跑 `make deploy-fc FUNCTION=issue_credential` 一次 → 部署成功 + curl 验证通过
- [ ] 用户跑 `make test-fc-live` → (D) 中所有云端反例 + 正例自动跑完并汇总 pass/fail
- [ ] 用户跑 `make fc-logs FUNCTION=issue-credential` → 能看到上面请求的日志
- [ ] 后续 `issue-credential` 代码改动只需重跑 `make deploy-fc FUNCTION=issue_credential`，**不需要打开 FC 控制台**

> ❌ 本 story **不**做的事（已在 US-001 完成）：开通 FC 服务 / 创建函数槽位 / 配置 HTTP 触发器 / 微信合法域名白名单 / 注入 FC 环境变量。这些都是 US-001 C/D/H 块的一次性人工准备，AI 不要试图自动化。

#### US-005: FC `/verify-upload` 完整交付（HeadObject + 扩展部署 + 云端 verify）

> **AI 编程任务**：写 `/verify-upload` 的 handler 代码 + 扩展 US-003 已建的 `make deploy-fc` 支持第二个函数 + 在云端真实联调全部 AC。
>
> **前置假设（来自 US-003）**：`make deploy-fc` 已存在且支持 `FUNCTION=<name>` 参数化；FC 部署 SDK / RAM 凭证 / 备份 / 回滚 / 日志机制已就绪。本 story 只需新增一个函数的部署配置。
>
> **本 story 完整闭环**：写完即部署到云端真实 FC、云端 AC 全部 verify 通过，故事独立可交付。

**描述：** 作为系统所有者，我需要 FC `/verify-upload` 接口在云端真实可用，能用 HeadObject 校验 OSS 对象存在性 + 大小一致性，给小程序提供"上传是否真的完整"的最终签收回执，性能目标见 §9 P-03。

> **技术规范参考**：API 协议完整定义见 `docs/tech-spec.md` §4.2。

**Acceptance Criteria：**

**(A) handler 代码**
- [ ] FC 函数 `/verify-upload` 请求/响应字段与校验逻辑严格符合 tech-spec §4.2 定义；鉴权复用 US-003 (A) 的 openid + allowlist 校验
- [ ] FC 日志记录每次 verify 的 fragment_id、结果、耗时
- [ ] P95 响应时间符合 §9 P-03 目标

**(B) 扩展 `make deploy-fc` 支持第二个函数**
- [ ] FC 函数源码组织符合 tech-spec §2.1（US-003 已建 workspace 配置，此处仅新增函数子目录）
- [ ] 跑 `make deploy-fc FUNCTION=verify_upload` 能复用 US-003 已建的部署能力（备份 / 回滚 / 日志 / 工程化基线全部复用，**不应**新写一份）
- [ ] 跑不带参的 `make deploy-fc` 能自动扫描 `apps/fc/*/` 并部署所有函数（此时应同时部署 `issue_credential` + `verify_upload`）；日志显示两个函数各自的 zip sha256 + curl 存活验证结果

**(C) 云端联调（必须在云端真实 FC 上 verify）**
- [ ] 跑 `make deploy-fc FUNCTION=verify_upload` 把 (A) 代码推到云端，部署日志显示 200 + curl 存活验证通过
- [ ] **真实闭环验证（脚本化）**：AI 提供 `make test-verify-upload` 脚本自动完成「上传测试对象 → 调用 `/verify-upload` 期望 `verified: true` → 删除对象（复用 `oss-delete-obj` 能力，仅测试用）→ 再次调用期望 `verified: false, reason: OBJECT_NOT_FOUND`」全流程，**用户无需手工操作 OSS 控制台**
- [ ] **大小不一致验证**：上传一个 100 字节对象 → 用 `expected_size=200` 调 `/verify-upload` → 返回 `verified: false, reason: SIZE_MISMATCH, actual_size: 100`
- [ ] **鉴权拒绝验证**：不带 code / 伪造 code → 同 US-003 (D)，返回 400/401
- [ ] **日志拉取验证**：跑 `make fc-logs FUNCTION=verify-upload` 能拉到上述请求的日志（含 fragment_id / 结果 / 耗时），**用户无需打开 FC 控制台**
- [ ] **性能验证**：跑 `make test-verify-upload` 时输出 P95 响应时间，符合 §9 P-03 目标

**(D) 质量门 + 本地测试**
- [ ] Typecheck（mypy strict）通过
- [ ] Lint（ruff）通过
- [ ] 单元测试覆盖：handler 字段校验、OSS 校验三种返回路径、鉴权逻辑、allowlist 判定（mock 云端依赖）

**(E) 用户操作清单（用户只需跑命令，不回控制台）**
- [ ] 用户跑 `make deploy-fc FUNCTION=verify_upload` 一次 → 部署成功 + curl 验证通过
- [ ] 用户跑 `make test-verify-upload` → (C) 中闭环验证自动跑完
- [ ] 用户跑 `make fc-logs FUNCTION=verify-upload` → 能看到日志
- [ ] 后续 `verify-upload` 代码改动只需重跑 `make deploy-fc FUNCTION=verify_upload`，**不需要打开 FC 控制台**

---

### 阶段 3：前端小程序（微信小程序极薄前端）

#### US-007: 录音基本交互（开始 / 停止 / 时长展示）

**描述：** 作为用户，我希望在小程序首页点一下就开始录音，再点一下就停止，并能实时看到已录时长，以便随时记录灵感。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 首页有一个明显的圆形录音按钮，处于"未录音"状态时显示"开始录音"
- [ ] 点击后立即调用小程序录音接口（tech-spec §6.1）开始录音；按钮切换为"停止录音"状态（颜色/文案变化）
- [ ] 录音过程中页面上实时显示已录时长（`mm:ss`，每秒刷新）
- [ ] 再次点击后停止录音，得到一个本地临时音频文件路径
- [ ] **音频格式策略（OQ-1 决议）**：按 tech-spec §5.1 执行。用户可观测行为——
  - MP3 机型：落盘扩展名 `.mp3`
  - AAC fallback 机型：落盘扩展名 `.aac`，不在前端转码
  - manifest 草案中**显式标注 `audio.original_format`**（`mp3` 或 `aac`）
  - OSS object key 始终用 `.mp3` 扩展名（格式标准化由 Worker US-015 负责）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **微信开发者工具验证**：在 DevTools 模拟器中点击"开始录音"→ 等 3 秒 → 点击"停止录音"，控制台无报错，能在小程序本地缓存目录下看到生成的音频文件，文件扩展名与 manifest 中 `audio.original_format` 一致
- [ ] **真机预览验证**：用真机扫码预览，授权录音权限后完成一次开始→停止流程，页面状态正常切换，无 JS 报错；vConsole 打印出 `original_format` 字段
- [ ] **多机型验证**：在至少 1 台 iOS 真机 + 1 台 Android 真机上分别录一次，记录各自得到的 `original_format` 到 runbook（用于 US-015 转码逻辑决定是否需要兜底）

#### US-008: 录音中断保护（锁屏 / 来电 / 切后台 / 杀进程 自动 stop + 保存草稿）

**描述：** 作为用户，我录音时如果被电话、锁屏、微信切后台、系统杀进程打断，希望已经录到的部分**自动**被保存为草稿，而不是丢失。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 小程序在录音开始时已注册录音中断回调（tech-spec §6.1）
- [ ] 中断事件触发时，前端自动停止录音并把当时的临时音频文件落到本地存储，状态标记为"草稿（被中断保存）"
- [ ] 回到前台后页面给出明确提示：「上次录音被中断，已自动保存草稿，是否保留 / 丢弃 / 继续新录？」三个按钮可点击

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：中断回调注册逻辑、中断时停止录音 + 落盘逻辑

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **模拟器中断验证**：DevTools 中触发"模拟切后台"或调用 `onInterruptionBegin` 钩子，可以看到草稿被生成
- [ ] **真机中断验证（至少跑通一种）**：录音中按下电源键锁屏 → 解锁回到小程序 → 看到草稿存在且时长与中断前一致；控制台 / vConsole 无未捕获异常
- [ ] **真机中断验证（另一种）**：录音中收到来电（或切到微信外的其他 App） → 回到小程序 → 看到草稿被保留
- [ ] 同时连续两次中断（先切后台再来电）→ 不会重复生成两份草稿，只保留最后状态

#### US-009: 草稿管理（试听 / 重录 / 删除 / 保存并上传）

**描述：** 作为用户，我录完音后希望先在草稿态预览（试听 / 重录 / 删除），确认满意后再点"保存并上传"晋升为正式 Fragment 并开始上传。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 停止录音后页面进入"草稿确认态"，显示：试听按钮、重录按钮、删除按钮、保存并上传按钮
- [ ] 点击试听 → 调用小程序音频播放接口（tech-spec §6.1）播放本地临时音频；点击暂停能暂停
- [ ] 点击重录 → 当前草稿被销毁（本地文件清理），回到 US-007 的录音初始态
- [ ] 点击删除 → 当前草稿被销毁，无任何 Fragment 记录被上传或落盘
- [ ] 点击保存并上传 → 草稿被冻结，生成 `fragment_id`（US-011），进入上传流程（US-012），并自动跳转到上传列表（US-014）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **DevTools 验证**：录音 5 秒 → 试听能播放出原声 → 点击重录 → 旧文件消失（USER_DATA_PATH 下查不到）；再录 5 秒 → 点击删除 → 同样消失；再录 5 秒 → 点击保存并上传 → 上传列表里出现一条"上传中"记录
- [ ] **真机验证**：同上流程，三种分支（重录 / 删除 / 保存并上传）都能正常切换，控制台无报错
- [ ] 删除 / 重录后，无任何残留草稿文件出现在本地缓存中（可在下次冷启动后再次确认）

#### US-010: 长录音自动分片（超过阈值自动切片，共享 session_id）

**描述：** 作为用户，我有时会一口气说很久；当录音超过分片阈值（tech-spec §3.1）时，前端应该**对我透明地**把它切成多个 Fragment，共享一个 session_id，UI 上仍显示为"一段录音"。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 录音开始时分配一个 `session_id`（ULID）
- [ ] 录音每达到分片阈值（前端常量，定义见 tech-spec §3.1）时，前端自动调用一次 stop + 立即 start，把已录的部分作为一个 chunk 落地，chunk_seq 从 1 递增
- [ ] 最终用户点击停止时，最后一片的 chunk 状态被正确写入，并把 chunk_total 回填到所有 chunk 的 manifest 草案中
- [ ] 单条 chunk 时长 ≤ 阈值 + 5 秒容差（阈值见 tech-spec §3.1），不会出现远超阈值的单条

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：session_id 分配、chunk_seq 递增、chunk_total 回填逻辑

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **真机验证（关键）**：录制 25 分钟的录音 → 自动生成 **3 条** Fragment，三条共享同一 `session_id`，`chunk_seq` 分别为 1/2/3，`chunk_total` = 3
- [ ] 上传列表（US-014）能把这 3 条聚合为 1 行"长录音"展示，点开能看到 3 个子 chunk 的状态
- [ ] 切片过程中没有音频丢失（3 条音频拼起来 ≈ 25 分钟，允许 ±2 秒切换间隙）

#### US-011: Fragment ID 生成 + 设备指纹持久化 + 本地 manifest 草案

**描述：** 作为系统设计者，我需要每条 Fragment 在前端生成时就有一个全局唯一、人眼可读的 `fragment_id`，并且 manifest 草案在前端落地，便于后续后端和Worker统一识别。

> **技术规范参考**：Fragment ID 格式见 `docs/tech-spec.md` §3.1，manifest.json 完整 schema 见 §3.3。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 小程序首次启动时生成 `device_short_id`（格式见 tech-spec §3.1），持久化到小程序本地存储（tech-spec §6.1），后续启动复用
- [ ] 每条 Fragment 在"保存并上传"时（US-009）生成 `fragment_id`，格式严格符合 tech-spec §3.1
- [ ] 同一秒内连续生成 2 条 Fragment 的 `fragment_id` **必须不同**（ULID 的随机性保证）
- [ ] 本地 manifest 草案（小程序端）字段以 tech-spec §3.3 为准；前端需填入的字段子集见 §3.3「字段来源」说明
- [ ] **元数据上传准备**：manifest 草案中需透传给 Worker 的字段，在 US-012 上传时作为 OSS 用户自定义元数据附带发送，完整 meta key 清单见 tech-spec §3.2（ADR-8）
- [ ] 音频 sha256 在前端计算完成（tech-spec §6.1），通过 OSS 用户自定义元数据传递给 Worker（tech-spec §3.2）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：device_short_id 生成逻辑、fragment_id 格式校验（正则）、同一秒唯一性、manifest 草案字段完整性、sha256 计算正确性

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **DevTools 验证**：连续录 2 条短录音并保存上传 → 在 vConsole 中能打印出 2 条不同的 `fragment_id`，且 `device_short_id` 字段一致
- [ ] **冷启动验证**：杀掉小程序进程，重新打开，`device_short_id` 仍是同一个值

#### US-012: 静默登录 + 获取 STS 凭证 + 直传 OSS

**描述：** 作为用户，我点击"保存并上传"后，前端应自动完成静默登录 → 调 FC `/issue-credential` 拿到单文件级 STS → 直传 OSS 这条链路（tech-spec §4.3），期间我无需手动登录。

> **技术规范参考**：上传确认时序见 `docs/tech-spec.md` §4.3，重试策略见 tech-spec §1.5。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 点击保存并上传后，前端按 tech-spec §4.3 时序完成：静默登录 → 获取单文件级 STS 凭证 → 直传 OSS（同时附带用户自定义元数据，完整清单见 tech-spec §3.2 / ADR-8）
- [ ] FC 返回非 200 → 上传状态切换为"待人工重传"，并在列表上展示错误码（如 `OPENID_NOT_ALLOWED`、`INVALID_CODE`）
- [ ] OSS 返回非 2xx → 按 tech-spec §1.5 重试策略执行
- [ ] 上传时 UI 显示进度条（百分比），上传完成后状态切换为"待 verify"

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：指数退避重试逻辑（mock）、FC 错误码映射、STS 签名构造
- [ ] `make test-sts-escape`：脚本自动模拟"小程序拿到 STS 凭证后试图写另一个 object key"的场景（用 oss2 SDK 直接调用，跳过小程序 UI），期望返回 `AccessDenied`（验证 US-003 (B) 的单 key 级别 policy 生效）

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **真实闭环验证（关键）**：从 DevTools 录一条 5 秒音频 → 保存并上传 → 用户跑 `make show-oss-object FRAGMENT_ID=<前端打印的 id>` 能 stat 到该对象 + 大小与前端记录的 `audio.size_bytes` 一致；**用户无需打开 OSS 控制台**
- [ ] 上传时 UI 显示进度条，上传完成后状态切换为"待 verify"
- [ ] vConsole / 控制台无未捕获异常

#### US-013: 上传后 verify + 本地缓存保留策略

**描述：** 作为系统所有者，我需要前端在 OSS 200 后立即调用 FC `/verify-upload` 拿到最终签收回执；本地缓存**仅在 verify 通过且超过 48 小时后**才允许自动清理，verify 未通过的文件永不自动删除（防止数据丢失），但用户可手动删除。

> **技术规范参考**：上传确认时序见 `docs/tech-spec.md` §4.3，verify-upload 协议见 tech-spec §4.2，重试策略见 tech-spec §1.5。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] OSS 直传收到 200 后，前端立即 POST FC `/verify-upload`（带 code、fragment_id、expected_size）
- [ ] 收到 `verified: true` → 本地 manifest 草案标记 `upload.verified_at` 为当前时间；上传列表状态切换为"上传成功"
- [ ] 收到 `verified: false` → 上传列表状态切换为"待人工重传"，错误原因展示给用户
- [ ] FC 调用本身失败（超时 / 网络错误） → 按 tech-spec §1.5 重试策略执行；3 次仍失败 → 状态切换为"待人工 verify"
- [ ] **本地保留策略（自动清理）**：
  - **仅当** `verified: true` **且** `verified_at` 距当前时间 **≥ 48 小时** 时，才允许自动清理本地音频缓存文件（小程序本地缓存目录下）
  - **verify 未通过**（`verified: false` / 待人工重传 / 待人工 verify）的文件 **永不自动删除**，无论过了多久
  - **verify 通过但不足 48 小时** 的文件 **不允许自动删除**
- [ ] **手动删除（异常兜底）**：上传列表中每条记录提供"删除本地缓存"操作入口（长按或滑动），用户确认后可手动删除任何状态的本地文件（含 verify 未通过的）；删除前弹出二次确认：「该录音尚未成功上传到云端，删除后无法恢复，确定删除？」（仅 verify 未通过时弹出，已通过的直接删除不二次确认）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：verify 调用逻辑、重试队列、保留策略三种分支（时间 mock）

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **真实闭环验证**：上传一条短录音 → 状态显示"上传成功" → 用户跑 `make oss-delete-obj FRAGMENT_ID=<前端打印的 id>` 删除该对象（**无需打开 OSS 控制台**）→ 在小程序上重新点击该条记录的"重新 verify" → 状态切换为"待人工重传"，错误码 `OBJECT_NOT_FOUND`
- [ ] **保留策略验证（verify 通过 + 48h 内不删）**：上传一条短录音 → verify 通过 → 在 DevTools 中把本地时间偏移设到 24 小时后 → 触发清理逻辑 → 文件**仍存在**
- [ ] **保留策略验证（verify 通过 + 48h 后可删）**：偏移到 49 小时后再触发 → 文件被自动清理
- [ ] **保留策略验证（verify 未通过永不自动删）**：模拟一条 verify 失败的录音 → 偏移到 7 天后 → 触发清理逻辑 → 文件**仍存在**
- [ ] **手动删除验证**：对一条"待人工重传"状态的记录执行手动删除 → 弹出二次确认 → 确认后文件被删除 + 列表中该条消失

#### US-014: 上传列表页（8 种状态展示 + 失败 3 次转人工 + 离线醒目提示）

**描述：** 作为用户，我希望有一个独立的"上传列表"页面，能清晰看到每条录音处在哪个状态，特别是当多条录音未上传 / 上传失败时给我醒目提醒。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 上传列表页能展示每条 Fragment 的**八种**状态之一（权威状态定义与迁移规则见 tech-spec §6.7）：`草稿` / `待上传（离线排队）` / `上传中` / `待 verify` / `上传成功（verified）` / `上传失败` / `待人工重传` / `待人工 verify`
- [ ] 上传失败连续 3 次自动重试后切换为"待人工重传"，列表中**红色标记**，并显示"点击手动重传"按钮
- [ ] 点击"手动重传"按钮 → 重置重试计数，重新走 US-012 + US-013 完整流程
- [ ] **长录音分片显示与重传（OQ-4 决议：分片各自可重传）**：
  - 同一 `session_id` 下的多个 chunk 在列表中**折叠显示为一行**"长录音"卡片，标题展示总时长 + chunk 总数（如 `25:00 · 3 段`）
  - 卡片右侧显示**聚合状态**：仅当**所有 chunk 都成功（verified）**才显示绿色"已完成"；只要有任何 chunk 失败 / 待人工 → 整张卡片显示红色"X / N 失败"
  - 点击卡片可**展开**，列出每个 chunk 的独立状态行（`chunk_seq=1/2/3` 各自一行 8 种状态之一）
  - **每个 chunk 都有独立的"手动重传"按钮**，只重传该 chunk，不会重传整段（避免一段 25 分钟里只有 chunk 2 失败时还要把 chunk 1/3 重新上传）
  - 折叠态下点击卡片主体 = 展开；展开态下点击右上角 ⌄ = 折叠
- [ ] 当存在 N 条状态为"待上传（离线排队）/ 上传失败 / 待人工重传 / 待人工 verify"的 Fragment 时，页面顶部出现醒目横条：「未上传 N 条，距离最早录音已 X 小时」（N 按**单个 chunk** 计数，与折叠卡片的聚合状态独立计算）
- [ ] 设备离线时点击"保存并上传"不会让 Fragment 永久滞留在"草稿"态——而是切换为 `待上传（离线排队）`，恢复网络后自动开始上传（切换为 `上传中`）
- [ ] **故障注入开关**：小程序提供「开发者菜单 → 故障注入」入口，开关清单与效果见 tech-spec §6.1；可在运行时切换，**无需用户修改源码**

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **DevTools 验证**：通过故障注入开关依次制造 3 种场景（全成功 / 自动失败 3 次 / 离线录音后联网） → 列表上 8 种状态都能正确出现且文案正确
- [ ] **真机验证（离线）**：开飞行模式录 2 条 → 列表显示离线积压 + 顶部红色提示 → 关闭飞行模式 → 自动开始上传，状态依次切换
- [ ] **真机验证（故障注入）**：在故障注入菜单打开 `mock-fc-url-broken` → 录一条 → 自动重试 3 次失败 → 列表变红 + 出现"点击手动重传"按钮 → 关闭故障注入 → 手动重传成功
- [ ] 控制台 / vConsole 无未捕获异常

---

### 阶段 4：转写 Worker（Python 后端进程，运行环境无关）

#### US-015: OSS 轮询 + 下载到 `.part` + 格式标准化（AAC → MP3）+ 原子 rename 为 `audio.mp3`

**描述：** 作为Worker，我需要按 `config.yaml` 配置的频率轮询 OSS，发现新 object 时下载到临时文件，校验完整后做**格式标准化**（如果是 AAC 转码为 MP3，如果已经是 MP3 直接保留），最终原子 rename 到 `audio.mp3`。

> **技术规范参考**：文件状态机协议见 `docs/tech-spec.md` §3.5，音频格式策略见 §5.1。

**Acceptance Criteria：**

**(A) 代码实现**

- [ ] 脚本启动后按 `poll.interval_seconds`（默认值见 tech-spec §2.3）周期轮询 OSS，列出 `recordings/` 前缀下所有对象
- [ ] 对每个**本地尚未存在**或**本地存在但无 `.done`** 的对象：
  - 下载到 `~/SoniScope/inbox/<fragment_id>.part`
  - 下载完成后计算 **`original_sha256`**；与 OSS 元数据比对一致性；不一致 → 删除 `.part`，下一轮重下
  - **格式检测与标准化**：按 tech-spec §5.1 / §3.5 执行格式检测 → MP3 直通 / 非 MP3 转码 → 原子 rename 到 `fragments/` 目录；转码失败 → 留档到 `inbox/failed/`（不参与自动重试，需人工介入）
  - **读取 OSS 用户自定义元数据**：通过 OSS API 获取前端上传时附带的元数据，写入 manifest 对应字段（tech-spec §3.2 / ADR-8）
  - 按 tech-spec §3.3「字段来源」填写 manifest 对应字段
- [ ] **OSS 永不删除**：脚本任何路径下都**不会**调用 OSS 删除接口（代码中无 DeleteObject 调用，仅测试 mock 中允许出现）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：sha256 校验、格式检测分支、转码失败处理、重复扫描跳过逻辑
- [ ] **可配置验证**：`make test-poll-interval` → 把 `poll.interval_seconds` 改为 30 → 重启脚本 → 日志显示每 30 秒一次扫描
- [ ] **下载中断验证**：`make test-download-interrupt` → 脚本下载过程中 `kill -9` → 重启后 `inbox/` 残留 `.part` 文件被识别为下载中断，重新下载，最终能完成
- [ ] **MP3 直通验证**：`make test-mp3-passthrough` → 上传一段真实 MP3 → Worker 下载后跳过 ffmpeg → `audio.sha256` == `upload.original_sha256`
- [ ] **AAC 转码验证**：`make test-aac-transcode` → 用 `tests/fixtures/audio/sample-aac.aac` 模拟 AAC 上传 → Worker 下载后转码 → 生成 `audio.mp3` → 验证转码是否成功
- [ ] **转码失败验证**：`make test-transcode-fail` → 上传一段被截断的 AAC（人为 corrupt） → Worker 转码失败 → `inbox/failed/` 下有留档 + 日志报错；不污染 fragments 目录
- [ ] **重复扫描验证**：`make test-no-redownload` → 脚本不重启的情况下，扫描周期内已 `.done` 的 Fragment 不会被重新下载（通过日志或 OSS 调用计数验证）

**(C) 手动验证清单**

> 本 story 无需手动验证，所有 AC 均可通过自动化脚本完成。

#### US-016: 启动恢复扫描 + 文件写入协议

**描述：** 作为系统所有者，我需要 Worker 在每次启动时按 tech-spec §3.6 执行三目录恢复扫描（`inbox/` → `tmp/` → `fragments/`），清理中间态残留文件并从中断处继续。

> **技术规范参考**：写入协议（先临时 → 原子 rename → `.done`）见 `docs/tech-spec.md` §3.5，启动恢复扫描见 §3.6。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 启动恢复扫描：按 tech-spec §3.6 执行三目录扫描（`inbox/` 清理下载残留 → `tmp/` 清理转写残留 → `fragments/**/` 判定 fragment 状态并恢复）
- [ ] 写入协议：严格按 tech-spec §3.5 定义执行（先临时文件 → 原子 rename → 最后写 `.done`）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：启动扫描 4 种状态判定、写入协议各阶段原子性
- [ ] **崩溃恢复验证（关键）**：`make test-crash-recovery` → 录入一条音频，等Worker下载完 `audio.mp3` 但还在调用云端 API 转写时 `kill -9` → 重启脚本 → 自动重新调用 API 转写并写出 `transcript.json` + `.done`
- [ ] **崩溃恢复验证（missing-done）**：`make simulate-worker-crash CASE=missing-done FRAGMENT_ID=<id>` → 等价于删掉 `.done` 标记 → 重启 Worker → 该条会被重新转写并补回 `.done`
- [ ] **崩溃恢复验证（stale-part）**：`make simulate-worker-crash CASE=stale-part FRAGMENT_ID=<id>` → 等价于残留 `.part` 空文件 → 重启 Worker → 该残留被识别并重下，不会因此污染下游 `audio.mp3`

**(C) 手动验证清单**

> 本 story 无需手动验证，所有 AC 均可通过自动化脚本完成。

#### US-017: 转写器抽象接口 + 云端转写实现（云端 API 优先）

> **本期 MVP 默认走云端 API**。本地转写仅保留占位骨架，本地推理推迟到流程跑通后再评估。

**描述：** 作为系统设计者，我需要把"转写器"抽象成可扩展接口（tech-spec §5.3），本期实现云端转写（调用 US-001 注册的云端语音转文字 API），并预留本地转写占位骨架，便于下一阶段切换到本地推理。

> **技术规范参考**：`transcript.json` schema 见 `docs/tech-spec.md` §3.4，转写策略（OSS URL vs 直传）见 §5.2，Transcriber 接口见 §5.3，ASR 选型见 §6.2，成本可观测日志见 §6.8。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 转写器抽象接口与返回结构符合 tech-spec §5.3
- [ ] **音频传递方式（OQ-7 决议：方案 A 优先）**：首选 OSS 签名 URL 让 ASR 服务自己拉取，降级方案为本地文件直传；具体实现策略符合 tech-spec §5.2；选用哪种方案在日志中明确打印，便于排查
- [ ] 云端转写实现符合 tech-spec §5.2 + §5.3：从配置读取 provider 信息 → 按策略选模式 → 提交转写任务 → 轮询或等待结果 → 映射成结构化结果
- [ ] **签名 URL 过期处理**：符合 tech-spec §5.2 策略（URL 有效期覆盖排队 + 处理时间，超时自动续签）
- [ ] 云端转写失败重试策略符合 tech-spec §1.5（网络错误 / 5xx 指数退避；4xx 立即失败）
- [ ] 预留本地转写占位骨架（本期不调用），证明接口预留可扩展
- [ ] 转写器选择由配置决定（tech-spec §2.3 + §5.3）；当前默认云端转写，未来切换不需要改业务代码
- [ ] **成本可观测**：每次 ASR 调用后输出结构化日志，字段符合 tech-spec §6.8 定义，便于运行过程中监控免费额度
- [ ] 输出的 `transcript.json` 结构稳定，字段符合 tech-spec §3.4 定义

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：工厂方法、方案 A/B 切换、签名 URL 过期续签、云端转写失败重试逻辑（mock API）、本地转写占位调用时抛异常
- [ ] **真实闭环验证（关键）**：`make test-transcribe` → 取 US-001 (E) 中跑通的同一段 10 秒测试 MP3 → 在 Worker 中调用云端转写（**用 OSS URL 方案**）→ 返回的文字内容与 US-001 (E) 控制台验证结果一致（允许小幅模型版本差异，但**主干文字必须能对得上**）
- [ ] **方案 A 验证**：`make test-transcribe-oss-url` → 日志显示 `mode=oss-url`；用 `make show-oss-object` 能看到该对象在转写时段的访问日志（NLS 真的来拉过了）；Worker 端**不产生**上行流量到 NLS（用 `nethogs` 或同等工具确认转写期间 Worker 上行流量极小）
- [ ] **降级方案 B 验证**：`make test-transcribe-direct` → 临时改 `config.yaml` 中 `transcriber.upload_mode = 'direct'` → 重新转写一条 → 日志显示 `mode=direct-upload`；转写结果与方案 A 一致
- [ ] **性能验证（P-01 基线）**：`make test-transcribe-perf` → 用一段 1 分钟标准音频跑云端转写 → 端到端耗时符合 §9 P-01 目标（视服务商不同可调整阈值，写进 runbook 作为基线）

**(C) 手动验证清单**

> 本 story 无需手动验证，所有 AC 均可通过自动化脚本完成。

#### US-018: 幂等判断 + 显式触发重转

**描述：** 作为系统所有者，我需要 Worker 在每次扫描时基于 `.done` 标记判断是否已完成转写，避免重复消耗算力；同时允许我通过 `retranscribe` CLI 命令显式触发存量重转。**更换模型 / 参数版本后，仅新进入的 Fragment 自动使用新配置，已完成的存量 Fragment 不会被自动重转。**

> **技术规范参考**：幂等规则与重转机制见 `docs/tech-spec.md` §3.7。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] **正常轮询幂等判断**：转写前检查 `.done` 文件是否存在 → 存在则**直接跳过**（无论当前配置中的模型 / 参数版本是否与 manifest 中记录的一致）
- [ ] `.done` 不存在 → 按当前配置进行转写
- [ ] **转写元数据记录**：转写完成后，四元组由 `audio.sha256` + `transcription.{transcriber, model, params_version}` 组合而成（分别位于 manifest 的 `audio` 和 `transcription` 对象中，见 tech-spec §3.3），用于溯源和 CLI 筛选
- [ ] OSS 端去重：同一 object key 重复下载只会覆盖本地 `audio.mp3`，不会产生新目录
- [ ] **显式重转 CLI（OQ-3 决议）**：提供 `retranscribe` 子命令（完整签名与 flag 行为见 tech-spec §3.7；顶层别名见 tech-spec §6.5 `make retranscribe`）。用户可观测行为：
  - 不带 flag → 已完成的 Fragment 给出提示而不重转
  - `--upgrade` → 仅对旧模型版本执行重转
  - `--force` → 无条件重转
  - `--all-from <date>` → 批量重转，失败不中断
  - 运行期间主轮询不阻塞，同一 fragment_id 不并发转写
- [ ] 显式重转过程中老的 `transcript.json` 不会"半覆盖"（始终通过 `.tmp` + rename 保证原子性）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：`retranscribe` 幂等性、`--force` 行为、`--upgrade` 筛选逻辑、file lock 并发保护
- [ ] **重复扫描跳过验证**：`make test-idempotent-skip` → 脚本完成一条 Fragment 的转写后，重启或等待下一轮扫描 → 该 Fragment 不会再次进入 transcriber.transcribe()（通过日志或调用计数验证）
- [ ] **配置变更不触发自动重转验证**：`make test-no-auto-retranscribe` → 修改 `config.yaml` 中 `transcriber.model` 或 `params_version` → 重启脚本 → 已有 `.done` 的存量 Fragment **不会**被重新转写（通过日志或调用计数验证，确认 transcriber.transcribe() 调用次数为 0）
- [ ] **CLI 显式重转验证**：`make test-cli-retranscribe` → 执行 `retranscribe <id> --force` → 日志显示重转 + 新 `transcript.json` 覆盖；manifest 的 `transcription.completed_at` 时间戳和 `model` 字段更新
- [ ] **CLI --upgrade 验证**：`make test-cli-upgrade` → 修改 `config.yaml` 模型版本 → 执行 `retranscribe --all-from <date> --upgrade` → 仅旧模型转写的 Fragment 被重转，已用新模型转写的 Fragment 被跳过

**(C) 手动验证清单**

> 本 story 无需手动验证，所有 AC 均可通过自动化脚本完成。

#### US-019: `manifest.json` 单向写入 + `transcript.json` + `.done` 完成标记

**描述：** 作为系统所有者，我需要每个 Fragment 目录最终包含完整的 `manifest.json`（权威状态来源）、`transcript.json`（结构化转写）、`transcript.txt`（从 transcript.json 派生的纯文本）和 `.done`（完成标记），且字段格式与 `docs/tech-spec.md` §3.3 中定义的 schema 完全一致。

> **技术规范参考**：manifest.json 完整 schema 见 `docs/tech-spec.md` §3.3，transcript.json 结构见 §3.4。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] `manifest.json` 字段必须符合 tech-spec §3.3 定义的完整 schema
- [ ] SHA256 一致性规则符合 tech-spec §3.3
- [ ] `manifest.json` 的写入也走写入协议（tech-spec §3.5），避免半写状态
- [ ] `transcript.json` 是结构化 JSON（segments + 时间戳 + 模型版本），不是纯文本
- [ ] `transcript.txt` 从 `transcript.json` 派生（拼接 segments.text），便于人眼直接读
- [ ] `.done` 是 0 字节空文件，仅作为"全流程完成"的旗标

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：manifest schema 校验、MP3/AAC 两种路径的 sha256 一致性断言、原子写入逻辑
- [ ] **完整性验证**：`make test-fragment-integrity` → 跑完一条 Fragment 后，目录里同时存在 5 个产物文件（清单见 tech-spec §2.2），且 manifest 中所有字段都已填充（无 null 残留，除非业务允许）
- [ ] **幂等性验证**：`make test-manifest-idempotent` → 用一段固定测试音频跑两次（同样 MP3 输入），**得到的 `manifest.json` 中除时间戳字段外，其他字段完全一致**（fragment_id 一致、所有 sha256 一致、segments 数量一致）

**(C) 手动验证清单**

> 本 story 无需手动验证，所有 AC 均可通过自动化脚本完成。

---

## 4. Feature 最终验收 AC（E2E）

> **本章节性质**：**不是 user story，而是整个 MVP feature 的最终交付验收清单**。前面 §3 章节中的 US-001 ~ US-019 全部完成后才能进入本章 AC。
>
> **验收前提**：必须用真实小程序 + 真实 FC + 真实 OSS + 真实 Worker 跑完整条链路，**不允许使用任何 mock**。
>
> **与其他章节的关系**：
> - 本章 §4 是"可执行的验收动作"——明确告诉用户跑哪条 `make` 命令、在真机上做哪些操作；
> - §9 Success Metrics 是"量化的目标指标表"——承诺（如端到端成功率 100%）；
> - 本章 §4.1 + §4.2 全部打勾即视为本 feature 验收完成。
>
> **范围覆盖**：正常路径（100 条录音端到端落盘）+ 关键异常路径（脚本崩溃恢复 / 显式重转 / 安全反例）+ 真机交互异常（中断保护 / 长录音分片 / 失败重试）+ 长期保留（OSS 永不删除）。

### 4.1 自动验证 AC（`make` 命令一键跑完，无需人工操作）

> 本节所有命令的实现脚本均由 AI 在前置 stories（US-002 ~ US-019）中提供；用户在完成 §4.2 真机录入后，按顺序跑下面命令并核对输出即可。

**[正常路径 · 100 条录音落盘完整性]**

- [ ] `make list-oss-objects DATE=<YYYY-MM-DD>` → 列出**完整的 100 个 `.mp3` 对象**（脚本化输出 + 计数 = 100），文件名与前端 `fragment_id` 一一对应；用户**无需打开 OSS 控制台**
- [ ] `make verify-e2e-integrity` → 本地 `~/SoniScope/fragments/` 下出现**完整的 100 个 Fragment 目录**，每个目录都同时包含 5 个产物文件（清单见 tech-spec §2.2）
- [ ] `make verify-e2e-sha256` → 每条 Fragment 的 sha256 完整性按 tech-spec §3.3 一致性规则校验通过（OSS 侧 + 本地侧）
- [ ] `make verify-e2e-fields` → 每条 Fragment 的 `manifest.upload.verified_at` 非空、`manifest.transcription.completed_at` 非空

**[异常路径 · 脚本崩溃恢复]**

- [ ] `make test-e2e-crash-recovery` → Worker 运行中，对一条正在转写的 Fragment 执行 `kill -9` → 该目录残留 `audio.mp3` 但无 `.done` → 重启脚本 → 自动重新转写并补回 `.done` + 完整的 `transcript.json`

**[异常路径 · 显式重转]**

- [ ] `make test-e2e-retranscribe` → 修改 `config.yaml` 的 `transcriber.params_version` v1 → v2 → 执行 `make retranscribe ARGS="--all-from <date> --upgrade"` → **仅旧 params_version 的 Fragment** 被重新转写，新的 `transcript.json` 覆盖旧的，`manifest.transcription.params_version` 变为 v2；修改配置后**不重启 Worker**验证下次扫描**不会**自动重转

**[安全反例 · 鉴权与越权]**

- [ ] `make test-e2e-security` → 用未在 allowlist 中的另一个微信号调用 FC → 收到 403；用合法 STS 凭证尝试 PutObject 到其他 key → OSS 返回 AccessDenied

**[完整性扫描 · 无半成品残留]**

- [ ] `make verify-no-stale` → 所有异常路径跑完后：OSS 上对象数 ≥ 本地 Fragment 目录数；`inbox/` 下无残留 `.part` / `.mp3.tmp`；`tmp/` 下无残留 `.transcript.json.tmp`（按 tech-spec §3.5，中间态文件写在中央 `inbox/` / `tmp/` 目录，不在 fragment 目录内）

**[长期保留 · OSS 永不删除]**

- [ ] **跑完后 1 周再次确认**：`make verify-oss-retention` → OSS 上对象数 ≥ 本地 fragments 目录数；Worker 日志中无任何 `DeleteObject` 调用记录

### 4.2 手动验证 AC（真机操作 checklist，必须人工执行）

> 本节所有项必须在**真实微信 + 真实手机 + 真实 OSS / FC / Worker** 环境下执行，AI 无法代跑；每完成一项请在原文打勾。

**[100 条真机录音 · 正常路径]**

- [ ] 在真机上连续录制 **100 条 30~90 秒**的录音，依次点击"保存并上传"
- [ ] 所有 100 条 Fragment 在小程序上传列表中状态最终都是"上传成功（verified）"
- [ ] 没有任何"待人工重传"或"待 verify"状态残留

**[本地缓存自动清理 · verify+48h 策略]**

- [ ] 上述 100 条跑完后再等 **48 小时 + 1 小时** → 真机本地的 100 条音频缓存自动清理；OSS 上的 100 个对象**仍然存在**

**[中断保护闭环]**

- [ ] 真机开飞行模式 → 录音 60 秒 → 中途按电源键锁屏 → 解锁 → 弹出中断恢复提示 → 选择"保留" → 草稿存在且时长 ≈ 锁屏前的时长 → 关闭飞行模式 → 上传成功

**[长录音分片闭环]**

- [ ] 真机连续录制 **25 分钟** → 自动切片为 3 条 Fragment（`chunk_total = 3`）→ 全部上传成功 + 本地全部转写完成 + 3 条 `manifest.session_id` 一致

**[失败重试 + 手动重传闭环]**

- [ ] 在小程序中打开「开发者菜单 → 故障注入」开关（AI 在 US-014 提供）→ 选「FC URL 失效」→ 录音上传 → 自动重试 3 次失败 → 上传列表红色提示 + "点击手动重传"按钮 → 关闭故障注入 → 手动重传 → 上传成功 + Worker 落盘完成；**用户无需修改源码**

---

## 5. Functional Requirements / 功能性需求

> 编号化的"系统必须做到 X"清单。每条都对应上面某个 US 的核心行为，便于实施时按条逐项 check。

- **FR-1**：小程序首页提供"开始 / 停止"录音单一按钮，单次录音目标时长 ≤ 分片阈值（tech-spec §3.1）（US-007）。
- **FR-2**：录音过程中遇到锁屏 / 来电 / 切后台 / 杀进程时，系统**必须**通过录音中断事件回调自动停止并保存已录部分为草稿（US-008）。
- **FR-3**：停止录音后**必须**先生成草稿，由用户显式点击"保存并上传"才晋升为 Fragment（US-009）。
- **FR-4**：当单次录音超过分片阈值（见 tech-spec §3.1）时，前端**必须**自动分片，多片共享 `session_id`、独立 `chunk_seq`（US-010）。
- **FR-5**：每条 Fragment 在前端生成时**必须**得到全局唯一的 `fragment_id`，格式符合 tech-spec §3.1（US-011）。
- **FR-6**：FC `/issue-credential` **必须**先用小程序登录 code 换 `openid` → 检查 allowlist → 通过后才用 STS 签发**精确到单个 object key** 的临时凭证，有效期上限见 tech-spec §4.1（US-003）。
- **FR-7**：FC `/verify-upload` **必须**校验 OSS 对象存在 + 大小一致；失败时返回明确原因码（US-005）。
- **FR-8**：小程序**必须**在收到 OSS 200 后立即调用 `/verify-upload`；本地缓存**仅在 verify 通过且超过 48 小时后**才允许自动清理，verify 未通过的文件永不自动删除；用户可手动删除任何状态的本地文件（US-013）。
- **FR-9**：上传连续失败 3 次后**必须**切换为"待人工重传"红色提示状态（US-014）。重试间隔策略见 tech-spec §1.5。
- **FR-10**：Worker**必须**按 `config.yaml` 中可配置的 `poll.interval_seconds`（默认值见 tech-spec §2.3）周期轮询 OSS（US-015）。
- **FR-11**：Worker**绝不**调用 OSS `DeleteObject`，OSS 文件永久保留（US-015 + §4 最终验收 AC）。
- **FR-12**：本地文件操作**必须**走"先临时 → 原子 rename → 写 `.done`"写入协议（tech-spec §3.5 / US-016）。
- **FR-13**：脚本启动时**必须**扫描 `~/SoniScope/fragments/`，对每个目录按状态机决定是跳过 / 重转 / 重下 / 新办（US-016）。
- **FR-14**：转写**必须**通过抽象接口调用（tech-spec §5.3）；本期默认实现云端转写（调用云端语音转文字 API），且预留本地转写占位骨架；**本期不部署本地推理模型**（US-017）。
- **FR-15**：转写幂等性**必须**基于 `.done` 标记文件判断——`.done` 存在即跳过，不因模型 / 参数版本变更自动重转；四元组 `(audio_sha256, transcriber, model, params_version)` 仅记录于 manifest 供溯源和 CLI 筛选（US-018）。
- **FR-16**：每个 Fragment 目录最终**必须**同时存在 `audio.mp3` / `manifest.json` / `transcript.json` / `transcript.txt` / `.done` 五个文件（US-019）。
- **FR-17**：`manifest.json` 字段格式**必须**与 `docs/tech-spec.md` §3.3 定义的 schema 完全一致。

---

## 6. Non-Goals / 本期不做

明确划出边界，避免范围蔓延：

- **NG-1**：不做 LLM 润色与每日文字稿生成（详见 §7 Future Roadmap【计划 C】）。
- **NG-2**：不做日稿呈现界面（Web / 邮件 / 移动 App），手机端**不需要**查看历史 Fragment 列表或日稿。
- **NG-3**：不做搜索 / 标签 / 聚合 / 统计；本期不引入 SQLite 索引（下一期【计划 E】）。
- **NG-4**：不做完整用户登录系统；只用 `openid` allowlist 单用户（下一期【计划 B】）。
- **NG-5**：不做录音 / 转写文件 / 日稿加密存储（下一期【计划 A】）。
- **NG-6**：不做自定义域名 + 备案；MVP 直接用阿里云自带 HTTPS 域名（下一期【计划 F】）。
- **NG-7**：不做 App 端；本期只在微信小程序运行。
- **NG-8**：Worker不做 Web UI / GUI，仅命令行 + 日志。
- **NG-9**：**本期不部署本地 Whisper / 本地 GPU 推理**。转写全部走云端 API（US-001 (E) 中注册的服务）；本地 Whisper large-v3 推迟到 MVP 流程跑通后再评估，届时通过切换 `transcriber.name` 配置即可启用，不需要改业务代码。

---

## 7. Future Roadmap / 下一阶段计划

> 以下计划在本期 MVP 跑通后依次启动。按预计触发时间排序。

### 7.1 晚上整理机制（决策已敲定）

| # | 议题 | 决策 |
|---|---|---|
| 1 | 触发时间 | 固定每天凌晨 **05:00** 自动整理「前一天」的所有碎片 |
| 2 | 重新生成策略 | 允许覆盖，但**必须保留所有历史版本**（追加式存储，旧版本不丢） |
| 3 | 文体风格 | 先输出**流水账风格**，后续再精细化调整 |
| 4 | 内容约束 | **绝对禁止「添油加醋」和虚假事实**——硬性约束 |
| 5 | LLM 输入 | 只给 LLM 看**转写后的文本**，不发送音频 |
| 6 | LLM 部署 | 下一期先用云端 LLM 跑通，本地 LLM 再评估 |

### 7.2 后续计划清单

- **【计划 C】LLM 润色与每日文字稿生成**
  - 触发时机：MVP 跑通后立刻开展
  - 范围：见 §7.1「晚上整理」机制
  - 实施方式：先接入云端 LLM 跑通，再评估本地 LLM

- **【计划 D】日稿呈现方式（手机 / Web / 邮件 等）**
  - 触发时机：与计划 C 同步或之后
  - 范围：决定用户最终在哪里读到生成的日记

- **【计划 A】录音文件 / 转写文本 / 日稿的加密存储**
  - 触发时机：MVP 跑通后、对外发布前
  - 范围：云端对象加密 + 本地文件加密

- **【计划 B】用户登录与多用户支持**
  - 触发时机：决定对外发布时
  - 范围：扩展为多用户 + 数据按用户隔离

- **【计划 E】索引数据库**
  - 触发时机：当文件数增长到检索 / 统计困难时
  - 范围：由元数据单向派生，作为只读查询视图

- **【计划 F】自定义域名 + 备案**
  - 触发时机：正式长期运行或对外发布时
  - 范围：评估自定义域名、稳定性、备案要求

- **【计划 G】本地 Whisper 推理**
  - 触发时机：云端 ASR 成本 / 隐私 / 可用性不满足需求时
  - 性能基线指标：本地 Whisper large-v3 1 分钟音频转写耗时 ≤ 10 秒（待评估）

---

## 8. Technical Design Reference / 技术设计参考

> 所有技术实现细节已移至 **`docs/tech-spec.md`**（唯一技术权威）。包括：
>
> | 主题 | Tech Spec 章节 |
> |---|---|
> | 四层架构 + 架构图 + 设计原则 | §1 |
> | Monorepo 结构 + 运行时目录 + 配置 Schema | §2 |
> | Fragment ID / OSS Key / manifest.json / transcript.json / 文件状态机 | §3 |
> | FC API 协议（issue-credential / verify-upload）+ STS + 鉴权 | §4 |
> | 音频格式策略 + 转写策略 | §5 |
> | 技术约束 + 依赖清单 | §6 |
> | 实施里程碑 | §7 |
> | 架构决策记录（ADR） | §8 |

---

## 9. Success Metrics / 成功指标

以下指标必须全部通过才算 MVP 验收完成。

> **编号说明**：R-06（原"OSS 副本校验"）、S-04（原"凭证自动轮换"）在需求精简过程中合并到相邻指标或推迟到下一阶段，编号保留缺口。

| 指标 | 目标 | 验收编号 |
|---|---|---|
| 端到端成功率 | 100 条录音 → 100 条本地落盘，0 丢失 | R-01 |
| FC `/verify-upload` 通过率 | 真实路径下 verify 通过 ≥ 99% | R-02 |
| 本地缓存保留 | verify 通过后仍保留 ≥ 48 小时；verify 未通过永不自动删除 | R-03 |
| `.done` 缺失恢复率 | 删除 `.done` 后重启脚本，能自动补齐 100% | R-04 |
| 3 次失败转人工 | 100% 触发，红色提示明显 | R-05 |
| OSS 文件永不删除 | 1 周后 OSS 对象数 ≥ 本地数 | R-07 |
| 无任何长期 AK 在小程序 | 反编译搜索为 0 命中 | S-01 |
| STS 凭证有效期 | ≤ 15 分钟（权威值见 tech-spec §4.1） | S-02 |
| STS 单 key 限制 | 反例（写其他 key）100% 被拒 | S-03 |
| 未授权 openid | 100% 被 FC 403 拒绝 | S-05 |
| 云端 API 1 分钟音频转写端到端耗时 | ≤ 60 秒基线（含上传 / 拉取；实际阈值视服务商不同可调，以 runbook 记录为准） | P-01 |
| FC P95 响应时间 | `/issue-credential` ≤ 1s，`/verify-upload` ≤ 1s | P-02 + P-03 |
| 轮询周期可配置 | 改配置并重启 Worker 后生效 | P-04 |
| 8 种上传状态展示 | 全部能在真机上构造出来（含离线排队态） | U-01 |
| 离线积压醒目提示 | 离线录音后顶部红色横条出现 | U-02 |
| 中断恢复提示 | 锁屏 / 来电 / 切后台后能弹出三选一提示 | U-03 |

---

## 10. Open Questions / 待澄清的问题

> **状态**：本期 PRD v1 起 8 个 OQ **全部已决议**（OQ-1~7 于 2026-05-26，OQ-8 于后续审计补入）。具体决策落到了对应 user stories 的 acceptance criteria 中；本节保留为决策索引，便于追溯。完整技术背景见 tech-spec §8（ADR-1 ~ ADR-8）。

| 编号 | 议题 | 决策 | 落到哪 |
|---|---|---|---|
| OQ-1 | 小程序录音 MP3 格式不支持时如何处理 | **能 MP3 就直出 MP3；不能则保持 AAC，由 Worker 下载后用 ffmpeg 转码** | US-007 / US-015 / US-019 manifest schema / tech-spec.md §6.3 依赖加 ffmpeg |
| OQ-2 | 前端是否算 sha256 | **保持现状：前端算 sha256**（卡顿如严重再退化为 size-only verify） | 无需改 PRD，已是默认行为（US-011） |
| OQ-3 | 是否提供单条 Fragment 强制重转 CLI | **要做，本期内提供** `make retranscribe`（完整签名见 tech-spec §3.7 / §6.5） | US-018 |
| OQ-4 | 长录音多 chunk 在上传列表如何展示 | **折叠卡片 + 每个 chunk 独立可重传**（不整段强制一起重传） | US-014 |
| OQ-5 | FC 是否对 expected_size 做上限校验 | **要加**（默认值见 tech-spec §4.0 `MAX_UPLOAD_BYTES`，可调） | US-003 (B) |
| OQ-6 | 选哪家云端语音转文字 API | **暂定阿里云智能语音交互 NLS 录音文件极速版**；执行 US-001 (E) 实测时若有调整需同步更新 PRD + runbook | US-001 (E) / tech-spec.md §6.2 / US-017 |
| OQ-7 | NLS 拉 OSS URL vs Worker 直传 | **方案 A：传 OSS 签名 URL 让 NLS 自己拉**（更省流量）；不支持的 provider 降级到方案 B | US-017 |
| OQ-8 | 前端 manifest 元数据如何送达 Worker | **OSS 用户自定义元数据（`x-oss-meta-*`）**：前端 PutObject 时附带元数据（完整 key 清单见 tech-spec §3.2），Worker 通过 OSS API 读回 | US-011 / US-012 / US-015 / tech-spec §3.2 ADR-8 |

> 后续如又冒出新的开放问题，按 `OQ-9 / OQ-10 ...` 顺延追加；不要静默改动已决议的 OQ。

---

## 附录 A · 实施顺序建议

> 完整里程碑定义（M0 ~ M4 范围、完成标志、依赖关系）见 `docs/tech-spec.md` §7。从 M1 开始，**用户不再回阿里云 / 微信任何控制台**。

---

## 附录 B · 验收清单（自检用）

实施过程中可对照下面清单逐项打勾。里程碑范围与完成标志见 tech-spec §7。

- [ ] **M0** 通过：`make verify-prep` 全绿 + `docs/runbook/cloud-setup.md` 已登记
- [ ] **M1** 通过：tech-spec §7 M1 完成标志全绿
- [ ] **M2** 通过：tech-spec §7 M2 完成标志全绿
- [ ] **M3** 通过：tech-spec §7 M3 完成标志全绿
- [ ] **M4** 通过：§4 最终验收 AC 全部通过（§4.1 自动 + §4.2 真机）
- [ ] Success Metrics 表中 16 行（17 个编号，P-02 + P-03 合并为一行）全部达标
- [ ] Non-Goals 列出的 9 条本期都没有"偷偷"做进来（避免范围蔓延）
- [ ] Open Questions 8 条均已决议并落到对应 US 的 AC（决策详情见 tech-spec §8 ADR）
- [ ] **零控制台合规**：从 M1 开始没有出现过"打开 X 控制台手工 Y"的操作

---

## 附录 C · Open Questions 决策溯源

> OQ-1 ~ OQ-8 的产品决策索引见 §10，完整技术背景与影响分析见 `docs/tech-spec.md` §8（ADR-1 ~ ADR-8）。本附录不再独立维护内容。

