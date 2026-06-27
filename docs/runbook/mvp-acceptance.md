# MVP 最终验收 Runbook（SoniScope / 日观声记）

> 本文是**日观声记 MVP 的最终验收操作手册**，把 `docs/PRD_v1.md` §4（Feature 最终验收 AC）落地为可逐条执行的命令与真机操作清单。
>
> 权威优先级：产品范围以 `docs/PRD_v1.md` 为准，技术实现/schema/make target 以 `docs/tech-spec.md` 为准，真实云资源/URL 以 `docs/runbook/cloud-setup.md` 为准，开发红线以 `AGENTS.md` 为准。冲突时按此顺序。
>
> 本文不替代上述文档，只提供"按什么顺序、跑哪条命令、在真机上做什么、看到什么算通过"的执行视角。

---

## 0. 验收前提（硬性约束 · 不允许 mock）

最终验收必须在**全真实环境**下完成，全链路任何一环都不允许使用 mock / stub / 假数据：

- **真实微信小程序**：真机微信客户端打开正式小程序（AppID `wx3f973c7297728b0c`），不是 DevTools 模拟器、不是 mock 数据构造。
- **真实 FC**：阿里云 FC 3.0 顶级 Web 函数 `issue-credential`（URL `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run`，注意子域名少一个 `r`，是真实分配值，**不要纠正拼写**）与 `verify-upload`（URL `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run`）。
- **真实 OSS**：私有 Bucket `soniscope-audio`，region `cn-beijing`。
- **真实 Worker**：在 Worker 主机（Mac Studio M4 Max，macOS 26.5，Python 3.13.2）上以真实 `config.yaml`（权限 600）运行 `make worker-run`，调用真实阿里云 NLS 云端 ASR。

进入本验收前，§3（US-001~US-031）所有 user story 必须已 `passes: true`。`make verify-prep` 应当全绿（OSS / RAM / FC / NLS / fixture / 环境真实可用）。

> ⚠️ 故障注入开关（`mock-fc-url-broken` / `mock-network-offline` / `mock-verify-fail`）**只**用于「失败重试闭环」那一项验收（§5），其余所有项必须在全部开关关闭、走真实链路下进行。

本文出现的 `<YYYY-MM-DD>` 一律替换为**实际录音当天日期**（按录音时小程序所在时区）。所有命令在仓库根目录执行；顶层 Makefile 是唯一入口，无需 `cd` 子目录。

---

## 1. 正常路径 · 100 条真机录音端到端落盘

### 1.1 真机录入（人工，AI 无法代跑）

1. 真机微信打开小程序，确认网络在线、已授权录音权限。
2. **连续录制 100 条、每条 30~90 秒**的录音，每条录完后依次点击「保存并上传」。
3. 在小程序「上传列表」页确认：
   - [ ] 100 条 Fragment 最终状态全部为 **上传成功（verified）**。
   - [ ] **没有**任何「待人工重传」「待人工 verify」「上传失败」「待 verify」残留状态。

> 建议分批录入并随时观察上传列表；若中途出现红色失败状态，先用「点击手动重传」清掉，确保 100 条全部 verified 后再进入自动验证。

### 1.2 OSS 对象计数（自动）

```bash
make list-oss-objects DATE=<YYYY-MM-DD>
```

- [ ] 输出列出当天 `recordings/<YYYY-MM-DD>/` 下的 `.wav` 对象，**总数 = 100**，文件名与前端 `fragment_id` 一一对应。
- [ ] 全程**无需打开 OSS 控制台**。

### 1.3 本地落盘完整性 + sha256 + 关键字段（自动）

依次运行下列三条命令，并**保存每条的完整输出**（验收留痕）：

```bash
make verify-e2e-integrity DATE=<YYYY-MM-DD> EXPECTED=100
make verify-e2e-sha256 DATE=<YYYY-MM-DD>
make verify-e2e-fields DATE=<YYYY-MM-DD>
```

- [ ] `verify-e2e-integrity`：`$SONISCOPE_HOME/fragments/<YYYY-MM-DD>/` 下出现**完整 100 个 Fragment 目录**，每个目录同时包含 `audio.wav` / `manifest.json` / `transcript.json` / `transcript.txt` / `.done` 五个产物（清单见 tech-spec §2.2）。
- [ ] `verify-e2e-sha256`：每条 Fragment 的 sha256 按 tech-spec §3.3 一致性规则校验通过（WAV 直通：`audio.sha256 == upload.original_sha256`；非 WAV 转码：两者真实计算、可不同且均非空）。
- [ ] `verify-e2e-fields`：每条 Fragment 的 `manifest.upload.verified_at` 与 `manifest.transcription.completed_at` 均**非空**。

每条命令通过时退出码为 0；失败时以非零退出并打印失败的 `fragment_id` 与失败字段路径，便于定位。

### 1.4 无半成品残留（自动）

```bash
make verify-no-stale
```

- [ ] `inbox/` 下无残留 `.part` / `.wav.tmp`；`tmp/` 下无残留 `.transcript.json.tmp`（中间态文件集中在 `inbox/` / `tmp/`，不在 fragment 目录内，见 tech-spec §3.5）。

---

## 2. 中断保护闭环（真机，人工）

模拟"录音中锁屏 / 切后台"后已录内容自动保存为草稿并可恢复：

1. 真机**打开飞行模式**。
2. 开始录音，录约 **60 秒**，中途按电源键**锁屏**。
3. 解锁回到小程序前台。
4. 验证：
   - [ ] 弹出中断恢复提示：「上次录音被中断，已自动保存草稿，是否保留 / 丢弃 / 继续新录？」
   - [ ] 选择「保留」后草稿存在，时长 ≈ 锁屏前的录制时长。
   - [ ] **关闭飞行模式**后，对该草稿点击「保存并上传」→ 最终状态变为 上传成功（verified）。

---

## 3. 长录音分片闭环（真机，人工）

验证超过分片阈值（`CHUNK_MAX_DURATION_SECONDS = 600`）的长录音自动切片：

1. 真机**连续录制 25 分钟**（中途不手动停止）。
2. 录制结束保存上传后，验证：
   - [ ] 自动切片为 **3 条 Fragment**，每条 `chunk_total = 3`，`chunk_seq` 为 1 / 2 / 3。
   - [ ] 3 条 Fragment 全部 上传成功（verified）。
   - [ ] 3 条 `manifest.session_id` **完全一致**。
   - [ ] 3 条本地 Fragment 目录均转写完成（各含完整五产物），拼接总时长 ≈ 25 分钟（允许 ±2 秒切换间隙）。

上传列表中同一 `session_id` 的 3 个 chunk 折叠为一张长录音卡片（如 `25:00 · 3 段`），全部 verified 时聚合状态显示「已完成」。

---

## 4. 异常路径自动脚本（自动，可由 AI / CI 跑）

下列脚本自包含、不要求用户打开阿里云或微信控制台，输出可读 pass/fail 汇总与失败时的复现命令；失败以非零退出。

### 4.1 崩溃恢复

```bash
make test-e2e-crash-recovery
```

- [ ] Worker 正在处理一条真实 Fragment 时 `kill -9` → 该目录残留 `audio.wav` 但无 `.done` → 重启后**自动重新转写**并补回完整 `transcript.json` 与 `.done`。

### 4.2 显式重转（params_version 升级）

```bash
make test-e2e-retranscribe
```

- [ ] 修改 / 临时覆盖 `transcriber.params_version`（如 v1 → v2）后运行 `make retranscribe ARGS="--all-from <date> --upgrade"` → **仅旧 params_version 的 Fragment** 被重转，新的 `transcript.json` 原子覆盖旧的，`manifest.transcription.params_version` 更新为新值。
- [ ] 修改配置后**不重启 Worker**，普通轮询**不会**自动重转已有 `.done` 的 Fragment（`.done` 是唯一幂等判据）。

### 4.3 安全反例（鉴权 + STS 越权）

```bash
make test-e2e-security
```

- [ ] 用**未在 allowlist** 的微信 code 或测试夹具调用 FC → 收到 403 或等价拒绝，**不返回任何 STS 凭证**。
- [ ] 用合法 STS 凭证尝试 `PutObject` 到**其他 object key** → OSS 返回 `AccessDenied`。

---

## 5. 失败重试 + 手动重传闭环（真机，人工）

用小程序内置故障注入菜单（仅非 production 可见）验证自动重试与手动重传：

1. 真机小程序打开「开发者菜单 → 故障注入」，开启 **`mock-fc-url-broken`**（FC URL 失效）。
2. 录一条音频并保存上传 → 自动重试 3 次后失败 → 上传列表出现**红色提示** + 「点击手动重传」按钮。
3. **关闭** `mock-fc-url-broken`（运行时切换，无需改源码 / 重新编译）。
4. 点击「手动重传」→ 重置重试计数 → 重新走获取 STS → OSS 上传 → verify。
5. 验证：
   - [ ] 手动重传后该 Fragment 状态变为 上传成功（verified）。
   - [ ] Worker 端轮询后该 Fragment 本地落盘完成（五产物齐全）。

> 验收完此项后**务必关闭所有故障注入开关**，避免污染其余真实链路验收。

---

## 6. 本地缓存自动清理（verify + 48 小时策略，真机，人工）

验证「verify 通过且超过 48 小时后才允许自动清理本地缓存；OSS 永不删除」：

1. 在 §1 的 100 条录音全部 verified 之后，**再等待 48 小时 + 1 小时**（缓冲）。
2. 验证：
   - [ ] 真机本地的 100 条音频缓存**已自动清理**。
   - [ ] OSS 上的 100 个对象**仍然存在**：

     ```bash
     make list-oss-objects DATE=<YYYY-MM-DD>   # 仍应为 100
     ```
   - [ ] verify 未通过 / 待人工重传 / 待人工 verify 的文件即使超过 7 天也**不会**被自动删除（如有此类样本一并复验）。

---

## 7. 长期保留复验（1 周后，自动）

验证 OSS 永不删除红线（AGENTS.md 安全红线 / FR-11）：

1. **跑完整套验收后 1 周再次执行**：

   ```bash
   make verify-oss-retention
   ```
2. 验证：
   - [ ] OSS 上对象数 **≥** 本地 `fragments/` 目录数。
   - [ ] 扫描 Worker 日志中**无任何 `DeleteObject` 调用记录**（Worker 业务源码中也不存在 DeleteObject 调用；`oss-delete-obj` 仅测试用）。

---

## 8. 验收完成判定

当且仅当下列全部打勾，本 MVP feature 验收完成：

| 区块 | 项 | 类型 |
|---|---|---|
| §1.1 | 100 条真机录音全部 verified、无失败残留 | 人工 |
| §1.2 | `make list-oss-objects` 计数 = 100 | 自动 |
| §1.3 | `verify-e2e-integrity` / `verify-e2e-sha256` / `verify-e2e-fields` 全通过 | 自动 |
| §1.4 | `verify-no-stale` 无残留 | 自动 |
| §2 | 中断保护闭环 | 人工 |
| §3 | 25 分钟长录音分片闭环（`chunk_total=3`、`session_id` 一致） | 人工 |
| §4.1 | `test-e2e-crash-recovery` | 自动 |
| §4.2 | `test-e2e-retranscribe` | 自动 |
| §4.3 | `test-e2e-security` | 自动 |
| §5 | 故障注入失败重试 + 手动重传闭环 | 人工 |
| §6 | 48h+1h 本地缓存自动清理、OSS 对象仍在 | 人工 |
| §7 | 1 周后 `verify-oss-retention` OSS 永不删除 | 自动 |

> 核心承诺复核：**音频与转写不丢、不重、不虚构**——100 条端到端无丢失（§1）、幂等不重复（§4.2 + `.done` 规则）、转写来自真实云端 ASR 非 mock（§0）。

---

## 9. 失败排查指引

| 现象 | 优先排查 |
|---|---|
| `list-oss-objects` 计数 < 100 | 小程序上传列表是否仍有未 verified 项；对失败项「手动重传」后复跑 |
| `verify-e2e-integrity` 报缺产物 | Worker 是否在运行（`make worker-run`）；查看对应 `fragment_id` 目录缺哪个文件；`make verify-no-stale` 看是否卡在中间态 |
| `verify-e2e-sha256` 不一致 | 区分 WAV 直通 / 非 WAV 转码两类规则（tech-spec §3.3）；非 WAV 路径允许 `audio.sha256 != upload.original_sha256` |
| `verify-e2e-fields` 报 `verified_at` 空 | 该条未走完 verify；检查小程序状态与 `/verify-upload` 回执 |
| `test-e2e-security` 未返回 403 | 检查 FC `OPENID_ALLOWLIST` 环境变量与测试夹具 code |
| `verify-oss-retention` 失败 | 确认 Worker 业务路径无 DeleteObject；区分测试用 `oss-delete-obj` 留下的人为删除 |

所有命令失败时输出具体 object key / 路径 / 配置项与复现命令，且不打印任何 AK Secret 明文。
