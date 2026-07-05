---
phase: 05-report-calibration-assembly
plan: 01
subsystem: audit-report
tags: [calibration, launch-gating, clustering, work-packages, markdown-ledger]
requires:
  - .planning/audit/findings/contract.md
  - .planning/audit/findings/code.md
  - .planning/audit/findings/toolchain.md
  - .planning/audit/findings/docs-config.md
  - .planning/audit/findings/test.md
  - .planning/audit/CHARTER.md
  - .planning/audit/DO-NOT-FIX.md
  - .planning/audit/TEST-AUDIT.md
provides:
  - .planning/audit/CALIBRATION.md
affects:
  - 05-02 (REPORT.md 组装的唯一判断来源)
  - 05-03 (附录组装与收尾验证)
tech-stack:
  added: []
  patterns:
    - 判断前置、组装机械化(Pattern 1)
    - 批准交互最小化:D-02/D-12 合并单次 checkpoint(Pattern 2)
    - 计数等式先写死、实跑照录(Pattern 3)
key-files:
  created:
    - .planning/audit/CALIBRATION.md
  modified: []
decisions:
  - "D-01/D-04 跨维度对齐扫描结论:零拟调整(六主题逐一对照,级差均有 CHARTER 锚点依据),经用户 approve-all 批准落账"
  - "D-08 真重复判定结论:6 组候选全部非真重复、零并入;40 条 ID 全保留"
  - "D-09/D-10/D-12:上线判定准则 B-1~B-3/P-1~P-3/PL-1 经用户批准定稿;40 条判定 BLOCKER 0 / PRE-LAUNCH 3 / POST-LAUNCH 37"
  - "D-11 总判定推导:CONDITIONAL GO(必做清单 = F-CODE-02、F-CODE-06、F-DOC-03)"
  - "RESEARCH 假设 A3 经用户确认:CHARTER schema 字段 8/9 台账回填由 CALIBRATION.md 承载,findings/*.md 封版不回写"
metrics:
  duration: ~25min
  completed: 2026-07-05
status: complete
---

# Phase 5 Plan 01: 汇总校准与判定落账 Summary

跨维度校准扫描(零拟调整)、真重复判定(零并入)、5 簇根因聚类、9 个修复工作包与经批准的三级上线判定准则 + 40 条逐条判定(0/3/37 → CONDITIONAL GO)全部落账新建 CALIBRATION.md,findings 封版零回写。

## What Was Done

### Task 1: CALIBRATION.md 呈报草稿(commit 47c018a)

- 以 `^### F-` 为唯一锚点逐条抽取 40 条真实发现(剔除 5 条 F-*-00 示例),现场 grep 复核分布:MEDIUM 11 / LOW 26 / INFO 3,S 32 / M 7 / L 1 / XL 0——与 RESEARCH 实测基准一致,未采用 CONTEXT.md 笔误计数。
- D-01 严重度对齐扫描:六主题(签名 URL 门禁面、门禁二值失效、契约镜像缺锁定、潜伏失配类、文档失实类、存在级观察)横向对照,全部同级一致或级差有 CHARTER 锚点依据 → 零拟调整(合法结果,显式记录)。D-04 工作量同法零拟调整。
- D-08 真重复判定:6 组候选逐一以"同一缺陷 + 同一修复动作"标准判定,全部非真重复(TEST 元发现归聚类互指,per Pitfall 6)。
- D-05/D-06 根因聚类:CL-01~05(key 派生多实现 / 契约镜像注释同步 / 失败路径静默化 / 门禁声明失真 / 文档叙述滞后);入簇 29 + 孤条 11 = 40,每簇附既有台账证据锚(TEST-AUDIT 成员归属等式、关联发现字段)。
- D-04/D-06 修复工作包:WP-01~09,成员并集 37 = 40 − 3 INFO − 0 副条,每包含成员/共同修复位置/包级工作量档(整体重估,注明理由)/依赖。
- D-09/D-10 判定准则 B-1~B-3/P-1~P-3/PL-1 + D-11 推导规则 + 40 行逐条判定表(文件内唯一 `| F-` 开行表)。

### Task 2: D-02/D-12 合并批量呈报(checkpoint:decision)

呈报五组内容(拟调整清单 0 条、并入判定 0 条、准则全文、判定抽样 = PRE-LAUNCH 3 条全量 + 相厄 8 条、A3 确认项)。**用户批复:approve-all(整批通过 ①~⑤,无逐条批注意见,2026-07-05)。**

### Task 3: 按批复落账终稿(commit 40ff93f)

- CAL 条目节与呈报节写入批准记录终态(批复原文、日期、方式);状态行改为 `状态: 已批准落账`;D-12 准则批准结论落账。
- 尾部对账等式实跑照录(命令 + 实际输出 + ✓):CAL 0 / CL 5 / WP 9 / 判定表 40 行 / 三态和 40 / findings 零改动 / 零 diff = 0;文件尾统一斜体总结行。

## Key Outcomes(供 05-02/05-03 机械引用)

| 裁定 | 终态 | 引用位置 |
|------|------|----------|
| 终级严重度/工作量 | 40 条原级即终级(零调整),无"经校准"标注需求 | CALIBRATION.md 逐条抽取清单 + CAL 条目节 |
| 并入副条 | 0 条 | 真重复并入判定节 |
| 聚类列(RPT-02) | CL-01~05,孤条 11 | 根因聚类划分节 |
| 处置列/工作包(RPT-04) | WP-01~09;INFO 3 条 acknowledge | 修复工作包划分节 |
| 上线判定列(RPT-03) | 40 行判定表(唯一 `| F-` 开行表) | 逐条上线判定表 |
| 总判定(RPT-01) | CONDITIONAL GO,必做清单 = F-CODE-02/F-CODE-06/F-DOC-03 | 判定表尾 D-11 推导 |

## Deviations from Plan

None - plan executed exactly as written.(Task 1 首次落盘时 D-08 候选表行误以 `| F-` 开头破坏判定表唯一性约束,提交前自查发现并在同一 task 内修正为序号首列,验证通过后才提交——属任务内自纠,非计划偏离。)

## Verification Evidence

- Task 1 自动验证:`| F-` 行数 = 40、三节标题命中、`状态: 呈报待批`、findings porcelain 空 → PASS
- Task 3 自动验证:`状态: 已批准落账`、判定表 40 行、三态计数 40、findings porcelain 空、`git diff --stat 5927f36 -- apps/ scripts/ docs/ | wc -l` = 0 → PASS
- 秘密反扫(COVERAGE 第 9 条同款模式)对 CALIBRATION.md:零命中(exit 1)
- 文件内无数值评分/小时估计(工作量仅 S/M/L/XL 档)

## Known Stubs

None — CALIBRATION.md 为终稿,无占位内容;批准记录字段全部落终态。

## Threat Flags

None — 本 plan 仅新建 `.planning/audit/CALIBRATION.md`,证据一律 `path:line @ 5927f36` + 模式名(T-05-01 缓解已执行,秘密反扫零命中);写入面仅 .planning/(T-05-02 缓解,零 diff 复核通过)。

## Self-Check: PASSED

- FOUND: .planning/audit/CALIBRATION.md
- FOUND: .planning/phases/05-report-calibration-assembly/05-01-SUMMARY.md
- FOUND: commit 47c018a(Task 1 呈报稿)
- FOUND: commit 40ff93f(Task 3 落账终稿)
- findings/ porcelain 输出 0 行(封版零改动)
