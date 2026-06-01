# SoniScope · 云端资源 & 运行环境登记表 (runbook)

## 元信息

- **填写人**：`Bemied`
- **首次完成时间**：`2026-05-28`
- **最近修订时间**：`2026-05-30`
- **本期 MVP 范围**：录音 → OSS 备份 → Worker 拉取 → 云端 ASR 转写 → 本地落盘
- **实际使用 region**：`cn-beijing`（华北2 北京）。所有 endpoint / 环境变量 / 域名白名单都以北京为准。

---

## 1. 阿里云 OSS

-  Bucket 名：`soniscope-audio`
-  地域 (region)：`cn-beijing`（华北2 北京；本项目实际选用，PRD 默认建议 `cn-hangzhou`，已调整）
-  Endpoint：`oss-cn-beijing.aliyuncs.com`（公网；同 region 内网为 `oss-cn-beijing-internal.aliyuncs.com`）
-  读写权限 ACL：`私有 private`
-  创建日期：`2026-05-28`
-  阿里云主账号 UID：1633875501759333

---

## 2. 阿里云 RAM

### 2.1 子账号 soniscope-fc（供 FC AssumeRole）

-  登录名：`soniscope-fc`
-  用途：FC 函数 `issue-credential` 调用 STS 签发临时凭证
-  绑定系统策略：`AliyunSTSAssumeRoleAccess`（且仅此一条）
-  AK 保存位置：`1Password` 中 `阿里云 soniscope-fc 账户 RAM`

### 2.2 子账号 soniscope-local-reader（供 Worker 拉音频）

-  登录名：`soniscope-local-reader`
-  用途：Worker 进程从 OSS 下载音频
-  绑定自定义策略：`soniscope-bucket-readonly`
-  AK 保存位置：`1Password` 中 `阿里云 soniscope-local-reader 账户 RAM` 

### 2.3 子账号 soniscope-asr（供调用 NLS API，可选独立或复用）

-  登录名： `soniscope-asr`
-  用途：调用阿里云智能语音交互 NLS 录音文件极速版
-  绑定策略：`AliyunNLSFullAccess`
-  AK 保存位置：`1Password` 中 `阿里云 soniscope-asr 账户 RAM` 

### 2.4 角色 soniscope-uploader-role

-  角色名：`soniscope-uploader-role`
-  **角色 ARN**：`acs:ram::1633875501759333:role/soniscope-uploader-role`
-  信任主体：`acs:ram::1633875501759333:user/soniscope-fc`（精确到该子账号）
-  绑定权限策略：`soniscope-upload-template`（PutObject 限 `soniscope-audio/recordings/*`）
-  默认会话有效期：一小时

---

## 3. 阿里云 函数计算 FC 3.0

> ⚠ **FC 3.0 重要变更**：阿里云函数计算已升级到 FC 3.0，**取消了"服务"层级**，函数变成顶级实体。  
> 因此本节不再有"服务名"字段，**不需要也不应创建 `soniscope-svc` 服务**。  
> URL 格式从 FC 2.0 的 `/2016-08-15/proxy/<svc>/<fn>/` 变为 FC 3.0 的 `https://<url-id>.<region>.fcapp.run/`。

### 3.1 函数槽位

-  函数计算版本：**FC 3.0**（控制台顶部 banner 应显示「函数计算 FC 3.0」）
-  地域：`cn-beijing`（必须与 OSS 同 region，本项目实际选用 `cn-beijing`）
-  函数 1 名（kebab-case，会成为 HTTP URL 子域名前缀）：`issue-credential`
-  函数 2 名：`verify-upload`
-  函数类型：**Web 函数**（自动配置 HTTP 触发器；非「事件函数」）
-  运行时：Python 3.12（或 3.10 / 3.11，按当前 FC 3.0 支持列表）
-  规格：0.35 vCPU / 512 MB
-  HTTP 触发器认证方式：`无身份认证（anonymous）`（业务层 openid allowlist 兜底，禁止用 sig 签名认证）
-  公网访问 URL：已开启
-  请求方式：GET + POST

### 3.2 函数 HTTP 触发器 URL（FC 3.0 格式）

> 这些 URL 是公网可访问的，**不属于敏感信息**，可入 git。需要登记到小程序「服务器域名」白名单。  
> FC 3.0 每个函数有独立的 `<url-id>` 子域名，**两个函数 hostname 不同**，小程序白名单需各加一条。
>
> ⚠️ **勿改拼写**：`issue-credential` 函数的公网 URL 子域名是 `issue-ce**d**ential`（少一个 `r`，**不是** `issue-credential`）。这个 `<url-id>` 由 FC 系统分配、不可自定义，已在控制台核实就是此拼写。看起来像 typo，但**确实如此，任何工具/人/AI 都不要把它"修正"成 `issue-credential`**，否则 curl / 小程序 request 会指向不存在的 host。同步出现处：本文件 §3.2 / §4.3、`docs/tech-spec.md` §4.1、`docs/PRD_v1.md` US-001。

-  `issue-credential` 公网 URL：https://issue-cedential-ottfirocds.cn-beijing.fcapp.run
-  `verify-upload` 公网 URL：https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run

---

## 4. 微信小程序

### 4.1 账号 / AppID

-  小程序名称：` 日观声记`
-  AppID：`wx3f973c7297728b0c`
-  AppSecret 保存位置：`1Password` 中 `日观声记 小程序 AppSecret`
-  主体类型：`个人`

### 4.2 体验者 + 真机 openid

-  体验成员列表：
  - `老庄道人` openid：`o68Nm3RodhXQKA6_Z5VGiWC8LEVI`
  - `Bemied` openid：`o68Nm3Z5tK1Dr8QchPT7Ikqjre8Q`

### 4.3 服务器域名白名单

-  `request` 合法域名（**两条**，FC 3.0 每函数子域名独立，小程序白名单不支持通配符）：
   - `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run`
   - `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run`
-  `uploadFile` 合法域名：` https://soniscope-audio.oss-cn-beijing.aliyuncs.com`

### 4.4 开发工具

-  微信开发者工具版本：`Stable 2.01.2510290`

---

## 5. 云端 ASR 服务

### 5.1 服务商选型

-  服务商：[阿里云智能语音交互](https://nls-portal.console.aliyun.com/app/627576/soniscope?appkey=1k8tqkjQsq65wp2m)
-  选型决策日期：`2026-05-29`


### 5.2 项目 / 接入点

-  项目名：`soniscope`
-  AppKey：`1k8tqkjQsq65wp2m`
-  API endpoint：`cn-beijing`
-  模型名 / 版本：`中文普通话 （识音石 V1 - 端到端模型)`
-  调用凭证保存位置：`1Password` 中 `阿里云 soniscope-asr 账户 RAM` 

### 5.3 免费额度 & 成本估算

-  免费额度（每月）：无
-  当前用量查询页路径：https://nls-portal.console.aliyun.com/statistics
-  **月度成本估算**（按日均 30 分钟录音 × 30 天 = 15 小时/月，主格式 WAV）：
  - ASR 转写：2.5元/小时 × 15 小时 = 37.5 元，暂不购买资源包
  - OSS 存储：0.12 元/GB/月 × 约 1.6 GB（15 小时 WAV，16kHz 单声道 PCM）≈ 0.19 元/月，暂不购买资源包
  - OSS 流量：
    - 内/外网流入流量（数据上传到 OSS）：免费
    - 内网流出流量（通过同地域 ECS 使用内网 Endpoint，下载 OSS 的数据）：免费
    - 外网流出流量：00:00 - 08:00（闲时，5%）：0.25 元/GB；08:00 - 24:00（忙时，95%）：0.50 元/GB。Worker 经外网下载约 1.6 GB WAV/月 ≈ 0.78 元
  - FC 调用：约 1.00 元/月（每月 ≤ 100 次调用。因单次执行耗时极短，触发“单小时有调用最低计费 0.01 元”规则。若 100 次分布在不同小时，最高 1.00 元）
  - **合计**：约 39.47 元/月

### 5.4 联调基线（用 sample-20s.wav 跑出来的真实结果）

-  联调日期：`2026-05-29`
-  联调命令 / 工具：`./test/test_asr.py`
-  原音内容（口述了什么）：
```
人们也在可支配时间面前开始面临真正的选择，是这些选择造成了人与人最初的分野。
始终是持续的优先级的甄选与落实，造就了每个人看上去的样子。
```
-  转写结果：
```json
{
  "TaskId": "579da9f608e6455a9e2fd91d531253ec",
  "RequestId": "D208501F-D741-52CE-8141-32E230C18CB7",
  "StatusText": "SUCCESS",
  "BizDuration": 24021,
  "SolveTime": 1780035661040,
  "RequestTime": 1780035655314,
  "StatusCode": 21050000,
  "Result": {
    "Words": [
      {
        "Word": "人们",
        "EndTime": 1668,
        "BeginTime": 1020,
        "ChannelId": 0
      },
      {
        "Word": "也",
        "EndTime": 1994,
        "BeginTime": 1669,
        "ChannelId": 0
      },
      {
        "Word": "在",
        "EndTime": 2319,
        "BeginTime": 1994,
        "ChannelId": 0
      },
      {
        "Word": "可支配",
        "EndTime": 3294,
        "BeginTime": 2319,
        "ChannelId": 0
      },
      {
        "Word": "时间",
        "EndTime": 3942,
        "BeginTime": 3294,
        "ChannelId": 0
      },
      {
        "Word": "面前",
        "EndTime": 4593,
        "BeginTime": 3943,
        "ChannelId": 0
      },
      {
        "Word": "开始",
        "EndTime": 5243,
        "BeginTime": 4593,
        "ChannelId": 0
      },
      {
        "Word": "面临",
        "EndTime": 5891,
        "BeginTime": 5243,
        "ChannelId": 0
      },
      {
        "Word": "真正",
        "EndTime": 6542,
        "BeginTime": 5892,
        "ChannelId": 0
      },
      {
        "Word": "的",
        "EndTime": 6867,
        "BeginTime": 6542,
        "ChannelId": 0
      },
      {
        "Word": "选择",
        "EndTime": 7517,
        "BeginTime": 6867,
        "ChannelId": 0
      },
      {
        "Word": "这是",
        "EndTime": 8167,
        "BeginTime": 7517,
        "ChannelId": 0
      },
      {
        "Word": "这些",
        "EndTime": 8815,
        "BeginTime": 8167,
        "ChannelId": 0
      },
      {
        "Word": "选择",
        "EndTime": 9466,
        "BeginTime": 8816,
        "ChannelId": 0
      },
      {
        "Word": "造成",
        "EndTime": 10116,
        "BeginTime": 9466,
        "ChannelId": 0
      },
      {
        "Word": "了",
        "EndTime": 10441,
        "BeginTime": 10116,
        "ChannelId": 0
      },
      {
        "Word": "人与人",
        "EndTime": 11415,
        "BeginTime": 10441,
        "ChannelId": 0
      },
      {
        "Word": "最初的",
        "EndTime": 12390,
        "BeginTime": 11415,
        "ChannelId": 0
      },
      {
        "Word": "分野",
        "EndTime": 13040,
        "BeginTime": 12390,
        "ChannelId": 0
      },
      {
        "Word": "始终",
        "EndTime": 14148,
        "BeginTime": 13520,
        "ChannelId": 0
      },
      {
        "Word": "是",
        "EndTime": 14462,
        "BeginTime": 14148,
        "ChannelId": 0
      },
      {
        "Word": "持续的",
        "EndTime": 15404,
        "BeginTime": 14462,
        "ChannelId": 0
      },
      {
        "Word": "优先级",
        "EndTime": 16346,
        "BeginTime": 15404,
        "ChannelId": 0
      },
      {
        "Word": "的",
        "EndTime": 16660,
        "BeginTime": 16346,
        "ChannelId": 0
      },
      {
        "Word": "甄选",
        "EndTime": 17288,
        "BeginTime": 16660,
        "ChannelId": 0
      },
      {
        "Word": "与",
        "EndTime": 17602,
        "BeginTime": 17288,
        "ChannelId": 0
      },
      {
        "Word": "落实",
        "EndTime": 18230,
        "BeginTime": 17602,
        "ChannelId": 0
      },
      {
        "Word": "造就",
        "EndTime": 18859,
        "BeginTime": 18231,
        "ChannelId": 0
      },
      {
        "Word": "了",
        "EndTime": 19173,
        "BeginTime": 18859,
        "ChannelId": 0
      },
      {
        "Word": "每个人",
        "EndTime": 20115,
        "BeginTime": 19173,
        "ChannelId": 0
      },
      {
        "Word": "看上去",
        "EndTime": 21057,
        "BeginTime": 20115,
        "ChannelId": 0
      },
      {
        "Word": "的",
        "EndTime": 21371,
        "BeginTime": 21057,
        "ChannelId": 0
      },
      {
        "Word": "样子",
        "EndTime": 21999,
        "BeginTime": 21371,
        "ChannelId": 0
      }
    ],
    "Sentences": [
      {
        "EndTime": 13040,
        "SilenceDuration": 1,
        "SpeakerId": "1",
        "BeginTime": 1020,
        "Text": "人们也在可支配时间面前开始面临真正的选择，这是这些选择造成了人与人最初的分野。",
        "ChannelId": 0,
        "SpeechRate": 194,
        "EmotionValue": 6.0
      },
      {
        "EndTime": 21999,
        "SilenceDuration": 0,
        "SpeakerId": "1",
        "BeginTime": 13520,
        "Text": "始终是持续的优先级的甄选与落实，造就了每个人看上去的样子。",
        "ChannelId": 0,
        "SpeechRate": 205,
        "EmotionValue": 5.9
      }
    ]
  }
}
```
---

## 6. 测试基线音频素材

> **存储方式**：音频二进制**不进 git**（体积大），存于 OSS 私有 bucket `soniscope-audio` 的 `sample/` 前缀下（如 `sample/sample-20s.wav`）。
> 本地通过 `python3 scripts/fetch_test_fixtures.py` 按 sha256 拉取到 `tests/audio/`（清单见 `tests/audio/fixtures.manifest.json`）。
> 同目录的转写文本 `*.md` 与 `test_asr.py` 仍在 git 中跟踪。下方 sha256 为唯一权威校验源。

| 文件 | 用途 | 期望 duration | 期望 codec | sha256 |
|---|---|---|---|---|
| `sample-20s.wav` | E 联调 + US-017 真实闭环 | ≈ 20s | wav | `b07dee76f9cab9cf4ed9ba482e7a6287409180fc05e476365bd9a92f665b7828` |
| `sample-54s.wav` | P-01 性能基线 + US-017 性能 | ≈ 60s | wav | `9c454b212654f8948557123d9bc16d78ea6b2cf425484fca195b60fe9c7c9cde` |
| `sample-25min.wav` | US-010 长录音分片 + §4.2 闭环 | ≈ 1500s | wav | `34db505eb44f93fd092e868664979c155ebbbb6c0a61019dd840b30d276cdb27` |
| `sample-20s.m4a` | OQ-1 / US-015 m4a 转码验证 | ≈ 20s | m4a | `d3d2866128efe258ff95e841a16e7abb4d783fd37536692932a875f9fb5380fd` |

> 校验/拉取命令：
> ```
> python3 scripts/fetch_test_fixtures.py          # 拉取缺失或损坏的 fixture
> python3 scripts/fetch_test_fixtures.py --check  # 只校验本地，不下载
> shasum -a 256 tests/audio/*.{wav,m4a}           # 手动核对 sha256
> ```

---

## 7. Worker 运行环境

-  主机标识：`Mac Studio M4 Max`
-  OS 版本：`macOS 26.5`
-  Python 版本：`3.13.2`
-  系统工具自检：

```
/usr/local/bin/git
/usr/bin/make
/usr/bin/curl
/opt/homebrew/bin/ffmpeg
/opt/homebrew/bin/ffprobe
```



-  工作目录环境变量：`SONISCOPE_HOME=/Volumes/Data/software/SoniScope`
-  工作目录可用磁盘空间：`2.38TB`
-  仓库 clone 路径：`/Volumes/Data/ProjectCode/my_soniscope`

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
6. **凭证密码管理器**：统一保管位置 `1Password`，并记录每个 AK 对应的 item 名称（已分散在 §2 / §4 / §5）。

---

## 10. 修订历史

| 日期 | 修订人 | 修订内容 |
|---|---|---|
| `2026-05-30` | `Bemied` | 初次创建 |
| `2026-05-30` | `Bemied` | §5.3 成本估算按主格式 WAV 重算（存储/外网流出流量随 1.6 GB/月调整），合计 38.72 → 39.47 元/月 |
