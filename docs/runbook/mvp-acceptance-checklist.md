# SoniScope MVP 最终验收 Runbook & 真机闭环清单

> **文档性质**：本文件是日观声记 MVP 的最终验收执行手册。所有步骤必须在真实环境中执行，**不允许使用 mock**。
>
> **版本**：v1.0 | **最后更新**：2026-06-02 | **适用分支**：`ralph/soniscope-mvp-cloud-asr`

---

## 元信息

| 项 | 值 |
|---|---|
| 项目 | 日观声记 SoniScope MVP |
| 验收范围 | 录音 → OSS 备份 → FC 签发/校验 → Worker 转写落盘 完整闭环 |
| 验收前提 | 真实微信小程序 + 真实 FC + 真实 OSS + 真实 Worker |
| 参考 PRD | `docs/PRD_v1.md` §4 Feature 最终验收 AC |
| 参考 Tech Spec | `docs/tech-spec.md` |
| 云资源登记 | `docs/runbook/cloud-setup.md` |

---

## 0. 验收前提检查

在开始验收之前，逐项确认以下前提已满足：

### 0.1 运行环境

首先设置运行环境`export SONISCOPE_HOME=/Volumes/Data/software/SoniScope`

- [x] Worker 主机已就绪（Mac Studio M4 Max / macOS 26.5 / Python 3.13.2）
- [x] `$SONISCOPE_HOME=/Volumes/Data/software/SoniScope` 已设置
- [x] `$SONISCOPE_HOME/config.yaml` 配置完整且权限为 `chmod 600`
- [x] `ffmpeg` 与 `ffprobe` 可执行

**验证命令**：

```bash
make check-config
make init-dirs
```

### 0.2 云资源

- [x] OSS Bucket `soniscope-audio`（`cn-beijing`，ACL private）已按 runbook 人工确认；`make verify-prep` A 块只验证 Worker 运行时所需的 `ListObjects` / `HeadObject` / `GetObject` 访问
- [x] FC `issue-credential`（`https://issue-cedential-ottfirocds.cn-beijing.fcapp.run`）公网可达
- [x] FC `verify-upload`（`https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run`）公网可达
- [x] NLS ASR 项目 `soniscope`（AppKey `1k8tqkjQsq65wp2m`）可用
- [x] 微信小程序 AppID `wx3f973c7297728b0c` 已配置服务器域名白名单

**验证命令**：

```bash
make verify-prep
```

预期输出最后一行：`✅ US-001 preparation verified. Ready for US-003+`

### 0.3 测试音频

- [ ] `tests/audio/` 下 4 个测试音频文件存在且 sha256 / duration / codec 校验通过

**验证命令**：

```bash
python3 scripts/fetch_test_fixtures.py --check
```

### 0.4 代码质量

- [ ] 所有代码通过 typecheck、lint、test

**验证命令**：

```bash
make typecheck
make lint
make test
```

### 0.5 真机准备

- [ ] 微信开发者工具已安装（Stable 2.01.2510290+）
- [ ] 真机已安装微信，已添加为小程序体验者
- [ ] 真机 openid 已在 `OPENID_ALLOWLIST` 中（参考 `docs/runbook/cloud-setup.md` §4.2）
- [ ] 真机可正常打开小程序首页

---

## Part 1：100 条真机录音 · 正常路径 E2E

> **目标**：验证 100 条真实录音从小程序到 OSS 到 Worker 转写落盘的整条链路完全闭环。
>
> **前提**：Worker 已在后台运行（`make worker-run` 或等价方式）。

### 1.1 真机录音（人工操作）

1. 在真机上打开「日观声记」微信小程序
2. 连续录制 **100 条**录音，每条时长 **30~90 秒**
3. 每条录音停止后进入草稿确认态 → 点击「试听」验证 → 点击「保存并上传」
4. 观察上传列表页：
   - [ ] 所有 100 条 Fragment 最终状态均为「上传成功（verified）」
   - [ ] 没有任何「待人工重传」或「待人工 verify」状态残留
   - [ ] 上传列表顶部横幅不再显示积压提醒
5. 记录本次录制日期：`<YYYY-MM-DD>`（后续自动验证需要）

> ⚠️ 建议分批次完成（如每天 20 条），避免单次操作疲劳。记录每次完成的日期。

### 1.2 OSS 对象计数验证（自动命令）

```bash
make list-oss-objects DATE=<YYYY-MM-DD>
```

- [ ] 命令输出对象计数为 **100**
- [ ] 文件名与前端 `fragment_id` 一一对应（所有 key 格式为 `recordings/<YYYY-MM-DD>/<fragment_id>.wav`）

### 1.3 本地 Fragment 完整性验证（自动命令）

```bash
make verify-e2e-integrity
```

- [ ] 本地 `$SONISCOPE_HOME/fragments/<YYYY-MM-DD>/` 下有 **100 个 Fragment 目录**
- [ ] 每个目录同时包含 5 个产物文件：`audio.wav` / `manifest.json` / `transcript.json` / `transcript.txt` / `.done`
- [ ] 输出通过数 = 100，失败数 = 0

### 1.4 SHA-256 一致性验证（自动命令）

```bash
make verify-e2e-sha256
```

- [ ] 所有 100 条 Fragment 的 sha256 校验通过：
  - WAV 直通路径：`audio.sha256 == upload.original_sha256`
  - 非 WAV 转码路径：`audio.sha256` 和 `upload.original_sha256` 均为合法 sha256 值（两者可以不同）
- [ ] 输出通过数 = 100，失败数 = 0
- [ ] 如有失败，检查输出中的 `fragment_id` 和失败字段路径

### 1.5 Manifest 关键字段验证（自动命令）

```bash
make verify-e2e-fields
```

- [ ] 每条 Fragment 的 `manifest.upload.verified_at` 非空
- [ ] 每条 Fragment 的 `manifest.transcription.completed_at` 非空
- [ ] 输出通过数 = 100，失败数 = 0

### 1.6 残留中间态检查（自动命令）

```bash
make verify-no-stale
```

- [ ] `inbox/` 下无残留 `.part` 文件
- [ ] `inbox/` 下无残留 `.wav.tmp` 文件
- [ ] `tmp/` 下无残留 `.transcript.json.tmp` 文件
- [ ] 如发现残留，输出会列出具体文件路径和修复指引

---

## Part 2：异常路径 · 脚本崩溃恢复

> **目标**：验证 Worker 在处理中被 `kill -9` 强制终止后，重启能自动补齐余下流程。

### 2.1 准备

确保 Worker 正在运行且有至少一条 Fragment 正在处理（或即将处理）。

### 2.2 执行崩溃恢复测试

```bash
make test-e2e-crash-recovery
```

或者手动执行完整流程：

1. 确认 Worker 正在运行中
2. 在真机上新录一条录音并保存上传
3. 在 Worker 下载完成、正在转写时执行：
   ```bash
   # 查 Worker 进程 PID
   ps aux | grep soniscope_worker
   # 强制终止
   kill -9 <PID>
   ```
4. 检查该 Fragment 目录：
   ```bash
   ls $SONISCOPE_HOME/fragments/<YYYY-MM-DD>/<fragment_id>/
   ```
   - [ ] 目录下存在 `audio.wav`
   - [ ] 目录下**没有** `.done`

5. 重启 Worker：
   ```bash
   make worker-run
   ```

6. 等待 Worker 完成恢复处理，再次检查：
   ```bash
   ls $SONISCOPE_HOME/fragments/<YYYY-MM-DD>/<fragment_id>/
   ```
   - [ ] 目录下最终存在完整的 5 个产物文件
   - [ ] `transcript.json` 内容完整（非占位）
   - [ ] `.done` 文件存在

### 2.3 验收判据

- [ ] 崩溃恢复脚本输出 pass
- [ ] Worker 重启日志显示 recovery scan 清理了残留中间态
- [ ] 崩溃中断的 Fragment 最终 `.done` 出现且 transcript 完整
- [ ] 原有已完成（有 `.done`）的 Fragment 不受影响、未被重转

---

## Part 3：异常路径 · 显式重转

> **目标**：验证 `retranscribe` CLI 的 `--upgrade` 和 `--force` 行为正确，且正常轮询不会自动重转。

### 3.1 准备

1. 记录当前 `config.yaml` 中的 `transcriber.params_version`（例如 `v1`）
2. 确保已有至少 2 条已完成的 Fragment（有 `.done`）

### 3.2 执行重转测试

```bash
make test-e2e-retranscribe
```

或者手动执行：

1. **验证正常轮询不自动重转**：
   ```bash
   # 查看已完成 Fragment 的 params_version
   cat $SONISCOPE_HOME/fragments/<YYYY-MM-DD>/<fragment_id>/manifest.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['transcription']['params_version'])"
   ```
   - [ ] Worker 正常运行一轮后，已有 `.done` 的 Fragment **未被重新转写**（通过日志或调用计数验证）

2. **修改配置触发 --upgrade 重转**：
   ```bash
   # 修改 config.yaml 中 transcriber.params_version 从 v1 改为 v2
   # （使用你习惯的编辑器修改 $SONISCOPE_HOME/config.yaml）
   ```

3. **执行 upgrade 重转**：
   ```bash
   make retranscribe ARGS="--all-from <YYYY-MM-DD> --upgrade"
   ```
   - [ ] 仅 `params_version == v1`（旧版）的 Fragment 被重转
   - [ ] `params_version` 已为 `v2` 的 Fragment 被跳过
   - [ ] 重转后 `manifest.transcription.params_version` 变为 `v2`
   - [ ] `manifest.transcription.completed_at` 时间戳更新
   - [ ] 命令输出显示成功/跳过/失败汇总

4. **验证 --force 无条件重转**：
   ```bash
   make retranscribe FRAGMENT_ID=<fragment_id>
   # 提示已完成，使用 --force 强制
   make retranscribe ARGS="<fragment_id> --force"
   ```
   - [ ] `--force` 无条件重转，即使 `.done` 存在且版本一致
   - [ ] 新 `transcript.json` 原子覆盖旧的

### 3.3 验收判据

- [ ] 正常轮询不自动重转已有 `.done` 的 Fragment
- [ ] `--upgrade` 仅重转旧版本，新版本被跳过
- [ ] `--force` 无条件重转
- [ ] 重转过程不影响其他 Fragment，失败不中断批量任务
- [ ] 修改配置后不重启 Worker 验证下次扫描不会自动重转

---

## Part 4：安全反例 · 鉴权与越权

> **目标**：验证未授权 openid 无法获取 STS 凭证，且合法 STS 凭证无法越权操作。

### 4.1 执行安全测试

```bash
make test-e2e-security
```

该命令会自动执行以下验证：

#### A 块：FC 鉴权拒绝

- [ ] 不带 `code` 参数或带伪造 `code` 调用 `POST /issue-credential` → 返回 `401 INVALID_CODE`
- [ ] 使用未在 allowlist 中的 openid 调用 → 返回 `403 OPENID_NOT_ALLOWED`
- [ ] 响应中不包含任何 STS 凭证字段（`access_key_id` / `access_key_secret` / `security_token`）

#### B 块：STS 越权拒绝

- [ ] 使用合法 STS 凭证尝试 `PutObject` 到其他 `recordings/<other_date>/<other_id>.wav` → 返回 `AccessDenied`
- [ ] 使用合法 STS 凭证尝试 `GetObject` → 返回 `AccessDenied`
- [ ] 使用合法 STS 凭证尝试 `ListObjects` → 返回 `AccessDenied`
- [ ] 使用合法 STS 凭证尝试 `DeleteObject` → 返回 `AccessDenied`

#### C 块：verify-upload 鉴权

- [ ] `POST /verify-upload` 不带有效 `code` → 返回 `401`
- [ ] 伪造 `code` 不能泄露云端对象存在性信息

#### D 块：汇总

- [ ] 所有安全反例通过
- [ ] 输出包含复现命令

### 4.2 验收判据

- [ ] `make test-e2e-security` 输出全部 pass
- [ ] 未授权 openid 在任何情况下都无法拿到 STS
- [ ] STS 凭证严格限定到单个 object key 的 `PutObject`，不可越权

---

## Part 5：真机交互异常闭环

> **目标**：验证真实手机上的中断保护、长录音分片、失败重试与手动重传。

### 5.1 中断保护闭环

1. 真机打开**飞行模式**
2. 在小程序中开始录音，录制 **60 秒**
3. 录音中途按**电源键锁屏**
4. 解锁手机，回到小程序
   - [ ] 弹出中断恢复提示：「上次录音被中断，已自动保存草稿」
   - [ ] 显示已保存草稿的时长（≈ 锁屏前时长）和格式
5. 点击「保留」
   - [ ] 草稿出现在首页确认态，可试听
6. 关闭飞行模式
7. 点击「保存并上传」
   - [ ] 上传成功，状态变为「上传成功（verified）」

### 5.2 长录音分片闭环

1. 真机网络正常，确保 Worker 在运行
2. 在小程序中开始录音，连续录制 **25 分钟**
3. 期间不要手动停止
4. 25 分钟后点击停止
   - [ ] 草稿确认态显示：总时长约 25:00 · 3 段
5. 点击「保存并上传」
6. 观察上传列表：
   - [ ] 长录音聚合卡片显示为 1 张卡片（3 段收缩）
   - [ ] 展开后可见 3 个 chunk：`chunk_seq = 1/2/3`
   - [ ] 3 个 Fragment 全部上传成功
7. Worker 完成处理后验证：
   ```bash
   # 查看 3 个 Fragment 的 session_id
   cat $SONISCOPE_HOME/fragments/<YYYY-MM-DD>/<fragment_id_1>/manifest.json | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])"
   cat $SONISCOPE_HOME/fragments/<YYYY-MM-DD>/<fragment_id_2>/manifest.json | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])"
   cat $SONISCOPE_HOME/fragments/<YYYY-MM-DD>/<fragment_id_3>/manifest.json | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])"
   ```
   - [ ] 3 条 `manifest.session_id` 完全一致
   - [ ] 3 条 `manifest.chunk_total` 均为 `3`
   - [ ] 3 条 `manifest.chunk_seq` 分别为 `1/2/3`

### 5.3 失败重试 + 手动重传闭环

1. 打开小程序首页 → 点击「👺 开发者菜单」
2. 打开「FC URL 失效」开关（`mock-fc-url-broken`）
3. 回到首页，录制一条短录音 → 保存并上传
   - [ ] 上传引擎自动重试 3 次（观察列表状态变化）
   - [ ] 3 次失败后状态变为红色「待人工重传」
   - [ ] 列表项显示「点击手动重传」按钮
4. 回到开发者菜单，关闭「FC URL 失效」开关
5. 回到上传列表，点击该条目的「手动重传」按钮
   - [ ] 重新执行获取 STS → OSS 上传 → verify
   - [ ] 最终状态变为「上传成功（verified）」
6. 等待 Worker 处理
   - [ ] Worker 正常下载、转写、落盘，5 个产物完整

---

## Part 6：长期保留验证

> **目标**：验证本地缓存的 48 小时自动清理策略和 OSS 永不删除承诺。

### 6.1 48 小时本地缓存自动清理

- [ ] **前提**：Part 1 的 100 条录音全部 verified 完成
- [ ] 从最后一条录音 verified 时间起算，等待 **48 小时 + 1 小时**（即 verified 后至少过了 49 小时）
- [ ] 再次打开小程序，进入上传列表：
  - [ ] 100 条记录的本地音频缓存已被自动清理
  - [ ] 上传列表记录仍在（显示状态）
- [ ] 在 Worker 端验证：
  ```bash
  make list-oss-objects DATE=<YYYY-MM-DD>
  ```
  - [ ] OSS 上 100 个对象**仍然存在**（未被删除）
  - [ ] 对象计数 = 100

### 6.2 1 周后 OSS 保留验证

- [ ] **前提**：距 Part 1 录音完成已超过 1 周
- [ ] 执行：
  ```bash
  make verify-oss-retention
  ```
  - [ ] OSS 对象数 ≥ 本地 Fragment 目录数
  - [ ] Worker 日志中无任何 `DeleteObject` 调用记录
  - [ ] `scripts/` 下所有非测试标注的脚本中无 `DeleteObject` 调用

---

## Part 7：最终验收汇总

### 7.1 自动验证汇总

执行以下命令并记录结果：

| 命令 | 预期结果 | 实际结果 | 通过？ |
|---|---|---|---|
| `make verify-prep` | ✅ US-001 preparation verified | | |
| `make list-oss-objects DATE=<YYYY-MM-DD>` | 计数 = 100 | | |
| `make verify-e2e-integrity` | 100 pass, 0 fail | | |
| `make verify-e2e-sha256` | 100 pass, 0 fail | | |
| `make verify-e2e-fields` | 100 pass, 0 fail | | |
| `make verify-no-stale` | 0 残留 | | |
| `make test-e2e-crash-recovery` | pass | | |
| `make test-e2e-retranscribe` | pass | | |
| `make test-e2e-security` | pass | | |
| `make verify-oss-retention` | OSS 数 ≥ 本地数，无 DeleteObject | | |
| `make typecheck` | 通过 | | |
| `make lint` | 通过 | | |
| `make test` | 通过 | | |

### 7.2 真机操作汇总

| 操作 | 预期结果 | 通过？ |
|---|---|---|
| 100 条录音全部上传成功 | 100 条 verified | |
| 48h+ 本地缓存清理 | 本地清，OSS 留 | |
| 飞行模式 + 锁屏中断 → 保留 → 上传 | 草稿恢复成功 | |
| 25 分钟长录音 → 3 chunk | chunk_total=3, session_id 一致 | |
| FC 故障注入 → 3 次失败 → 关开关 → 手动重传成功 | Worker 落盘完成 | |

---

## 附录 A：常见问题与修复指引

### A.1 `make verify-prep` 失败

参考 `docs/runbook/cloud-setup.md` 逐项检查云资源配置。

### A.2 上传卡在「待上传（离线排队）」

1. 检查手机网络连接
2. 检查开发者菜单中「模拟离线」开关是否误开启
3. 关闭并重新打开小程序

### A.3 Worker 无法连接 OSS

1. 检查 `$SONISCOPE_HOME/config.yaml` 中 OSS AK/SK 是否正确
2. `make check-config` 确认配置权限为 600
3. 检查网络是否能访问 `oss-cn-beijing.aliyuncs.com`

### A.4 NLS 转写失败

1. 检查 `config.yaml` 中 `transcriber.appkey` 和 AK/SK 是否正确
2. 登录阿里云 NLS 控制台确认项目 `soniscope` 状态正常
3. 检查 NLS 服务配额是否超限

### A.5 sha256 不匹配

1. WAV 直通：检查 `audio.sha256 == upload.original_sha256`
2. 非 WAV 转码：两者不同是正常的，但都必须是非空的合法 sha256
3. 如发现异常，检查对应 Fragment 的 `manifest.json` 中的字段值

---

## 附录 B：验收签字

| 角色 | 姓名/ID | 日期 | 签字 |
|---|---|---|---|
| 开发者 | Bemied | | |
| 验收人 | | | |

---

> **完成标志**：Part 7 的 7.1 自动验证汇总表全部打勾 + 7.2 真机操作汇总表全部打勾。
>
> MVP 验收通过！
