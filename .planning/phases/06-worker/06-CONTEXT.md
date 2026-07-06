# Phase 6: Worker 失败路径隔离与告警 - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

关闭审计发现 `F-CODE-02`:让 Worker 对**下载/标准化前置阶段**的持久失败对象有失败计数、阈值隔离与显式告警,不再每轮无界重下重处理。交付 WKR-01/WKR-02/WKR-03。

**问题证据(@ 5927f36):**
- `apps/worker/src/soniscope_worker/poller.py:273` — sha256 失配删本地 `.part` 返回 `sha256_mismatch`,无按 fragment 的重试上限或失败历史;`pipeline.py:412-422` 仅记日志 `continue`,下一轮因无 `.done` 再次 `plan_downloads` 纳入 → 无界循环。
- `apps/worker/src/soniscope_worker/audio.py:134-142,221-235` — 转码/探测失败 `_archive_failed` docstring 称"不再重试",但只移走本地 `.part`;OSS 对象无 `.done` → 下一轮重下重试,同样无界,且与 docstring 语义相悖。

**本 phase 只澄清 HOW,不新增能力。** NLS 转写失败、verify-upload sha256 校验(F-CON-04)等均在边界外。
</domain>

<decisions>
## Implementation Decisions

### 失败态落盘位置与格式
- **D-01:** 用**单一 JSON 账本**记录按 fragment 的失败历史,位于 `inbox/failed/ledger.json`(与既有转码留档 `inbox/failed/<id>.part` 同目录)。key=`fragment_id`,value 至少含 `{attempt 计数, 最后失败原因/阶段, first_seen, last_seen}`。一个账本同时支撑 WKR-01(历史)、WKR-02(阈值判定)、WKR-03(诊断)。
- **D-02:** 不用纯进程内计数 — 架构红线要求 Worker 状态可从磁盘推导,重启不能丢失隔离状态。
- **D-03:** 账本写入沿用仓库既有原子写协议(temp → atomic rename),与 `inbox/`/`tmp`/`fragments/` 同文件系统前提一致。Worker 单线程轮询,账本无并发写风险。

### 隔离阈值取值与可配置性
- **D-04:** 阈值**进 `config.yaml`**(在 `PollConfig` 新增字段,如 `max_fragment_failures`),Pydantic 校验,**默认 3**(与既有 `RETRY_DELAYS_SECONDS` 最多 3 次的重试约定一致)。运维改值无需改代码。
- **D-05:** 所有隔离类失败类型**共用同一个阈值**,不按类型分开(sha256 失配虽极低可能,仍走同一阈值,保持逻辑简单)。

### 隔离后的恢复出口
- **D-06:** 隔离**持久保留**直到 operator 显式处理,不自动过期重试(避免周期性回到无界循环,违背"持久失败应被显式发现和处理"的初衷)。
- **D-07:** 新增一个**专用 CLI 子命令 + make 目标**(命名如 `clear-quarantine` / `worker-clear-quarantine`,支持 `FRAGMENT_ID=<id>` 单条或 `--all`)清空账本对应条目 → 下一轮重新下载。**不扩展 `retranscribe`**:`retranscribe` 用 `scan_fragments` 面向已有 `audio.wav` 的 fragment 目录,而隔离对象在 sha256/转码阶段就失败、从未生成 fragment 目录,两者正交,职责分离。

### 告警/诊断的暴露面
- **D-08:** WKR-03 用**日志 + 查询 CLI 两者**:
  - 隔离发生时打一条**显式告警日志行**,含四要素 `fragment_id` + 失败原因 + attempt count + 下一步处理建议(如"已隔离,运维用 clear-quarantine 解除")。沿用既有 `typer.echo` / 注入 `log` 通道。
  - 新增一个**查询 CLI**(如 `quarantine-list` / `worker-quarantine-list`)列出当前隔离清单,与 `clear-quarantine` 配套 — 一个看、一个清。

### 失败类型范围(边界锁定)
- **D-09:** 计入隔离账本的失败**仅限 fragment 目录创建前的前置失败**:`sha256_mismatch` + 下载 `error` + 探测/标准化(ffmpeg)失败。**不含 NLS 转写失败** — 转写失败发生在 `audio.wav` 已就绪之后,由 `process_pending` 恢复,且 NLS 自身已有 5/15/45s 重试;纳入会与既有语义重叠并可能误隔离可恢复片段。此范围与 F-CODE-02 原始判定一致。

### 幂等红线(不可回归)
- **D-10:** 既有 `.done` 幂等跳过路径必须保持不变(成功标准 #4)。隔离逻辑只作用于**无 `.done` 且失败计数超阈值**的对象;已完成 fragment 永远走原有跳过路径。

### `_archive_failed` docstring 修正
- **D-11:** 同步修正 `audio.py` `_archive_failed` docstring 中"不再重试"的错误表述,使其与新的隔离语义一致(留档本身不阻止重试,阈值隔离才阻止)。

### Claude's Discretion
- 账本 JSON 的确切字段命名、schema 版本字段是否需要、CLI 子命令的精确命名与 flag 形态 — 交给 planning/研究阶段按仓库既有命名约定(`snake_case`、UPPER_SNAKE 常量、每 make 目标映射一 CLI 子命令)定稿。
- 隔离对象在账本外是否额外落一个 skiplist 文件,还是账本本身即隔离依据(attempt >= 阈值即视为隔离) — 倾向后者(单一真相源),但由研究确认与 `plan_downloads` 的集成点最简。
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审计发现(修复输入 — 不重新解释已批准判定)
- `.planning/audit/findings/code.md` §F-CODE-02 — 本 phase 的唯一发现输入:证据行号、严重度、修复建议(计数/隔离/告警三件套 + docstring 修正)。
- `.planning/audit/REPORT.md` — PRE-LAUNCH 必做清单与工作包 WP-03(承载 F-CODE-02)。

### 需求与路线图
- `.planning/REQUIREMENTS.md` §Worker Failure Isolation — WKR-01/02/03 验收口径。
- `.planning/ROADMAP.md` §Phase 6 — Goal 与 4 条 Success criteria(含 pytest 覆盖多轮失败/阈值隔离/告警诊断/既有成功幂等跳过)。

### 待修改代码
- `apps/worker/src/soniscope_worker/poller.py` — `process_plan`(sha256 失配 `:273`)、`plan_downloads`(隔离跳过集成点)、`poll_once`、`ObjectOutcome`(status 取值 downloaded/sha256_mismatch/error)。
- `apps/worker/src/soniscope_worker/audio.py` — `standardize`、`_archive_failed`(`:134`)、探测/转码失败路径(`:185,225`)。
- `apps/worker/src/soniscope_worker/pipeline.py` — `:412-422` 消费端处理 outcome、主循环入口(`:510`)。
- `apps/worker/src/soniscope_worker/config.py` — `PollConfig`(`:51`)新增阈值字段 + Pydantic 校验 + summary 打印(`:93`)。
- `apps/worker/src/soniscope_worker/cli.py` — 新增 CLI 子命令(`:27` 委托模式)。
- `apps/worker/src/soniscope_worker/retranscribe.py` — 仅参考其 CLI/幂等模式,**不修改语义**(正交)。
- `Makefile` — 新增 make 目标映射新 CLI 子命令(参考 `:119` retranscribe 目标形态)。

### 关联发现(边界外,勿顺带修)
- `.planning/audit/findings/contract.md` §F-CON-04 — 修复建议提及可合并,但 F-CON-04 是 POST-LAUNCH,**不在 v1.1 范围**。仅修正 `_archive_failed` docstring 这一交集动作。
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **原子写协议**:`recovery.py::atomic_write_json` / `create_done_marker` 已实现 temp→rename,账本写盘可复用。
- **文件锁**:`locks.py::fragment_lock` 保证同 `fragment_id` 不并发处理;账本读改写若需要可复用同锁。
- **CLI 委托模式**:`cli.py` 每子命令 lazy-import 实现模块 + `typer.echo` 注入 log;新命令照此。
- **Makefile 目标映射**:每 make 目标 shell 到 `uv run python -m soniscope_worker <subcommand>`(参考 `retranscribe` 目标)。
- **config summary 打印**:`SoniScopeConfig` summary 已按段落打印,新阈值字段加一行即可。

### Established Patterns
- **纯逻辑 + 注入 IO**:账本判定(是否超阈值/是否隔离)应为纯函数,IO(读写 ledger.json)注入,单测不触网 — 这是双语言仓库核心模式,成功标准 #4 的 pytest 靠它实现。
- **磁盘即权威状态**:无 DB/队列,隔离状态必须落盘可推导(D-01/D-02 由此)。
- **失败态在 fragment 目录外**:sha256/转码失败发生在 fragment 目录创建前,账本与留档都放 `inbox/failed/`,不污染 fragment 目录(与 F-CODE-03 孤儿 tmp 边界一致)。
- **stable 状态字符串常量**:`ObjectOutcome.status`、`STAGE_*` 均模块级常量并被测试断言;隔离原因/状态也应用常量。

### Integration Points
- **隔离跳过注入点**:`plan_downloads`(poller.py:177)决定下载哪些对象 — 隔离判定应在此读账本,把超阈值 fragment 从 `to_download` 排除(类比现有 `.done` → `skipped_done`,可新增 `skipped_quarantined`)。
- **计数递增点**:`process_plan` 的 `sha256_mismatch`/`error` 返回处 + `standardize` 的失败留档处,失败即递增账本。
- **告警发出点**:计数达阈值的那一次,打显式告警日志。
</code_context>

<specifics>
## Specific Ideas

- 账本文件建议 `inbox/failed/ledger.json`,与既有 `inbox/failed/<id>.part` 转码留档并置,operator 一处看全。
- 告警日志四要素固定顺序,便于 grep 与未来 pytest 断言:`fragment_id` / reason / attempt / next-action。
- `clear-quarantine` 与 `quarantine-list` 成对,命名与 make 目标风格对齐现有 `retranscribe` / `test-*`。
</specifics>

<deferred>
## Deferred Ideas

- **NLS 转写失败的隔离/计数** — 转写阶段失败(fragment 目录已建)有独立恢复语义与 NLS 自带重试,本 phase 不纳入;若未来发现转写侧也无界重试,另开条目。
- **F-CON-04(verify-upload 校验 sha256)** — POST-LAUNCH,独立工作包,不在 v1.1。
- **F-CODE-03(孤儿 `*.tmp` 清理)/ F-CODE-04(`.env` 无界向上搜索)** — 同为 POST-LAUNCH Worker 债务,不在本 phase。
- **账本自动过期/TTL 重试策略** — 明确否决(D-06),若未来运维反馈手动清除负担过重再评估。

### FC 直转迁移(`docs/fc-transcribe-design.md`)时的隔离复用与新增面

> 背景:分析确认 F-CODE-02 的**问题内核不在具体代码行,而在"用『完成标记缺失』做幂等 + 无界重处理 + 无计数/阈值/告警"这个模式**。FC 直转迁移会删除本 phase 改动的 `poller.py` 下载校验循环与 `audio.py._archive_failed`(§3.6/§5.5 退役音频下载+ffmpeg+audio.wav 主干),但该模式在新架构原样复活。属独立里程碑(REQUIREMENTS.md Out of Scope),此处仅登记,不在 v1.1 动手。

- **对账补转循环 = F-CODE-02 同构重现**:`docs/fc-transcribe-design.md` §3.6 role #1 "现有 poller 骨架降频复用",对 `recordings/` 减 `transcripts/` 做差集补转。持久失败音频(NLS 永远转不出)永远缺 `transcripts/<date>/<id>.md`(§3.3 步骤 2 的完成标记),因而每个对账周期被重新 invoke FC → 无界循环,且带云计费放大器(每次 invoke = FC 驻留 + 一次 NLS SubmitTask;§3.3 的 FC 异步 3 次重试是**每次 invoke 清零重来**,无跨周期全局 attempt 计数)。§3.6 仅一句"持续失败的记入失败清单",无阈值/排除/告警/解隔离出口。
- **迁移时的复用点**:本 phase 的隔离抽象(按 fragment_id 失败计数账本 + config 阈值 + 从工作集排除 + 显式告警 + clear-quarantine CLI)正是 §3.6 那句"失败清单"缺失的机制。迁移只需把隔离判定的输入从 `plan_downloads` 的下载集**平移**到 `recordings−transcripts` 差集——同一个纯逻辑判定函数换输入。**为此本 phase 落地时应有意把隔离判定写成与工作集解耦的纯函数(判据:attempt ≥ 阈值 → 排除),而非硬编进 poller 下载路径**,否则会随 poller 一起被删。(动机补注 D-10 与 code_context "隔离跳过注入点"。)
- **迁移时新增的两个隔离面(本 phase 不覆盖)**:① FC 异步调用的失败 Destination / 死信是否接告警(§3.2 仅"便于观测",未接告警);② NLS filetrans 侧的持久失败(损坏/不支持格式音频)——现状 ffmpeg 失败在 Worker,迁移后变成 FC 无状态函数内的 NLS 转写失败,失败历史需回写 OSS(如 `transcripts/failed/` 旁账本)或由对账层统一持有。
- **迁移前需先对齐的文档张力(不影响 v1.1)**:`docs/fc-transcribe-design.md` 开头称"已决策,部署阶段立即实施",与 `.planning/PROJECT.md` / `REQUIREMENTS.md` 将 FC 直转列为 Out of Scope、另开里程碑的口径冲突;启动迁移里程碑前先对齐"是否立即实施"。
</deferred>

---

*Phase: 6-Worker 失败路径隔离与告警*
*Context gathered: 2026-07-06*
