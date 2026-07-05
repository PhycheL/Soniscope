---
phase: 04-docs-config-test-audit
plan: 5
subsystem: audit-doc
tags: [audit, doc-claims, hyp-02, hyp-05, hyp-06, hyp-14, dead-ref, dnf-02, doc-closeout]
requires:
  - .planning/audit/CHARTER.md(取证纪律/LOW-INFO 锚点/九字段 schema/D-06 目标态排除)
  - .planning/audit/DOC-CLAIMS.md(04-03 骨架 + 04-04 runbook 4 节)
  - .planning/audit/DO-NOT-FIX.md(DNF-01/DNF-02 闭环条目)
  - .planning/audit/HYPOTHESES.md(HYP-02 :29-35 / HYP-05 :55-61 / HYP-06 :63-69 假设原文)
  - .planning/audit/HANDOFF-PHASE4.md(DOC 节第 2/3 条 HYP-14 移交证据)
  - .planning/phases/04-docs-config-test-audit/04-04-SUMMARY.md(F-DOC 编号基数 03;dead-ref 4 处移交)
provides:
  - .planning/audit/DOC-CLAIMS.md 全量收口:AGENTS.md(AG-01~39)+ README×3(R/RF/RM 13 条)+ config.js(CF-01~08)+ 两 JSON 普审(PC/AJ 6 条)+ 普审级 5 文档 + 目标态 2 文档引用级 + 存在级登记 + DOC 总机械对账 + 尾注
  - .planning/audit/findings/docs-config.md F-DOC-04~08 五条 + 04-05 批次导语
  - ROADMAP 成功判据 1 两条点名线索核实结论(issue-cedential → CF-02 闭环 DNF-02;AGENTS.md 死链 → AG-01~17 + F-DOC-06)
  - 6 条 DOC HYP 回填锚点(HYP-02/05/06/14/16/21)供 04-09 回填
affects: [04-09(HYP 回填与阶段收尾)]
tech-stack:
  added: []
  patterns: [四态销号清单范式续用, 聚合立条(D-12 同款), 存在级证据登记(D-09), 目标态引用级审计(D-06)]
key-files:
  created: []
  modified:
    - .planning/audit/DOC-CLAIMS.md
    - .planning/audit/findings/docs-config.md
decisions:
  - "AGENTS.md wasm-crypto(:53)与 nls20180628(:58)两处与 tech-spec 同款失实声明判 drift 共证既有 F-DOC-01/F-DOC-02,不另立条(HYP-03 已裁定不复判)"
  - "AGENTS.md ~/SoniScope 配置回退声明(:110)与 paths.py 实态及 tech-spec/deployment-guide 双文档口径同时冲突 → 独立立 F-DOC-04(LOW)"
  - "三文件『现状/后续 story』滞后叙述(AGENTS:25,89 / fc README:31-34 / mp README:33-35)同根聚合一条 F-DOC-05(LOW),不逐文件立条"
  - "HYP-02 聚合条 F-DOC-06 census 修正:multi-user-design.md:600 为 04-RESEARCH 预核(3 处)之外的实测新增命中,设计文档实为 4 处;us-001-manual.html:471 机械命中计入底数但内容不审(存在级纪律)"
  - "domain.md/issue-tracker.md 引用的 CONTEXT.md/docs/adr//.scratch/ 基线不存在但声明自带懒创建语义(domain.md:12 明示 proceed silently)——判非死链,已审无发现"
  - "config.js 深核零 drift:8 条全 agree,配置侧与文档侧(cloud-setup/tech-spec/PRD/AGENTS)四文档字面值逐字符一致,头注一致性自证属实"
metrics:
  duration: ~35min
  completed: 2026-07-05
status: complete
---

# Phase 4 Plan 5: DOC 维度收口(AGENTS/README/config 深核 + 聚合立条)Summary

DOC 维度 23 对象四层全收口:AGENTS.md 39 条销号(HYP-02 主战场 17 处死链逐处登记)、README×3 + config.js + 两 JSON 共 27 条销号、普审级 5 文档与目标态 2 文档引用级审计完毕;聚合立条 5 条(F-DOC-04~08,含 HYP-02 死链聚合 LOW 与 HYP-05/06 两条 INFO);ROADMAP 成功判据 1 两条点名线索核实结论落档;阶段累计 198 条声明四态销号,总对账等式闭合。

## 完成任务

| Task | 名称 | Commit |
|------|------|--------|
| 1 | AGENTS.md 深核(HYP-02 主战场)与 README×3 深核 | 43c3219 |
| 2 | config.js 深核与 project.config.json/app.json 普审(D-08) | 6d0f8c2 |
| 3 | 普审/引用级/存在级审计、聚合立条与 DOC 收口 | 1a1a4f1 |

## 销号结果(04-05 批次 66 条)

- **AGENTS.md(AG-01~AG-39):** agree 17 / drift 4 / dead-ref 17 / 无法静态核实 1;等式 17+4+17+1=39 ✓
- **README.md(R-01):** 1 条 agree(基线仅 2 行,照实登记)
- **apps/fc/README.md(RF-01~06):** agree 5 / drift 1(RF-06 现状节占位声明 → F-DOC-05)
- **apps/miniprogram/README.md(RM-01~06):** agree 5 / drift 1(RM-06 骨架声明 → F-DOC-05)
- **config.js(CF-01~08):** agree 8 / 零 drift;CF-02 为 issue-cedential 核实结论行(闭环 DNF-02);CF-08 为 ENV 现值 HYP-14 配置侧证据行;闭合 04-03/04-04 互指(T-11/T-19/CS-01/CS-08/CS-12)
- **project.config.json(PC-01~03):** agree 2 / 无法静态核实 1(PC-02 平台真值,RESEARCH OQ2 口径);**app.json(AJ-01~03):** agree 3(三页四件套 12 文件静态复核通过)
- **普审级 5 文档:** 结论行 5 条——architecture-review/domain/issue-tracker/triage-labels 已审无发现;transcribe-approach-comparison dead-ref ×1(:5 → HYP-02)
- **目标态 2 文档(引用级,D-06):** 节首均显式标『目标态对照未审(章程排除)』;FT-01 + MU-01/02 共 dead-ref 4 行登记;现状代码引用实存核对通过,无明显自相矛盾
- **存在级 3 组:** PNG ×4 / drawio / us-001-manual.html 已登记;HYP-05 底数(1003 文件、28,227,670 字节 ≈28 MB)与 HYP-06 证据(四目录 54/440/420/468 文件;execute-plan.md 三处 blob 各异实证漂移)在档
- **DNF 闭环命中:** DNF-02 ×4(CF-02/AG-29/AG-38/RF-01/RM-03 内)、DNF-01 ×2(AG-21/AG-34),均不占 F-ID

## DOC 总对账(收口)

- 四层对象:11 深核 + 7 普审 + 2 引用级 + 3 存在级 = **23** ✓,覆盖总表 23 行全部终态(`grep -c '待审'` = 0)
- 编号清单:66(04-03)+ 66(04-04)+ 66(04-05)= **198** 条;四态合计 146 agree + 9 drift + 24 dead-ref + 19 无法静态核实 = 198 ✓
- drift 去向 9 处全闭环(F-DOC-01×2 共证 / 02×2 共证 / 03 / 04 / 05×3);dead-ref 全量 → HYP-02(F-DOC-06 聚合,P-26 fixture 异源死链以附注并档)

## 发现(F-DOC 最终编号:**F-DOC-08**;本计划立 5 条)

- **F-DOC-04(LOW,draft):** AGENTS.md:110 声称未设置 SONISCOPE_HOME 时回退 `~/SoniScope/config.yaml`,实态 paths.py 无任何兜底直接报错,与 tech-spec/deployment-guide 双文档口径同时冲突。修复 S 档。
- **F-DOC-05(LOW,draft):** AGENTS.md(:25,89)与两份子 README(fc:31-34 / mp:33-35)的"现状/后续 story"叙述停留在早期 story 时点,声称占位/骨架而基线已全量实现。修复 S 档。
- **F-DOC-06(LOW,draft,HYP-02 聚合):** 权威文档迁移后全仓 10 文件 ≈47 处旧路径引用未随迁——AGENTS.md 17 处为主体(导航双表整体失效),census 含设计文档 4 处(预核 3 处 + 实测 :600 新增)、runbook 4 处、自引用 22 处、普审/存在级各 1 处;附注 CS-15 与 P-26 两处异源死链并档。修复 S 档(批量替换,新路径含空格需转义)。
- **F-DOC-07(INFO,draft,HYP-05):** vendored `docs/example/start-fc-main/` 1,003 文件 ≈28 MB 整仓入库(CHARTER INFO 锚点逐字点名)。
- **F-DOC-08(INFO,draft,HYP-06):** agent 脚手架四目录重复且独立漂移已实证(同名工作流文件三处 blob 各异)。

## ROADMAP 成功判据 1 线索闭环

- **issue-cedential 拼写域名:** 核实结论落 DOC-CLAIMS.md **CF-02**(显式『核实结论』字样)——五处文档登记逐字符同值、行内注释与 lint 拼写守卫自证系 Aliyun 分配真实 URL,agree 闭环 **DNF-02**,不立 F-DOC,可机械检索(`grep '核实结论' + 'DNF-02'`)。
- **AGENTS.md 引用已删除文档:** 17 处旧路径引用逐处登记(**AG-01~AG-17**,每行 dead-ref → HYP-02)并聚合立条 **F-DOC-06**,`→ HYP-02` 闭环。

## 6 条 DOC HYP 回填锚点(04-09 回填引用)

| HYP | 锚点位置 |
|-----|----------|
| HYP-02 | DOC-CLAIMS AG-01~17 逐处登记 + 各节 dead-ref 登记行 + findings F-DOC-06 聚合条(census 全量行号);"deletions uncommitted"半句已被基线推翻的口径在 F-DOC-06 关联字段复述 |
| HYP-05 | DOC-CLAIMS §存在级登记 vendored 底数(1003 文件/28,227,670 字节)+ F-DOC-07 |
| HYP-06 | DOC-CLAIMS §存在级登记四目录并存与 blob 漂移抽样 + F-DOC-08 |
| HYP-14 | FD-16(文档侧,04-04)+ CF-08(配置侧现值,本计划)+ F-DOC-03 |
| HYP-16 | P-29 + T-36 结论行(04-03;runbook 侧 04-04 同口径) |
| HYP-21 | P-28 结论行(04-03) |

(HYP-11 属目标态章程排除,引用级节未涉内容对照,04-09 按 D-14"细化:范围外"关闭。)

## Deviations from Plan

- **[census 修正] multi-user-design.md:600 实测新增命中:** 04-RESEARCH 预核记设计文档旧路径命中 3 处(fc-transcribe:5 + multi-user:5,599),本计划全量 grep 实测 multi-user-design.md:600(`docs/PRD_v1.md`)亦命中,设计文档实为 **4 处**——F-DOC-06 census 按实测登记并在条目内标注修正,MU-02 行同步说明。属证据完备性修正,不改判定结论。
- 其余按计划执行,无偏差。

## 交接备注

- 覆盖总表 23 行全部终态,`grep -c '待审' DOC-CLAIMS.md` = 0、`grep -cE '待定|TODO'` = 0,可机械验收。
- HYPOTHESES.md 本计划未动(锚点就位,回填统一由 04-09 执行)。
- 零 diff 验证通过:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 空输出(T-04-12 缓解落实,写入面仅两个 .planning 文件)。
- 证据中 URL/appid 均为仓库明文非秘密,照 CHARTER 口径引用;本批次未涉任何凭证模式命中(T-04-11 缓解落实)。

## Self-Check: PASSED

- .planning/audit/DOC-CLAIMS.md 收口(尾注落款 + 总对账节)— FOUND
- .planning/audit/findings/docs-config.md F-DOC-04~08 + 04-05 批次导语 — FOUND
- Commits 43c3219 / 6d0f8c2 / 1a1a4f1 — FOUND
