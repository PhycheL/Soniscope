# SoniScope · 云端资源 & 运行环境登记表 (runbook)

> 本文件由 **US-001 人工准备** 阶段填写，**完成后进 git**。  

---

## 填写约定（必读）

1. **禁止**填入任何明文 AK / AccessKeySecret / AppSecret / Token / API Key。
   - 明文凭证必须存放在密码管理器（如 1Password / Bitwarden），本文只记录"保存位置"。
   - 自检命令：`grep -E 'LTAI|sk-|aliyun_ak|access_key_secret' docs/runbook/cloud-setup.md`，应**无匹配**。
2. 未填字段用 `<待填写>` 占位，便于 `grep` 查漏。
3. 每填好一项，把对应的 checkbox `[ ]` 改为 `[x]`。
4. 完成判据：全部 checkbox 为 `[x]`，且自检命令无敏感信息匹配。

---

## 元信息

- **填写人**：`<待填写>`（GitHub 用户名 / 内部 ID）
- **首次完成时间**：`<待填写>`（如 `2026-05-28`）
- **最近修订时间**：`<待填写>`
- **本期 MVP 范围**：录音 → OSS 备份 → Worker 拉取 → 云端 ASR 转写 → 本地落盘

---

## 1. 阿里云 OSS

> 对应 US-001 (A)。详细步骤见手册 §A。

- [ ] Bucket 名：`<待填写>`（PRD 默认 `soniscope-audio`，被占用可加后缀）
- [ ] 地域 (region)：`<待填写>`（PRD 默认 `cn-hangzhou`）
- [ ] Endpoint：`<待填写>`（PRD 默认 `oss-cn-hangzhou.aliyuncs.com`）
- [ ] 读写权限 ACL：`私有 private`
- [ ] 创建日期：`<待填写>`（如 `2026-05-28`）
- [ ] 阿里云主账号 UID：`<待填写>`（纯数字，右上角头像 → 安全设置可看；后面 RAM 角色 ARN 要用）
- [ ] 反例已验证（未鉴权 GET 返回 AccessDenied）：☐

**备注**：
```
<待填写：可记录创建过程中的特殊情况，如 Bucket 名冲突、跨账号迁移等>
```

---

## 2. 阿里云 RAM

> 对应 US-001 (B)。详细步骤见手册 §B。

### 2.1 子账号 soniscope-fc（供 FC AssumeRole）

- [ ] 登录名：`soniscope-fc`
- [ ] 用途：FC 函数 `issue-credential` 调用 STS 签发临时凭证
- [ ] 绑定系统策略：`AliyunSTSAssumeRoleAccess`（且仅此一条）
- [ ] AK 保存位置：`<待填写>`（如 `1Password vault: soniscope · item: ram-soniscope-fc`）

### 2.2 子账号 soniscope-local-reader（供 Worker 拉音频）

- [ ] 登录名：`soniscope-local-reader`
- [ ] 用途：Worker 进程从 OSS 下载音频
- [ ] 绑定自定义策略：`soniscope-bucket-readonly`（仅 GetObject / HeadObject / ListObjects 限 soniscope-audio）
- [ ] AK 保存位置：`<待填写>`（如 `1Password vault: soniscope · item: ram-local-reader`）

### 2.3 子账号 soniscope-asr（供调用 NLS API，可选独立或复用）

- [ ] 登录名：`<待填写>`（建议 `soniscope-asr`；若复用其他子账号请注明）
- [ ] 用途：调用阿里云智能语音交互 NLS 录音文件极速版
- [ ] 绑定策略：`<待填写>`（如 `AliyunNLSFullAccess`）
- [ ] AK 保存位置：`<待填写>`

### 2.4 角色 soniscope-uploader-role

- [ ] 角色名：`soniscope-uploader-role`
- [ ] **角色 ARN**：`<待填写>`（形如 `acs:ram::123456789:role/soniscope-uploader-role`）
- [ ] 信任主体：`acs:ram::<UID>:user/soniscope-fc`（精确到该子账号）
- [ ] 绑定权限策略：`soniscope-upload-template`（PutObject 限 `soniscope-audio/recordings/*`）
- [ ] 默认会话有效期：`<待填写>`（建议 ≤ 900 秒 / 15 分钟）

### 2.5 STS 反例验证记录

> US-001 (B-4) 已亲手跑过的反例（结果与预期一致后打勾，并记录日期）。

- [ ] 反例 1：越界 PutObject `recordings/evil.mp3` → AccessDenied ✓ 已验证 `<日期>`
- [ ] 反例 2：ListObjects → AccessDenied ✓ 已验证 `<日期>`
- [ ] 反例 3：GetObject `recordings/test.mp3` → AccessDenied ✓ 已验证 `<日期>`
- [ ] 反例 4：16 分钟后 PutObject → ExpiredToken ✓ 已验证 `<日期>`

---

## 3. 阿里云 函数计算 FC

> 对应 US-001 (C)。详细步骤见手册 §C。

### 3.1 服务 + 函数槽位

- [ ] 服务名：`soniscope-svc`
- [ ] 地域：`<待填写>`（必须与 OSS 同 region，默认 `cn-hangzhou`）
- [ ] 函数 1 名（kebab-case，作为 HTTP URL 路径）：`issue-credential`
- [ ] 函数 2 名：`verify-upload`
- [ ] 运行时：Python 3.11
- [ ] HTTP 触发器认证方式：`anonymous`（业务层 openid allowlist 兜底）

### 3.2 函数 HTTP 触发器 URL

> 这些 URL 是公网可访问的，**不属于敏感信息**，可入 git。但需要登记到小程序「服务器域名」白名单。

- [ ] `issue-credential` URL：`<待填写>`  
  （形如 `https://<account>.<region>.fcapp.run/2016-08-15/proxy/soniscope-svc/issue-credential/`）
- [ ] `verify-upload` URL：`<待填写>`
- [ ] curl 两个 URL 均返回 HTTP 200 + hello world：☐ 已验证

### 3.3 FC 环境变量清单（**仅列 key 名，不列 value**）

> 实际值在 FC 控制台 → 服务 `soniscope-svc` → 函数配置 → 环境变量中填入并脱敏显示。  
> **此处禁止写明文值。**

| Key | 来源 | 是否敏感 |
|---|---|---|
| `OSS_BUCKET` | §1 Bucket 名 | 否 |
| `OSS_REGION` | §1 region | 否 |
| `OSS_ENDPOINT` | §1 endpoint | 否 |
| `RAM_ROLE_ARN` | §2.4 角色 ARN | 否 |
| `ALIYUN_AK_ID` | §2.1 soniscope-fc AK ID | **是** |
| `ALIYUN_AK_SECRET` | §2.1 soniscope-fc AK Secret | **是** |
| `WX_APPID` | §4.1 小程序 AppID | 否 |
| `WX_APP_SECRET` | §4.1 小程序 AppSecret | **是** |
| `OPENID_ALLOWLIST` | §4.2 真机 openid（逗号分隔多值） | 否（轻敏感） |

- [ ] 9 个环境变量在 FC 控制台均已填入并脱敏显示
- [ ] `verify-upload` 函数也有同样 9 个环境变量（或服务级共享变量已生效）

---

## 4. 微信小程序

> 对应 US-001 (D)。详细步骤见手册 §D。

### 4.1 账号 / AppID

- [ ] 小程序名称：`<待填写>`（如 `日观声记` 或 `SoniScope`）
- [ ] AppID：`<待填写>`（形如 `wx1234567890abcdef`，**可入 git，非敏感**）
- [ ] AppSecret 保存位置：`<待填写>`（如 `1Password vault: soniscope · item: mp-wechat-app-secret`）
- [ ] 主体类型：`<待填写>`（个人 / 企业）

### 4.2 体验者 + 真机 openid

- [ ] 体验成员列表（仅记录微信昵称或代号，不记录手机号）：
  - `<待填写：成员 1>`
  - `<待填写：成员 2>`
- [ ] **本人真机 openid**（用作 FC `OPENID_ALLOWLIST`）：`<待填写>`（形如 `o6zAJs________________`，约 28 字符）

### 4.3 服务器域名白名单

- [ ] `request` 合法域名：`<待填写>`（应为 FC 域名，如 `https://<account>.<region>.fcapp.run`）
- [ ] `uploadFile` 合法域名：`<待填写>`（应为 OSS Bucket 域名，如 `https://soniscope-audio.oss-cn-hangzhou.aliyuncs.com`）

### 4.4 开发工具

- [ ] 微信开发者工具版本：`<待填写>`（如 `Stable Build 1.06.xxxx`）
- [ ] DevTools → 详情 → 本地设置：「不校验合法域名」已**取消**勾选

---

## 5. 云端 ASR 服务

> 对应 US-001 (E)。详细步骤见手册 §E。

### 5.1 服务商选型

- [ ] 服务商：`<待填写>`（默认 `阿里云智能语音交互 NLS 录音文件极速版`；若选备选请注明原因）
- [ ] 选型决策日期：`<待填写>`
- [ ] 选型理由备注（如换成备选）：
```
<待填写>
```

### 5.2 项目 / 接入点

- [ ] 项目名：`<待填写>`（默认 `soniscope-mvp`）
- [ ] AppKey：`<待填写>`（NLS 项目级标识，约 16 字符，**非 AccessKey，可入 git**）
- [ ] API endpoint：`<待填写>`（如 `nls-meta.cn-shanghai.aliyuncs.com` 或 region 对应值）
- [ ] 模型名 / 版本：`<待填写>`（如 `paraformer-v2`）
- [ ] 调用凭证保存位置：`<待填写>`（如 `1Password vault: soniscope · item: ram-soniscope-asr`）

### 5.3 免费额度 & 成本估算

- [ ] 免费额度（每月）：`<待填写>`（如 `每月 X 小时录音文件转写`）
- [ ] 当前用量查询页路径：`<待填写>`（如 智能语音交互控制台 → 资源中心 → 资源包）
- [ ] **月度成本估算**（按日均 30 分钟录音 × 30 天 = 15 小时/月）：
  - ASR 转写：`<待填写>`（如 `约 ¥X / 月，免费额度内 = ¥0`）
  - OSS 存储：`<待填写>`（如 `15h MP3 ≈ 360MB ≈ ¥0.05 / 月`）
  - OSS 流量：`<待填写>`（同 region 内网拉取免费）
  - FC 调用：`<待填写>`（每月 ≤ 100 次调用，几乎为 0）
  - **合计**：`<待填写>`

### 5.4 联调基线（用 sample-10s.mp3 跑出来的真实结果）

- [ ] 联调日期：`<待填写>`
- [ ] 联调命令 / 工具：`<待填写>`（如 `官方 demo` / `curl` / `阿里云 SDK 测试脚本`）
- [ ] 原音内容（口述了什么）：
```
<待填写：把当时录的话原文写在这里，便于比对>
```
- [ ] 转写结果（关键字段，**不要贴敏感 token / signature**）：
```json
{
  "task_id": "<填或脱敏>",
  "status": "SUCCESS",
  "result": {
    "text": "<待填写：完整转写文本>",
    "sentences": [
      {
        "begin_time": 0,
        "end_time": 3200,
        "text": "<待填写：第一句>"
      }
    ]
  }
}
```
- [ ] 主干文字与原音一致（允许标点 / 同音字差异）：☐ 通过

---

## 6. 测试基线音频素材

> 对应 US-001 (F)。详细步骤见手册 §F。  
> 文件位置：仓库内相对路径 `tests/fixtures/audio/`。

| 文件 | 用途 | 期望 duration | 期望 codec | sha256 |
|---|---|---|---|---|
| `sample-10s.mp3` | E 联调 + US-017 真实闭环 | ≈ 10s | mp3 | `<待填写>` |
| `sample-1min.mp3` | P-01 性能基线 + US-017 性能 | ≈ 60s | mp3 | `<待填写>` |
| `sample-25min.mp3` | US-010 长录音分片 + §4.2 闭环 | ≈ 1500s | mp3 | `<待填写>` |
| `sample-aac.aac` | OQ-1 / US-015 AAC 转码验证 | ≈ 10s | aac | `<待填写>` |

- [ ] `ls tests/fixtures/audio/` 能看到 4 个文件
- [ ] `shasum -a 256 tests/fixtures/audio/*.{mp3,aac}` 输出与上表一致
- [ ] `ffprobe sample-aac.aac` 显示 codec=aac（不是 mp3 假冒）
- [ ] 每个文件能播放、人声清晰

> 生成 sha256 的命令：
> ```
> shasum -a 256 tests/fixtures/audio/*.{mp3,aac}
> ```

---

## 7. Worker 运行环境

> 对应 US-001 (G)。详细步骤见手册 §G。

- [ ] 主机标识：`<待填写>`（如 `Mac Studio M2 Ultra · hostname=studio.local` 或 `阿里云 ECS · 172.16.x.y`）
- [ ] OS 版本：`<待填写>`（如 `macOS 26.5` / `Ubuntu 22.04 LTS`）
- [ ] Python 版本：`<待填写>`（≥ 3.11，跑 `python3 --version` 输出）
- [ ] 系统工具自检：☐ `git make curl ffmpeg ffprobe` 五条 `which` 均找到
- [ ] 工作目录环境变量：`SONISCOPE_HOME=<待填写>`（默认 `~/SoniScope/`）
- [ ] 工作目录可用磁盘空间：`<待填写>`（≥ 50GB，`df -h` 输出）
- [ ] 仓库 clone 路径：`<待填写>`（如 `~/ProjectCode/my_soniscope`）

> Worker 主机如未来切换（如从笔记本迁到 NAS），在本节追加历史记录而不是覆盖。

---

## 8. 凭证管理约定（红线说明）

本期 MVP 的凭证一律遵守以下规则：

1. **明文 AK / Secret / Token / AppSecret 不进 git 仓库**——本文件、所有源码、所有配置模板都不允许出现明文值。
2. **FC 端**：所有凭证走 FC **环境变量**注入。环境变量在控制台填入并脱敏显示；FC 函数代码通过 `os.environ[...]` 读取，**禁止**完整打印到日志（前后 4 位约定，AGENTS.md §"配置与敏感信息"）。
3. **Worker 端**：所有凭证写在 `$SONISCOPE_HOME/config.yaml`（默认 `~/SoniScope/config.yaml`）。该文件：
   - 权限 `chmod 600`（仅当前用户可读）
   - 路径默认在 `$SONISCOPE_HOME` 下，与代码仓库严格分离，**绝不在 repo 内**
   - 即使路径在 repo 内，也已被 `.gitignore` 覆盖
4. **小程序端**：源代码内**绝不**包含任何长期 AccessKey 或业务密钥；上传 OSS 用 FC 签发的 STS 临时凭证（精确到单 object key）。
5. **OSS 端**：Worker **绝不**调用 `DeleteObject`——OSS 文件永不删除（数据零丢失承诺）。
6. **凭证密码管理器**：统一保管位置 `<待填写>`（如 `1Password Team Vault: soniscope`），并记录每个 AK 对应的 item 名称（已分散在 §2 / §4 / §5）。

---

## 9. 自检清单（提交前跑一遍）

```bash
# 9.1 无明文 AK 泄漏
grep -E 'LTAI|sk-|aliyun_ak|access_key_secret|AppSecret\s*[:=]\s*[A-Za-z0-9]{8}' \
  docs/runbook/cloud-setup.md
# 期望：无匹配（exit code 1）

# 9.2 无未填字段（提交前应全部填掉）
grep -c '<待填写>' docs/runbook/cloud-setup.md
# 期望：0

# 9.3 所有 checkbox 已勾选
grep -c '^- \[ \]' docs/runbook/cloud-setup.md
# 期望：0

# 9.4 runbook 已被 git 跟踪
git ls-files docs/runbook/cloud-setup.md
# 期望：输出文件路径
```

- [ ] 9.1 通过（无明文敏感信息）
- [ ] 9.2 通过（无 `<待填写>` 残留）
- [ ] 9.3 通过（无 `[ ]` 未勾）
- [ ] 9.4 通过（已 git add）

---

## 10. 修订历史

| 日期 | 修订人 | 修订内容 |
|---|---|---|
| `<待填写>` | `<待填写>` | 初次创建（US-001 完成） |

---

> **US-001 验收完成判据**：本文件第 9 节自检全部通过 + `docs/runbook/us-001-manual.html` 上 61 个 checkbox 全部勾选。  
> 完成后即可进入 US-002（仓库骨架 + `make verify-prep` 脚本由 AI 实现）。
