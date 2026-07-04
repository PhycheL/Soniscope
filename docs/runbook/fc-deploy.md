# SoniScope FC 部署 runbook

最近修订：2026-07-03

本文用于把仓库中的 FC 代码部署到阿里云 FC 3.0 的两个现有函数槽位：

- `issue-credential`
- `verify-upload`

本文不保存任何明文 AccessKey、Secret、Token、AppSecret。所有真实密钥只放在 1Password、本地 `.env`、FC 控制台环境变量或 `$SONISCOPE_HOME/config.yaml`。

---

## 0. 按这个顺序操作

如果你只是想完成部署，按下面顺序做：

1. 在 RAM 控制台创建部署用户 `soniscope-fc-deploy`。
2. 给 `soniscope-fc-deploy` 授权，让它能更新 FC 代码。
3. 给已有运行时用户 `soniscope-fc` 补 OSS HeadObject 所需权限。
4. 在两个 FC 函数里填写运行时环境变量。
5. 在本地仓库根目录创建 `.env`，填入 `soniscope-fc-deploy` 的 AK。
6. 执行 `make deploy-fc`。

最容易混淆的一点：`soniscope-fc-deploy` 是**本地部署代码用**，`soniscope-fc` 是**线上函数运行时用**。两个账号都可能有 AK，但放的位置不同，权限也不同。

---

## 1. 先分清现有 RAM 与凭证

本项目里有多组阿里云 ID / Secret。部署前先确认每组凭证用途，不要混用。

| 名称 | 放在哪里 | 用途 | 应该使用哪个账号 |
|---|---|---|---|
| `ALIYUN_AK_ID` / `ALIYUN_AK_SECRET` | 阿里云 FC 控制台环境变量 | FC 函数运行时调用 STS / OSS HeadObject | `soniscope-fc` |
| `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET` | 仓库根目录本地 `.env` | 本地 `make deploy-fc` 调阿里云 FC OpenAPI 更新函数代码 | 推荐新建 `soniscope-fc-deploy` |
| `oss.access_key_id` / `oss.access_key_secret` | `$SONISCOPE_HOME/config.yaml` | Worker 轮询、读取、下载 OSS 音频 | `soniscope-local-reader` |
| `transcriber.access_key_id` / `transcriber.access_key_secret` | `$SONISCOPE_HOME/config.yaml` | Worker 调阿里云 NLS ASR | `soniscope-asr` |

关键区别：

- `ALIYUN_AK_ID` 是**函数运行时凭证**，填在 FC 控制台。
- `ALIYUN_DEPLOY_AK_ID` 是**本地部署凭证**，填在仓库根目录 `.env`。
- 微信 `WX_APP_SECRET` 不是阿里云 AK，不能用于 `.env`。
- STS 临时凭证不是长期部署凭证，不能用于 `.env`。

### 1.1 已有三个 RAM 的职责

`us-001-manual.html` 里创建的三个 RAM 用户是运行链路账号，不是部署账号。

| RAM 用户 | 主要使用方 | 凭证保存位置 | 应有权限边界 | 说明 |
|---|---|---|---|---|
| `soniscope-fc` | 阿里云 FC 运行时 | FC 控制台环境变量 `ALIYUN_AK_ID` / `ALIYUN_AK_SECRET` | 调 STS AssumeRole；对 `soniscope-audio/recordings/*` 做 `oss:GetObject` 以支持 HeadObject | `issue-credential` 用它向 `soniscope-uploader-role` AssumeRole 签发单 object key STS；`verify-upload` 用它确认对象是否存在和大小是否一致。 |
| `soniscope-local-reader` | 本机 Python Worker | `$SONISCOPE_HOME/config.yaml` 的 `oss.*` | 只读 OSS：List / Head / Get 目标音频对象 | Worker 用它轮询 OSS、下载音频、读取对象元数据。它不应该能改 FC 代码，也不应该拥有 OSS 写权限。 |
| `soniscope-asr` | 本机 Python Worker | `$SONISCOPE_HOME/config.yaml` 的 `transcriber.*` | 调阿里云 NLS ASR | Worker 用它提交云端 ASR 转写任务。它和 FC、OSS 上传链路无关。 |

运行时账号的原则是：谁在运行时需要什么能力，就只给那部分能力。FC 运行时、Worker 读取 OSS、Worker 调 ASR 是三个不同风险面，所以拆成三个 RAM。

---

## 2. 创建部署专用 RAM 用户

如果还没有部署专用账号，建议在 RAM 控制台新建：

```text
soniscope-fc-deploy
```

创建要求：

- 访问方式：只勾选 `OpenAPI 调用访问`
- 不开启控制台登录
- AccessKey ID / AccessKey Secret 立即保存到密码管理器
- 不写入 git，不写入 runbook

### 2.1 控制台操作：创建 `soniscope-fc-deploy`

1. 打开阿里云控制台。
2. 进入 `访问控制 RAM`。
3. 左侧进入 `身份管理 -> 用户`。
4. 点击 `创建用户`。
5. 用户名填写：

   ```text
   soniscope-fc-deploy
   ```

6. 访问方式只勾选：

   ```text
   OpenAPI 调用访问
   ```

7. 不要勾选控制台登录。
8. 创建后立即复制 `AccessKey ID` 和 `AccessKey Secret`。
9. 保存到 1Password，建议条目名：

   ```text
   阿里云 soniscope-fc-deploy 账户 RAM
   ```

10. 关闭页面后 Secret 无法再次查看。如果没保存，只能删除这个 AccessKey 后重新创建。

### 2.2 给 `soniscope-fc-deploy` 授权

部署脚本实际会调用这些 FC API：

| 脚本动作 | 代码位置 | 需要的能力 |
|---|---|---|
| 部署前下载旧代码备份 | `client.get_function_code(function)` | 获取函数代码 |
| 读取环境变量名快照 | `client.get_function(function)` | 读取函数配置 |
| 上传新代码包 | `client.update_function(function, req)` | 更新函数代码 |

首次部署推荐先用系统策略：

```text
AliyunFCFullAccess
```

控制台操作：

1. RAM 控制台进入 `身份管理 -> 用户`。
2. 点开 `soniscope-fc-deploy`。
3. 进入 `权限管理`。
4. 点击 `新增授权`。
5. 授权主体确认是 `soniscope-fc-deploy`。
6. 策略类型选择 `系统策略`。
7. 搜索并勾选：

   ```text
   AliyunFCFullAccess
   ```

8. 点击确认授权。

这一步会给部署账号完整 FC 管理能力。它不是最终最小权限，但最适合首次部署排除权限干扰。首次部署成功后，再收紧成下面的自定义策略。

收紧版本的自定义策略建议命名为：

```text
soniscope-fc-deploy-code-only
```

策略内容：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "fc:GetFunction",
        "fc:GetFunctionCode",
        "fc:UpdateFunction"
      ],
      "Resource": "*"
    }
  ]
}
```

收紧步骤：

1. RAM 控制台进入 `权限管理 -> 权限策略`。
2. 点击 `创建权限策略`。
3. 选择 `脚本编辑`。
4. 粘贴上面的 JSON。
5. 保存为 `soniscope-fc-deploy-code-only`。
6. 给 `soniscope-fc-deploy` 新增授权，选择这个自定义策略。
7. 用它跑一次 `make deploy-fc FUNCTION=issue-credential`。
8. 如果部署通过，再移除 `AliyunFCFullAccess`。

说明：上面自定义策略把 `Resource` 写成 `*`，是为了避免 FC 3.0 控制台不同资源 ARN 写法导致首次收紧失败。确认部署链路稳定后，可以再用阿里云 RAM 权限助手把资源范围收敛到 `issue-credential` 和 `verify-upload` 两个函数。

### 2.3 把部署 AK 填到本地 `.env`

这个账号专门用于仓库根目录 `.env`：

```bash
ALIYUN_DEPLOY_AK_ID=<soniscope-fc-deploy 的 AK ID>
ALIYUN_DEPLOY_AK_SECRET=<soniscope-fc-deploy 的 AK Secret>
```

实施建议：

1. 为了尽快部署，可先给 `soniscope-fc-deploy` 使用 FC 部署所需的较宽权限完成首次上线。
2. 首次部署跑通后，再收敛为只允许读取函数、获取函数代码、更新函数代码的最小权限策略。
3. 不推荐长期用主账号 AK。
4. 不推荐复用 `soniscope-local-reader` 或 `soniscope-asr`，它们职责不对。

### 2.4 为什么不直接复用现有 RAM

不复用的核心原因是权限边界。部署账号需要“改 FC 代码”的能力，而现有三个账号分别属于运行时、OSS 读取、ASR 调用。把部署权限加到其中任意一个账号，都会扩大凭证泄漏后的影响范围。

具体风险：

- 不复用 `soniscope-fc`：它是 FC 运行时账号，长期放在两个函数环境变量里。如果它同时拥有更新 FC 代码的能力，一旦函数运行环境、日志配置或依赖链路出问题，攻击面会从“签发 STS / HeadObject”扩大到“可替换线上函数代码”。运行时账号应保持为业务运行能力，不承担发布能力。
- 不复用 `soniscope-local-reader`：它放在 Worker 主机的 `$SONISCOPE_HOME/config.yaml`，Worker 进程会长期读取。它的职责是只读 OSS 音频。如果给它 FC 部署权限，Worker 主机或配置文件泄漏就会变成云端函数代码可被篡改。
- 不复用 `soniscope-asr`：它只用于调用 NLS ASR。ASR 凭证不需要 OSS 管理权，也不需要 FC 代码发布权。把部署权限加给它会让一个转写服务账号变成云端控制账号。

单独创建 `soniscope-fc-deploy` 的好处：

- 最小权限更清晰：只给“读取函数 / 获取函数代码 / 更新函数代码”等部署所需能力。
- 审计更清楚：阿里云操作日志里，代码发布动作来自 `soniscope-fc-deploy`，运行时调用来自 `soniscope-fc`。
- 轮换更安全：怀疑部署凭证泄漏时，只轮换 `soniscope-fc-deploy`，不影响线上函数运行、Worker 下载和 ASR 转写。
- 回收更简单：部署完成后可以禁用、删除或进一步收紧 `soniscope-fc-deploy`，不影响业务链路。

如果暂时不想新建 `soniscope-fc-deploy`，可以短期复用 `soniscope-fc` 的 AK 做 `ALIYUN_DEPLOY_AK_ID`，只用于首轮验证或排障。验证完成后应把 FC 部署权限从 `soniscope-fc` 收回，改用单独部署账号。

---

## 3. 给运行时 RAM 和两个 FC 函数配置权限

这一节配置的是线上运行时，不是本地部署。要处理两件事：

1. 给已有 RAM 用户 `soniscope-fc` 补 `verify-upload` 需要的 OSS HeadObject 权限。
2. 在两个 FC 函数中填写运行时环境变量。

### 3.1 给 `soniscope-fc` 补 OSS HeadObject 权限

`soniscope-fc` 已经用于 `issue-credential` 调 STS AssumeRole。现在 `verify-upload` 还会用它对 OSS 对象做 HeadObject，确认对象是否存在以及大小是否一致。

在 OSS RAM 策略里，HeadObject 按 `oss:GetObject` 授权。创建一个自定义策略：

```text
soniscope-fc-recordings-headonly
```

策略内容：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject"
      ],
      "Resource": [
        "acs:oss:*:*:soniscope-audio/recordings/*"
      ]
    }
  ]
}
```

控制台操作：

1. 打开阿里云控制台。
2. 进入 `访问控制 RAM`。
3. 左侧进入 `权限管理 -> 权限策略`。
4. 点击 `创建权限策略`。
5. 选择 `脚本编辑`。
6. 粘贴上面的 JSON。
7. 策略名称填写：

   ```text
   soniscope-fc-recordings-headonly
   ```

8. 保存。
9. 回到 `身份管理 -> 用户`。
10. 点开已有用户 `soniscope-fc`。
11. 进入 `权限管理`。
12. 点击 `新增授权`。
13. 策略类型选择 `自定义策略`。
14. 勾选：

    ```text
    soniscope-fc-recordings-headonly
    ```

15. 确认授权。

授权完成后，`soniscope-fc` 应至少有：

- 系统策略 `AliyunSTSAssumeRoleAccess`
- 自定义策略 `soniscope-fc-recordings-headonly`

不要给 `soniscope-fc` 直接 OSS 写权限。小程序上传 OSS 必须走 `issue-credential` 签发出来的单 object key STS。

### 3.2 在两个 FC 函数中配置环境变量

在阿里云 FC 3.0 控制台分别打开：

```text
issue-credential
verify-upload
```

进入：

```text
配置 -> 环境变量
```

两个函数都要设置同一组环境变量。FC 3.0 没有 service 层级，也没有服务级共享环境变量，所以必须填两遍。

```text
OSS_BUCKET=soniscope-audio
OSS_REGION=cn-beijing
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
RAM_ROLE_ARN=acs:ram::1633875501759333:role/soniscope-uploader-role
ALIYUN_AK_ID=<soniscope-fc 的 AK ID>
ALIYUN_AK_SECRET=<soniscope-fc 的 AK Secret>
WX_APPID=wx3f973c7297728b0c
WX_APP_SECRET=<微信小程序 AppSecret>
OPENID_ALLOWLIST=o68Nm3RodhXQKA6_Z5VGiWC8LEVI,o68Nm3Z5tK1Dr8QchPT7Ikqjre8Q
MAX_UPLOAD_BYTES=52428800
```

字段来源：

| 环境变量 | 填什么 | 来源 |
|---|---|---|
| `OSS_BUCKET` | `soniscope-audio` | runbook 已登记 |
| `OSS_REGION` | `cn-beijing` | runbook 已登记 |
| `OSS_ENDPOINT` | `oss-cn-beijing.aliyuncs.com` | runbook 已登记 |
| `RAM_ROLE_ARN` | `acs:ram::1633875501759333:role/soniscope-uploader-role` | `cloud-setup.md` §2.4 |
| `ALIYUN_AK_ID` | `soniscope-fc` 的 AK ID | 1Password |
| `ALIYUN_AK_SECRET` | `soniscope-fc` 的 AK Secret | 1Password |
| `WX_APPID` | `wx3f973c7297728b0c` | `cloud-setup.md` §4.1 |
| `WX_APP_SECRET` | 小程序 AppSecret | 1Password |
| `OPENID_ALLOWLIST` | 允许调用的 openid，英文逗号分隔 | `cloud-setup.md` §4.2 |
| `MAX_UPLOAD_BYTES` | `52428800` | 50 MB 默认上限 |

对 `issue-credential` 的操作：

1. FC 3.0 控制台进入函数 `issue-credential`。
2. 打开 `配置`。
3. 找到 `环境变量`。
4. 点击编辑。
5. 逐项新增或修改上表 10 个变量。
6. 保存。

对 `verify-upload` 的操作：

1. FC 3.0 控制台进入函数 `verify-upload`。
2. 打开 `配置`。
3. 找到 `环境变量`。
4. 点击编辑。
5. 填入同样 10 个变量。
6. 保存。

保存后再次打开两个函数的环境变量页，逐项核对变量名。变量名必须完全一致，尤其是：

```text
ALIYUN_AK_ID
ALIYUN_AK_SECRET
WX_APP_SECRET
OPENID_ALLOWLIST
MAX_UPLOAD_BYTES
```

### 3.3 这里不需要配置 FC 服务角色

本项目当前 FC 代码不是通过“FC 执行角色”拿权限，而是显式读取环境变量里的 `ALIYUN_AK_ID` / `ALIYUN_AK_SECRET`：

```python
os.environ["ALIYUN_AK_ID"]
os.environ["ALIYUN_AK_SECRET"]
```

所以你需要在两个函数里配置的是环境变量，不是给函数绑定 `AliyunFCDefaultRole` 或其他服务角色。

如果缺少 `soniscope-fc-recordings-headonly`，`verify-upload` 部署后会在运行时返回：

```json
{"error":"HEAD_OBJECT_FAILED"}
```

---

## 4. 创建本地 `.env`

在仓库根目录创建：

```text
./.env
```

内容只放部署期凭证：

```bash
ALIYUN_DEPLOY_AK_ID=<soniscope-fc-deploy 的 AK ID>
ALIYUN_DEPLOY_AK_SECRET=<soniscope-fc-deploy 的 AK Secret>
```

不要把这些值发到聊天里，不要写入任何 Markdown 文档。

仓库 `.gitignore` 已忽略 `.env`。确认命令：

```bash
git check-ignore .env
```

期望输出：

```text
.env
```

---

## 5. 部署前本地检查

进入仓库根目录：

```bash
cd /Users/bemied/ProjectCode/my_soniscope
```

`make deploy-fc` 会自动读取仓库根目录 `.env` 中的 `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET`。如果当前 shell 已经显式导出了同名变量，shell 里的值优先，`.env` 不会覆盖它。

排障时可以手动检查 `.env` 是否存在且被 git 忽略：

```bash
test -f .env && echo ".env ok"
git check-ignore .env
```

期望输出：

```text
.env ok
.env
```

可选：先跑 FC 本地单测，确认要部署的代码逻辑自洽：

```bash
uv run pytest apps/fc/tests apps/worker/tests/test_fc_deploy.py
```

期望全部通过。

---

## 6. 执行部署

推荐先单个部署，便于定位失败点：

```bash
make deploy-fc FUNCTION=issue-credential
make deploy-fc FUNCTION=verify-upload
```

也可以一次部署两个：

```bash
make deploy-fc
```

部署脚本会执行：

1. 下载线上旧代码并备份到 `build/fc/backup/<timestamp>/`
2. 打包当前仓库的 `handler.py`
3. 把 `apps/fc/shared/fc_shared` vendoring 到函数包根目录
4. 安装函数运行依赖到包内
5. 只更新 FC 代码包
6. 不修改环境变量、触发器、运行时规格或公网 URL
7. 对函数公网 URL 做 GET 存活验证

如果输出里出现“备份跳过”，不要直接忽略。因为当前云上已有旧代码，正常情况下应该能备份旧代码。首次正式替换旧代码时，应优先确认备份成功后再继续。

部署产物位置：

```text
build/fc/<function_name>/
build/fc/<function_name>.zip
build/fc/backup/<timestamp>/
build/fc/logs/deploy-<timestamp>.log
```

---

## 7. 部署后存活验证

直接访问两个函数 URL：

```bash
curl https://issue-cedential-ottfirocds.cn-beijing.fcapp.run
curl https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run
```

期望响应：

```json
{"function":"issue-credential","status":"ok"}
```

```json
{"function":"verify-upload","status":"ok"}
```

注意：`issue-cedential` 子域名少一个 `r` 是阿里云分配的真实 URL，不要修正为 `issue-credential`。

---

## 8. 云端联调

先跑不需要真实 code 的基础联调：

```bash
make test-fc-live
make test-verify-upload
```

这会覆盖伪造 code 等拒绝路径。部分正例会因为缺少一次性 `wx.login` code 被标记为 SKIP。

完整正例需要从微信小程序获取一次性 `wx.login` code。每个场景都要独立 code，不能复用：

```bash
make test-fc-live CODE=<allowlist内code> SIZE_CODE=<另一个allowlist内code>
```

```bash
make test-verify-upload VERIFIED_CODE=<code1> NOT_FOUND_CODE=<code2> MISMATCH_CODE=<code3>
```

联调预期：

- 伪造 code 返回 `401 INVALID_CODE`
- allowlist 外 code 返回 `403 OPENID_NOT_ALLOWED`
- allowlist 内 code 可签发单 object key STS
- STS 只能 PutObject 到签发的单个 object key
- `verify-upload` 能返回 `verified:true`
- 对象不存在返回 `OBJECT_NOT_FOUND`
- 大小不一致返回 `SIZE_MISMATCH`

---

## 9. 回滚

如果部署后发现问题，从最新备份恢复指定函数：

```bash
make rollback-fc FUNCTION=issue-credential
make rollback-fc FUNCTION=verify-upload
```

回滚后重新做存活验证：

```bash
curl https://issue-cedential-ottfirocds.cn-beijing.fcapp.run
curl https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run
```

---

## 10. 常见错误

### `make deploy-fc` 报缺少部署凭证

原因：部署进程没有读到 `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET`。新版 `make deploy-fc` 会自动读取仓库根目录 `.env`，所以优先检查文件位置和键名。

处理：

```bash
cd /Users/bemied/ProjectCode/my_soniscope
test -f .env && echo ".env ok"
awk -F= 'BEGIN{id=0;sec=0} /^[[:space:]]*(export[[:space:]]+)?ALIYUN_DEPLOY_AK_ID[[:space:]]*=/{id=1} /^[[:space:]]*(export[[:space:]]+)?ALIYUN_DEPLOY_AK_SECRET[[:space:]]*=/{sec=1} END{print "ALIYUN_DEPLOY_AK_ID " (id ? "present" : "missing"); print "ALIYUN_DEPLOY_AK_SECRET " (sec ? "present" : "missing")}' .env
make deploy-fc FUNCTION=issue-credential
```

### `make deploy-fc` 没有权限更新函数

原因：`.env` 里的 AK 不是部署账号，或者部署账号没有 FC 更新函数代码权限。

处理：

- 确认 `.env` 使用的是 `soniscope-fc-deploy` 的 AK
- 确认该 RAM 用户有读取函数、获取函数代码、更新函数代码的权限
- 不要使用 `soniscope-local-reader` 或 `soniscope-asr`

### `make deploy-fc` 显示 `TypeError` 或 `UnretryableException`

如果看到类似输出：

```text
[FAIL] issue-credential — sha256=...（备份跳过：获取线上代码失败：TypeError；上传失败：更新函数代码失败：UnretryableException）
```

先确认当前仓库已经包含 FC SDK 调用修复：

```bash
uv run pytest apps/worker/tests/test_fc_deploy.py
```

修复后再次部署：

```bash
make deploy-fc FUNCTION=issue-credential
```

如果仍然失败，新的部署输出会带上脱敏后的 `code`、`request_id`、`message`。按 `code` 判断：

- `AccessDenied`：回到 RAM 给 `soniscope-fc-deploy` 补 FC 读取/更新函数权限
- `InvalidArgument` 或 `BadRequest`：优先检查函数名是否是 `issue-credential` / `verify-upload`
- 其他错误：保留 `request_id`，在阿里云 FC OpenAPI 调用记录或工单里定位

### `issue-credential` 返回 `STS_ISSUE_FAILED`

原因通常是 `soniscope-fc` 运行时账号无法 AssumeRole。

处理：

- 检查 FC 环境变量 `RAM_ROLE_ARN`
- 检查 `soniscope-uploader-role` 信任主体是否是 `acs:ram::1633875501759333:user/soniscope-fc`
- 检查 `soniscope-fc` 是否有 `AliyunSTSAssumeRoleAccess`

### `verify-upload` 返回 `HEAD_OBJECT_FAILED`

原因通常是 `soniscope-fc` 运行时账号没有 OSS HeadObject 所需权限。

处理：

- 给 `soniscope-fc` 增加对 `soniscope-audio/recordings/*` 的 `oss:GetObject`
- 确认 `OSS_BUCKET`、`OSS_REGION`、`OSS_ENDPOINT` 与 runbook 一致

### 小程序请求失败

优先检查微信公众平台域名白名单：

- request 合法域名：
  - `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run`
  - `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run`
- uploadFile 合法域名：
  - `https://soniscope-audio.oss-cn-beijing.aliyuncs.com`

---

## 11. 部署检查清单

- [ ] `soniscope-fc-deploy` 已创建，AK 已保存到密码管理器
- [ ] `soniscope-fc-deploy` 已临时绑定 `AliyunFCFullAccess`，或已绑定可用的 `soniscope-fc-deploy-code-only`
- [ ] `soniscope-fc-recordings-headonly` 自定义策略已创建
- [ ] `soniscope-fc` 已绑定 `soniscope-fc-recordings-headonly`
- [ ] `.env` 已创建，且只包含 `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET`
- [ ] `git check-ignore .env` 输出 `.env`
- [ ] `issue-credential` 已配置完整 FC 运行时环境变量
- [ ] `verify-upload` 已配置完整 FC 运行时环境变量
- [ ] `soniscope-fc` 可 AssumeRole 到 `soniscope-uploader-role`
- [ ] `soniscope-fc` 对 `soniscope-audio/recordings/*` 有 `oss:GetObject`
- [ ] `make deploy-fc FUNCTION=issue-credential` 成功，且备份旧代码成功
- [ ] `make deploy-fc FUNCTION=verify-upload` 成功，且备份旧代码成功
- [ ] 首次部署成功后，已计划把 `soniscope-fc-deploy` 从 `AliyunFCFullAccess` 收紧到自定义部署策略
- [ ] 两个 `curl` 存活验证返回 `status=ok`
- [ ] `make test-fc-live` 无 FAIL
- [ ] `make test-verify-upload` 无 FAIL
- [ ] 如果有问题，`make rollback-fc FUNCTION=<name>` 可从备份恢复
