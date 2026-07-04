# SoniScope / 日观声记 · 部署指南（Deployment Guide）

> 本指南是**从零到全链路上线**的可逐步执行操作手册，覆盖四层架构：OSS/RAM/STS（云存储与授权）、FC 3.0（无服务器 API）、Python Worker（后端转写）、微信小程序（前端）。
>
> **权威优先级**（冲突时按此顺序）：产品范围以 `docs/PRD_v1.md` 为准 → 技术实现 / schema / make target 以 `docs/tech-spec.md` 为准 → 真实云资源 / URL 以 `docs/runbook/cloud-setup.md` 为准 → 开发红线以 `AGENTS.md` 为准。本指南只提供"按什么顺序、跑哪条命令、看到什么算通过"的执行视角，不替代上述文档。
>
> 所有命令均在**仓库根目录**（`/Users/bemied/ProjectCode/my_soniscope`）执行；顶层 `Makefile` 是唯一命令入口，**无需 `cd` 进子目录**。文中 `<YYYY-MM-DD>` 一律替换为实际日期。

---

## 0. 部署总览

### 0.1 四层架构与部署顺序

| 顺序 | 层 | 组件 | 部署动作 | 章节 |
|---|---|---|---|---|
| ① | 云端存储 / 授权 | OSS + RAM + STS 角色 | 控制台人工创建（一次性） | §2 |
| ② | 云端 ASR | 阿里云智能语音交互 NLS | 控制台开通 + 拿 AppKey（一次性） | §2.6 |
| ③ | 云端无服务器 | FC 3.0 两个 Web 函数 | 控制台建函数槽位 + `make deploy-fc` | §4 |
| ④ | 后端 | Python Worker | `make install` + `config.yaml` + `make worker-run` | §5 |
| ⑤ | 前端 | 微信小程序 | 配域名白名单 + 上传体验版 / 发布 | §6 |

> **关键分界**：§2 / §6 中的"控制台人工准备"是**一次性**动作（对应 PRD US-001(H)）。完成后，从 §4 开始 **AI / 开发者不再回阿里云 / 微信控制台**——FC 部署、Worker 运行、回滚全部走 `make` 命令。

### 0.2 凭证管理红线（必须遵守）

来自 `AGENTS.md` 与 runbook §8，部署全程强制：

1. **明文 AK / Secret / Token / AppSecret 绝不进 git**——任何源码、配置模板、文档都不允许出现明文值；统一保管在 **1Password**。
2. **FC 端**凭证走 FC **环境变量**注入（控制台填入、脱敏显示），代码用 `os.environ[...]` 读取，日志只打印前后 4 位。
3. **Worker 端**凭证写在 `$SONISCOPE_HOME/config.yaml`（**repo 之外**），权限强制 `chmod 600`。
4. **小程序端**源码绝不含长期 AccessKey，上传 OSS 只用 FC 签发的单文件 STS 临时凭证。
5. **部署期凭证**（`ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET`）走本地 `.env`（已 gitignore）或 CI secret，与运行时凭证分开管理。

---

## 1. 前置条件

### 1.1 Worker 主机环境（本项目实际基线）

| 项 | 要求 / 实际值 |
|---|---|
| 主机 | Mac Studio M4 Max（参考基线；代码要求 Python 3.11+，无 GPU 要求） |
| OS | macOS 26.5 |
| Python | 3.13.2（代码要求 `>=3.11`） |
| 磁盘 | `$SONISCOPE_HOME` 所在盘可用 ≥ 50GB |
| 系统工具 | `git` / `make` / `curl` / `ffmpeg` / `ffprobe`（缺失则 Worker 启动失败并提示） |
| 包管理 | `uv`（管理 Python workspace） |

自检命令：

```bash
git --version && make --version && curl --version
ffmpeg -version && ffprobe -version
uv --version
python3 --version   # 需 ≥ 3.11
```

### 1.2 运行时目录与环境变量

Worker 运行时数据与代码仓库**严格分离**，由 `SONISCOPE_HOME` 指定。可在当前 shell 中导出：

```bash
export SONISCOPE_HOME=/path/to/SoniScope
```

也可以写入仓库根目录本地 `.env`（已被 `.gitignore` 忽略）：

```bash
SONISCOPE_HOME=/path/to/SoniScope
```

> `SONISCOPE_HOME` 必须显式存在；脚本不会兜底到固定目录。目录结构（`inbox/` / `fragments/` / `tmp/` / `config.yaml`）见 tech-spec §2.2；`make init-dirs` 只创建已存在工作目录下的子目录。

### 1.3 拉取代码

```bash
git clone <repo-url> /Users/bemied/ProjectCode/my_soniscope
cd /Users/bemied/ProjectCode/my_soniscope
```

---

## 2. 云端资源准备（一次性 · 阿里云 / NLS 控制台）

> 对应 PRD US-001(H)。所有登记信息以 `docs/runbook/cloud-setup.md` 为唯一权威来源；本节给出创建顺序，**具体名称 / region / ARN 以 runbook 已登记值为准**。region 全程用 `cn-beijing`（华北2 北京），FC 必须与 OSS 同 region。

### 2.1 OSS Bucket

- 创建私有 Bucket：`soniscope-audio`，region `cn-beijing`，ACL **私有 private**。
- Endpoint：公网 `oss-cn-beijing.aliyuncs.com`；同 region 内网 `oss-cn-beijing-internal.aliyuncs.com`。
- 主账号 UID：`1633875501759333`。

### 2.2 RAM 子账号（3 个）

| 子账号 | 用途 | 绑定策略 |
|---|---|---|
| `soniscope-fc` | FC 函数运行时：`issue-credential` 签发 STS；`verify-upload` 对 OSS 对象做 HeadObject 校验 | `AliyunSTSAssumeRoleAccess` + 自定义策略 `soniscope-fc-recordings-headonly` |
| `soniscope-local-reader` | Worker 从 OSS 下载音频（只读） | 自定义策略 `soniscope-bucket-readonly` |
| `soniscope-asr` | 调用 NLS ASR | `AliyunNLSFullAccess` |

每个子账号创建后生成 AK/Secret，**存入 1Password 对应 item**，不进 git。

### 2.3 RAM 角色 soniscope-uploader-role（STS 单文件授权核心）

- 角色名：`soniscope-uploader-role`
- ARN：`acs:ram::1633875501759333:role/soniscope-uploader-role`
- 信任主体：`acs:ram::1633875501759333:user/soniscope-fc`（精确到 FC 子账号）
- 绑定权限策略：`soniscope-upload-template`（`PutObject` 限 `soniscope-audio/recordings/*`）
- 默认会话有效期：1 小时

> FC 拿此角色 AssumeRole 后，再收窄为**单 object key** 的 15 分钟临时凭证签发给小程序（tech-spec §4.4）。

### 2.4 自定义权限策略

- `soniscope-bucket-readonly`：授予 `soniscope-local-reader` 对 `soniscope-audio` 的只读（`oss:GetObject` / `oss:ListObjects`；HeadObject 按 `oss:GetObject` 授权）。
- `soniscope-upload-template`：限定 `PutObject` 到 `soniscope-audio/recordings/*`。
- `soniscope-fc-recordings-headonly`：授予 `soniscope-fc` 对 `soniscope-audio/recordings/*` 的 `oss:GetObject`，用于 `verify-upload` 的 HeadObject 校验；不授予写权限。

### 2.5 测试基线音频（可选，验证用）

音频二进制不进 git，存于 OSS `sample/` 前缀。拉取到本地：

```bash
python3 scripts/fetch_test_fixtures.py          # 拉取缺失 / 损坏的 fixture
python3 scripts/fetch_test_fixtures.py --check  # 只校验，不下载
```

sha256 清单以 `tests/audio/fixtures.manifest.json` 与 runbook §6 为准。

### 2.6 云端 ASR（NLS）

- 服务商：阿里云智能语音交互，项目名 `soniscope`，endpoint `cn-beijing`。
- AppKey：`1k8tqkjQsq65wp2m`（**非** AccessKey，可入非敏感登记；调用凭证 AK 在 §2.2 `soniscope-asr`）。
- 模型：`中文普通话（识音石 V1 - 端到端模型)`，无免费额度。

---

## 3. 一键校验云端准备（进入部署前的门禁）

完成 §2 后、进入 FC / Worker 部署前，先装依赖并校验所有人工准备产物：

```bash
make install        # uv sync，安装 workspace 全部 Python 依赖
make verify-prep    # 一键校验 OSS / RAM / STS / FC / NLS / fixture / 环境
```

- `make verify-prep` **必须全绿**才继续。它验证 OSS 可读、STS 可签发、FC 槽位存在、NLS 可用、fixture 完整、系统工具齐备。
- 若报缺失，按输出提示补齐对应 §2 步骤或 §5.2 的 `config.yaml` 字段。

> `verify-prep` 依赖 Worker 的 `config.yaml`（§5.2）与部署期 `.env`（§4.1）中已注入的凭证；建议先完成 §4.1 与 §5.2 再跑本步。

---

## 4. 部署 FC 3.0 函数

### 4.1 部署期凭证（本地 `.env`）

FC 部署脚本会自动读取仓库根目录 `.env` 中的部署凭证（`fc_deploy.py`）。Worker 相关命令也会从同一个 `.env` 读取 `SONISCOPE_HOME`。如果当前 shell 已显式导出同名变量，shell 中的值优先，`.env` 不会覆盖它。在仓库根目录创建 `.env`（已被 `.gitignore` 覆盖）：

```bash
# .env（绝不进 git）
SONISCOPE_HOME=/path/to/SoniScope
ALIYUN_DEPLOY_AK_ID=<soniscope-fc-deploy 的 AK ID>
ALIYUN_DEPLOY_AK_SECRET=<soniscope-fc-deploy 的 AK Secret>
```

> Worker 的 OSS / ASR 明文 AK 仍只放 `$SONISCOPE_HOME/config.yaml`，不要放进仓库 `.env`。

> 缺失时 `make deploy-fc` 报错：`缺少部署凭证 ALIYUN_DEPLOY_AK_ID/ALIYUN_DEPLOY_AK_SECRET（tech-spec §6.4）`。

### 4.2 FC 函数槽位（一次性控制台准备）

FC 3.0 **无 service 层级**，两个顶级 Web 函数：

| 代码目录（snake_case） | 云端函数名（kebab-case） | 公网 URL |
|---|---|---|
| `apps/fc/issue_credential/` | `issue-credential` | `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run` |
| `apps/fc/verify_upload/` | `verify-upload` | `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run` |

> ⚠️ `issue-ce**d**ential`（少一个 `r`）是阿里云系统分配的真实 `<url-id>`，**任何人 / 工具 / AI 都不要"修正"拼写**，否则请求指向不存在的 host。

槽位配置（控制台建函数时设置一次）：

| 项 | 值 |
|---|---|
| FC 版本 | FC 3.0（控制台顶部应显示「函数计算 FC 3.0」） |
| 地域 | `cn-beijing`（必须与 OSS 同 region） |
| 函数类型 | **Web 函数**（自动配 HTTP 触发器，非事件函数） |
| 运行时 / 启动入口 | Web 函数槽位；当前线上启动命令按 `python3 app.py` 验证，部署包根目录必须包含 `app.py` |
| 监听端口 | `app.py` 优先读取 `FC_SERVER_PORT` / `PORT`，未设置时回退 `9000` |
| 规格 | 0.35 vCPU / 512 MB |
| HTTP 触发器认证 | **无身份认证 anonymous**（业务层 openid allowlist 兜底，禁用 sig 签名） |
| 请求方式 | GET + POST，公网访问开启 |

### 4.3 FC 运行时环境变量（控制台注入）

在 FC 控制台 → 每个函数的环境变量中注入（脱敏显示，不进 git）。变量语义的唯一权威定义见 tech-spec §4.0：

| 变量名 | 说明 | 示例 / 备注 |
|---|---|---|
| `OSS_BUCKET` | Bucket 名 | `soniscope-audio` |
| `OSS_REGION` | region | `cn-beijing` |
| `OSS_ENDPOINT` | OSS endpoint | `oss-cn-beijing.aliyuncs.com` |
| `RAM_ROLE_ARN` | STS AssumeRole 角色 ARN | `acs:ram::1633875501759333:role/soniscope-uploader-role` |
| `ALIYUN_AK_ID` | `soniscope-fc` 子账号 AK ID | 1Password |
| `ALIYUN_AK_SECRET` | `soniscope-fc` 子账号 AK Secret | 1Password |
| `WX_APPID` | 小程序 AppID | `wx3f973c7297728b0c` |
| `WX_APP_SECRET` | 小程序 AppSecret | 1Password |
| `OPENID_ALLOWLIST` | 允许访问的 openid（逗号分隔） | 单用户填 1 个 |
| `MAX_UPLOAD_BYTES` | 上传上限（可选） | 默认 `52428800`（50MB） |

> `deploy-fc` **只更新代码包**，不改环境变量 / 触发器 / 运行时规格 / 公网 URL。环境变量变更需在控制台手动进行。

### 4.4 部署命令

```bash
make deploy-fc FUNCTION=issue-credential   # 打包 + 备份 + 部署单个函数
make deploy-fc FUNCTION=verify-upload
make deploy-fc                             # 不传 FUNCTION 时部署两个函数
```

`FUNCTION=` 参数统一用**云端函数名（kebab-case）**；部署脚本负责映射到 snake_case 代码目录。

部署过程产物：

| 产物 | 路径 |
|---|---|
| 打包暂存 + zip | `build/fc/<function_name>/` + `build/fc/<function_name>.zip` |
| Custom Runtime 入口 | `apps/fc/shared/app.py` 复制到每个函数包根目录 `app.py` |
| 部署前备份（代码 + 环境变量**名**快照） | `build/fc/backup/<YYYYMMDD-HHMMSS>/<function_name>.zip` |
| 部署日志（函数名 / zip sha256 / 耗时 / curl 存活验证） | `build/fc/logs/deploy-<YYYYMMDD-HHMMSS>.log`；HTTP 2xx 才算存活通过 |

### 4.5 部署后云端联调（正例 + 反例）

```bash
make test-fc-live       # issue-credential 云端联调（正例签发 + 越权/超限反例）
make test-verify-upload # verify-upload 云端闭环（verified / OBJECT_NOT_FOUND / SIZE_MISMATCH）
```

可选参数（用真实 wx.login code 时）见 Makefile：`CODE=` / `CODE_NOT_ALLOWED=` / `SIZE_CODE=` / `VERIFIED_CODE=` 等。

### 4.6 回滚与日志

```bash
make rollback-fc FUNCTION=issue-credential  # 从最新备份恢复指定函数
make fc-logs FUNCTION=verify-upload         # 拉取近 1 小时 FC 日志（SLS）
```

---

## 5. 部署 Python Worker

### 5.1 安装依赖 + 初始化目录

```bash
make install     # uv sync
make init-dirs   # 读取 SONISCOPE_HOME，在已存在工作目录下创建 inbox/ inbox/failed/ fragments/ tmp/
```

### 5.2 生成并填写运行时配置 config.yaml

用脚本从 runbook 自动抽取非敏感值生成模板，敏感字段留占位符手工填：

```bash
scripts/gen_worker_config.sh          # 读取 SONISCOPE_HOME，生成 $SONISCOPE_HOME/config.yaml（已存在则拒绝覆盖）
scripts/gen_worker_config.sh --force  # 强制重新生成（会清掉已填凭证）
```

脚本会：写到 `$SONISCOPE_HOME/config.yaml`（repo 之外）→ 生成后立即 `chmod 600` → 列出仍需手工填写的字段。

**需手工填写的敏感字段**（从 1Password 取，runbook 不含明文）：

- `oss.access_key_id` / `oss.access_key_secret` —— §2.2 `soniscope-local-reader` 只读 AK
- `transcriber.access_key_id` / `transcriber.access_key_secret` —— §2.2 `soniscope-asr` AK

配置 Schema（tech-spec §2.3）关键项：

```yaml
oss:
  endpoint: oss-cn-beijing.aliyuncs.com
  bucket: soniscope-audio
  access_key_id: <soniscope-local-reader AK ID>
  access_key_secret: <soniscope-local-reader AK Secret>
poll:
  interval_seconds: 60
transcriber:
  name: cloud-speech            # 工厂选择：cloud-speech | whisper-local
  provider: aliyun-nls
  model: "中文普通话（识音石 V1 - 端到端模型)"
  params_version: v1
  api_endpoint: cn-beijing
  appkey: 1k8tqkjQsq65wp2m       # NLS AppKey（非 AccessKey）
  access_key_id: <soniscope-asr AK ID>
  access_key_secret: <soniscope-asr AK Secret>
  upload_mode: oss-url           # oss-url（首选）| direct（降级）
  local:
    enabled: false
```

### 5.3 校验配置

```bash
scripts/gen_worker_config.sh --check   # 校验权限 600 + 无未填占位符
make check-config                      # 读 config.yaml → 校验必填字段 → 打印脱敏摘要 → 检查 600 权限
```

- 权限**必须** 600，否则 `check-config` 警告；修复：`chmod 600 "$SONISCOPE_HOME/config.yaml"`。
- 敏感字段（`access_key_secret` / `appkey`）在日志中只显示前后 4 位。

### 5.4 启动 Worker

```bash
make worker-run   # 启动主轮询：轮询 OSS → 下载 → 标准化 WAV → 转写 → 落盘 → 写 .done
```

Worker 启动时自动做三段式崩溃恢复扫描（tech-spec §3.6）：清理 `inbox/` 残留 `.part`/`.wav.tmp`、清理 `tmp/` 残留 `.transcript.json.tmp`、扫描 `fragments/` 判定未完成条目续跑。以 `.done` 标记为唯一完成态权威。

> 生产常驻建议用 `launchd`（macOS）或 `nohup make worker-run &` 守护；本期 MVP 手动 `make worker-run` 即可。

### 5.5 本地质量门禁（部署前建议全绿）

```bash
make typecheck   # mypy strict
make lint        # ruff（apps/）+ 小程序静态检查
make test        # pytest 单元测试（mock 云端依赖）
```

---

## 6. 部署微信小程序

### 6.1 账号与开发工具

| 项 | 值 |
|---|---|
| 小程序名称 | 日观声记 |
| AppID | `wx3f973c7297728b0c` |
| 主体类型 | 个人 |
| AppSecret | 1Password（同时注入 FC `WX_APP_SECRET`，§4.3） |
| 开发者工具 | 微信开发者工具 Stable 2.01.2510290 |

### 6.2 服务器域名白名单（必须在小程序管理后台配置）

FC 3.0 每函数子域名独立，白名单**不支持通配符**，需逐条添加：

- `request` 合法域名（**两条**）：
  - `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run`
  - `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run`
- `uploadFile` 合法域名（**一条**）：
  - `https://soniscope-audio.oss-cn-beijing.aliyuncs.com`

> 这些 URL 是公网可访问、非敏感信息，可入 git。前端常量 `CHUNK_MAX_DURATION_SECONDS = 600`（10 分钟分片阈值）定义在小程序配置中，如需调整改常量后重新发布。

### 6.3 开发者工具打开与配置

1. 微信开发者工具导入 `apps/miniprogram/` 目录，AppID 填 `wx3f973c7297728b0c`。
2. 确认 `apps/miniprogram/config.js` 中的 FC / OSS URL 与 §6.2 一致。
3. 在 DevTools 中先用模拟器 + 真机预览走通"录音 → 上传 → verify"，确认 verified。

### 6.4 体验版 / 发布

1. DevTools 点「上传」→ 微信管理后台「版本管理」设为体验版。
2. 将真机 openid 加入 FC `OPENID_ALLOWLIST`（§4.3）与小程序「体验成员」列表。
3. 真机微信打开体验版验证全链路 verified 后，提交审核 → 发布正式版。

> 体验成员 openid 登记见 runbook §4.2；`OPENID_ALLOWLIST` 与体验成员是两套授权，需同时包含目标用户。

---

## 7. 部署后端到端验收

完成四层部署后，按 `docs/runbook/mvp-acceptance.md` 做最终验收（全真实环境，不允许 mock）。核心自动化命令：

```bash
# 正常路径：100 条真机录音落盘后
make list-oss-objects DATE=<YYYY-MM-DD>              # OSS 对象计数 = 100
make verify-e2e-integrity DATE=<YYYY-MM-DD> EXPECTED=100  # 五产物齐全
make verify-e2e-sha256 DATE=<YYYY-MM-DD>            # sha256 一致性（tech-spec §3.3）
make verify-e2e-fields DATE=<YYYY-MM-DD>            # verified_at / completed_at 非空
make verify-no-stale                                # 无中间态残留

# 异常路径（自包含，AI/CI 可跑）
make test-e2e-crash-recovery   # 崩溃恢复
make test-e2e-retranscribe     # 显式重转（params_version 升级）
make test-e2e-security         # 鉴权 + STS 越权反例

# 长期保留复验（1 周后）
make verify-oss-retention      # OSS 对象数 ≥ 本地 + 无 DeleteObject
```

完整验收判定矩阵（人工 + 自动 12 项）见 `docs/runbook/mvp-acceptance.md` §8。

---

## 8. 运维速查

### 8.1 常用命令

| 场景 | 命令 |
|---|---|
| 重新部署单个 FC 函数 | `make deploy-fc FUNCTION=<name>` |
| 回滚 FC 函数 | `make rollback-fc FUNCTION=<name>` |
| 查 FC 近 1 小时日志 | `make fc-logs FUNCTION=<name>` |
| 启动 Worker | `make worker-run` |
| 校验配置 | `make check-config` |
| 单条重转 | `make retranscribe FRAGMENT_ID=<id>` |
| 批量升级重转 | `make retranscribe ARGS="--all-from <date> --upgrade"` |
| 列出某日 OSS 对象 | `make list-oss-objects DATE=<YYYY-MM-DD>` |
| 查单个 OSS 对象详情 | `make show-oss-object FRAGMENT_ID=<id>` |

### 8.2 显式重转 CLI（tech-spec §3.7）

```bash
python -m soniscope_worker retranscribe <fragment_id> [--all-from <YYYY-MM-DD>] [--upgrade] [--force]
```

| flag | 行为 |
|---|---|
| 无 flag | `.done` 存在则提示"已完成，用 --force 或 --upgrade" |
| `--upgrade` | 仅重转 model / params_version 与当前配置不同的 Fragment |
| `--force` | 忽略一切判断，直接重转 |
| `--all-from <date>` | 按目录批扫描逐条重转，失败继续并汇总 |

普通轮询以 `.done` 为唯一幂等判据，**不会**因配置变化自动重转已完成条目。

### 8.3 成本参考（runbook §5.3）

| 项 | 月成本 |
|---|---|
| FC 调用 | ≈ ¥1.00 |
| STS | ¥0（免费） |
| OSS 存储（约 1.6GB/月） | ≈ ¥0.19 |
| OSS 外网流出（约 1.6GB/月） | ≈ ¥0.78 |
| 云端 ASR（15 小时/月，无免费额度） | ≈ ¥37.50 |
| **合计** | **≈ ¥39.47/月** |

---

## 9. 常见故障排查

| 现象 | 优先排查 |
|---|---|
| `make deploy-fc` 报缺少部署凭证 | 仓库根目录 `.env` 缺 `ALIYUN_DEPLOY_AK_ID/SECRET`，或当前 shell 覆盖了空值（§4.1） |
| `curl` FC URL 返回 `python3: can't open file '/code/app.py'` | 线上仍是旧代码包；重新执行 `make deploy-fc`，确认部署包根目录包含 `app.py` |
| `make verify-prep` 不全绿 | 按输出定位 OSS/RAM/STS/FC/NLS/fixture 哪项缺失，回 §2 补齐 |
| `make check-config` 权限告警 | `chmod 600 "$SONISCOPE_HOME/config.yaml"` |
| Worker 启动即失败 | `ffmpeg`/`ffprobe` 缺失或 `SONISCOPE_HOME` 磁盘 < 50GB（§1.1） |
| 小程序 request 失败 | 域名白名单未加两条 FC URL；核对 `issue-cedential` 拼写（少一个 r，勿改） |
| `test-e2e-security` 未返回 403 | 检查 FC `OPENID_ALLOWLIST` 与测试 code |
| `verify-e2e-integrity` 报缺产物 | Worker 是否在运行；`make verify-no-stale` 看是否卡中间态 |
| `verify-e2e-sha256` 不一致 | 区分 WAV 直通（sha256 相等）与非 WAV 转码（可不同）两类规则（tech-spec §3.3） |
| `verify-oss-retention` 失败 | 确认 Worker 业务路径无 `DeleteObject`；区分测试用 `oss-delete-obj` 的人为删除 |

> 所有 `make` 命令失败时输出具体 object key / 路径 / 配置项与复现命令，且不打印任何 AK Secret 明文。

---

## 附录 A：部署检查清单

**一次性云端准备（§2）**
- [ ] OSS Bucket `soniscope-audio`（cn-beijing，私有）
- [ ] RAM 子账号 3 个 + 角色 `soniscope-uploader-role` + 两条自定义策略
- [ ] NLS 项目 `soniscope` 开通，AppKey 已登记
- [ ] AK/Secret 全部存入 1Password

**FC 部署（§4）**
- [ ] 仓库根目录 `.env` 已写入部署凭证，且被 `.gitignore` 忽略
- [ ] 两个 FC Web 函数槽位建好，运行时环境变量注入
- [ ] `make deploy-fc` 两函数成功
- [ ] `make test-fc-live` / `make test-verify-upload` 通过

**Worker 部署（§5）**
- [ ] `make install` + `make init-dirs`
- [ ] `config.yaml` 生成、填写敏感字段、`chmod 600`
- [ ] `make check-config` 通过
- [ ] `make worker-run` 正常轮询

**小程序（§6）**
- [ ] 域名白名单三条已配
- [ ] 真机 openid 加入 `OPENID_ALLOWLIST` + 体验成员
- [ ] 体验版真机全链路 verified

**验收（§7）**
- [ ] `make verify-prep` 全绿
- [ ] 端到端 §7 自动脚本全通过
- [ ] `docs/runbook/mvp-acceptance.md` §8 判定矩阵全打勾
