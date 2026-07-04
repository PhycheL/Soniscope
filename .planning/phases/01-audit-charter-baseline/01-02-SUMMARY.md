---
phase: 01-audit-charter-baseline
plan: 02
subsystem: audit
tags: [audit, hypotheses, do-not-fix, concerns-triage, d-08]

# Dependency graph
requires:
  - phase: none (wave 1)
    provides: "源材料 .planning/codebase/CONCERNS.md(29 条粗体线索)与 01-RESEARCH.md 分流盘点"
provides:
  - ".planning/audit/DO-NOT-FIX.md — RPT-05 登记表初稿:4 条 DNF 预录入(D-08),每条带 ⚠ intentional 标注与 git show 5927f36 核实的 path:line 证据"
  - ".planning/audit/HYPOTHESES.md — 25 条未验证假设(HYP-01~25),每条恰一个待验证维度(CON/CODE/TOOL/DOC/TEST),头部对账等式 25+4=29 机械可复核"
  - "Known Bugs 显式'已检查,无已知 bug 线索'负向记录(喂 RPT-08)"
  - ".planning/STATE.md 过时 Phase 1 dirty-tree 阻塞改写为已解除记录"
affects: [phase-02-contract, phase-03-code-toolchain, phase-04-docs-test-audit-05, phase-05-report-rpt-05, rpt-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "计数对账等式在台账头部,grep 机械可复核(HYP+DNF=CONCERNS 粗体条目数)"
    - "秘密类证据只引位置与模式名,不复制值本体(含已过期值)"
    - "证据行号一律出自 git show 5927f36:<path>,不读工作树"

key-files:
  created:
    - .planning/audit/DO-NOT-FIX.md
    - .planning/audit/HYPOTHESES.md
  modified:
    - .planning/STATE.md

key-decisions:
  - "DNF-04(小程序接收原始 STS 秘密)按 RESEARCH A3 以 D-08 '等'字延伸归入 DNF,条目内写明假设性质供 Phase 5 用户裁定"
  - "HYP 维度分布采纳 plan 建议不作调整:CON 1 / CODE 10 / TOOL 4 / DOC 6 / TEST 4"
  - "HYP-02 备注写明 CONCERNS.md 'deletions uncommitted' 半句已被基线核实推翻,仅'引用失效'半句待 Phase 4 验证"
  - "handler.py mypy 豁免双侧交叉引用:DNF-03(豁免本身故意)↔ HYP-23(仅验证行为测试补偿充分性)"

patterns-established:
  - "台账头部对账块:总数等式 + 机械计数命令 + 勘误记录(29 非 30)"
  - "HYP 条目五字段:来源/假设/待验证维度/状态/备注(可选)"

requirements-completed: [CHARTER-05]

coverage:
  - id: D1
    description: "DO-NOT-FIX.md 含 4 条 DNF,每条带 ⚠ intentional 标注与 @ 5927f36 证据"
    requirement: "CHARTER-05"
    verification:
      - kind: other
        ref: "grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md == 4; grep -c 'intentional' >= 4; grep -c '@ 5927f36' >= 4"
        status: pass
    human_judgment: false
  - id: D2
    description: "HYPOTHESES.md 25 条 HYP 与 DNF 4 条对账等于 CONCERNS.md 粗体线索 29 条,五维度短码均出现,含显式无 bug 线索记录"
    requirement: "CHARTER-05"
    verification:
      - kind: other
        ref: "HYP(25)+DNF(4)==grep -cE '^\\*\\*[^*]+:\\*\\*$' CONCERNS.md(29); 五维度 grep;'无已知 bug 线索' grep"
        status: pass
    human_judgment: false
  - id: D3
    description: "两台账文件秘密模式负向 grep 零命中;零 diff 不变量保持"
    verification:
      - kind: other
        ref: "! grep -qE 'OSSAccessKeyId=TMP\\.[A-Za-z0-9]{4,}|Signature=[0-9A-Za-z%+]{16,}' 两文件; git diff --stat 5927f36 -- apps/ scripts/ docs/ 为空"
        status: pass
    human_judgment: false
  - id: D4
    description: "STATE.md 过时 dirty-tree 阻塞改写为已解除记录,REQUIREMENTS 计数修正条目保留"
    verification:
      - kind: other
        ref: "grep '已解除' 命中;'决定阻塞' 零命中;'REQUIREMENTS.md 原统计' 仍命中"
        status: pass
    human_judgment: false

# Metrics
duration: 6min
completed: 2026-07-04
status: complete
---

# Phase 01 Plan 02: CONCERNS.md 线索分流 Summary

**CONCERNS.md 全部 29 条线索按 D-08 分流完成:4 条故意设计预录入 DO-NOT-FIX.md(RPT-05 初稿,证据经 git show 5927f36 逐条核实),25 条转 HYPOTHESES.md 未验证假设(每条恰一个待验证维度),另含 Known Bugs 显式无线索记录;STATE.md 过时 dirty-tree 阻塞改写为已解除**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-07-04T22:47:46Z
- **Completed:** 2026-07-04T22:53:30Z
- **Tasks:** 3
- **Files modified:** 3(2 新建 + 1 修改)

## Accomplishments

- **DO-NOT-FIX.md(RPT-05 初稿):** DNF-01~04 各带逐字 `⚠ intentional — do not "fix"` 标注、CONCERNS.md 来源、`path:line @ 5927f36` 证据(transcriber.py:144-165、config.js:8-10、pyproject.toml:30-32、sts.py:102-114,全部经 `git show 5927f36` 核实而非读工作树)、理由与分流依据;DNF-04 明示 A3 假设性质供 Phase 5 裁定
- **HYPOTHESES.md(Phase 4 AUDIT-05 工作底稿):** 25 条 HYP 按 CONCERNS.md 原节顺序 1:1 转写(标题原样沿用,零合并零改写),头部对账等式 `29 = 4 DNF + 25 HYP` 机械可 grep 复核,并记录 30→29 勘误;维度分布 CON 1 / CODE 10 / TOOL 4 / DOC 6 / TEST 4
- **可追溯交叉引用:** HYP-01↔HYP-20(FC 直转同根)、DNF-03↔HYP-23(mypy 豁免 vs 测试补偿)、HYP-11 预标"细化:范围外"(FC 直转目标态属章程排除项)、4 条 "acceptable for MVP" 条目备注 A4 分流依据
- **秘密红线守住:** Security 类条目只引位置与模式名(`OSSAccessKeyId=TMP.*`),两文件秘密模式负向 grep 零命中
- **STATE.md 清理:** Phase 1 dirty-tree 阻塞条目改写为含"已解除"的事实记录,REQUIREMENTS 计数修正条目原样保留

## Task Commits

Each task was committed atomically:

1. **Task 1: 创建 DO-NOT-FIX.md — D-08 四条预录入** - `94d50b5` (docs)
2. **Task 2: 创建 HYPOTHESES.md — 25 条线索转未验证假设** - `f9b20d8` (docs)
3. **Task 3: 清理 STATE.md 过时 dirty-tree 阻塞** - `d61d93e` (docs)

## Files Created/Modified

- `.planning/audit/DO-NOT-FIX.md` - RPT-05 登记表初稿,4 条 DNF 预录入,Phase 5 用户最终裁定
- `.planning/audit/HYPOTHESES.md` - 25 条未验证假设 + Known Bugs 显式无线索记录,Phase 4 逐条回填状态
- `.planning/STATE.md` - Blockers/Concerns 节过时条目改写为已解除记录

## Decisions Made

- 维度标注全部采纳 plan 建议清单,逐条核对后未发现更合理归属,零调整
- HYP-02 的假设范围收窄:CONCERNS.md 原条目含"deletions uncommitted"半句,已被基线核实推翻(工作树干净、删除已入库),备注写明只验证"引用失效"半句——保持 1:1 转写同时不把已证伪事实当假设

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. 与 plan 01-01 并行执行的 `.planning/audit/` 目录以 `mkdir -p` 幂等创建,无冲突(01-01 在隔离 worktree 中工作)。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 4(AUDIT-05)可用 HYPOTHESES.md 逐条关闭线索;对账等式保证 RPT-08 映射表可完整组装
- Phase 5 组装 RPT-05 时直接取 DO-NOT-FIX.md 四条,DNF-04 归属留待用户裁定
- 零 diff 不变量在本 plan 全程保持(`git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空)
- 待办:HYPOTHESES.md/DO-NOT-FIX.md 头部引用 `.planning/audit/CHARTER.md`(plan 01-01 产物,merge 后即闭合)

## Self-Check: PASSED

- FOUND: .planning/audit/DO-NOT-FIX.md
- FOUND: .planning/audit/HYPOTHESES.md
- FOUND: commit 94d50b5
- FOUND: commit f9b20d8
- FOUND: commit d61d93e

---
*Phase: 01-audit-charter-baseline*
*Completed: 2026-07-04*
