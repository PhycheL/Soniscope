---
phase: 04-docs-config-test-audit
plan: 3
subsystem: audit-doc
tags: [audit, doc-claims, prd, tech-spec, four-state, dead-ref]
requires:
  - .planning/audit/CHARTER.md(取证纪律/严重度锚点/九字段 schema)
  - .planning/audit/CONTRACT-MATRIX.md(状态词表/负面清单/机械对账范式)
  - .planning/audit/DO-NOT-FIX.md(DNF-01~04 负面清单依据)
  - .planning/audit/HYPOTHESES.md(HYP-16/HYP-21 原文与既有证据行)
  - .planning/audit/HANDOFF-PHASE4.md(HYP-16 文档一致性半句移交)
provides:
  - .planning/audit/DOC-CLAIMS.md(骨架四段 + PRD 30 条 + tech-spec 36 条四态销号)
  - .planning/audit/findings/docs-config.md 批次导语 + F-DOC-01/F-DOC-02
  - HYP-21 / HYP-16(半句)DOC 侧结论锚点(P-28/P-29/T-36,04-09 回填引用)
  - dead-ref 3 处登记 → HYP-02(04-05 聚合立条)
affects: [04-04(runbook 深核续接), 04-05(AGENTS/README/config 收口), 04-09(HYP 回填)]
tech-stack:
  added: []
  patterns: [CONTRACT-MATRIX 四态清单范式, 证据层/判断层分离, DNF 负面清单闭环]
key-files:
  created:
    - .planning/audit/DOC-CLAIMS.md
  modified:
    - .planning/audit/findings/docs-config.md
decisions:
  - "PRD 转引 tech-spec 章节的声明由 tech-spec 节承接,PRD 节只核 PRD 直接给出字面值/行为的声明(避免双计)"
  - "tech-spec §6.1 NODE_ENV 泛称判 agree(小程序无该概念,门控经 config.ENV 语义一致);§6.3 FC 依赖少列 tea-openapi 判 agree 括注登记不立发现(完整性小疏漏非误导)"
  - "fixtures 时长标称差(54s 标 ≈60s)判 agree:manifest 自文档化约定,sha256 为唯一权威"
metrics:
  duration: ~35min
  completed: 2026-07-05
status: complete
---

# Phase 4 Plan 3: DOC-CLAIMS 骨架与 PRD/tech-spec 深核 Summary

DOC-CLAIMS.md 四段骨架(四态词表/负面清单/23 对象覆盖总表)落成,权威链头两文档 66 条声明四态销号完毕:PRD 30 条零发现级 drift,tech-spec 36 条揪出 2 条 LOW drift(sha256 wasm 声明失实、Worker 依赖清单失实)立 F-DOC-01/02。

## 完成任务

| Task | 名称 | Commit |
|------|------|--------|
| 1 | DOC-CLAIMS.md 骨架(四态词表 + 负面清单 + 覆盖总表) | 27f96f7 |
| 2 | PRD_v1.md 深核 30 条声明四态销号 | 1401110 |
| 3 | tech-spec.md 深核 36 条销号 + F-DOC-01/02 立条 | cd10c8a |

## 销号结果

- **PRD_v1.md(P-01~P-30):** agree 26 / drift 0 / dead-ref 2 / 无法静态核实 2;等式 26+0+2+2=30 ✓
- **tech-spec.md(T-01~T-36):** agree 32 / drift 2 / dead-ref 1 / 无法静态核实 1;等式 32+2+1+1=36 ✓
- **DNF 闭环命中:** DNF-01(whisper 桩)×2、DNF-02(issue-cedential 拼写)×2——核实结论 + 闭环,不占 F-ID
- **dead-ref 登记 3 处(→ HYP-02,04-05 聚合):** PRD:204 `tests/fixtures/wx-login-fixture.json`(基线不存在,fc_live 实现自造伪 code)、PRD 全篇 `docs/tech-spec.md` 旧路径、tech-spec:3,80-81 `docs/PRD_v1.md`/monorepo 树旧路径

## 发现(F-DOC 已用最大编号:**F-DOC-02**,04-04 从 F-DOC-03 续接)

- **F-DOC-01(LOW,draft):** tech-spec §6.1 两处声称前端 sha256 用 wasm-crypto 避免主线程阻塞,实态为主线程同步纯 JS(sha256.js docstring 自认本期取舍)。关联 HYP-03。
- **F-DOC-02(LOW,draft):** tech-spec §6.3 声称 Worker 依赖 `alibabacloud-nls20180628`,实际未装该包;承载生产转写主路径的 legacy `aliyun-python-sdk-core` 未列入清单。关联 HYP-18。

## HYP 结论锚点(待 04-09 回填引用)

- **HYP-21(P-28):** PRD:15 与 NG-1/NG-2(:722-723)明示 LLM 润色/日稿展示范围外;代码实态零读取 UI(app.json 三页、miniprogram 零 transcript 命中)——口径互证 agree。
- **HYP-16 半句(P-29/T-36):** PRD(:15,27,596,725)与 tech-spec(:41,49,341,461)对单机单用户/本地盘权威/离线滞留的声明与代码实态(HYP-16 既有证据)口径一致;runbook 侧同口径核对留 04-04。销号引 HANDOFF-PHASE4.md DOC 节第 1 条。

## Deviations from Plan

None - plan executed exactly as written.

## 交接备注

- 措辞硬约束已守:占位词只出现在覆盖总表表行状态列(21 行未销 + 2 行已改终态),说明性文字零出现——04-05 Task 3 负向 grep 收口可直接跑。
- tech-spec §3.1 域名声明行(T-19)已备注"配置侧对照行见 config.js 节(04-05)"互指。
- 零 diff 验证通过:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 空输出。

## Self-Check: PASSED

- .planning/audit/DOC-CLAIMS.md — FOUND
- .planning/audit/findings/docs-config.md F-DOC-01/02 — FOUND
- Commits 27f96f7 / 1401110 / cd10c8a — FOUND
