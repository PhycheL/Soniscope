# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — 上线前审计

**Shipped:** 2026-07-06
**Phases:** 5 | **Plans:** 25 | **Sessions:** not tracked

### What Was Built

- 审计章程、严重度体系、工作量分档、发现 schema 与零 diff 基线。
- FC / Worker / 小程序三侧契约漂移矩阵、往返校验佐证与跨语言契约测试配方。
- CODE / CONTRACT / DOC / TEST / TOOL 五维度发现台账与最终 40 条发现汇总。
- 最终报告、附录 A/B、校准台账、WP-01~09 修复工作包与 DNF/优点盘点。

### What Worked

- 先钉 baseline 和 schema,再收集证据,避免后续发现口径漂移。
- 所有工具输出都经过人工核实后入账,报告可追溯性强。
- 独立 verification 与 milestone audit 给出了清晰的 23/23 requirements、5/5 phases、0 overrides 结论。

### What Was Inefficient

- SUMMARY one-liner 自动抽取混入了执行噪声,closeout 时必须人工清理 MILESTONES.md。
- 本仓库 `.codex/gsd-core` 缺 `bin/lib/cli-exit.cjs`,需要改用全局 `/Users/bemied/.claude/gsd-core` 执行官方查询。
- 部分 GSD 簿记字段与当前实际状态不同步,例如 STATE.md 在归档前仍指向 Phase 05 executing。

### Patterns Established

- 审计型里程碑应把最终结论写成可执行 backlog:发现 ID、严重度、上线判定、工作包、依赖。
- Do NOT fix 登记表与优点盘点必须和 findings 同等保留,防止修复阶段误改已裁定设计。
- 契约审计应使用生产者-消费者矩阵和样本往返校验,避免只看单边实现。

### Key Lessons

1. 里程碑收尾前先跑 `audit-open` 和 `init.manager`;两者比手读 ROADMAP 更适合作为 closeout gate。
2. GSD CLI 自动归档只能做机械部分;PROJECT.md、ROADMAP.md、MILESTONES.md 和 retrospective 仍需要人工判断。
3. 修复里程碑应先处理 PRE-LAUNCH 三项,再处理 POST-LAUNCH 工作包,不要把 40 条发现平铺执行。

### Cost Observations

- Model mix: not tracked
- Sessions: not tracked
- Notable: 阶段多、文档多时,稳定 schema 和机械对账比一次性长报告更省返工。

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | not tracked | 5 | 从功能开发转为证据驱动审计,并建立可复用审计方法论 |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Diff Scope |
|-----------|-------|----------|-----------------|
| v1.0 | pytest collected 567; node tests 126 | Python 73%; node 92.73% | apps/, scripts/, docs/ 相对审计 SHA 零 diff |

### Top Lessons (Verified Across Milestones)

1. 审计和修复必须分里程碑,否则 baseline、证据行号和风险口径会互相污染。
2. 文档、配置、测试与工具链要和代码同等审计;上线风险不只来自业务代码。
