# PRD: 日观声记 MVP（SoniScope）

> 本 PRD 基于 `docs/requirements/requirements_v5.md` 拆分而来，**仅覆盖本期 MVP 范围**（第五章定义的最小闭环：录音 → 草稿 → 上传 OSS → 上传确认 → 本地下载 → **云端 API 转写** → 落盘）。**本期不部署本地 Whisper**，转写走公共云端语音转文字 API；本地模型推迟到流程跑通后再评估。下一阶段计划（LLM 润色、加密、多用户、SQLite 索引、自定义域名等）见原需求文档第八、九章，本 PRD 不展开。

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
- **G-4（转写幂等）**：Worker以 (audio_sha256, transcriber, model, params_version) 四元组判等；同一组合下重复扫描不会触发重复转写（避免重复消耗云端 API 额度）；显式改配置（如切换 provider / 模型版本）后能自动重转存量。
- **G-5（安全可控）**：小程序代码内不含任何长期 AccessKey；STS 临时凭证只能写本次指定的那一个 object key；FC 接口拒绝匿名调用。
- **G-6（可验证）**：本期所有验收项（原需求第十章 F-01 ~ U-03）均能通过明确的人工或脚本步骤验证通过。

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

> **AC 验证脚本化**：从 US-002 开始，每个 story 的 AC 验证步骤要么能通过 AI 提供的脚本/命令一键完成（如 `make test-fc-auth`、`make verify-upload-flow`），要么是用户在真机/DevTools 上的标准化操作（如"录音 5 秒"）。不允许出现"请到 X 控制台手工配置 Y"这种步骤。

### 3.2 仓库结构约定

本仓库采用 **monorepo**：微信小程序、FC 函数、Worker 进程放在同一 git 仓库，便于协议与数据契约同步演进。

| 路径 | 职责 |
|---|---|
| `apps/miniprogram/` | 微信小程序前端 |
| `apps/fc/` | 阿里云函数计算（`issue_credential` / `verify_upload` 等） |
| `apps/worker/` | Worker 后端进程（轮询、转码、转写、manifest） |
| `scripts/` | 跨组件运维与验证脚本（部署、校验、测试辅助） |
| `tests/` | 共享 fixtures（如标准音频）与集成 / 端到端测试 |
| `docs/` | PRD、需求文档、runbook |

**关键约定**：

1. **Python 用 uv workspace 管理**；Worker 包名 `soniscope-worker`，CLI 入口 `python -m soniscope_worker`。
2. **代码仓库与 Worker 运行时目录分离**：代码在 repo 内；运行时数据（`config.yaml`、`fragments/` 等）由环境变量 `SONISCOPE_HOME` 指定。
3. **顶层 Makefile 提供统一命令入口**（如 `make verify-prep`、`make deploy-fc`），用户无需进入子目录。
4. **本期不抽共享 Python 包**；FC 与 Worker 如有重复逻辑，先各自保留一份。

---

### 阶段 1：基础设施 (Infrastructure)

#### US-001: 人工准备：账号 / 资源 / 凭证 / 测试素材 / 运行环境 一站式 checklist

> **本 story 是整个 MVP 唯一的人工准备 story**，全部在控制台 / 浏览器 / 终端手工完成，不写业务代码。完成后所有后续 stories（US-002 ~ US-019）才能由 AI 编程接手，进而进入 §4 最终验收 AC 阶段。
>
> **完成判据**：以下 A~I 九个块的所有检查项都打勾，且 `docs/runbook/cloud-setup.md` 已包含全部非敏感信息。

**描述：** 作为开发者，我需要一次性把阿里云（OSS / RAM / FC）、微信小程序、云端语音转文字 API、测试音频素材、Worker 运行环境、凭证注入这六类外部依赖全部准备就绪，并在 `docs/runbook/cloud-setup.md` 中登记，让 AI 从 US-002 开始可以纯靠代码 + 脚本完成剩余工作，不再回控制台。

**Acceptance Criteria：**

---

**(A) 阿里云账号 + OSS 私有 Bucket**

- [ ] 阿里云账号已完成个人实名认证（aliyun.com → 账号中心 → 实名）
- [ ] 账号已充值 ≥ ¥100 作为押金（防欠费）
- [ ] 已创建私有 Bucket `soniscope-audio`（或同等命名），地域建议 `cn-hangzhou`（与 FC / NLS 同 region）
- [ ] Bucket ACL = **private**（不是 public-read）
- **检查方法**：
  - 控制台路径：对象存储 OSS → Bucket 列表 → 点击 `soniscope-audio` → 概览页 → 看「读写权限」= 私有 ✅
  - 或终端：`ossutil ls oss://soniscope-audio/` 能成功列出（即使为空也算通过）
  - 反例：未登录的浏览器访问 `https://soniscope-audio.oss-cn-hangzhou.aliyuncs.com/test.txt` 应返回 `AccessDenied`（即使对象不存在也是 AccessDenied 而不是 404）

---

**(B) 阿里云 RAM（两个子账号 + 一个角色 + STS 反例验证）**

- [ ] 已创建 RAM 子账号 `soniscope-fc`，仅授予系统策略 `AliyunSTSAssumeRoleAccess`；AccessKey 已保存到密码管理器（**不要写进任何代码仓库**）
- [ ] 已创建 RAM 子账号 `soniscope-local-reader`（**与 FC 用的子账号严格分开**），授予自定义策略 `soniscope-bucket-readonly`，仅允许 `oss:GetObject` / `oss:ListBucket` / `oss:HeadObject` 对 `soniscope-audio` 及其子对象
- [ ] 已创建 RAM 角色 `soniscope-uploader-role`，信任主体精确到 `soniscope-fc`（信任策略 Principal 为 `acs:ram::<uid>:user/soniscope-fc`）
- [ ] 角色权限策略 `soniscope-upload-template` 允许 `oss:PutObject` 到 `acs:oss:*:*:soniscope-audio/recordings/*`（这是模板上限，FC 在运行时还会进一步收紧到单文件级别）
- **检查方法**：
  - **正例**：用 `soniscope-fc` 的 AK 调 `aliyun sts AssumeRole --role-arn <角色 ARN> --role-session-name test --policy '{"Version":"1","Statement":[{"Effect":"Allow","Action":["oss:PutObject"],"Resource":["acs:oss:*:*:soniscope-audio/recordings/test.mp3"]}]}'` 能成功拿到临时凭证三件套
  - 用上述临时凭证 `PutObject` 到 `recordings/test.mp3` 成功 ✅
  - **反例 1**：用同一临时凭证 PutObject 到 `recordings/evil.mp3`（不在 policy 内）→ 必须返回 `AccessDenied`
  - **反例 2**：用同一临时凭证 `ListObjects` → 必须返回 `AccessDenied`
  - **反例 3**：用同一临时凭证 `GetObject recordings/test.mp3` → 必须返回 `AccessDenied`
  - **反例 4**：等待 16 分钟后用同一临时凭证再 PutObject → 必须返回 `ExpiredToken`

---

**(C) 阿里云函数计算 FC（服务 + 函数槽位 + HTTP 触发器）**

- [ ] FC 已开通（首次开通自动创建服务关联角色）
- [ ] 已创建服务 `soniscope-svc`，地域与 OSS 一致（如 `cn-hangzhou`）
- [ ] 已在服务下创建两个函数 `issue-credential` 和 `verify-upload`，运行时 Python 3.11，**函数体可暂时是空的 hello world**（实际代码与部署由 AI 在 US-003 和 US-005 各自完整交付：US-003 负责 `issue-credential` 的代码 + 部署，US-005 负责 `verify-upload` 的代码 + 扩展部署）
- [ ] 两个函数都配置了 HTTP 触发器（认证方式 = anonymous，不是 function；后续业务层鉴权由 US-003 的 openid allowlist 兜底）
- **检查方法**：
  - 终端：`curl -i https://<account>.<region>.fcapp.run/2016-08-15/proxy/soniscope-svc/issue-credential/` 应返回 200 + hello world，**不是** 404 / 502 / 网络错误
  - 同样验证 `verify-upload` URL
  - FC 控制台 → 服务 `soniscope-svc` → 函数列表 → 两个函数都状态正常
  - 两个 URL 都已记录到 `docs/runbook/cloud-setup.md`

---

**(D) 微信小程序（账号 + AppID + 域名白名单 + 工具 + 真机 openid）**

- [ ] 已在 mp.weixin.qq.com 注册微信小程序（个人主体即可），AppID 已记录（形如 `wx1234567890abcdef`）
- [ ] 已在小程序后台 → 开发设置 → 服务器域名，把 **FC 公网域名** 加入 `request` 合法域名（一行）
- [ ] 已把 **OSS Bucket 域名**（形如 `soniscope-audio.oss-cn-hangzhou.aliyuncs.com`）加入 `uploadFile` 合法域名（另一行）
- [ ] 已下载并安装「微信开发者工具」（稳定版），且用 AppID 新建项目能成功打开
- [ ] 已用真机微信扫码加入小程序「体验者」名单（小程序后台 → 成员管理 → 体验成员）
- [ ] 已用真机 / DevTools 跑过一次 `wx.login` + `jscode2session`（可用控制台 → 接口调试器，或 DevTools 里临时插一段 `wx.login` + `console.log`），**记录自己的 openid**
- **检查方法**：
  - 微信小程序后台 → 设置 → 基本设置：能看到 AppID
  - 微信小程序后台 → 服务器域名：能看到 FC 域名在 request 列、OSS 域名在 uploadFile 列
  - 微信开发者工具 → 详情 → 本地设置：取消勾选「不校验合法域名」，然后在小程序里临时跑 `wx.request({ url: <FC URL> })`，**不应**报「不在合法域名列表中」
  - openid 已记录到 `docs/runbook/cloud-setup.md`（格式形如 `o6zAJs...`）

---

**(E) 云端语音转文字 API（本期 MVP 转写后端）**

> **已暂定方案**：阿里云智能语音交互 **NLS 录音文件极速版**（OQ-6 决议）。理由：与现有阿里云资源同账号最省事 + 与 OSS 同 region 流量便宜 + 有免费时长 + **支持直接传 OSS 公网/签名 URL 让 API 自己拉，无需 Worker 重传**（与 OQ-7 决策 A 配套）。如执行 US-001 (E) 实测后发现障碍（如免费额度不够 / API 不支持传 OSS URL / 转写质量不达标），可改用备选方案，**改动需同步更新本 PRD 与 `docs/runbook/cloud-setup.md`**。

- [ ] 已选定服务商：默认 **阿里云智能语音交互 NLS 录音文件极速版**；备选：通义听悟 / OpenAI Whisper API（如最终选了备选，需在 runbook 中记录变更原因 + 影响哪些 stories）
- [ ] 已开通服务（如阿里云：智能语音交互控制台 → 立即开通）
- [ ] 已创建项目并拿到 AppKey（NLS 项目级标识，不是 AccessKey）
- [ ] 已领取免费额度（NLS 通常每月若干小时免费，足够开发期使用）
- [ ] 已了解计费方式（按时长 / 按次），并在 runbook 中估算"日均录音 30 分钟"的月度预估成本
- [ ] **真实联调基线**：用官方 demo 或 `curl` 上传一段 10 秒测试 MP3（来自下面 F 块）→ 拿到结构化转写结果（含文字 + segments + 时间戳）→ JSON 输出贴入 runbook 作为基线参考
- **检查方法**：
  - 控制台能看到项目 + AppKey
  - 上面那一次官方 demo 联调的输出文本与你说出口的内容一致（允许标点 / 同音字差异，但主干必须对）
  - AppKey / API endpoint 已记录到 runbook，AccessKey 已保存到密码管理器

---

**(F) 测试基线音频素材**

- [ ] 已准备 4 段标准测试音频，**全部放在 `tests/fixtures/audio/` 目录下**（这是项目仓库内的相对路径，AI 在 US-015 / US-017 以及 §4 最终验收 AC 中会直接引用）：
  - `tests/fixtures/audio/sample-10s.mp3`：约 10 秒 MP3，清晰人声，无背景音（US-001 E 联调 + US-017 真实闭环验证用）
  - `tests/fixtures/audio/sample-1min.mp3`：约 60 秒 MP3，含 5~10 句话（P-01 性能基线 + US-017 性能验证用）
  - `tests/fixtures/audio/sample-25min.mp3`：约 25 分钟 MP3（US-010 长录音分片 + §4.2 手动验收闭环用）
  - `tests/fixtures/audio/sample-aac.aac`：约 10 秒 AAC 格式（OQ-1 决议中**AAC 转码验证**用，US-015 强依赖）；可以用 `ffmpeg -i sample-10s.mp3 -c:a aac sample-aac.aac` 从 MP3 转出来
- [ ] 每个文件的 sha256 已记录到 runbook，便于后续校验文件未被改动
- **检查方法**：
  - `ls -la tests/fixtures/audio/` 能看到 4 个文件
  - `shasum -a 256 tests/fixtures/audio/*.{mp3,aac}` 输出与 runbook 中记录的一致
  - 每个文件用任意播放器试听，能听到清晰人声
  - `ffprobe tests/fixtures/audio/sample-1min.mp3` 显示 duration ≈ 60s + codec=mp3
  - `ffprobe tests/fixtures/audio/sample-aac.aac` 显示 codec=aac（验证不是误传 MP3）

---

**(G) Worker 运行环境（一次性就绪，不绑定 macOS / Mac Studio）**

- [ ] 已选定 Worker 部署位置（可以是 Linux 服务器 / Docker / 本机 / NAS / 树莓派，任意一种），并记录主机标识到 runbook
- [ ] 该主机上 `python3 --version` ≥ 3.11
- [ ] 该主机上已安装 `git`、`make`、`curl`，能 `git clone` 本项目
- [ ] 该主机上已选定 Worker 工作目录根路径，默认 `~/SoniScope/`（可通过环境变量 `SONISCOPE_HOME` 覆盖）；该路径所在磁盘有 ≥ 50GB 可用空间（音频积压 + 转写文件长期保留预留）
- **检查方法**：
  - SSH 到 Worker 主机后执行 `python3 --version` 输出 3.11+
  - `which git make curl` 三条命令都能找到
  - `df -h ~` 显示 ≥ 50GB available
  - `mkdir -p ~/SoniScope` 不报错（路径可写）

---

**(H) 凭证注入两个目标位置（FC 环境变量 + Worker 工作目录）**

- [ ] **FC 环境变量**（在 FC 控制台 → 服务 `soniscope-svc` → 配置 → 环境变量）已填入以下键值（具体值从前面 A~E 块得到）：
  - `OSS_BUCKET=soniscope-audio`
  - `OSS_REGION=cn-hangzhou`（与 Bucket 同 region）
  - `OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com`
  - `RAM_ROLE_ARN=<B 块创建的 soniscope-uploader-role 的 ARN>`
  - `ALIYUN_AK_ID=<soniscope-fc 子账号的 AK ID>`
  - `ALIYUN_AK_SECRET=<soniscope-fc 子账号的 AK Secret>`
  - `WX_APPID=<D 块的小程序 AppID>`
  - `WX_APP_SECRET=<小程序后台 → 开发设置 → AppSecret>`
  - `OPENID_ALLOWLIST=<D 块拿到的自己的 openid>`（单值或逗号分隔多值）
- [ ] **Worker 工作目录** `~/SoniScope/config.yaml` 已填入以下字段（具体值同样从 A~E 块得到）：
  ```yaml
  oss:
    endpoint: oss-cn-hangzhou.aliyuncs.com
    bucket: soniscope-audio
    access_key_id: <soniscope-local-reader 的 AK ID>
    access_key_secret: <soniscope-local-reader 的 AK Secret>
  poll:
    interval_seconds: 60
  transcriber:
    name: cloud-speech
    provider: aliyun-nls
    model: paraformer-v2
    params_version: v1
    api_endpoint: <从 E 块得到>
    appkey: <E 块的 NLS AppKey>
    access_key_id: <调用 NLS 的 AK>
    access_key_secret: <调用 NLS 的 AK Secret>
    local:
      enabled: false
  ```
- **检查方法**：
  - FC 控制台 → 函数 `issue-credential` → 配置 → 环境变量：能看到 9 个键都已填值（值在控制台是脱敏显示）
  - Worker 主机：`grep -c '^[a-z]' ~/SoniScope/config.yaml` ≥ 8（粗略统计已填字段数）
  - `~/SoniScope/config.yaml` 文件权限为 `chmod 600`（仅自己可读，防止其他用户偷看明文 AK）
  - **回头确认（US-002 完成后）**：跑 `make check-config`（等价于 `python -m soniscope_worker check-config`）输出"所有必填字段已就绪"

---

**(I) `docs/runbook/cloud-setup.md` 文档登记**

- [ ] 已新建 `docs/runbook/cloud-setup.md`，包含以下章节（**不含明文 AK / Secret / Token**）：
  - `## 阿里云 OSS`：Bucket 名 / region / Endpoint / 创建日期
  - `## 阿里云 RAM`：两个子账号名 / 角色名 / 角色 ARN / AK 保存位置（如「1Password vault: soniscope」）
  - `## 阿里云 FC`：服务名 / 两个函数名 / 两个 HTTP URL / 9 个环境变量名（**只列名字不列值**）
  - `## 微信小程序`：AppID / AppSecret 保存位置 / 体验者列表 / **自己的 openid**
  - `## 云端 ASR 服务`：服务商名 / 项目名 / AppKey / API endpoint / 免费额度信息 / 月度成本估算 / 联调基线 JSON 片段
  - `## 测试音频素材`：3 个 fixture 文件的相对路径 + sha256 + duration
  - `## Worker 运行环境`：主机标识 / Python 版本 / 工作目录路径 / 可用磁盘空间
  - `## 凭证管理约定`：明文 AK 一律不进仓库；FC 端在环境变量、Worker 端在 `~/SoniScope/config.yaml`（chmod 600，已被 `.gitignore` 覆盖）
- **检查方法**：
  - `cat docs/runbook/cloud-setup.md` 能看到上述 8 个章节
  - `grep -E 'LTAI|sk-|aliyun_ak' docs/runbook/cloud-setup.md` 应**无任何匹配**（验证没有明文 AK 泄漏到仓库）
  - `git status docs/runbook/cloud-setup.md` 显示该文件已被 git 跟踪（人工知识沉淀必须进仓库）

---

**最终验收命令（一行跑完所有可自动化的检查项）**：

完成后，AI 将在 US-002 中提供一个 `make verify-prep` 脚本，执行下面这些检查并汇总 pass/fail 报告：
- 跑 `aliyun oss stat oss://soniscope-audio` 验证 Bucket 私有
- 跑 4 条 STS 反例（PutObject 越界 / ListBucket / GetObject / Expired）
- `curl` 两个 FC URL 返回 200
- `ls tests/fixtures/audio/*.mp3` 3 个文件存在 + sha256 匹配
- `make check-config`（等价于 `python -m soniscope_worker check-config`）读取 `~/SoniScope/config.yaml` 通过

> ⚠️ `make verify-prep` 脚本本身由 AI 在 US-002 提供；US-001 完成时只需手工跑过反例验证 + 把信息记入 runbook 即可。

#### US-002: Python 项目骨架 + 配置 schema + `make verify-prep` 准备校验脚本

> **AI 编程任务**：写 Python 项目骨架、配置 schema、CLI 入口、`make verify-prep` 一键校验脚本。
>
> **前置假设（来自 US-001）**：用户已按 US-001 H 块填好 `~/SoniScope/config.yaml`，已按 F 块准备好 `tests/fixtures/audio/*.mp3`。本 story 不要求用户做任何额外手工操作。

**描述：** 作为开发者，我需要 AI 搭好 **monorepo 骨架**（顶层 uv workspace + `apps/worker/` Python 子项目 + 顶层 Makefile），实现 Worker 的配置 schema 与 CLI 入口，并提供 `make verify-prep` 脚本验证 US-001 准备的全部产物（OSS / RAM / FC / 测试音频 / config.yaml）真实可用。本 story **不**创建 `apps/miniprogram/` 与 `apps/fc/`（它们分别由 US-007+ 和 US-003+ 创建对应代码），但顶层 workspace 配置要为后续 member 留好位置。

**Acceptance Criteria：**

**(A) monorepo + uv workspace 骨架**
- [ ] 仓库根存在 `pyproject.toml`，声明 `[tool.uv.workspace] members = ["apps/worker"]`（`apps/fc` 在 US-003 时追加为 member，本 story 不强求）；声明 `requires-python = ">=3.11"`；**根 pyproject 不直接装业务依赖**（依赖在各 member 自己的 pyproject 里）
- [ ] 仓库根存在 `Makefile`，至少提供以下 target：`install` / `verify-prep` / `check-config` / `init-dirs` / `worker-run` / `typecheck` / `lint` / `test`；每个 target 内部 `uv run --package <member> ...`，**用户不需要 cd 进子目录**
- [ ] 仓库根存在 `apps/worker/pyproject.toml`，声明 `name = "soniscope-worker"`，依赖：`oss2` / `pyyaml` / `pydantic>=2` / `typer` / `alibabacloud-nls20180628`（**与 OQ-6 决议 NLS 选型对齐**）
- [ ] 仓库根存在 `apps/worker/src/soniscope_worker/` 目录，含 `__init__.py` / `__main__.py` / `cli.py` / `config.py` / `paths.py`；`__main__.py` 让 `python -m soniscope_worker ...` 可直接执行
- [ ] 跑 `make install` → 等价于 `uv sync` → 在干净环境中能在 5 分钟内安装完成所有 Python 依赖；`uv.lock` 已生成并已 commit
- [ ] **目录合规**：存在 `apps/worker/` 子项目（含 `pyproject.toml` 与 `src/soniscope_worker/`）；`apps/miniprogram/` 与 `apps/fc/` 本 story 不要求存在

**(B) 配置 schema + 加载器（in `apps/worker/src/soniscope_worker/config.py`）**
- [ ] 用 Pydantic v2 定义 `SoniScopeConfig` 模型，字段与 US-001 (H) yaml 一一对应（含 `oss.*` / `poll.*` / `transcriber.*` / `transcriber.local.enabled`）；缺失必填字段时 raise 明确异常 + 列出缺失字段名
- [ ] 配置加载顺序：① 环境变量 `SONISCOPE_HOME/config.yaml` → ② `~/SoniScope/config.yaml`；找不到时报错并提示用户参考 PRD US-001 (H) 块
- [ ] 敏感字段（`access_key_secret` / `appkey` / `api_key`）在 `__repr__` / 日志输出中自动脱敏（只显示前后 4 位）

**(C) CLI 命令（in `apps/worker/src/soniscope_worker/cli.py`，用 typer）**
- [ ] `python -m soniscope_worker check-config`（顶层 `make check-config` 别名）→ 读取配置 → 打印脱敏摘要 → 对缺失字段报错并退出非零
- [ ] `python -m soniscope_worker init-dirs`（顶层 `make init-dirs` 别名）→ 在 `SONISCOPE_HOME`（默认 `~/SoniScope/`）下创建 `inbox/` / `fragments/` / `tmp/`，已存在时幂等不报错

**(D) `make verify-prep` 一键校验 US-001 全部产物（**本 story 最关键的产出**，实现在 `scripts/verify_prep.py`）**
- [ ] `make verify-prep` 依次执行下列检查，并输出汇总 pass/fail 报告：
  1. **(A 块)** 读取 `config.yaml` → 用 `soniscope-local-reader` 的 AK 调 `oss2.Bucket(...).get_bucket_info()` → 验证 Bucket 存在且 ACL = private
  2. **(B 块)** 用 `soniscope-fc` 的 AK（从 `~/.soniscope-test-creds` 或 env 临时读取，**仅本机测试用**）调 `aliyuncs sts AssumeRole`，policy 限定到 `recordings/__verify_prep__.mp3` → 拿到临时凭证 → 跑 4 个反例（越界 PutObject / ListBucket / GetObject / 等待 16 分钟 ExpiredToken）→ 全部如预期失败才算 pass
  3. **(C 块)** `curl` FC 两个 URL → HTTP 状态码 200~499（不是 5xx / 网络错误）
  4. **(E 块)** 用 config 中的 NLS AppKey + AK，上传 `tests/fixtures/audio/sample-10s.mp3` → 拿到结构化转写结果 → 验证 segments 数 ≥ 1
  5. **(F 块)** `tests/fixtures/audio/sample-{10s,1min,25min}.mp3` + `sample-aac.aac` 四个文件存在 + sha256 与 runbook 中记录的一致 + ffprobe duration 与文件名标注的时长在 ±2s 内；额外检查 `sample-aac.aac` 的 codec=aac（验证 OQ-1 转码 fixture 就绪）
  6. **(G 块)** Python 版本 ≥ 3.11；`SONISCOPE_HOME` 路径可写；可用磁盘 ≥ 50GB；`ffmpeg` + `ffprobe` 可用（**OQ-1 决议依赖**）
  7. **(H 块)** `~/SoniScope/config.yaml` 权限为 600；所有必填字段非空
- [ ] 单项失败时，输出中包含**修复指引**（如 "请重做 US-001 (B) 反例 3"，附 runbook 中对应章节锚点）
- [ ] 全部通过时，最后一行打印 `✅ US-001 preparation verified. Ready for US-003+`
- [ ] **runbook 中 sha256 校验失败**时（用户改动了 fixture）→ 明确提示并指向 US-001 (F) 块的更新步骤

**(E) 质量门**
- [ ] `make typecheck` 通过（mypy strict 模式，扫 `apps/worker/src/` 与 `scripts/`）
- [ ] `make lint` 通过（ruff，同上）
- [ ] `make test` 覆盖 `SoniScopeConfig` 的合法 / 非法配置场景（至少 5 个测试用例）；对涉及云端的检查项（OSS / FC / NLS）使用 mock 而非真实 API；测试代码放在 `apps/worker/tests/`

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

**描述：** 作为系统所有者，我需要 FC `/issue-credential` 接口在云端真实可用，能 (1) 用 wx.login code 换 openid 校验是否在 allowlist，(2) 给合法用户签发精确到单 object key、≤15 分钟、≤50MB 的 STS 临时凭证，(3) 拒绝越权 / 过期 / 超限请求。

**Acceptance Criteria：**

**(A) handler 代码 — openid 校验 + allowlist**
- [ ] FC 函数 `/issue-credential` 接收 `{ code, fragment_id, sha256, size }`，**必填字段缺失返回 400**，含明确错误码
- [ ] FC 调用 `jscode2session` 成功换得 openid；微信侧返回错误时 FC 返回 401 并透传错误码（如 `INVALID_CODE`）
- [ ] FC 环境变量 `OPENID_ALLOWLIST` 中硬编码 openid 列表（逗号分隔，支持多设备测试）
- [ ] openid **不在** allowlist → FC 返回 403 `{ "error": "OPENID_NOT_ALLOWED" }`，不再签发任何凭证
- [ ] openid **在** allowlist → 继续进入 (B) 的凭证签发流程
- [ ] FC 日志记录每次调用的 openid（哈希后）、fragment_id、判定结果

**(B) handler 代码 — STS 签发 + 大小校验**
- [ ] FC 根据请求中的 `fragment_id` + 当前日期，组装目标 object key：`recordings/<YYYY-MM-DD>/<fragment_id>.mp3`
- [ ] FC 调用 STS AssumeRole 时，传入的 policy 文档 `Resource` 字段**精确等于** `acs:oss:*:*:<bucket>/<object_key>`（单条，不带通配符）
- [ ] 凭证有效期设置为 ≤ 900 秒（15 分钟）
- [ ] **上传大小上限校验（OQ-5 决议）**：FC 检查请求中的 `size` 字段，**必须 ≤ 50 MB（52428800 字节）**；超过则**直接返回 400 `{ "error": "SIZE_EXCEEDED", "limit_bytes": 52428800, "actual_bytes": <size> }`**，不签发任何凭证。理由：单条录音目标 ≤ 10 分钟，MP3 约 10MB；50MB 已留足余量，超此阈值视为可疑请求（防止 Worker 被洪水下载攻击）。上限值通过 FC 环境变量 `MAX_UPLOAD_BYTES` 可调（默认 52428800）
- [ ] 返回体包含 `access_key_id`、`access_key_secret`、`security_token`、`expiration`、`bucket`、`endpoint`、`object_key`

**(C) FC 部署能力首版（含工程化基线）**
- [ ] FC 函数源码位于 `apps/fc/issue_credential/handler.py`；同步把 `apps/fc/` 加入根 `pyproject.toml` 的 `[tool.uv.workspace] members`
- [ ] 仓库新增 `scripts/deploy_fc.py` 和顶层 `make deploy-fc` target
- [ ] `make deploy-fc` 自动完成：
  1. 接收 `FUNCTION=<name>` 参数（如 `make deploy-fc FUNCTION=issue_credential`），不传时默认部署所有 `apps/fc/*/` 下的函数（本 story 阶段只有一个）
  2. 在 `build/fc/<function_name>/` 下打包源码（从 `apps/fc/<function_name>/` 拷贝）+ `apps/fc/<function_name>/requirements.txt` 中声明的 vendored 依赖
  3. 用 aliyun fc SDK（`alibabacloud-fc20230330` 或同等）把 zip 上传到 `soniscope-svc` 服务下对应函数（覆盖代码，**不动**环境变量 / 触发器 / 运行时配置——这些都是 US-001 已经配置好的，AI 不要动）
  4. 部署完成后，自动 `curl` 该函数 URL 做存活验证
- [ ] 部署脚本读取 FC 部署所需的 AK 来源（环境变量 `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET`），**不写死到代码里**；本地 `.env`（已 gitignore）或 CI secret 都可注入
- [ ] **工程化基线（必须在首次部署就具备，US-005 直接复用，不允许后续追加）**：
  - 部署脚本每次推送前从 FC 读取当前代码 zip 并备份到 `build/fc/backup/<timestamp>/<function_name>.zip`，便于一键回滚
  - 部署日志写入 `build/fc/logs/deploy-<timestamp>.log`，包含：函数名、zip sha256、上传耗时、curl 验证结果
  - `build/` 目录已加入 `.gitignore`（构建产物不进仓库）

**(D) 云端联调（必须在云端真实 FC 上 verify）**
- [ ] 跑 `make deploy-fc FUNCTION=issue_credential` 把 (A)(B) 代码推到云端，部署日志显示 200 + curl 存活验证通过
- [ ] **公网 curl 拒绝匿名验证**：从任意可访问公网的终端用 `curl` 直接调用 FC 公网 URL（不带 code 或带伪造 code）**必须**被拒（400/401/403），不会拿到任何凭证
- [ ] **wx-login 失败验证**：跑 `make test-fc-live` → 用 `tests/fixtures/wx-login-fixture.json` 中的伪造 code 调 `/issue-credential` → 验证返回 401 `INVALID_CODE`（证明 (A) 代码生效）
- [ ] **allowlist 拒绝验证**：用真实 wx.login code（通过 `scripts/get_wx_code.py` 由用户在 DevTools 中临时获取并传入）调 `/issue-credential` → 验证 openid 不在 allowlist 时返回 403 `OPENID_NOT_ALLOWED`（**不需要用户回控制台**，只需 DevTools 跑 `wx.login` 一次）
- [ ] **STS 签发成功验证**：用 allowlist 内 openid 的 code 调 `/issue-credential` 返回有效 STS 凭证（含 (B) 要求的 7 个字段）
- [ ] **安全反例验证（拿到 STS 后越权）**：拿到的凭证尝试上传到 `recordings/<其他日期>/<其他 id>.mp3` → OSS 返回 `AccessDenied`
- [ ] **安全反例验证**：拿到的凭证尝试 `GetObject` / `ListObjects` / `DeleteObject` → 全部返回 `AccessDenied`
- [ ] **安全反例验证**：等待 16 分钟后用同一凭证再 PutObject → 返回 `ExpiredToken` 或等价错误
- [ ] **大小反例验证**：用 `size=60000000` 调 `/issue-credential` → 返回 400 `SIZE_EXCEEDED`；用 `size=10000000` → 返回正常 STS 凭证
- [ ] **日志拉取验证**：跑 `make fc-logs FUNCTION=issue-credential` 能拉到上述请求的日志（含 openid 哈希、fragment_id、判定结果），**用户无需打开 FC 控制台**

**(E) 质量门 + 本地测试**
- [ ] Typecheck（mypy strict）通过；扫 `apps/fc/issue_credential/src/`、`scripts/deploy_fc.py`
- [ ] Lint（ruff）通过
- [ ] 单元测试覆盖：handler 字段校验、`jscode2session` mock、allowlist 判定、STS policy 字符串拼接、大小上限边界、deploy 脚本打包逻辑 / SDK 调用 mock / 错误重试

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

**描述：** 作为系统所有者，我需要 FC `/verify-upload` 接口在云端真实可用，能用 HeadObject 校验 OSS 对象存在性 + 大小一致性，给小程序提供"上传是否真的完整"的最终签收回执，P95 ≤ 1 秒。

**Acceptance Criteria：**

**(A) handler 代码**
- [ ] FC 函数 `/verify-upload` 接收 `{ code, fragment_id, expected_sha256, expected_size }`；同样走 US-003 (A) 的 openid + allowlist 校验（代码层面**可复用** US-003 已有的鉴权 helper；如已抽公共模块更佳，未抽则各自实现一遍亦可，本期不强求 DRY）
- [ ] FC 对目标 object key 执行 HeadObject；对象不存在 → 返回 `{ verified: false, reason: "OBJECT_NOT_FOUND" }`
- [ ] 对象存在但 `Content-Length` 与 `expected_size` 不一致 → 返回 `{ verified: false, reason: "SIZE_MISMATCH", actual_size: ... }`
- [ ] 对象存在且大小一致 → 返回 `{ verified: true, etag, size, last_modified }`
- [ ] FC 日志记录每次 verify 的 fragment_id、结果、耗时
- [ ] P95 响应时间 ≤ 1 秒（原需求 P-03）

**(B) 扩展 `make deploy-fc` 支持第二个函数**
- [ ] FC 函数源码位于 `apps/fc/verify_upload/handler.py`（US-003 已建 `apps/fc/` workspace 配置，此处仅新增子目录 + `pyproject.toml` member 配置）
- [ ] 跑 `make deploy-fc FUNCTION=verify_upload` 能复用 US-003 已建的部署能力（备份 / 回滚 / 日志 / 工程化基线全部复用，**不应**新写一份）
- [ ] 跑不带参的 `make deploy-fc` 能自动扫描 `apps/fc/*/` 并部署所有函数（此时应同时部署 `issue_credential` + `verify_upload`）；日志显示两个函数各自的 zip sha256 + curl 存活验证结果

**(C) 云端联调（必须在云端真实 FC 上 verify）**
- [ ] 跑 `make deploy-fc FUNCTION=verify_upload` 把 (A) 代码推到云端，部署日志显示 200 + curl 存活验证通过
- [ ] **真实闭环验证（脚本化）**：AI 提供 `make test-verify-upload` 脚本自动完成「ossutil 上传测试对象 → 调用 `/verify-upload` 期望 `verified: true` → ossutil 删除对象 → 再次调用期望 `verified: false, reason: OBJECT_NOT_FOUND`」全流程，**用户无需手工操作 OSS 控制台**
- [ ] **大小不一致验证**：上传一个 100 字节对象 → 用 `expected_size=200` 调 `/verify-upload` → 返回 `verified: false, reason: SIZE_MISMATCH, actual_size: 100`
- [ ] **鉴权拒绝验证**：不带 code / 伪造 code → 同 US-003 (D)，返回 400/401
- [ ] **日志拉取验证**：跑 `make fc-logs FUNCTION=verify-upload` 能拉到上述请求的日志（含 fragment_id / 结果 / 耗时），**用户无需打开 FC 控制台**
- [ ] **性能验证**：跑 `make test-verify-upload` 时输出 P95 响应时间，必须 ≤ 1 秒

**(D) 质量门 + 本地测试**
- [ ] Typecheck（mypy strict）通过；扫 `apps/fc/verify_upload/src/`
- [ ] Lint（ruff）通过
- [ ] 单元测试覆盖：handler 字段校验、HeadObject mock 三种返回路径、`jscode2session` mock、allowlist 判定

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
- [ ] 点击后立即调用 `wx.getRecorderManager()` 开始录音；按钮切换为"停止录音"状态（颜色/文案变化）
- [ ] 录音过程中页面上实时显示已录时长（`mm:ss`，每秒刷新）
- [ ] 再次点击后停止录音，得到一个本地临时音频文件路径
- [ ] **音频格式策略（OQ-1 决议）**：
  - 优先调用 `wx.getRecorderManager().start({ format: 'mp3', ... })`；如果当前机型支持 MP3，直接得到 MP3，落盘扩展名 `.mp3`
  - **如机型不支持 MP3**（部分安卓 / 旧机型可能 fallback 为 AAC），不在前端做转码（避免电量与卡顿），保持 AAC 不变，落盘扩展名 `.aac`
  - 不论格式，在 manifest 草案中**显式标注 `audio.original_format`**（`mp3` 或 `aac`）；后续上传 OSS 时 object key 始终用 `.mp3` 扩展名作为统一约定，**真实格式以 manifest 为准**
  - 由 Worker（US-015）在下载后做格式标准化转码（AAC → MP3）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **微信开发者工具验证**：在 DevTools 模拟器中点击"开始录音"→ 等 3 秒 → 点击"停止录音"，控制台无报错，能在 `wx.env.USER_DATA_PATH` 或同等路径下看到生成的音频文件，文件扩展名与 manifest 中 `audio.original_format` 一致
- [ ] **真机预览验证**：用真机扫码预览，授权录音权限后完成一次开始→停止流程，页面状态正常切换，无 JS 报错；vConsole 打印出 `original_format` 字段
- [ ] **多机型验证**：在至少 1 台 iOS 真机 + 1 台 Android 真机上分别录一次，记录各自得到的 `original_format` 到 runbook（用于 US-015 转码逻辑决定是否需要兜底）

#### US-008: 录音中断保护（锁屏 / 来电 / 切后台 / 杀进程 自动 stop + 保存草稿）

**描述：** 作为用户，我录音时如果被电话、锁屏、微信切后台、系统杀进程打断，希望已经录到的部分**自动**被保存为草稿，而不是丢失。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 小程序在录音开始时已注册 `RecorderManager.onInterruptionBegin` 回调
- [ ] 中断事件触发时，前端调用 `recorderManager.stop()` 并把当时的临时音频文件落到本地存储，状态标记为"草稿（被中断保存）"
- [ ] 回到前台后页面给出明确提示：「上次录音被中断，已自动保存草稿，是否保留 / 丢弃 / 继续新录？」三个按钮可点击

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：`onInterruptionBegin` 回调注册逻辑、中断时 stop + 落盘逻辑

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
- [ ] 点击试听 → 调用 `wx.createInnerAudioContext` 播放本地临时音频；点击暂停能暂停
- [ ] 点击重录 → 当前草稿被销毁（本地文件清理），回到 US-007 的录音初始态
- [ ] 点击删除 → 当前草稿被销毁，无任何 Fragment 记录被上传或落盘
- [ ] 点击保存并上传 → 草稿被冻结，生成 `fragment_id`（US-011），进入上传流程（US-012），并自动跳转到上传列表（US-014）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **DevTools 验证**：录音 5 秒 → 试听能播放出原声 → 点击重录 → 旧文件消失（USER_DATA_PATH 下查不到）；再录 5 秒 → 点击删除 → 同样消失；再录 5 秒 → 点击保存并上传 → 上传列表里出现一条"上传中"记录
- [ ] **真机验证**：同上流程，三种分支（重录 / 删除 / 保存并上传）都能正常切换，控制台无报错
- [ ] 删除 / 重录后，无任何残留草稿文件出现在本地缓存中（可在下次冷启动后再次确认）

#### US-010: 长录音自动分片（≥ 10 分钟自动切片，共享 session_id）

**描述：** 作为用户，我有时会一口气说很久；当录音超过 10 分钟时，前端应该**对我透明地**把它切成多个 Fragment（每个 ≤ 10 分钟），共享一个 session_id，UI 上仍显示为"一段录音"。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 录音开始时分配一个 `session_id`（ULID）
- [ ] 录音每达到配置时长（默认 600 秒）时，前端自动调用一次 stop + 立即 start，把已录的部分作为一个 chunk 落地，chunk_seq 从 1 递增
- [ ] 最终用户点击停止时，最后一片的 chunk 状态被正确写入，并把 chunk_total 回填到所有 chunk 的 manifest 草案中
- [ ] 单条 chunk 时长 ≤ 10 分 5 秒（容忍一点点切片误差），不会出现 25 分钟单条

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：session_id 分配、chunk_seq 递增、chunk_total 回填逻辑

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **真机验证（关键）**：录制 25 分钟的录音 → 自动生成 **3 条** Fragment，三条共享同一 `session_id`，`chunk_seq` 分别为 1/2/3，`chunk_total` = 3
- [ ] 上传列表（US-014）能把这 3 条聚合为 1 行"长录音"展示，点开能看到 3 个子 chunk 的状态
- [ ] 切片过程中没有音频丢失（3 条音频拼起来 ≈ 25 分钟，允许 ±2 秒切换间隙）

#### US-011: Fragment ID 生成 + 设备指纹持久化 + 本地 manifest 草案

**描述：** 作为系统设计者，我需要每条 Fragment 在前端生成时就有一个全局唯一、人眼可读的 `fragment_id`，并且 manifest 草案在前端落地，便于后续后端和Worker统一识别。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 小程序首次启动时生成一个 4-8 字符的 `device_short_id`，持久化到 `wx.setStorageSync`，后续启动复用
- [ ] 每条 Fragment 在"保存并上传"时（US-009）生成 `fragment_id`，格式严格为 `<YYYYMMDDTHHMMSS>_<deviceShortId>_<ulid>`
- [ ] 同一秒内连续生成 2 条 Fragment 的 `fragment_id` **必须不同**（ULID 的随机性保证）
- [ ] 本地 manifest 草案（小程序端）至少包含：`fragment_id`、`session_id`、`chunk_seq`、`chunk_total`、`device_id`、`recorded_at`（ISO8601 带时区）、`duration_seconds`、`audio.size_bytes`、`audio.sha256`
- [ ] 音频 sha256 在前端计算完成（用 WeChat 原生 crypto 或第三方 wasm 库），与后续后端 verify 时使用的 `expected_sha256` 一致

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：device_short_id 生成逻辑、fragment_id 格式校验（正则）、同一秒唯一性、manifest 草案字段完整性、sha256 计算正确性

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **DevTools 验证**：连续录 2 条短录音并保存上传 → 在 vConsole 中能打印出 2 条不同的 `fragment_id`，且 `device_short_id` 字段一致
- [ ] **冷启动验证**：杀掉小程序进程，重新打开，`device_short_id` 仍是同一个值

#### US-012: 静默登录 + 获取 STS 凭证 + 直传 OSS

**描述：** 作为用户，我点击"保存并上传"后，前端应自动完成 `wx.login` → 调 FC `/issue-credential` 拿到单文件级 STS → `wx.uploadFile` 直传 OSS 这条链路，期间我无需手动登录。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 点击保存并上传后，前端依次：① `wx.login` 拿 code → ② POST FC `/issue-credential`（带 code、fragment_id、sha256、size） → ③ 用拿到的 STS 三件套构造 OSS PutObject 签名 → ④ `wx.uploadFile` 直传到 `recordings/<YYYY-MM-DD>/<fragment_id>.mp3`
- [ ] FC 返回非 200 → 上传状态切换为"待人工重传"，并在列表上展示错误码（如 `OPENID_NOT_ALLOWED`、`INVALID_CODE`）
- [ ] OSS 返回非 2xx → 进入指数退避自动重试（最多 3 次，间隔 5s / 15s / 45s）
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

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] `wx.uploadFile` 收到 200 后，前端立即 POST FC `/verify-upload`（带 code、fragment_id、expected_sha256、expected_size）
- [ ] 收到 `verified: true` → 本地 manifest 草案标记 `upload.verified_at` 为当前时间；上传列表状态切换为"上传成功"
- [ ] 收到 `verified: false` → 上传列表状态切换为"待重传"，错误原因展示给用户
- [ ] FC 调用本身失败（超时 / 网络错误） → 进入重试队列，最多 3 次；3 次仍失败 → 状态切换为"待人工 verify"
- [ ] **本地保留策略（自动清理）**：
  - **仅当** `verified: true` **且** `verified_at` 距当前时间 **≥ 48 小时** 时，才允许自动清理本地音频缓存文件（`wx.env.USER_DATA_PATH` 下）
  - **verify 未通过**（`verified: false` / 待重传 / 待人工 verify）的文件 **永不自动删除**，无论过了多久
  - **verify 通过但不足 48 小时** 的文件 **不允许自动删除**
- [ ] **手动删除（异常兜底）**：上传列表中每条记录提供"删除本地缓存"操作入口（长按或滑动），用户确认后可手动删除任何状态的本地文件（含 verify 未通过的）；删除前弹出二次确认：「该录音尚未成功上传到云端，删除后无法恢复，确定删除？」（仅 verify 未通过时弹出，已通过的直接删除不二次确认）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：verify 调用逻辑、重试队列、保留策略三种分支（时间 mock）

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **真实闭环验证**：上传一条短录音 → 状态显示"上传成功" → 用户跑 `make oss-delete-obj FRAGMENT_ID=<前端打印的 id>` 删除该对象（**无需打开 OSS 控制台**）→ 在小程序上重新点击该条记录的"重新 verify" → 状态切换为"待重传"，错误码 `OBJECT_NOT_FOUND`
- [ ] **保留策略验证（verify 通过 + 48h 内不删）**：上传一条短录音 → verify 通过 → 在 DevTools 中把本地时间偏移设到 24 小时后 → 触发清理逻辑 → 文件**仍存在**
- [ ] **保留策略验证（verify 通过 + 48h 后可删）**：偏移到 49 小时后再触发 → 文件被自动清理
- [ ] **保留策略验证（verify 未通过永不自动删）**：模拟一条 verify 失败的录音 → 偏移到 7 天后 → 触发清理逻辑 → 文件**仍存在**
- [ ] **手动删除验证**：对一条"待重传"状态的记录执行手动删除 → 弹出二次确认 → 确认后文件被删除 + 列表中该条消失

#### US-014: 上传列表页（5 种状态展示 + 失败 3 次转人工 + 离线醒目提示）

**描述：** 作为用户，我希望有一个独立的"上传列表"页面，能清晰看到每条录音处在哪个状态，特别是当多条录音未上传 / 上传失败时给我醒目提醒。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 上传列表页能展示每条 Fragment 的五种状态之一：`草稿` / `上传中` / `上传成功（verified）` / `上传失败` / `待人工重传`
- [ ] 上传失败连续 3 次自动重试后切换为"待人工重传"，列表中**红色标记**，并显示"点击手动重传"按钮
- [ ] 点击"手动重传"按钮 → 重置重试计数，重新走 US-012 + US-013 完整流程
- [ ] **长录音分片显示与重传（OQ-4 决议：分片各自可重传）**：
  - 同一 `session_id` 下的多个 chunk 在列表中**折叠显示为一行**"长录音"卡片，标题展示总时长 + chunk 总数（如 `25:00 · 3 段`）
  - 卡片右侧显示**聚合状态**：仅当**所有 chunk 都成功（verified）**才显示绿色"已完成"；只要有任何 chunk 失败 / 待人工 → 整张卡片显示红色"X / N 失败"
  - 点击卡片可**展开**，列出每个 chunk 的独立状态行（`chunk_seq=1/2/3` 各自一行 5 种状态之一）
  - **每个 chunk 都有独立的"手动重传"按钮**，只重传该 chunk，不会重传整段（避免一段 25 分钟里只有 chunk 2 失败时还要把 chunk 1/3 重新上传）
  - 折叠态下点击卡片主体 = 展开；展开态下点击右上角 ⌄ = 折叠
- [ ] 当存在 N 条状态为"上传失败 / 待人工 / 离线积压"的 Fragment 时，页面顶部出现醒目横条：「未上传 N 条，距离最早录音已 X 小时」（N 按**单个 chunk** 计数，与折叠卡片的聚合状态独立计算）
- [ ] 设备离线时点击"保存并上传"不会让 Fragment 永久滞留在"草稿"态——而是进入"离线队列"，恢复网络后自动开始上传
- [ ] **故障注入开关**：小程序提供「开发者菜单 → 故障注入」入口（仅 NODE_ENV != 'production' 可见），可在运行时切换以下开关，**无需用户修改源码**：
  - `mock-fc-url-broken`：让所有 FC 请求强制返回失败
  - `mock-network-offline`：模拟离线（即使真实网络通畅）
  - `mock-verify-fail`：让 `/verify-upload` 永远返回 `verified: false`

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过

**(C) 手动验证清单（用户在 DevTools / 真机上操作）**
- [ ] **DevTools 验证**：通过故障注入开关依次制造 3 种场景（全成功 / 自动失败 3 次 / 离线录音后联网） → 列表上 5 种状态都能正确出现且文案正确
- [ ] **真机验证（离线）**：开飞行模式录 2 条 → 列表显示离线积压 + 顶部红色提示 → 关闭飞行模式 → 自动开始上传，状态依次切换
- [ ] **真机验证（故障注入）**：在故障注入菜单打开 `mock-fc-url-broken` → 录一条 → 自动重试 3 次失败 → 列表变红 + 出现"点击手动重传"按钮 → 关闭故障注入 → 手动重传成功
- [ ] 控制台 / vConsole 无未捕获异常

---

### 阶段 4：转写 Worker（Python 后端进程，运行环境无关）

#### US-015: OSS 轮询 + 下载到 `.part` + 格式标准化（AAC → MP3）+ 原子 rename 为 `audio.mp3`

**描述：** 作为Worker，我需要按 `config.yaml` 配置的频率轮询 OSS，发现新 object 时下载到临时文件，校验完整后做**格式标准化**（如果是 AAC 转码为 MP3，如果已经是 MP3 直接保留），最终原子 rename 到 `audio.mp3`。

**Acceptance Criteria：**

**(A) 代码实现**

- [ ] 脚本启动后按 `poll.interval_seconds`（默认 600）周期轮询 OSS，列出 `recordings/` 前缀下所有对象
- [ ] 对每个**本地尚未存在**或**本地存在但无 `.done`** 的对象：
  - 下载到 `~/SoniScope/inbox/<fragment_id>.part`
  - 下载完成后计算 **`original_sha256`**；与 OSS 上的 ETag/Content-Length 比对一致；不一致 → 删除 `.part`，下一轮重下
  - **格式检测**（用 `ffprobe` 或文件头 magic bytes）：
    - 若是 **MP3** → 直接原子 rename `.part` 为 `~/SoniScope/fragments/<YYYY-MM-DD>/<fragment_id>/audio.mp3`，`audio.sha256` = `original_sha256`
    - 若是 **AAC**（或其他非 MP3 格式）→ 转码到 `inbox/<fragment_id>.mp3.tmp` → 计算转码后的 `audio.sha256` → 原子 rename 为 `audio.mp3`
    - **转码失败** → 不写入 fragments 目录，把 `.part` 移到 `inbox/failed/<fragment_id>.part` 留档，日志报错并跳过该 Fragment（下次扫描会重试）
  - 在 manifest 中记录：`audio.original_format`（来自前端上报或检测结果）、`audio.format`（始终 `mp3`）、`audio.sha256`（最终 audio.mp3 的）、`upload.original_sha256`（OSS 上对象的，与 FC verify 一致）、`upload.original_size_bytes`
- [ ] **OSS 永不删除**：脚本任何路径下都**不会**调用 `DeleteObject` 或 `oss2.Bucket.delete_object`（用 `rg "delete_object|DeleteObject"` 应只在测试 mock 中出现）

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

#### US-016: 启动恢复扫描 + 文件状态机三段式协议

**描述：** 作为系统所有者，我需要Worker在每次启动时扫描 `~/SoniScope/fragments/`，根据每个目录里 `.part` / `audio.mp3` / `transcript.json.tmp` / `transcript.json` / `.done` 的组合，准确判断该 Fragment 处在哪个阶段，并从中断处继续。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 启动时遍历 `~/SoniScope/fragments/**/`，对每个 fragment 目录按下表判定：

  | 目录内容 | 判定 | 动作 |
  |---|---|---|
  | 有 `.done` | 已完成 | 跳过 |
  | 无 `.done`，有 `audio.mp3` | 转写未完 | 进入转写流程 |
  | 无 `audio.mp3`，有 `.part` | 下载中断 | 删除 `.part`，下次轮询重下 |
  | 全无 | 新 Fragment | 走完整下载 + 转写 |

- [ ] 三段式协议严格执行：
  - 下载：先写 `<id>.part` → sha256 校验 → 原子 `rename` 为 `audio.mp3`
  - 转写：先写 `transcript.json.tmp` → 原子 `rename` 为 `transcript.json`
  - 完成：上述都成功后才写 `.done`（空文件）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：启动扫描 4 种状态判定、三段式协议各阶段原子性
- [ ] **崩溃恢复验证（关键）**：`make test-crash-recovery` → 录入一条音频，等Worker下载完 `audio.mp3` 但还在调用云端 API 转写时 `kill -9` → 重启脚本 → 自动重新调用 API 转写并写出 `transcript.json` + `.done`
- [ ] **崩溃恢复验证（missing-done）**：`make simulate-worker-crash CASE=missing-done FRAGMENT_ID=<id>` → 等价于删掉 `.done` 标记 → 重启 Worker → 该条会被重新转写并补回 `.done`
- [ ] **崩溃恢复验证（stale-part）**：`make simulate-worker-crash CASE=stale-part FRAGMENT_ID=<id>` → 等价于残留 `.part` 空文件 → 重启 Worker → 该残留被识别并重下，不会因此污染下游 `audio.mp3`

**(C) 手动验证清单**

> 本 story 无需手动验证，所有 AC 均可通过自动化脚本完成。

#### US-017: Transcriber 抽象接口 + CloudSpeechTranscriber 实现（云端 API 优先）

> **本期 MVP 默认走云端 API**。`WhisperLocalTranscriber` 仅保留占位骨架，本地推理推迟到流程跑通后再评估。

**描述：** 作为系统设计者，我需要把"转写器"抽象成接口 `Transcriber.transcribe(audio_path) -> TranscriptResult`，本期实现 `CloudSpeechTranscriber`（调用 US-001 注册的云端语音转文字 API），并预留 `WhisperLocalTranscriber` 占位骨架，便于下一阶段切换到本地推理。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] 存在 `Transcriber` 抽象基类（ABC 或 Protocol），定义方法 `transcribe(audio_path: Path, oss_object_key: str | None) -> TranscriptResult`；`TranscriptResult` 是结构化 dataclass，含 `segments`、`language`、`duration`、`model`、`params_version`、`provider`（如 `aliyun-nls`）
- [ ] **音频传递方式（OQ-7 决议：方案 A）**：
  - **首选方案 A（OSS 签名 URL）**：`CloudSpeechTranscriber` 优先用 `oss2.Bucket.sign_url('GET', object_key, expires=3600)` 生成 OSS 临时签名 URL（**注意：传给 NLS 的是 OSS 上的原始 object，不是 Worker 本地转码后的 audio.mp3**——因为 NLS API 也支持 MP3/AAC 等多种格式，且原始对象本身就在 OSS 上，省一次上传）
  - **降级方案 B（直传文件）**：当 `config.yaml` 中 `transcriber.upload_mode = 'direct'`、或 provider 是 OpenAI Whisper API 等不支持 URL 拉取的服务时，回退到方案 B（用 `audio_path` 把 Worker 本地的 `audio.mp3` 通过 multipart 上传给 API）
  - 选用哪种方案在日志中明确打印（`mode=oss-url` / `mode=direct-upload`），便于排查
- [ ] `CloudSpeechTranscriber` 实现该接口：从 `config.yaml` 读取 provider / endpoint / api_key / appkey → 按上面策略选模式 → 提交转写任务 → 轮询或等待结果 → 映射成 `TranscriptResult`
- [ ] **签名 URL 过期处理**：调用 NLS 前生成的 URL 有效期至少 1 小时（覆盖 NLS 排队 + 处理）；若 NLS 异步轮询超过 50 分钟仍未完成，重新签发一次 URL 继续等
- [ ] `CloudSpeechTranscriber` 失败重试策略：网络错误 / 5xx 自动指数退避重试 3 次（间隔 5s/15s/45s）；4xx（鉴权 / 配额）立即失败并打印明确错误码
- [ ] `WhisperLocalTranscriber` **占位类**存在（`raise NotImplementedError("Local Whisper deferred to next phase")`），证明接口预留可扩展，但本期不调用
- [ ] 转写器实例由 `config.yaml` 中的 `transcriber.name` 决定（工厂方法）；当前默认 `cloud-speech`，未来切到 `whisper-local` 时不需要改业务代码
- [ ] **成本可观测**：每次调用后日志输出"本次预估消耗时长 / 调用次数 / 累计成本（估算）"，便于运行过程中监控免费额度
- [ ] 输出的 `transcript.json` 结构稳定，至少包含：`segments[].start`、`segments[].end`、`segments[].text`、`language`、`model`、`params_version`、`provider`

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：工厂方法、方案 A/B 切换、签名 URL 过期续签、`CloudSpeechTranscriber` 失败重试逻辑（mock API）、`WhisperLocalTranscriber` 调用时抛 `NotImplementedError`
- [ ] **真实闭环验证（关键）**：`make test-transcribe` → 取 US-001 (E) 中跑通的同一段 10 秒测试 MP3 → 在 Worker 中调用 `CloudSpeechTranscriber.transcribe()`（**用 OSS URL 方案**）→ 返回的文字内容与 US-001 (E) 控制台验证结果一致（允许小幅模型版本差异，但**主干文字必须能对得上**）
- [ ] **方案 A 验证**：`make test-transcribe-oss-url` → 日志显示 `mode=oss-url`；用 `make show-oss-object` 能看到该对象在转写时段的访问日志（NLS 真的来拉过了）；Worker 端**不产生**上行流量到 NLS（用 `nethogs` 或同等工具确认转写期间 Worker 上行流量极小）
- [ ] **降级方案 B 验证**：`make test-transcribe-direct` → 临时改 `config.yaml` 中 `transcriber.upload_mode = 'direct'` → 重新转写一条 → 日志显示 `mode=direct-upload`；转写结果与方案 A 一致
- [ ] **性能验证（替代 P-01）**：`make test-transcribe-perf` → 用一段 1 分钟标准音频跑 `CloudSpeechTranscriber.transcribe()` → 端到端耗时 ≤ 60 秒（含 NLS 排队 + 处理；视服务商不同可调整阈值，写进 runbook 作为基线）

**(C) 手动验证清单**

> 本 story 无需手动验证，所有 AC 均可通过自动化脚本完成。

#### US-018: 幂等判断 + 显式触发重转

**描述：** 作为系统所有者，我需要 Worker 在每次扫描时基于 `.done` 标记判断是否已完成转写，避免重复消耗算力；同时允许我通过 `retranscribe` CLI 命令显式触发存量重转。**更换模型 / 参数版本后，仅新进入的 Fragment 自动使用新配置，已完成的存量 Fragment 不会被自动重转。**

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] **正常轮询幂等判断**：转写前检查 `.done` 文件是否存在 → 存在则**直接跳过**（无论当前配置中的模型 / 参数版本是否与 manifest 中记录的一致）
- [ ] `.done` 不存在 → 按当前配置进行转写
- [ ] **转写元数据记录**：转写完成后，将四元组 `(audio_sha256, transcriber_name, model_version, params_version)` 写入 `manifest.json` 的 `transcription` 字段，用于溯源和 CLI 筛选
- [ ] OSS 端去重：同一 object key 重复下载只会覆盖本地 `audio.mp3`，不会产生新目录
- [ ] **显式重转 CLI（OQ-3 决议）**：提供 `python -m soniscope_worker retranscribe <fragment_id> [--all-from <YYYY-MM-DD>] [--upgrade] [--force]` 子命令（顶层 `make retranscribe FRAGMENT_ID=<id>` 别名）：
  - 不带 `--force` / `--upgrade` 时：若该 Fragment `.done` 存在 → 提示"已完成转写，使用 --force 强制重转或 --upgrade 升级旧模型"
  - `--upgrade`：比对 manifest 中的 `model` / `params_version` 与当前配置，仅对"用旧版本转写的 Fragment"执行重转
  - `--force`：忽略一切判断，直接重转
  - 支持 `--all-from <YYYY-MM-DD>` 批量重转某日期起的全部 Fragment（按目录批扫描，逐条转写，遇到失败继续下一条并最后汇总）
  - 命令运行期间 Worker 主轮询线程可继续工作（不互斥），但同一 fragment_id 不会被同时转两遍（用 file lock 防并发）
- [ ] 显式重转过程中老的 `transcript.json` 不会"半覆盖"（始终通过 `.tmp` + rename 保证原子性）

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：`retranscribe` 幂等性、`--force` 行为、`--upgrade` 筛选逻辑、file lock 并发保护
- [ ] **重复扫描验证（F-08）**：`make test-idempotent-skip` → 脚本完成一条 Fragment 的转写后，重启或等待下一轮扫描 → 该 Fragment 不会再次进入 transcriber.transcribe()（通过日志或调用计数验证）
- [ ] **配置变更不触发自动重转验证（F-10）**：`make test-no-auto-retranscribe` → 修改 `config.yaml` 中 `transcriber.model` 或 `params_version` → 重启脚本 → 已有 `.done` 的存量 Fragment **不会**被重新转写（通过日志或调用计数验证，确认 transcriber.transcribe() 调用次数为 0）
- [ ] **CLI 显式重转验证（F-11）**：`make test-cli-retranscribe` → 执行 `retranscribe <id> --force` → 日志显示重转 + 新 `transcript.json` 覆盖；manifest 的 `transcription.completed_at` 时间戳和 `model` 字段更新
- [ ] **CLI --upgrade 验证**：`make test-cli-upgrade` → 修改 `config.yaml` 模型版本 → 执行 `retranscribe --all-from <date> --upgrade` → 仅旧模型转写的 Fragment 被重转，已用新模型转写的 Fragment 被跳过

**(C) 手动验证清单**

> 本 story 无需手动验证，所有 AC 均可通过自动化脚本完成。

#### US-019: `manifest.json` 单向写入 + `transcript.json` + `.done` 完成标记

**描述：** 作为系统所有者，我需要每个 Fragment 目录最终包含完整的 `manifest.json`（权威状态来源）、`transcript.json`（结构化转写）、`transcript.txt`（从 transcript.json 派生的纯文本）和 `.done`（完成标记），且字段格式与 requirements_v5 第 7.5 节完全一致。

**Acceptance Criteria：**

**(A) 代码实现**
- [ ] `manifest.json` 字段至少包含：
  - **顶层**：`fragment_id`、`session_id`、`chunk_seq`、`chunk_total`、`device_id`、`recorded_at`、`duration_seconds`
  - **`audio`**（最终落盘后的 `audio.mp3`）：`format`（始终 `mp3`）、`original_format`（`mp3` 或 `aac`，来自 US-007 决策 1）、`size_bytes`、`sha256`（最终 audio.mp3 的，用于幂等四元组）
  - **`upload`**（OSS 上的对象，用于 FC verify）：`uploaded_at`、`verified_at`、`verify_method`、`original_sha256`（前端上传到 OSS 的文件 sha256，与 OSS ETag / FC verify 一致）、`original_size_bytes`
  - **`transcription`**：`started_at`、`completed_at`、`elapsed_seconds`、`transcriber`、`model`、`params_version`、`provider`、`upload_mode`（`oss-url` / `direct-upload`，来自 US-017 决策 7）
- [ ] **当 `audio.original_format == 'mp3'`**（前端直接录到 MP3，无转码）：`audio.sha256 == upload.original_sha256`、`audio.size_bytes == upload.original_size_bytes`
- [ ] **当 `audio.original_format == 'aac'`**（Worker 端转码）：`audio.sha256` 与 `upload.original_sha256` 不同；两个字段都必须真实计算并写入，不允许任意一方留 null
- [ ] `manifest.json` 的写入也走"先写临时文件再原子 rename"，避免半写状态
- [ ] `transcript.json` 是结构化 JSON（segments + 时间戳 + 模型版本），不是纯文本
- [ ] `transcript.txt` 从 `transcript.json` 派生（拼接 segments.text），便于人眼直接读
- [ ] `.done` 是 0 字节空文件，仅作为"全流程完成"的旗标

**(B) 自动验证（`make` 命令一键跑完，无需人工操作）**
- [ ] Typecheck / lint 通过
- [ ] 单元测试覆盖：manifest schema 校验、MP3/AAC 两种路径的 sha256 一致性断言、原子写入逻辑
- [ ] **完整性验证**：`make test-fragment-integrity` → 跑完一条 Fragment 后，目录里**同时**存在以下 5 个文件：`audio.mp3` / `manifest.json` / `transcript.json` / `transcript.txt` / `.done`，且 manifest 中所有字段都已填充（无 null 残留，除非业务允许）
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
- [ ] `make verify-e2e-integrity` → 本地 `~/SoniScope/fragments/` 下出现**完整的 100 个 Fragment 目录**，每个目录都同时包含 `audio.mp3` / `manifest.json` / `transcript.json` / `transcript.txt` / `.done` 五个文件
- [ ] `make verify-e2e-sha256` → 每条 Fragment 的本地 `audio.mp3` sha256 与 OSS 对象 ETag 与小程序前端 `manifest.audio.sha256` **三者一致**
- [ ] `make verify-e2e-fields` → 每条 Fragment 的 `manifest.upload.verified_at` 非空、`manifest.transcription.completed_at` 非空

**[异常路径 · 脚本崩溃恢复]**

- [ ] `make test-e2e-crash-recovery` → Worker 运行中，对一条正在转写的 Fragment 执行 `kill -9` → 该目录残留 `audio.mp3` 但无 `.done` → 重启脚本 → 自动重新转写并补回 `.done` + 完整的 `transcript.json`

**[异常路径 · 显式重转]**

- [ ] `make test-e2e-retranscribe` → 修改 `config.yaml` 的 `transcriber.params_version` v1 → v2 → 下次扫描时**所有存量 Fragment** 被重新转写，新的 `transcript.json` 覆盖旧的，`manifest.transcription.params_version` 全部变为 v2

**[安全反例 · 鉴权与越权]**

- [ ] `make test-e2e-security` → 用未在 allowlist 中的另一个微信号调用 FC → 收到 403；用合法 STS 凭证尝试 PutObject 到其他 key → OSS 返回 AccessDenied

**[完整性扫描 · 无半成品残留]**

- [ ] `make verify-no-stale` → 所有异常路径跑完后：OSS 上对象数 ≥ 本地 Fragment 目录数；未出现任何"半成品"目录（即不存在"有 `.part` 又有 `audio.mp3`"或"有 `transcript.json.tmp` 残留"的目录）

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

- **FR-1**：小程序首页提供"开始 / 停止"录音单一按钮，单次录音目标时长 ≤ 10 分钟（US-007）。
- **FR-2**：录音过程中遇到锁屏 / 来电 / 切后台 / 杀进程时，系统**必须**通过 `RecorderManager.onInterruptionBegin` 自动停止并保存已录部分为草稿（US-008）。
- **FR-3**：停止录音后**必须**先生成草稿，由用户显式点击"保存并上传"才晋升为 Fragment（US-009）。
- **FR-4**：当单次录音 ≥ 10 分钟时，前端**必须**自动按 600 秒分片，多片共享 `session_id`、独立 `chunk_seq`（US-010）。
- **FR-5**：每条 Fragment 在前端生成时**必须**得到全局唯一的 `fragment_id = <YYYYMMDDTHHMMSS>_<deviceShortId>_<ulid>`（US-011）。
- **FR-6**：FC `/issue-credential` **必须**先用 `wx.login` 的 code 换 `openid` → 检查 allowlist → 通过后才用 STS 签发**精确到单个 object key** 的临时凭证，凭证有效期 ≤ 15 分钟（US-003）。
- **FR-7**：FC `/verify-upload` **必须**用 HeadObject 校验 OSS 对象存在 + 大小一致；失败时返回明确原因码（US-005）。
- **FR-8**：小程序**必须**在收到 OSS 200 后立即调用 `/verify-upload`；本地缓存**仅在 verify 通过且超过 48 小时后**才允许自动清理，verify 未通过的文件永不自动删除；用户可手动删除任何状态的本地文件（US-013）。
- **FR-9**：上传连续失败 3 次后**必须**切换为"待人工重传"红色提示状态（US-014）。
- **FR-10**：Worker**必须**按 `config.yaml` 中可配置的 `poll.interval_seconds`（默认 60）周期轮询 OSS（US-015）。
- **FR-11**：Worker**绝不**调用 OSS `DeleteObject`，OSS 文件永久保留（US-015 + §4 最终验收 AC）。
- **FR-12**：本地文件操作**必须**走"先临时 → 原子 rename → 写 `.done`"三段式协议（US-016）。
- **FR-13**：脚本启动时**必须**扫描 `~/SoniScope/fragments/`，对每个目录按状态机决定是跳过 / 重转 / 重下 / 新办（US-016）。
- **FR-14**：转写**必须**通过 `Transcriber` 抽象接口调用；本期默认实现 `CloudSpeechTranscriber`（调用云端语音转文字 API），且预留 `WhisperLocalTranscriber` 占位骨架；**本期不部署本地推理模型**（US-017）。
- **FR-15**：转写幂等性**必须**基于 `.done` 标记文件判断——`.done` 存在即跳过，不因模型 / 参数版本变更自动重转；四元组 `(audio_sha256, transcriber, model, params_version)` 仅记录于 manifest 供溯源和 CLI 筛选（US-018）。
- **FR-16**：每个 Fragment 目录最终**必须**同时存在 `audio.mp3` / `manifest.json` / `transcript.json` / `transcript.txt` / `.done` 五个文件（US-019）。
- **FR-17**：`manifest.json` 字段格式**必须**与 requirements_v5 第 7.5 节完全一致（US-019）。

---

## 6. Non-Goals / 本期不做

明确划出边界，避免范围蔓延：

- **NG-1**：不做 LLM 润色与每日文字稿生成（详见 requirements_v5 第八章，下一期【计划 C】）。
- **NG-2**：不做日稿呈现界面（Web / 邮件 / 移动 App），手机端**不需要**查看历史 Fragment 列表或日稿。
- **NG-3**：不做搜索 / 标签 / 聚合 / 统计；本期不引入 SQLite 索引（下一期【计划 E】）。
- **NG-4**：不做完整用户登录系统；只用 `openid` allowlist 单用户（下一期【计划 B】）。
- **NG-5**：不做录音 / 转写文件 / 日稿加密存储（下一期【计划 A】）。
- **NG-6**：不做自定义域名 + 备案；MVP 直接用阿里云自带 HTTPS 域名（下一期【计划 F】）。
- **NG-7**：不做 App 端；本期只在微信小程序运行。
- **NG-8**：Worker不做 Web UI / GUI，仅命令行 + 日志。
- **NG-9**：**本期不部署本地 Whisper / 本地 GPU 推理**。转写全部走云端 API（US-001 (D) 中注册的服务）；本地 Whisper large-v3 推迟到 MVP 流程跑通后再评估，届时通过切换 `transcriber.name` 配置即可启用，不需要改业务代码。

---

## 7. Design Considerations / 设计说明

### 7.1 极薄前端 + 重后端原则
- 小程序只做采集、上传、状态展示；任何"业务规则"（鉴权、签发、校验、转写、幂等）都不能放在小程序里。
- 小程序代码里**绝对不能**出现长期 AccessKey、任何业务密钥。

### 7.2 UI 极简
- 首页只有一个圆形录音按钮（开始 / 停止），二级页面是草稿确认态 + 上传列表。
- 默认状态 = 准备录音；任何"异常状态"（离线积压、上传失败堆积）用红色横条置顶提示。

### 7.3 状态机为权威
- 本地以 `manifest.json` + 文件 `.part` / `.tmp` / `.done` 为权威；不引入数据库（本期）。
- 任何时候出现冲突，都以"硬盘上实际有什么文件"为准，代码不能假设"我记得我做过 X"。

---

## 8. Technical Considerations / 技术约束与依赖

- **微信小程序限制**：单条录音目标 ≤ 10 分钟（与微信后台限制对齐）；`wx.uploadFile` 单文件大小有限制，超长录音必须前端分片（见 US-010）。
- **OSS 直传**：必须使用 STS 临时凭证 + V4 签名直传，不允许走 FC 中转上传（FC 内存 + 网络成本太高）。
- **转写方案（本期）**：**云端 API 优先**，由 US-001 (D) 注册的服务承担。Worker 进程本期仅承担"轮询 + 下载 + 调用 API + 落盘"角色，不依赖 GPU / 本地模型。
- **Worker 运行环境**：本期 Worker 不做模型推理，对 CPU / 内存 / GPU 都没有硬性要求；任何能跑 Python 3.11+ 的环境都可以（Linux 服务器 / 个人电脑 / Docker / 树莓派均可）。**本地 Whisper large-v3 推理推迟到下一阶段**，届时再评估部署环境（届时通过 `transcriber.name` 切换即可，不改业务代码）。
- **云端 API 选型倾向**：与现有阿里云资源同账号，倾向「**阿里云智能语音交互 NLS 录音文件极速版**」（与 OSS 同 region 调用免外网流量费 + 有免费额度）；备选「OpenAI Whisper API」「通义听悟」。最终选型在 US-001 (D) 时确认并写进 runbook。
- **音频格式**：统一保存为 MP3；微信小程序录音默认 AAC，需要在前端或后端转码——本期暂以前端 `wx.getRecorderManager({ format: 'mp3' })` 为准（部分机型可能 fallback，需在 US-007 真机阶段确认；若不支持，转码工作转到Worker"下载后转码"环节并新增一个 story）。
- **音频 sha256**：前端用 wasm-crypto-js 或类似库计算（不要尝试用纯 JS 在主线程算大文件，会卡 UI）。
- **依赖项**：
  - 小程序：`miniprogram-recorder-manager`（系统 API）、`wasm-crypto`（可选，用于前端 sha256 计算）
  - 后端 FC：`@alicloud/sts-sdk20150401`、`@alicloud/oss-client`
  - Worker（Python）：`oss2`、`pyyaml`、`pydantic`（manifest schema）、**云端 ASR SDK**（如 `alibabacloud-nls-python-sdk` 或 `openai`）；**本期不安装** `faster-whisper` / `whisper.cpp`
  - Worker（系统二进制，OQ-1 决议新增）：**`ffmpeg`** + **`ffprobe`**，用于 AAC → MP3 转码 + 格式检测。Worker 启动时校验可用性，缺失则启动失败并提示安装方式（macOS: `brew install ffmpeg`；Ubuntu/Debian: `apt install ffmpeg`；Docker 基础镜像内置）

---

## 9. Success Metrics / 成功指标

以下指标必须全部通过才算 MVP 验收完成。每条都对应 requirements_v5 第十章的某条验收。

| 指标 | 目标 | 对应原始验收编号 |
|---|---|---|
| 端到端成功率 | 100 条录音 → 100 条本地落盘，0 丢失 | R-01 |
| FC `/verify-upload` 通过率 | 真实路径下 verify 通过 ≥ 99% | R-02 |
| 本地缓存保留 | verify 通过后仍保留 ≥ 48 小时；verify 未通过永不自动删除 | R-03 |
| `.done` 缺失恢复率 | 删除 `.done` 后重启脚本，能自动补齐 100% | R-04 |
| 3 次失败转人工 | 100% 触发，红色提示明显 | R-05 |
| OSS 文件永不删除 | 1 周后 OSS 对象数 ≥ 本地数 | R-07 |
| 无任何长期 AK 在小程序 | 反编译搜索为 0 命中 | S-01 |
| STS 凭证有效期 | ≤ 15 分钟 | S-02 |
| STS 单 key 限制 | 反例（写其他 key）100% 被拒 | S-03 |
| 未授权 openid | 100% 被 FC 403 拒绝 | S-05 |
| 云端 API 1 分钟音频转写端到端耗时 | ≤ 60 秒（含上传 / 拉取） | P-01（本期替代版） |
| 本地 Whisper large-v3 1 分钟音频转写耗时 | ≤ 10 秒（下一阶段评估，不进本期） | P-01（原版，暂挂起） |
| FC P95 响应时间 | `/issue-credential` ≤ 1s，`/verify-upload` ≤ 1s | P-02 + P-03 |
| 轮询周期可配置 | 改配置后下次扫描立即生效 | P-04 |
| 5 种上传状态展示 | 全部能在真机上构造出来 | U-01 |
| 离线积压醒目提示 | 离线录音后顶部红色横条出现 | U-02 |
| 中断恢复提示 | 锁屏 / 来电 / 切后台后能弹出三选一提示 | U-03 |

---

## 10. Open Questions / 待澄清的问题

> **状态**：本期 PRD v1 起 7 个 OQ **全部已决议**（2026-05-26）。具体决策落到了对应 user stories 的 acceptance criteria 中；本节保留为决策索引，便于追溯。完整决策语境记录在附录 C。

| 编号 | 议题 | 决策 | 落到哪 |
|---|---|---|---|
| OQ-1 | 小程序录音 MP3 格式不支持时如何处理 | **能 MP3 就直出 MP3；不能则保持 AAC，由 Worker 下载后用 ffmpeg 转码** | US-007 / US-015 / US-019 manifest schema / Technical Considerations 依赖加 ffmpeg |
| OQ-2 | 前端是否算 sha256 | **保持现状：前端算 sha256**（卡顿如严重再退化为 size-only verify） | 无需改 PRD，已是默认行为（US-011） |
| OQ-3 | 是否提供单条 Fragment 强制重转 CLI | **要做，本期内提供** `python -m soniscope_worker retranscribe <id> --force`（顶层 `make retranscribe` 别名） | US-018 |
| OQ-4 | 长录音多 chunk 在上传列表如何展示 | **折叠卡片 + 每个 chunk 独立可重传**（不整段强制一起重传） | US-014 |
| OQ-5 | FC 是否对 expected_size 做上限校验 | **要加，上限 50 MB**（环境变量 `MAX_UPLOAD_BYTES` 可调） | US-003 (B) |
| OQ-6 | 选哪家云端语音转文字 API | **暂定阿里云智能语音交互 NLS 录音文件极速版**；执行 US-001 (E) 实测时若有调整需同步更新 PRD + runbook | US-001 (E) / Technical Considerations / US-017 |
| OQ-7 | NLS 拉 OSS URL vs Worker 直传 | **方案 A：传 OSS 签名 URL 让 NLS 自己拉**（更省流量）；不支持的 provider 降级到方案 B | US-017 |

> 后续如又冒出新的开放问题，按 `OQ-8 / OQ-9 ...` 顺延追加；不要静默改动已决议的 OQ。

---

## 附录 A · 实施顺序建议（不属于 PRD 主体，仅供参考）

按本 PRD user stories 编号自然实施即可，但建议关键里程碑：

1. **里程碑 M0（人工，唯一一次）**：US-001 完成 → 阿里云资源 + 微信小程序 + 云端 ASR + 测试素材 + Worker 环境 + 凭证全部就绪 → `make verify-prep` 全绿
2. **里程碑 M1（AI 编程）**：US-002 + US-003 + US-005 完成 → 项目骨架就绪 + 两个 FC 函数代码已部署到云端且联调通过；跑 `make typecheck` / `make lint` / `make test` / `make deploy-fc` / `make test-fc-live` 全绿
3. **里程碑 M2（AI 编程）**：US-007 ~ US-014 完成 → 小程序端完整完成"录音 → 上传 → verify"；故障注入开关可用
4. **里程碑 M3（AI 编程）**：US-015 ~ US-019 完成 → Worker 端完整完成"轮询 → 下载 → 调用云端 API 转写 → 落盘"（本期不部署本地模型）
5. **里程碑 M4（AI 编程 + 用户跑）**：§4 Feature 最终验收 AC 全部通过 → MVP 整体闭环验收完成；§4.1 自动验证脚本全绿 + §4.2 真机 checklist 全部打勾（100 条录音 + 中断 / 长录音 / 失败重试 / 安全反例 / 长期保留）
6. **下一阶段（不在本 PRD 内）**：用 `WhisperLocalTranscriber` 替换 `CloudSpeechTranscriber`，验证本地推理可行性 + 成本下降

> **关键约定**：从 M1 开始，**用户不再回阿里云 / 微信任何控制台**。所有验证步骤都通过 AI 提供的 `make` 命令完成；如果某个 AC 用户被要求"打开控制台"，那是 PRD 没对齐，请反馈。

---

## 附录 B · 验收清单（自检用）

实施过程中可对照下面清单逐项打勾：

- [ ] **M0（人工，必须先完成）**：US-001 全部 A~I 9 块的检查方法通过；`make verify-prep` 全绿；`docs/runbook/cloud-setup.md` 已登记
- [ ] **M1（AI）**：US-002 + US-003 + US-005 完成；`make typecheck` / `make lint` / `make test` / `make deploy-fc` / `make test-fc-live` 全绿
- [ ] **M2（AI + 真机）**：US-007 ~ US-014 完成；DevTools 模拟器 + 真机预览两侧均 verified；上传列表 5 种状态可通过故障注入开关构造出来
- [ ] **M3（AI + Worker 主机）**：US-015 ~ US-019 完成；`make test` 通过；`make simulate-worker-crash` 三种恢复场景均成功补齐
- [ ] **M4（AI + 真机 + Worker）**：§4 最终验收 AC 全部通过——§4.1 自动验证 `make` 脚本全绿（正常路径 / 崩溃恢复 / 显式重转 / 安全反例 / 无残留 / OSS 长期保留）+ §4.2 真机 checklist 全部打勾（100 条录音成功率 100% + 中断 / 长录音 / 失败重试）
- [ ] Success Metrics 表中 15 条全部达标
- [ ] Non-Goals 列出的 9 条本期都没有"偷偷"做进来（避免范围蔓延）
- [ ] Open Questions 7 条均已决议并落到对应 US 的 AC（决策详情见附录 C）
- [ ] **零控制台合规**：从 M1 开始没有出现过"打开 X 控制台手工 Y"的操作；如有，回到 PRD 调整对应 story

---

## 附录 C · Open Questions 决策溯源（2026-05-26）

本附录记录 PRD v1 中 7 个 Open Questions 的最终决策语境与影响范围，便于后续追溯"为什么这么做"。

### OQ-1：小程序录音 MP3 格式兼容

- **背景**：微信小程序 `wx.getRecorderManager().start({ format: 'mp3' })` 在部分安卓机型 / 旧版本会 fallback 到 AAC，且无法在前端透明转码。
- **候选**：(a) 前端用 WebAssembly 库做 AAC→MP3（增加电量与卡顿）；(b) 不转，由 Worker 下载后用 ffmpeg 转码；(c) 直接接受 AAC，本系统支持混合格式存储。
- **决策**：**(a) 优先；前端不支持时回退到 (b)**——即"能 MP3 就直出 MP3；不能就 AAC，由 Worker 下载后转码"。
- **理由**：前端转码会拖累电量与延迟，Worker 端 ffmpeg 转码毫秒级完成且不影响用户体验；不引入 wasm 库可减小小程序包体积。
- **影响**：
  - US-007（前端音频格式策略 + 真机机型实测）
  - US-015（Worker 端格式检测 + ffmpeg 转码 + 失败处理）
  - US-019（manifest schema 区分 `audio.sha256` 与 `upload.original_sha256`，新增 `audio.original_format`）
  - Technical Considerations（依赖列表新增 `ffmpeg` + `ffprobe`）
- **风险**：ffmpeg 转码失败时（损坏 AAC）需要明确兜底——已在 US-015 加 `inbox/failed/` 留档逻辑。

### OQ-2：前端 sha256 计算

- **背景**：小程序前端在低端机型上对 10MB MP3 算 sha256 可能卡顿。
- **决策**：**保持现状（前端算 sha256）**，回归测试时若发现严重卡顿再退化为 size-only verify。
- **理由**：sha256 是 FC verify 的关键信号；先按完整方案做，遇到具体性能瓶颈再优化。
- **影响**：US-011 / US-013（无需改动 PRD 主体）。
- **后置触发条件**：US-007 在低端 Android（如 4GB RAM 以下）真机预览时若出现明显卡顿（> 2s 阻塞 UI），则降级，并在 PRD 追加 OQ-8 记录退化决策。

### OQ-3：单条 Fragment 强制重转 CLI

- **背景**：仅靠改 `transcriber.params_version` 全局重转粒度太粗。
- **决策**：**本期内提供 `python -m soniscope_worker retranscribe <fragment_id> --force` CLI**（顶层 Makefile `make retranscribe FRAGMENT_ID=<id> ARGS=--force` 别名），支持 `--all-from <YYYY-MM-DD>` 批量。
- **理由**：单条调试 / 修复转写错误的高频需求，少加一个 100 行 CLI 子命令成本极低。
- **影响**：US-018。

### OQ-4：长录音 chunk 在上传列表的展示

- **背景**：一段 25 分钟录音切成 3 个 chunk 时，UI 上是"聚合显示一行"还是"分 3 行"，以及失败时是"整段一起重传"还是"分片各自重传"。
- **决策**：**折叠卡片聚合显示 + 每个 chunk 独立可重传**。
- **理由**：聚合卡片让用户视觉上仍感知为"一段录音"；独立重传按钮避免无谓地把已成功的 chunk 重新上传。
- **影响**：US-014（折叠 / 展开交互 + 聚合状态 + 每 chunk 独立按钮 + 顶部计数按单 chunk）。

### OQ-5：FC `/issue-credential` 上传大小上限

- **背景**：FC 接口暴露在公网，恶意调用可能要求签发大对象凭证，导致 Worker 后续被洪水下载。
- **决策**：**加 50 MB 上限**，环境变量 `MAX_UPLOAD_BYTES` 可调。
- **理由**：单条目标 ≤ 10 分钟约 10 MB；50 MB 留 5x 余量；超此阈值视为可疑。
- **影响**：US-003 (B)。

### OQ-6：云端语音转文字 API 选型

- **背景**：可选服务商较多（阿里云 NLS / 通义听悟 / OpenAI Whisper API / 火山引擎 ASR / 腾讯云 ASR）。
- **决策**：**先定阿里云智能语音交互 NLS 录音文件极速版**；执行 US-001 (E) 实测时如发现障碍可调整，但需同步更新 PRD + runbook。
- **理由**：与阿里云 OSS 同账号最省事；同 region 调用免外网流量；有免费额度可用；且支持传 OSS URL（与 OQ-7 决策 A 配套）。
- **影响**：US-001 (E) / Technical Considerations / US-017。

### OQ-7：NLS 拉 OSS URL vs Worker 直传

- **背景**：转写时是用 OSS 临时签名 URL 让 NLS 自己去拉（方案 A），还是 Worker 把 audio.mp3 重新上传给 NLS（方案 B）。
- **决策**：**默认方案 A**；不支持 URL 拉取的 provider（如 OpenAI Whisper API）降级到方案 B。
- **理由**：方案 A 省一次 Worker 上行流量；NLS 与 OSS 同 region 调用免外网流量；签名 URL 短期有效（1 小时）安全可控。
- **影响**：US-017（同时实现两个 mode + 自动切换）。
- **风险**：签名 URL 过期处理已在 US-017 AC 明确（NLS 排队超 50 分钟时重新签发）。

