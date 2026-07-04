# SoniScope 架构审计报告

> 审计日期：2026-07-02
> 审计范围：`apps/miniprogram/`（微信小程序）、`apps/fc/`（阿里云 FC 函数）、`apps/worker/`（Python Worker）、顶层工程配置与文档体系
> 代码规模：Worker 约 9700 行 Python（25 模块 + 24 个测试文件）；FC 两个函数 + `fc_shared` 共享包；小程序约 5800 行 JS

---

## 1. 总体结论

**架构整体是合理的，对一个个人 MVP 来说质量明显高于平均水平。** 四层架构（小程序极薄前端 → FC 签发单文件 STS → OSS 私有桶 → 本地 Worker 轮询转写）职责切分清晰，安全模型和崩溃恢复设计是真正的亮点。不需要推翻重来，但存在：**2 个安全/正确性问题、1 个结构性重复、1 个包边界失焦**，以及一批小 bug。

如果只修三件事，建议是：

1. FC 请求体无上限读取（§4.1 问题 1）
2. 空转写被静默标记为成功（§4.1 问题 2）
3. 小程序两套上传编排合并（§4.1 问题 4）

---

## 2. 做得好的地方（不要改）

- **安全模型扎实**：STS policy 精确到单个 object key、只给 `oss:PutObject`、900 秒过期（`fc_shared/sts.py:62-73`）；前端零长期密钥，配 `lint-miniprogram` 静态检查兜底；openid 哈希后才记日志、敏感字段自动打码（`fc_shared/audit.py`）。
- **崩溃安全设计**：`.part` → 原子 rename → `.done` 三段式文件状态机 + 启动三目录恢复扫描，Worker 任意时刻 kill -9 都能正确恢复。`.done` 作为唯一完成信号、OSS 永不删除的红线在源码与 `verify-oss-retention` 双重保障。
- **可测性架构一致**：三个子系统全部采用「纯逻辑 + IO 通过 Protocol/回调注入」模式，单测不触网。这一纪律贯穿 JS 与 Python 两侧。
- **文档体系**：tech-spec 作为唯一技术权威来源 + ADR 记录决策 + PRD 引用章节号的做法执行到位；Makefile 提供统一命令入口。
- **两个 FC 函数不建议合并**：依赖不同（STS SDK vs OSS SDK）、安全画像不同（窄凭证签发 vs 宽读校验），分开部署是正确的隔离。
- **轮询 vs 事件触发**：单用户 MVP 场景下轮询完全够用，不必现在换 OSS 事件通知（规模化天花板见 §5）。

---

## 3. 分子系统详细分析

### 3.1 微信小程序（`apps/miniprogram/`）

#### 模块职责与数据流

整体是清晰的**「纯逻辑 + IO 注入」两层架构**：utils 为无 wx 依赖的纯函数，页面（Page）负责 wx IO 与渲染。依赖方向健康，无循环依赖，utils 不反向依赖页面。

- **录音**：`pages/index/index.js` 持有 `wx.getRecorderManager()`，`onLoad`（:78）绑定回调；`_startRecording`（:176）分配 `session_id`（`chunking.createRecordingSession`），启动 1s 计时器。
- **分片**：计时器每秒调 `_maybeRotateChunk`（:215）→ 到 600s 主动 `recorder.stop()`；`_onRecordStop`（:238）通过 `_interrupting`/`_userStopping` 三态路由：分片边界则 `addChunk` + `_startNextChunk`（:203）无缝续录，最终停止则 `_finalizeStopped`（:282）。
- **草稿**：`utils/audio.js` 的 `buildDraftManifest`（:111）/`buildUploadManifestDraft`（:130）构造 manifest；`utils/draft.js` 叠加中断态；单槽位落盘 `soniscope:interrupted_draft`。
- **入队**：`onTapSaveUpload`（index.js:512）生成正式 `fragment_id`，`_computeOriginalSha256`（:630）算 sha256，`audio.buildOssMetadata` 生成 `x-oss-meta-*`，落盘 `soniscope:upload_queue`。
- **上传**：`utils/uploader.js` `uploadFragment`（:60）编排 `login → requestSts → oss_sign.buildPostObjectForm → uploadFile`；`utils/oss_sign.js` 用 STS 临时密钥做 OSS4-HMAC-SHA256 PostObject 表单签名。
- **校验**：`utils/verify.js` `verifyFragment`（:56）POST verify-upload，分类 verified/unverified/retryable/fatal。
- **运行时编排**：`utils/queue_runtime.js` 与 `pages/uploads/uploads.js` **各自**封装 wx 适配器 + 队列驱动——两套并存（见下文问题 A）。

#### 状态管理

- 本地存储三个 key：`soniscope:device_short_id`（device.js:8）、`soniscope:interrupted_draft`（draft.js:14，单槽位后到覆盖）、`soniscope:upload_queue`（upload_queue.js:30，唯一真实来源）。
- 状态机每步迁移立即 `writeQueue` 落盘（uploads.js:197、queue_runtime.js:160），中途杀进程后 `onShow` 幂等重驱动恢复。
- 断点续传是 **Fragment 级恢复**而非分片级续传：OSS object_key 由 FC 固定，重复上传幂等，因此重复驱动安全。

#### 安全设计

- config.js 只含公开 URL 与 region，无 AK/AppSecret；STS 凭证仅内存使用、从不落盘/日志（uploader.js:94、oss_sign.js:93）。
- `utils/logger.js` 的 `redact`（:20）按敏感键名正则自动打码。
- 故障注入受 ENV 门控，production 下读永远全关、写忽略（fault_injection.js:82-107）。

#### 发现的问题

- **（A）严重重复：两套上传编排并存**。`utils/queue_runtime.js:83-324` 与 `pages/uploads/uploads.js:111-386` 几乎逐行相同（wxLogin/wxRequestSts/wxRequestVerify/wxUploadFile、processQueue/processVerifyQueue、_autoCleanup、manualRetry、删除逻辑）。注释（queue_runtime.js:5-6）自认是为保留既有单测而不重构。任何状态机修复都要改两处。
- **（B）两份实现行为已经分叉（潜在 bug）**。`_isOnline` 语义不一致：uploads.js:163-178 遇 `fail`/`catch` 视为**在线**；queue_runtime.js:62-81 缺 API/`catch` 视为**离线**。同一判断在异常分支给出相反结论，首页与上传页离线行为会不同。
- **（C）主线程同步大计算卡 UI**。`_computeOriginalSha256`（index.js:630）同步读整文件 + 纯 JS SHA-256；长录音 `_saveLongRecording`（index.js:580-596）对每个分片逐个同步计算，会明显冻结界面。sha256.js:4-5 注释已承认待 wasm 化（tech-spec ADR-2 规划了但未落实）。
- **（D）跨页并发写同一 storage**。`_processing`/`_verifying` 守卫是实例级（uploads.js:40-41）/闭包级（queue_runtime.js:33-34），互不感知；首页与 uploads 页可并发 read-modify-write 同一 `upload_queue` key，存在竞态覆盖风险（object_key 幂等降低了危害）。
- **（E）常量重复**。退避延时 `[5000,15000,45000]` 在 uploader.js:28 与 verify.js:16 各一份；八状态常量在 upload_queue.js 与 uploads_view.js 间耦合分散。
- **（F）遗留/死代码**。queue_runtime.js:232 残留 `// PLACEHOLDER_PUBLIC`；upload_queue.js:38-54 的历史退回分支已不会走到；`chunk_total` null/0 语义映射分散在 audio.js:133-134/:160、chunking.js:40 三处。
- **（G）静默失败掩盖 bug**。`updateQueueItem`（upload_queue.js:88-101）找不到 fragmentId 静默返回原数组；多处 `catch(e)` 吞异常仅返回空值（index.js:377-381、:551-554）。
- **（H）草稿覆盖边角**。`_maybeShowRecovery`（index.js:375-386）在 `onShow` 无条件 `setData({ draft: saved })`，可能用中断草稿覆盖页面上已有的正常草稿。
- **（I）环境判定靠源码常量**。`config.ENV = 'development'` 硬编码（config.js:29），无构建期注入；发版忘改会把开发者菜单与故障注入带上线（index.js:111、dev.js:18）。
- **（J）PostObject policy 未加 `content-length-range`**（oss_sign.js:75-83），仅靠 STS 边界约束大小。

### 3.2 FC 云函数（`apps/fc/`）

#### 职责与请求处理流程

- **issue-credential**（`issue_credential/handler.py`）：GET 存活探针；POST 走 `load_env` → `authorize_request`（JSON 校验 → 微信 code 换 openid → allowlist）→ `load_sts_env` → `parse_size`/`check_size` → `object_key_for` → `assume_role` 传 `single_key_policy` + 900s → 7 字段响应。
- **verify-upload**（`verify_upload/handler.py`）：鉴权流程与 issue-credential 一致，用子账号长期 AK 对该 key `head_object`，`verify_upload_result` 映射 verified/OBJECT_NOT_FOUND/SIZE_MISMATCH 三态。
- **Custom Runtime 入口**（`apps/fc/shared/app.py`）：云端启动命令为 `python3 app.py`；入口启动标准库 WSGI server，监听 `FC_SERVER_PORT` / `PORT` / 默认 `9000`，再把请求委托给函数包内的 `handler.handler`。
- 错误分层清晰：`FcConfigError`→500 `SERVER_MISCONFIGURED`（只列缺失变量名），`FcHttpError`→4xx，云调用异常→统一 500 不泄漏明文。

#### 安全评估

做得好：微信登录任何失败统一 401 `INVALID_CODE` 不泄漏 code/secret（wechat.py:29-52）；STS policy 单 key 无通配符、fragment_id 严格正则杜绝路径穿越（sts.py:30-33、:62-73）；审计日志 openid 只记 sha256 前 16 位 + 敏感字段名单双兜底（audit.py:35-58）；测试覆盖了「伪造 code 拿不到任何 STS/对象信息」的红线反例。

弱点：

- **请求体先读后鉴权、无大小上限（DoS 面）**：`authorize_request` 第一步 `read_json_body`（auth.py:47），`read_json_body` 按 `CONTENT_LENGTH` 直接 `stream.read(length)` 无上限（http.py:57-61）。匿名攻击者可发超大 body 撑爆内存。
- **微信调用放大**：每个格式合法的请求即使不在 allowlist 也会先真实外呼一次 jscode2session（auth.py:50 在 `check_allowlist` 之前），可被用来消耗微信接口配额。
- **无防重放机制**：接口层无 nonce/timestamp，唯一防重放来自微信 code 一次性；同一 fragment_id 可被反复签发 STS。风险有限，值得知悉。
- **STS policy region/account 用通配符**：`acs:oss:*:*:...`（sts.py:70）。key 精确所以整体风险低，严格最小权限应钉死 region/account。
- **两条路径凭证安全等级不对称**：verify-upload 的长期 AK 有整桶读权限，且与 issue 侧环境变量**同名** `ALIYUN_AK_ID/SECRET`（env.py:27-38）——若配同一子账号，该 AK 同时拥有 AssumeRole 和 OSS 读。建议两函数用不同子账号、各自最小授权。

#### 共享代码与部署

- 复用方式健康：两 handler 都 `import fc_shared`，云 SDK 全部 lazy import（sts.py:133-138、head.py:73-76），互不拖入对方依赖。
- 打包：`fc_deploy.package_function` copy 函数目录 → 复制 Custom Runtime 入口 `app.py` → `_vendor_shared` 复制共享包 → 按 requirements.txt 装依赖 → 确定性 zip；部署前自动备份、可一键回滚；部署后 curl 存活验证只接受 HTTP 2xx。

部署的坑：

- **跨平台依赖（最大的坑）**：`install_deps` 用 `uv pip install --target`（fc_deploy.py:552-559）**未指定目标平台**——macOS 打包、FC 跑 Linux。当前依赖恰好纯 Python 能跑，一旦引入 C 扩展依赖就会云端 import 崩。应加 `--python-platform manylinux` 类约束。
- **共享包 vendoring 仍需收紧**：Custom Runtime 入口 `app.py` 缺失已改为打包时报错，但 `_vendor_shared` 在 `fc_shared` 目录不存在时仍静默 return，会打出一 import 就崩的包且部署无告警。
- **依赖未固定版本**：两个 requirements.txt 均无 `==`，缺可复现性。

#### 代码质量问题

- `head.py:79-99`：判断「对象不存在」在取不到结构化 code 时回退对异常文本做 `"404"` 子串匹配（:93、:99、:21）——异常文本偶然含 404（如 request-id）会误判为 OBJECT_NOT_FOUND；反之真 404 无该文本会误判为存在进而 500。应改用 SDK 结构化 status_code。
- `head.py:85-92`：`unwrap` 递归仅防自环，两异常互相 unwrap 会无限递归（低概率）。
- `verify_upload/handler.py:96`：`verify_upload_result` 在 try/except 之外，与 issue 侧风格不一致。
- `wechat.py:50`：`errcode not in (0, None)` 假定 int，若微信返回字符串 `"0"` 会误判失败。
- `env.py:98-107`：`MAX_UPLOAD_BYTES` 非法值静默回退默认 50MB，配置写错无告警。
- 两个 handler 骨架约 80% 重复（GET 探针、异常分层、耗时日志），可抽 `wsgi_endpoint` 装饰器进一步去重。

### 3.3 Python Worker（`apps/worker/`）

#### 核心流程

```
cli.run (cli.py:24) → poller.run_worker_run (poller.py:455)
  → pipeline.run_worker_pipeline (pipeline.py:511)
    → run_pipeline_loop (pipeline.py:445)
        ├─ 启动恢复：recovery.recover + process_pending
        └─ 周期 run_pipeline_once (pipeline.py:375)
```

单轮处理：`RealOssSource.list_recordings`（poller.py:417）→ `plan_downloads` 纯逻辑决策（:177）→ `process_plan` 下载 `.part` + sha256 校验 + HeadObject 读 meta（:248）→ `audio.standardize`（audio.py:145，ffprobe 探测真实格式、WAV 直通/非 WAV 转 16k 单声道 PCM，失败留档 `inbox/failed/`）→ `manifest.build_manifest`（manifest.py:108）→ 转写工厂分发到 `nls.transcribe_via_nls`（nls.py:334，oss-url 异步轮询 / direct 直传两模式，退避 5s→15s→45s，50 分钟续签 URL）→ 原子落盘 transcript.json → transcript.txt → manifest 终稿 → 最后 0 字节 `.done`（pipeline.py:238-274）。

#### 可靠性设计

- **幂等**：只看 `.done`；同轮 `seen` 集合去重（pipeline.py:406-410）；任一阶段失败绝不建 `.done`。
- **原子写**：`atomic_write_text/json`（recovery.py:47-65）同目录临时文件 + `os.replace`；transcript 临时文件刻意放 `tmp/` 使中断残留可被恢复扫描识别（recovery.py:73）。
- **断点恢复**：`recover`（recovery.py:253）三段扫描；「有 audio.wav 无 .done」判为 pending 重转补齐（pipeline.py:282）。
- **锁**：`fragment_lock`（locks.py:41）flock，主轮询与 retranscribe 跨进程互斥，锁目录一致（pipeline.py:219、retranscribe.py:140）。

竞态/数据风险：

- **锁窗口过窄（次要竞态）**：`standardize` rename 与 manifest 初稿写盘在锁外（pipeline.py:178-216），transcribe 才进锁（:219）。并发 `retranscribe --force` 可能因缺 manifest 失败，或两条路径先后重复转写同一 fragment（串行但浪费 ASR 费用）。
- **`.lock` 文件永不清理**：建在 `tmp/<fid>.lock`（locks.py:37），recovery 与 `verify-no-stale` 都只清 `.transcript.json.tmp`（recovery.py:209、ops.py:151），随 fragment 数无限累积。
- **静默空转写**：NLS `SUCCESS_WITH_NO_VALID_FRAGMENT` 被当成功终态（nls.py:64、:306），空 transcript 也建 `.done`，不重试无告警——违背「绝对不丢」承诺，属数据质量隐患。

#### 包内容混杂

生产运行时真正需要约 12 个模块：`cli, poller, pipeline, audio, manifest, transcriber, nls, recovery, locks, config, paths, oss_admin`（外加 `fixtures` 中被生产依赖的 `probe_media`/`sha256_of`）。与生产同包的非生产模块：

| 模块 | 性质 |
|---|---|
| `fc_deploy.py`（611 行） | FC 打包/部署/回滚/日志——纯 DevOps |
| `fc_live.py`（556）/ `verify_upload_live.py`（464） | FC 云端联调 |
| `sts_escape.py`（268） | STS 越权安全测试 |
| `verify_prep.py`(924) | US-001 准备校验（却被 nls/poller lazy import 复用 SDK 构造——耦合点） |
| `miniprogram_lint.py`（218） | 小程序 JS 静态检查，与音频 worker 无关 |
| `e2e.py`（295）/ `e2e_scenarios.py`（268） | E2E 验收编排 |
| 各核心模块内嵌 `run_test_*` | pipeline.py 近 40% 是 `make test-*` 自包含用例 |

影响：wheel 带上无关代码；CLI 约 40 个命令中生产命令仅 `run`/`check-config`/`init-dirs`/`retranscribe`；真实 NLS 客户端构造逻辑藏在名为 `verify_prep` 的模块里（nls.py:410、:439），语义耦合混乱。

#### 代码质量问题

- **主循环阻塞（架构级倾向）**：`run_pipeline_once` 逐条同步 `process_part`（pipeline.py:407-441），内含同步 NLS 轮询；单条 fragment 最长可阻塞 2 小时（nls.py:297、:327 阻塞式 sleep），期间其他 fragment 全部排队，`poll.interval_seconds` 节奏形同虚设。
- `pipeline.py:88`：`_now_iso` docstring 写「本地时区」，实现依赖运行机时区，跨机器时间戳语义不稳定。
- `oss_admin.py:143`：`put_object` 的 `self._oss or self._import()` 与 `_client()` 的 import 路径重复，易混。
- 重复派生：transcriber.py:64 `transcript_json()` 与 manifest.py:167 `transcript_json_from_result` 做同一件事，生产走后者，前者近乎死代码。
- 异常吞没广泛：大量 `except Exception`（poller.py:263、pipeline.py:223/340/499、nls.py:426/492 等），detail 常只留 `type(exc).__name__`（nls.py:428），真实根因丢失，排障困难。
- retranscribe 计数不累积：每次新建 transcriber（retranscribe.py:311）使 `DailyCounter`（transcriber.py:118）重置，§6.8 当日成本统计对重转路径失真。
- `run_pipeline_loop` 的 `process_pending` 循环（pipeline.py:474）未包 try/except，防御性不足。

---

## 4. 修改建议（按优先级）

### 4.1 第一优先级：正确性与安全

| # | 问题 | 位置 | 修法 |
|---|---|---|---|
| 1 | FC 鉴权前读取无上限请求体（DoS 面）+ allowlist 前外呼微信 | `http.py:57-61`、`auth.py:47-50` | body 加 64KB 上限；可将 allowlist 快速失败前移 |
| 2 | 空转写静默标记成功，违背「绝对不丢」 | `nls.py:64,306` | 打 warning + manifest 标记 `no_valid_fragment`，便于人工复查 |
| 3 | 「对象不存在」靠 `"404"` 子串匹配，可能误判 | `head.py:93-99` | 改用 SDK 结构化 status_code |
| 4 | 小程序两套上传编排重复且 `_isOnline` 行为已分叉 | `queue_runtime.js:83-324` vs `uploads.js:111-386` | 统一到 `queue_runtime`，迁移测试，统一 `_isOnline` 语义 |

### 4.2 第二优先级：结构问题

| # | 问题 | 位置 | 修法 |
|---|---|---|---|
| 5 | Worker 包混装部署/联调/lint/E2E 工具 | `soniscope_worker` 全包 | 拆出 `soniscope_devtools` 包或移 `scripts/`；内嵌 `run_test_*` 抽到 tests/；NLS 客户端构造从 `verify_prep` 迁出 |
| 6 | FC 打包跨平台无约束 + 依赖不固定 + `fc_shared` vendoring 静默跳过 | `fc_deploy.py`、两个 requirements.txt | 加 `--python-platform manylinux`；requirements 固定版本；`fc_shared` 缺失改报错 |
| 7 | 主线程同步 SHA-256 卡 UI（ADR-2 规划未落实） | `index.js:630,580-596`、`sha256.js` | wasm 或异步分片计算 |
| 8 | 跨页并发驱动队列缺全局互斥 | `uploads.js:40-41`、`queue_runtime.js:33-34` | 引入 app 级单例调度器统一互斥 |

### 4.3 第三优先级：小问题清单

- `tmp/<fid>.lock` 永不清理（locks.py:37）——恢复扫描顺带回收。
- 单 fragment NLS 轮询可阻塞主循环 2 小时（nls.py:297,327）——单用户可接受，记录在案。
- `config.ENV` 硬编码（config.js:29）——构建期注入或发布 checklist 强制项。
- 两 FC 函数共用同名 AK 环境变量（env.py:27-38）——拆两个最小授权子账号。
- 异常收敛只留类型名丢根因（nls.py:428 等）——保留 message，必要时留 stack。
- 退避常量重复（uploader.js:28 / verify.js:16）；transcript 派生逻辑重复（transcriber.py:64 / manifest.py:167）。
- PostObject policy 加 `content-length-range`（oss_sign.js:75-83）。
- `MAX_UPLOAD_BYTES` 非法值静默回退（env.py:98-107）——加 warning。
- 草稿覆盖边角（index.js:375-386）；`updateQueueItem` 静默失败（upload_queue.js:88-101）。

---

## 5. 扩展性备注（现在不修）

当前「全量列举 OSS + 单进程同步流水线 + 本地 flock」的组合，天花板是单机单用户：

- flock 只在同机有效，多 Worker 实例会重复 list/下载/转写（无分布式租约）。
- 每轮全量列举 `recordings/`，对象规模增长后成本线性上升，延迟至少一个 `interval_seconds`。
- manifest 是唯一权威但无汇总索引，查「哪些待重转/失败」需全盘扫描（retranscribe.py:255、ops.py:191）。

PRD 明确这是单人 MVP，**为不存在的规模做设计是错误的**。建议只在 tech-spec 里补一条 ADR：规模化时的迁移路径为 OSS 事件通知（+MNS/任务队列）+ 分布式租约 + 状态索引。

---

## 6. 结语

这套架构的骨架——分层、安全边界、文件状态机、可测性纪律——值得保留；主要债务是**代码级重复与包边界**，而非架构方向。按 §4 优先级逐项收口即可。
