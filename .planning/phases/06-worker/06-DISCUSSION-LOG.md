# Phase 6: Worker 失败路径隔离与告警 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 6-Worker 失败路径隔离与告警
**Areas discussed:** 失败态落盘位置与格式, 隔离阈值取值与可配置性, 隔离后的恢复出口, 告警/诊断的暴露面, 失败类型范围(边界)

---

## 失败态落盘位置与格式

| Option | Description | Selected |
|--------|-------------|----------|
| 单一 JSON 账本 | inbox/failed/ledger.json,key=fragment_id;一个文件支撑 WKR-01/02/03,与转码留档同目录,单线程无并发写风险 | ✓ |
| 每 fragment 一个 JSON | inbox/failed/<id>.json 并列 <id>.part;去中心化但列清单需遍历目录 | |
| state/ 专用目录 | $SONISCOPE_HOME/state/ 分离诊断与中间文件;语义清但引入新顶层目录 | |

**User's choice:** 单一 JSON 账本
**Notes:** 与既有 inbox/failed/ 转码留档同置,operator 一处看全。纯进程内计数被排除(架构红线:状态须落盘可推导)。

---

## 隔离阈值取值与可配置性

| Option | Description | Selected |
|--------|-------------|----------|
| config 可配 + 共用阈值 | config.yaml poll 段新增 max_fragment_failures 默认 3,所有失败类型共用;Pydantic 校验,改值不改代码 | ✓ |
| 写死常量 + 共用 | 模块级 UPPER_SNAKE 常量;不动 schema 但改值需改代码重启 | |
| config 可配 + 按类型分开 | sha256 失配 1 次即隔离,转码 3 次;更精细但 schema/判定更复杂 | |

**User's choice:** config 可配 + 共用阈值
**Notes:** 默认 3 与既有 RETRY_DELAYS_SECONDS 最多 3 次一致;PollConfig 已是 Pydantic 校验入口。

---

## 隔离后的恢复出口

| Option | Description | Selected |
|--------|-------------|----------|
| 专用 clear-quarantine CLI | 新 CLI 子命令 + make 目标清空账本条目;与 retranscribe 正交,职责单一;隔离持久保留至 operator 处理 | ✓ |
| 扩展 retranscribe | 统一重处理入口,但需改 scan_fragments 前提,blast radius 更大 | |
| 自动过期重试 | last_seen 超 N 天重置;无需人工但可能周期回到无界循环 | |

**User's choice:** 专用 clear-quarantine CLI
**Notes:** 关键事实:retranscribe 面向已有 audio.wav 的 fragment 目录,而隔离对象在下载/标准化阶段就失败、从未生成 fragment 目录,两者正交。

---

## 告警/诊断的暴露面

| Option | Description | Selected |
|--------|-------------|----------|
| 日志 + 查询 CLI 两者 | 隔离时打含四要素告警日志行 + 新增 quarantine-list 查询 CLI;实时发现 + 事后排障,与 clear-quarantine 配套 | ✓ |
| 仅结构化日志 | 只打告警日志行;最小改动但需翻滚动日志看全貌 | |
| 仅诊断文件/CLI | 靠读 ledger.json/CLI,不打专门告警日志;少了实时告警信号 | |

**User's choice:** 日志 + 查询 CLI 两者
**Notes:** 告警日志四要素固定顺序 fragment_id/reason/attempt/next-action,便于 grep 与 pytest 断言。

---

## 失败类型范围(边界)

| Option | Description | Selected |
|--------|-------------|----------|
| 下载/标准化前置失败 | sha256 失配 + 下载 error + 探测/标准化失败;不含 NLS 转写失败;与 F-CODE-02 原始范围一致 | ✓ |
| 含 NLS 转写失败 | 更全但转写失败多为瞬时,可能误隔离,与 NLS 重试/process_pending 语义重叠 | |
| 仅字面三类 | 严格照 WKR-01 字面,不含下载 error;但下载 error 同样无界重试,会留缺口 | |

**User's choice:** 下载/标准化前置失败
**Notes:** NLS 转写失败发生在 audio.wav 已就绪后,由 process_pending 恢复且 NLS 自带 5/15/45s 重试,故排除。

---

## Claude's Discretion

- 账本 JSON 确切字段命名、schema 版本字段是否需要、CLI 子命令精确命名与 flag 形态 — 按仓库既有命名约定定稿。
- 隔离依据是账本本身(attempt >= 阈值)还是额外 skiplist 文件 — 倾向单一真相源,由研究确认 plan_downloads 集成最简形态。

## Deferred Ideas

- NLS 转写失败的隔离/计数 — 独立恢复语义,本 phase 不纳入。
- F-CON-04(verify-upload 校验 sha256)— POST-LAUNCH,仅交集的 _archive_failed docstring 修正纳入本 phase。
- F-CODE-03(孤儿 tmp 清理)/ F-CODE-04(.env 无界向上搜索)— POST-LAUNCH Worker 债务。
- 账本自动过期/TTL 重试 — 明确否决(D-06)。
