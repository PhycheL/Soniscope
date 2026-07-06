---
phase: quick-260705-obh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/audit-methodology.md
autonomous: true
requirements: [QUICK-260705-OBH]
must_haves:
  truths:
    - "docs/audit-methodology.md 存在,包含 CONTEXT.md 锁定草稿的六章结构与全部实质内容"
    - "文档自包含:读者无需访问 .planning/ 即可套用方法论(.planning/audit/ 产物名仅作案例引用)"
    - "文档不含任何秘密/凭证明文(符合项目秘密红线)"
  artifacts:
    - "docs/audit-methodology.md"
  key_links:
    - ".planning/quick/260705-obh-docs-audit-methodology-md/260705-obh-CONTEXT.md <decisions> 内锁定草稿 → docs/audit-methodology.md 正文(转写关系,实质内容不变)"
---

<objective>
将已在 CONTEXT.md 中锁定的"代码审计方法论"权威草稿转写落盘为 `docs/audit-methodology.md`,作为可复用的通用审计方法论指南(以 SoniScope v1.0 审计里程碑为案例来源)。

Purpose: v1.0 审计里程碑已完成并通过审计,方法论散落在 .planning/ 产物中;本任务把主会话已综合完成的成果沉淀为正式产品文档,下次审计(本项目或其他项目)可直接套用。

Output: `docs/audit-methodology.md`(新建,唯一产品文件)。

注意:v1.0 审计里程碑的 docs/ 零 diff 红线已随里程碑完结解除,现在允许写入 docs/。
</objective>

<execution_context>
@/Volumes/Data/ProjectCode/my_soniscope/.claude/gsd-core/workflows/execute-plan.md
@/Volumes/Data/ProjectCode/my_soniscope/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/quick/260705-obh-docs-audit-methodology-md/260705-obh-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: 将 CONTEXT.md 锁定草稿转写为 docs/audit-methodology.md</name>
  <files>docs/audit-methodology.md</files>
  <action>
    读取 `.planning/quick/260705-obh-docs-audit-methodology-md/260705-obh-CONTEXT.md` 的 `<decisions>` 段,其中"内容基准(locked)"下两条 `---` 分隔线之间的全文即文档正文的权威草稿(从标题「# 代码审计方法论 — 从 SoniScope v1.0 审计里程碑提炼」起,到「## 六、一句话总结」章节末尾止)。

    按锁定决策将该草稿转写为新文件 `docs/audit-methodology.md`:

    1. **保持六章结构与实质内容不变**(用户锁定):一、审计是什么;二、方法论总纲:六条核心原则;三、怎么审计:五阶段流程;四、工具箱;五、需要注意什么(踩过的坑);六、一句话总结。允许排版规整与措辞微调;禁止增删章节、禁止改变任何结论/原则/坑条目的实质内容、禁止重新研读 .planning/ 重新综合。
    2. **语言约定**(用户锁定):中文正文 + 英文 ID/术语(沿 RPT-09 约定,如 HYP、DNF、CHARTER、BLOCKER 等保留英文)。
    3. **头部来源说明**(Claude 酌情,采纳 CONTEXT 建议):在主标题下加一行来源说明——提炼自 SoniScope v1.0 审计里程碑(审计基线 5927f36),日期 2026-07-06。
    4. **轻度去项目化**(Claude 酌情):正文以通用方法论口吻表述,SoniScope 具体数字与文件名(如 63 对象 × 9 面、config.js、.planning/audit/CHARTER.md)保留为"本次实践/案例"式引用;文档必须自包含,不要求读者能访问 .planning/。
    5. **秘密红线**:全文不得出现任何真实凭证值或秘密明文(草稿本身只含模式名与纪律描述,转写时不得额外引入示例凭证)。
    6. 保留草稿中的表格(五阶段流程表、工具箱表)与代码块(数据流管道图)原有形态。

    这是唯一的产品文件;不修改任何其他文件。
  </action>
  <verify>
    <automated>test -f docs/audit-methodology.md && [ "$(grep -cE '^## (一、审计是什么|二、方法论总纲|三、怎么审计|四、工具箱|五、需要注意什么|六、一句话总结)' docs/audit-methodology.md)" -eq 6 ] && ! grep -nE 'LTAI[0-9A-Za-z]{12,}|AKID[0-9A-Za-z]{13,}|BEGIN (RSA |EC )?PRIVATE KEY' docs/audit-methodology.md</automated>
  </verify>
  <done>
    docs/audit-methodology.md 存在;六个二级章节标题(一、审计是什么 / 二、方法论总纲 / 三、怎么审计 / 四、工具箱 / 五、需要注意什么 / 六、一句话总结)各出现一次;文档含头部来源说明行;凭证模式负向 grep 零命中;与 CONTEXT.md 锁定草稿逐章对照实质内容一致(六条原则、五阶段表、工具箱表 9 行、四组十四条坑全部在场)。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 仓库 → 公开文档 | docs/ 内容随仓库分发,写入即长期留存于 git 历史 |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-260705-01 | Information Disclosure | docs/audit-methodology.md | medium | mitigate | 转写时禁止引入任何真实凭证值(action 第 5 点);verify 门禁对 AK-ID/私钥等凭证模式做负向 grep,零命中方通过 |
</threat_model>

<verification>
- `test -f docs/audit-methodology.md` — 文件存在
- `grep -cE '^## (一、审计是什么|二、方法论总纲|三、怎么审计|四、工具箱|五、需要注意什么|六、一句话总结)' docs/audit-methodology.md` 输出 6 — 六章齐全
- `! grep -nE 'LTAI[0-9A-Za-z]{12,}|AKID[0-9A-Za-z]{13,}|BEGIN (RSA |EC )?PRIVATE KEY' docs/audit-methodology.md` — 无秘密模式命中
- `git status --porcelain docs/` 仅显示新增 docs/audit-methodology.md,无其他 docs/ 改动
</verification>

<success_criteria>
- docs/audit-methodology.md 落盘,六章结构与 CONTEXT.md 锁定草稿一致,实质内容零变更
- 文档头部含来源说明(v1.0 审计里程碑、基线 5927f36、日期)
- 中文正文 + 英文 ID/术语约定得到遵守
- 文档自包含,秘密模式零命中
- 除该文件外无任何其他产品文件被创建或修改
</success_criteria>

<output>
执行完成后创建 `.planning/quick/260705-obh-docs-audit-methodology-md/260705-obh-SUMMARY.md`
</output>
