---
phase: 04-docs-config-test-audit
plan: 4
subsystem: audit-doc
tags: [audit, doc-claims, runbook, four-state, hyp-14, hyp-04, dead-ref]
requires:
  - .planning/audit/CHARTER.md(取证纪律/MEDIUM 锚点/九字段 schema/D-01 真云红线)
  - .planning/audit/DOC-CLAIMS.md(04-03 骨架与清单行格式)
  - .planning/audit/HANDOFF-PHASE4.md(DOC 节第 2/3 条 HYP-14 移交证据)
  - .planning/audit/HYPOTHESES.md(HYP-14 原文 :141-146、HYP-04 既有证据行 :46-53)
provides:
  - .planning/audit/DOC-CLAIMS.md runbook 4 节(CS ×19 + MA ×12 + DG ×19 + FD ×16 = 66 条四态销号)+ 04-04 批次机械对账表
  - .planning/audit/findings/docs-config.md F-DOC-03 + 04-04 批次导语
  - HYP-14 结论锚点(FD-16,drift → F-DOC-03)与 HYP-04 runbook 侧闭环锚点(FD-09),04-09 回填引用
  - dead-ref 4 处登记 → HYP-02(CS-09/CS-15/MA-01/DG-01,04-05 聚合立条)
affects: [04-05(AGENTS/README/config 收口 + HYP-02 聚合), 04-09(HYP-14/HYP-04 回填)]
tech-stack:
  added: []
  patterns: [四态销号清单范式续用, 控制台事实『无法静态核实』零猜测纪律, HYP 证据引用不重复采证]
key-files:
  created: []
  modified:
    - .planning/audit/DOC-CLAIMS.md
    - .planning/audit/findings/docs-config.md
decisions:
  - "HYP-14 判定为『发布文档未覆盖 ENV 翻转步骤』→ 立 F-DOC-03(MEDIUM):deployment-guide §6.3-6.4 与附录 A 零 ENV 项,四 runbook + AGENTS.md 全文检索零命中翻转步骤;唯一记载风险的 architecture-review(:70,:193)建议未落入任何 runbook"
  - "fc-deploy.md 与 fc_deploy.py 能力面对照零 drift:runbook 把控制台人工步骤(§2-3)与工具步骤(§5-9)划分清晰,未声称工具不具备的能力——HYP-04『环境重建依赖 runbook 保真度』的 runbook 侧口径闭环(FD-09 锚点)"
  - "cloud-setup §5.4 『./test/test_asr.py』判 dead-ref(实存 scripts/test_asr.py)登记 → HYP-02,与权威文档旧路径 3 处同走 04-05 聚合,不单独立条"
  - "『备份跳过』警示(fc-deploy:468)判 agree 并关联 F-TOOL-02 不重复立条:文档如实告知工具行为并给人工把关建议"
metrics:
  duration: ~25min
  completed: 2026-07-05
status: complete
---

# Phase 4 Plan 4: runbook 4 份深核与 HYP-14 全文档核对 Summary

runbook 4 份(cloud-setup 461 行 / mvp-acceptance 217 行 / deployment-guide 487 行 / fc-deploy 670 行)共 66 条声明四态销号完毕,纯控制台/云端/机器侧事实 14 条零猜测标注;HYP-14 全文档检索判定"发布文档未覆盖 config.js ENV 生产翻转步骤"立 F-DOC-03(MEDIUM),HANDOFF DOC 第 2/3 条移交证据显式销号;fc_deploy 能力面对照零 drift,HYP-04 runbook 保真度口径闭环。

## 完成任务

| Task | 名称 | Commit |
|------|------|--------|
| 1 | cloud-setup.md 与 mvp-acceptance.md 深核销号 | 44a5515 |
| 2 | deployment-guide.md 与 fc-deploy.md 深核销号 + HYP-14 全文档核对 | 5a9dae7 |
| 3 | runbook 批次 F-DOC 立条与机械对账 | 88e0d25 |

## 销号结果

- **cloud-setup.md(CS-01~CS-19):** agree 9 / drift 0 / dead-ref 2 / 无法静态核实 8;等式 9+0+2+8=19 ✓
- **mvp-acceptance.md(MA-01~MA-12):** agree 10 / drift 0 / dead-ref 1 / 无法静态核实 1;等式 10+0+1+1=12 ✓(make 目标存在性逐名 grep 核对,**零执行**——D-01 红线全程遵守)
- **deployment-guide.md(DG-01~DG-19):** agree 15 / drift 0 / dead-ref 1 / 无法静态核实 3;等式 15+0+1+3=19 ✓
- **fc-deploy.md(FD-01~FD-16):** agree 13 / drift 1(FD-16)/ dead-ref 0 / 无法静态核实 2;等式 13+1+0+2=16 ✓
- **批次合计:** 66 条(47+1+4+14=66 ✓);阶段累计 132 条(04-03 66 + 04-04 66)
- **DNF-02 闭环命中 ×5**(CS-08/MA-02/DG-09/DG-16/FD-12,issue-cedential 拼写),不占 F-ID
- **dead-ref 登记 4 处(→ HYP-02,04-05 聚合):** CS-09(cloud-setup:83 同步出现处引 docs/tech-spec.md、docs/PRD_v1.md 旧路径)、CS-15(cloud-setup:151 `./test/test_asr.py`,实存 scripts/test_asr.py)、MA-01(mvp-acceptance:3,5 权威链旧路径)、DG-01(deployment-guide:5 权威链旧路径)

## 发现(F-DOC 已用最大编号:**F-DOC-03**,04-05 从 F-DOC-04 续接)

- **F-DOC-03(MEDIUM,draft):** 发布文档未覆盖 `config.js:29` ENV 常量的生产翻转步骤——deployment-guide §6.3-6.4 发布流程与附录 A 清单零 ENV 项(§6.3 仅核对 URL);`git grep 'ENV'/'production'` 全文档检索命中全集仅 architecture-review(:58,70,193,风险已知未落实)、tech-spec:529、mvp-acceptance:138(均假设 production 已生效)。照文档发布即带 development 上线,开发者菜单与故障注入开关暴露给最终用户。修复 S 档(发布清单补两行)。关联 HYP-14 + HANDOFF DOC 第 2/3 条。

## HYP 结论锚点(待 04-09 回填引用)

- **HYP-14(FD-16):** 判定态 drift → F-DOC-03;命中/未命中行号全集在档(DOC-CLAIMS FD-16 行);销号引 HANDOFF-PHASE4.md DOC 节第 2、3 条(config.js:29 现值 + dev.js/fault_injection.js 三重门控证据直引,03-04 采证不重复)。
- **HYP-04(FD-09):** runbook 侧口径闭环——fc-deploy.md 八步骤清单与工具能力面五项(backup/package/update_code/rollback/logs)逐条对应,未声称函数创建/env 配置/触发器等工具不具备的能力;"环境重建依赖 runbook 保真度"半句的 runbook 保真度经本计划 66 条销号背书(发现级 drift 仅 F-DOC-03 一条,属步骤缺失非步骤失实)。

## Deviations from Plan

None - plan executed exactly as written.

## 交接备注

- 覆盖总表 runbook 4 行状态列均已改终态;剩余 17 行待 04-05 收口(AGENTS/README/config.js 等)。
- MA-05/T-26 与 FD-16 互指已建:mvp-acceptance 故障注入行 agree 判定显式指向 HYP-14 专项结论行。
- cloud-setup §8→§10 章节编号跳格(无 §9)记于节导语,纯编号跳格不涉声明失实,未立条。
- 零 diff 验证通过:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 空输出。

## Self-Check: PASSED

- .planning/audit/DOC-CLAIMS.md runbook 4 节 + 批次对账表 — FOUND
- .planning/audit/findings/docs-config.md F-DOC-03 + 04-04 批次导语 — FOUND
- Commits 44a5515 / 5a9dae7 / 88e0d25 — FOUND
