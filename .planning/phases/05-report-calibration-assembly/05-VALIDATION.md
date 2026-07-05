---
phase: 5
slug: report-calibration-assembly
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-05
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 本阶段为纯文档阶段:验证体系 = bash 机械门禁(grep/git 计数等式,项目 Phase 3/4 既有范式),无测试框架。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash 机械验证命令(grep/git,无测试框架) |
| **Config file** | none — 命令写死在各 PLAN 的 verify 与 REPORT.md 收尾章节 |
| **Quick run command** | `git diff --stat 5927f36 -- apps/ scripts/ docs/ \| wc -l`(期望 0) |
| **Full suite command** | 05-03 Task 3 的 8 项门禁全套(零 diff + 计数等式 + 秘密反扫 + 写入面复核) |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command(零 diff 快查)+ `git status --porcelain .planning/audit/findings/`(封版零改动)
- **After every plan wave:** Run 计数等式子集(findings 45/40、判定表 40、溯源 25+4=29)
- **Before `/gsd-verify-work`:** 全套 8 项门禁 green 且照录进 REPORT.md 收尾验证章节
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | RPT-02/03/04 | T-05-01/02 | 证据只引位置+模式名;findings 只读 | 机械 | `grep -c '^\| F-' .planning/audit/CALIBRATION.md` = 40 + findings porcelain 空 | ✅(命令即测试) | ⬜ pending |
| 05-01-02 | 01 | 1 | RPT-03 | — | 落账前用户批复(D-02/D-12) | checkpoint | `grep -q '状态: 呈报待批' .planning/audit/CALIBRATION.md` | ✅ | ⬜ pending |
| 05-01-03 | 01 | 1 | RPT-02/03/04 | T-05-02 | 仅 .planning/ 写入 | 机械 | `grep -q '状态: 已批准落账'` + 三态计数和 = 40 | ✅ | ⬜ pending |
| 05-02-01 | 02 | 2 | RPT-02/03/09 | T-05-01 | 不复制证据片段(D-15) | 机械 | `grep -c '^\| F-' .planning/audit/REPORT.md` = 40 + 三态和 = 40 | ✅ | ⬜ pending |
| 05-02-02 | 02 | 2 | RPT-01/04/05/06/07 | T-05-01 | 优点补录只引既有行号(D-16) | 机械+人读 | `grep -c '^### 置信·'` = 5 + `grep -c '^\| DNF-'` = 4 + WP 数一致 | ✅(RPT-06 引证核对为 human-check) | ⬜ pending |
| 05-03-01 | 03 | 3 | RPT-08 | T-05-01 | 只引既有台账行 | 机械 | 附录 A `^\| HYP-` = 25 且 `^\| DNF-` = 4 | ✅ | ⬜ pending |
| 05-03-02 | 03 | 3 | RPT-08 | T-05-01 | 聚类照搬 CALIBRATION 零改判 | 机械 | 附录 B CL 数 = CALIBRATION CL 数 + 附录索引存在 | ✅ | ⬜ pending |
| 05-03-03 | 03 | 3 | RPT-09 | T-05-01/02 | 秘密反扫零命中 + 零 diff | 机械 | 8 项门禁全套(见 05-03 Task 3 verify) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.(验证全部为既有 bash 命令,无需搭建任何测试基础设施;RESEARCH Validation Architecture 同判。)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RPT-06 每条优点的台账行号引用真实且未新采证 | RPT-06 | 引证语义核对无法 grep 判定 | 逐条打开引用的 HYPOTHESES/COVERAGE/矩阵行,确认行存在且语义支撑该优点(05-02 Task 2 human-check,end-of-phase) |
| 汇总表排序方向符合方法声明 | RPT-02 | 排序正确性需通读表 | 抽查 MEDIUM 段整体先于 LOW、同级内 S 先于 M |
| 判定理由与准则条款语义一致 | RPT-03 | 条款套用为语义判断(已经用户批准) | 抽查 BLOCKER/PRE-LAUNCH 各条理由与 B-*/P-* 条款吻合 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references(无 MISSING)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-05
