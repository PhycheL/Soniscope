# Phase 5: 汇总校准与报告组装 - Research

**Researched:** 2026-07-05
**Domain:** 审计发现校准、去重聚类与结构化报告组装(纯文档阶段,零代码)
**Confidence:** HIGH(全部输入已逐文件直接盘点核实,无外部依赖)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 校准权限与调整口径
- **D-01(校准范围 = 仅修跨维度不一致):** 先做同类发现横向对齐扫描,只对"同类问题在不同维度定了不同级"的条目调整到统一 CHARTER 锚点;单条发现的原定级默认信任,不做全量复核。最小化"新判断"风险,与 ROADMAP"不产生新判断"措辞对齐。
- **D-02(批准机制 = 批量呈报一次批准):** 扫描后把全部拟调整项(ID、原级→新级、理由、锚点依据)一次性列表呈报用户,逐条确认或整批通过后才落账;不逐条实时请示,也不先斩后奏。
- **D-03(落账 = 独立 CALIBRATION.md):** 新建 `.planning/audit/CALIBRATION.md` 记录每条调整(ID、原级→终级、理由、锚点);findings/*.md 封版不动;报告以终级为准并标注"经校准"。延续"封版产物只读不续写"惯例(Phase 4 D-16 同源)。
- **D-04(工作量同法 + 工作包重估):** 单条发现的 S/M/L/XL 与严重度同法——仅修跨维度不一致,并入 D-02 同一批呈报;RPT-04 工作包层面另按包重估一个整体档(包内共修一处时总量 < 各条之和),两层都有记录。

#### 去重与聚类形态
- **D-05(ID 全保留,聚类作叠加层):** 40 条发现 ID 不合并不退役(追溯链与 RPT-08 映射表不断),新建聚类层(如 CL-NN)引用成员 ID;RPT-02 汇总表仍按条列、加聚类列;重叠处用关联字段互指。
- **D-06(聚类与工作包两层分开):** 根因聚类是分析层(按同一成因分组,回答"为什么会有这类问题",喂 RPT-01 摘要叙事);RPT-04 修复工作包是执行层(按共同修复位置分组、标依赖、按影响÷工作量排序,可直接排期)。两层互相引用但不强制对齐。
- **D-07(INFO 全量入表标"无需动作"):** 40 条全部进 RPT-02 表保证"每条发现有下落"(RPT-08 追溯闭环最直接);INFO/良性行的处置列标 acknowledge/无需修复,排序自然沉底,不进工作包。
- **D-08(真重复 = 主条+副条标注):** 两条 ID 实质描述同一缺陷同一修复动作时,选证据更完整的一条为主条(携严重度/工作量进排序),副条保留在表但处置列标"并入 F-XX-NN 处理",不单独进工作包;并入判定入 CALIBRATION.md 同批呈报(D-02)。

#### 上线判定口径
- **D-09(准则先行,逐条套用):** 规划时先写定三级判定准则(方向:BLOCKER = 上线即触发的数据丢失/泄密/主链路不可用;PRE-LAUNCH = 首批真实用户前必需,否则排障/运维成本高;POST-LAUNCH = 其余),准则全文写进报告;每条判定引准则条款 + 一句理由,与严重度独立评(严重度≠紧迫度,REQUIREMENTS 明示)。
- **D-10(上线语境 = 小范围真实用户,allowlist 扩容):** 判定以"邀请制加人、非作者用户无法自救(不会重录、不看日志)"为语境。判定重心:数据不丢、静默失败可发现,**加上**用户可感知的卡死态与无提示失败(如 F-CODE-06 uploading 死态在此语境下权重升高);开放注册级的滥用/频控风险不按公开口径拔高。
- **D-11(总判定 = 三档词机械推导):** RPT-01 总体上线判定由判定结果推导:有 BLOCKER→NO-GO;无 BLOCKER 有 PRE-LAUNCH→CONDITIONAL GO(附必做清单);全 POST-LAUNCH→GO。结论可复核、不依赖主观拿捏,用户在验收时确认。
- **D-12(判定批准 = 准则批准 + 抽样呈报):** 判定准则先呈用户批准;逐条套用后只呈报非平凡项——全部 BLOCKER 与 PRE-LAUNCH 条目、与严重度直觉相厄的条目(如 MEDIUM 却 POST-LAUNCH);POST-LAUNCH 大盘不逐条过。可与 D-02 校准呈报合并为一次交互或分两次,由规划定。

#### 报告文件结构与内容边界
- **D-13(DNF-04 用户已裁定 = 维持 DNF 登记表):** DNF-04(小程序接收原始 STS 秘密)确认为故意设计,留在 RPT-05 Do-NOT-fix 表并标 `⚠ intentional — do not "fix"`;本裁定经过写入报告(Phase 1 遗留的"Phase 5 用户裁定归属"事项就此闭环)。理据:单 key/仅 PutObject/≤900s 爆炸半径限定 + `make test-sts-escape` 实测。
- **D-14(文件形态 = 主报告 + 附录分文件):** 主报告(如 `.planning/audit/REPORT.md`)面向阅读:执行摘要、汇总表、工作包、DNF 表、优点盘点、置信声明;机械性长内容(RPT-08 追溯映射表、聚类明细等)分附录文件,主报告内链引用。
- **D-15(详情深度 = 表行摘要 + 链回台账):** 报告内每条发现只占表行(ID/终级/判定/标题/工作量/处置)+ 一句概要;九字段全文与证据片段留在封版 findings/*.md,报告链引不复制。单一真值源,避免校准后双源级差。
- **D-16(优点盘点来源 = 既有标注为主,允许有证据补录):** RPT-06 主体从三处汇集:Phase 3 HYP 备注标注的"RPT-06 优点候选"、DNF 4 条、REQUIREMENTS 点名例子(MaskedSecret、单键 STS、`.done` 状态机);允许从已有台账证据(COVERAGE、矩阵 agree 行等)补录明显遗漏项,但每条必须引既有台账证据行号,不新采证。

### Claude's Discretion
- 判定准则草案的具体条文(D-09 给方向,定稿在规划,批准在执行时呈用户)。
- 聚类的命名规则、粒度与预期数量;CL-NN 或其他 ID 形式。
- 附录文件的具体拆分清单与命名;主报告章节顺序(满足 RPT-01~08 全覆盖即可)。
- CONDITIONAL GO 必做清单的呈现形式(引用 PRE-LAUNCH 条目即可,无需另立实体)。
- 校准呈报与判定抽样呈报是合并一次交互还是分两次(D-02/D-12)。
- F-*-00 schema 示例条目在报告中的处置(剔除出计数,可在方法声明中注记)。

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RPT-01 | 一页执行摘要:审计缘由、范围、按严重度的发现计数、总体上线判定 | 实测终级分布输入(见"输入盘点");缘由/范围直接引 CHARTER 范围与方法章节;总判定由 D-11 三档词机械推导 |
| RPT-02 | 发现汇总表(ID、严重度、维度、标题、工作量),按严重度再按工作量排序 | 40 条真实发现全量清单已盘点(表行字段全部可从 findings/*.md 机械抽取);排序规则见"架构模式 · 排序" |
| RPT-03 | 每个发现附 BLOCKER/PRE-LAUNCH/POST-LAUNCH 上线阻断判定 | findings/*.md 每条已建 `上线判定` 空槽(两种格式,见"格式差异");判定准则按 D-09/D-10 定稿、D-12 批准 |
| RPT-04 | 修复工作包:按共同修复位置分组、按影响÷工作量排序、标注依赖 | 分组信号 = 每条发现`修复建议`字段的修复位置 + `关联发现`互指;影响÷工作量必须序数化(禁数值评分,见 Pitfall 5) |
| RPT-05 | "Do NOT fix" 登记表 | `.planning/audit/DO-NOT-FIX.md` DNF-01~04 全文即直接来源;DNF-04 归属已裁定(D-13),报告记"经用户裁定维持"即闭环 |
| RPT-06 | 优点盘点章节 | HYPOTHESES.md 内 7 处 "RPT-06 优点候选" 备注已定位(HYP-03/04/08/09/10/16/19);DNF 4 条;REQUIREMENTS 点名 3 例;补录须引台账行号(D-16) |
| RPT-07 | 分维度置信声明 | 五维度各有封版覆盖底稿:CON=CONTRACT-MATRIX(103 格:agree 91/diverge 2/absent 10)、CODE/TOOL=COVERAGE(63 对象 9/9 面)、DOC=DOC-CLAIMS(23 对象 198 条声明四态)、TEST=TEST-AUDIT(41 模块 8/8 面) |
| RPT-08 | 可追溯映射表(发现↔CONCERNS 线索↔需求,含"已检查无发现") | HYPOTHESES.md「29 条溯源闭环声明」表是直接输入;findings `关联发现` 字段反向补边;"无发现"显式源已定位(见"RPT-08 输入源") |
| RPT-09 | 中文正文 + 英文 ID/严重度术语 | 与 Phase 1~4 全部产物既有风格一致,无需转换;零 diff 验证命令 CHARTER 已写定 |
</phase_requirements>

## Summary

本阶段是纯文档汇编阶段:输入全部就绪且已封版,产出两个新文件族(`.planning/audit/CALIBRATION.md` 与 `.planning/audit/REPORT.md` + 附录),不装任何依赖、不写任何代码、不碰 apps/scripts/docs。研究核心工作是把"Phase 5 的 plan 到底读什么文件、每个文件里有什么、格式长什么样"逐一钉死——已全部完成,结果见"输入盘点"。

关键实测更正:**40 条真实发现的现级分布为 MEDIUM 11 / LOW 26 / INFO 3(无 CRITICAL/HIGH),工作量分布 S 32 / M 7 / L 1 / XL 0**——CONTEXT.md 中"约 MEDIUM 19 / LOW 32 / INFO 5"是笔误(合计 56 > 40,自相矛盾),规划与报告一律以本研究的 grep 实测为准(命令在"机械验证命令库")。另一关键发现:findings 五个文件的`上线判定`空槽存在两种格式(27 条带"(Phase 5 填,留空)"注记、18 条裸槽),任何机械抽取脚本必须同时匹配两种;且 CHARTER 九字段 schema 原文预期 Phase 5 回填台账(`状态: draft → calibrated`、`上线判定` 槽),与后来锁定的 D-03"封版不回写"存在字面冲突——**以 D-03 为准,不回写,终态一律落 CALIBRATION.md 与报告**,报告方法声明中注记此取舍。

**Primary recommendation:** 按"校准判断(需用户批准)→ 机械组装(零新判断)→ 机械验收"三段组织 plans:第一段产出 CALIBRATION.md 草案 + 判定准则 + 逐条判定草案并以 checkpoint 呈用户批准(D-02/D-12 可合并为一次交互);第二段从封版台账 + 已批准的 CALIBRATION.md 纯机械生成 REPORT.md 与附录;第三段跑零 diff + 计数等式 + 秘密反扫三类机械门禁。

## Architectural Responsibility Map

本阶段无运行时分层;按"文档流水线"角色映射:

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 跨维度对齐扫描、真重复判定、聚类划分 | 校准层(plan 01,人读 + 用户批准) | — | 本阶段仅有的两类被授权新判断之一,必须先于组装完成并落账 |
| 上线判定准则定稿与逐条套用 | 校准层(plan 01,用户批准准则 + 抽样呈报) | — | D-09/D-12;判定结果是 REPORT 表行字段,必须在组装前锁定 |
| CALIBRATION.md 落账 | 校准层输出 | — | D-03 唯一调整记录载体;findings/*.md 只读 |
| RPT-01~08 各章节组装 | 组装层(plan 02,纯机械汇编) | 封版台账(只读引用源) | "报告组装阶段不产生新判断"——所有表行字段从台账 + CALIBRATION.md 机械抽取 |
| 附录文件(追溯映射表、聚类明细) | 组装层 | — | D-14 主报告面向阅读,机械长表分文件 |
| 零 diff / 计数等式 / 秘密反扫验收 | 验收层(plan 03 或并入 02 收尾) | — | CHARTER D-03 命令 + COVERAGE 完成判定第 9 条秘密反扫范式,均已有先例可照抄 |
| STATE.md / ROADMAP 收官 | 验收层 | — | 本阶段是里程碑最后一个 phase,报告交付后走 milestone 收尾流程 |

## 输入盘点(Phase 5 plans 将读取的全部文件,逐一实测核实)

以下全部数据由本研究会话直接 `grep`/`Read` 实测 [VERIFIED: 本仓库 .planning/audit/ 直接盘点,2026-07-05]。

### 发现台账(封版只读,单一真值源)

| 文件 | `### F-` 总数 | 真实发现 | ID 范围 | 上线判定槽格式 |
|------|--------------|---------|---------|----------------|
| `.planning/audit/findings/contract.md` | 7 | 6 | F-CON-01~06 | 全部 `- **上线判定:** (Phase 5 填,留空)` |
| `.planning/audit/findings/code.md` | 9 | 8 | F-CODE-01~08 | 同上(带注记) |
| `.planning/audit/findings/docs-config.md` | 9 | 8 | F-DOC-01~08 | 同上(带注记) |
| `.planning/audit/findings/toolchain.md` | 9 | 8 | F-TOOL-01~08 | **8 条裸槽 `- **上线判定:**`**(仅 F-TOOL-00 示例带注记) |
| `.planning/audit/findings/test.md` | 11 | 10 | F-TEST-01~10 | **10 条裸槽**(仅 F-TEST-00 示例带注记) |
| **合计** | **45** | **40** | | 带注记 27 / 裸槽 18 |

每条真实发现九字段齐备(ID 标题、维度、严重度+影响×可能性理由、证据 `path:line @ 5927f36` + 引用片段、修复建议、工作量、关联发现、上线判定空槽、`状态: draft`)。`状态` 字段 45/45 全部为 `draft`。

**实测终级分布(40 条真实发现,校准前):**

- 严重度:MEDIUM 11 / LOW 26 / INFO 3;CRITICAL 0 / HIGH 0
- 工作量:S 32 / M 7 / L 1 / XL 0(唯一 L = F-CON-04 闭环方案;其保守方案为 M,报告排序时按台账字面 L 处理并可在处置列注记)
- MEDIUM 11 条清单:F-CON-02/03、F-CODE-02/06、F-TOOL-05/06、F-DOC-02/03、F-TEST-03/05(注:Phase 3 收口记 "MEDIUM 4"=F-CODE-02/06、F-TOOL-05/06;其余 MEDIUM 在 CON/DOC/TEST 维度)——plan 执行时应重新 grep 复核逐条归属,勿抄本清单

⚠ **CONTEXT.md 的"约 MEDIUM 19 / LOW 32 / INFO 5"为笔误**(合计 56,超过总数),以上述 grep 实测为准。

### 校准与判定的裁定基准

- `.planning/audit/CHARTER.md` — 基线 `5927f362785d44b085a791ca387732991012ce5a`(短 SHA `5927f36`,分支 ralph/soniscope-mvp-claude);五级严重度 SoniScope 场景锚点表(校准对齐的唯一裁定基准,D-01);S/M/L/XL 判定标准;九字段 schema;零 diff 命令 `git diff --stat 5927f36 -- apps/ scripts/ docs/`(输出必须空);秘密类证据红线(只引位置与模式名,绝不复制值本体);"台账与报告一律落 `.planning/audit/`"条款
- ⚠ **CHARTER schema 与 D-03 的字面冲突:** CHARTER 字段 8/9 原文预期 Phase 5 回填台账(上线判定槽 + `draft→calibrated`);D-03(后定,locked)要求 findings/*.md 封版不动。**以 D-03 为准**:上线判定与终级严重度只落 CALIBRATION.md 附录/报告表行,台账槽位保持 as-built;报告方法声明注记"CHARTER 字段 8/9 槽位按 D-03 改由 CALIBRATION.md 承载"。

### RPT-05 / RPT-06 输入

- `.planning/audit/DO-NOT-FIX.md` — DNF-01(whisper-local 故意桩)/ DNF-02(issue-cedential 拼写域名)/ DNF-03(handler mypy 豁免)/ DNF-04(小程序接收原始 STS 秘密);每条含标注、来源、证据、理由、分流依据,可整体照搬进 RPT-05 表;DNF-04 归属已由用户裁定维持(D-13),报告只记裁定经过,**不再请示**
- HYPOTHESES.md 中 "RPT-06 优点候选" 标注共 7 处,位于 HYP-03(纯 JS sha256 可辩护取舍)/ HYP-04(deploy 工具覆盖完整)/ HYP-08(双侧脱敏机制 MaskedSecret + is_sensitive/hash_openid)/ HYP-09(单键 STS + test-sts-escape 实测)/ HYP-10(单线程换文件状态机免锁)/ HYP-16(OSS 备份 + retranscribe 可重建)/ HYP-19(Transcriber/NlsBackend 双层 Protocol)——每条备注自带台账证据行号,直接满足 D-16"引既有证据"要求
- REQUIREMENTS 点名 3 例:MaskedSecret、单键 STS、`.done` 状态机(第三例在 HYP 候选中无独立条目,补录时可引 COVERAGE/CONCERNS 既有行,D-16 允许)

### RPT-07 置信声明输入(分维度)

| 维度 | 底稿 | 实测规模 | "已检查无发现"显式源 |
|------|------|---------|---------------------|
| CON | `CONTRACT-MATRIX.md` | 状态格 agree 91 / diverge 2 / absent 10(表格状态词实测;文件自述 51 行矩阵 + 普查记录) | agree 格即显式"已核对一致" |
| CODE+TOOL | `COVERAGE.md` | 63 对象(CODE 47 + TOOL 16)× 9/9 面全过;深挖点 20 处全下落;"无发现"字样 48 处 | 逐对象行"无发现"结论 |
| DOC | `DOC-CLAIMS.md` | 23 对象 198 条声明四态销号(agree/drift/dead-ref/无法静态核实,每节有复算等式) | agree 行 + "无法静态核实"行(置信声明需区分两者) |
| TEST | `TEST-AUDIT.md` | 41 模块 × 8/8 面;反向映射 22 行终态;三方对照 6 项 | 2 处显式『已检查,无发现』+ 8/8 面台账 |
| 仪器证据 | `scans/`(9 份) | gates-baseline 90 + ruff-extended 69 + vulture 1 + eslint 29 + secrets 69 = 258 命中全销号(确认 15/误报 243) | scans 各文件尾部封版行 |

### RPT-08 追溯映射输入

- `HYPOTHESES.md` §「29 条溯源闭环声明」— 现成的 29 行表(25 HYP + 4 DNF),每行含状态与去向(→ F-XX-NN / RPT-06 候选 / DNF / RPT 呈现),**是 RPT-08 的骨架,可直接机械转写**
- HYPOTHESES.md「Known Bugs 显式无线索行」(不计入 29)— RPT-08 的"已检查,无发现"显式行范例
- findings 各条 `关联发现` 字段 — 补"发现↔发现"与"发现↔矩阵行/样本 S-NN"边;格式不完全统一(有 `F-CON-02`、`关联线索: HYP-13`、`矩阵组① 行 4`、`D14-6` 等多种记法),机械解析需容忍自由文本,建议人工转写为规整三列表
- `.planning/REQUIREMENTS.md` traceability 表 — "发现↔需求"边:CON 维度↔CONTRACT-01~03、CODE↔AUDIT-01、TOOL↔AUDIT-02、DOC↔AUDIT-03、TEST↔AUDIT-04、HYP 闭环↔AUDIT-05(维度→需求是固定映射,无需逐条判断)
- `HANDOFF-PHASE4.md` — 6 条移交线索销号记录(佐证,非新边)
- 4 条 HYP 不落发现而"→ RPT 汇总呈现":HYP-01/20(FC 直转落差,XL 档存在级)、HYP-21(转写消费,明示 MVP 范围外)、HYP-11(章程范围外)、HYP-18(两代 SDK 并存观察)——**报告须给这些"RPT 呈现"条目一个落点**(建议执行摘要或范围声明段落),否则 29 条闭环在报告侧断链

### 聚类扫描起点(CONTEXT 已列 + 台账佐证)

已知重叠群(D-05 聚类层与 D-08 真重复判定的起点,非结论):

1. 重试常量四落点:F-CODE-07 × F-TEST-05 × F-TOOL-08(TEST-AUDIT 反向映射等式实证 F-TEST-05 覆盖 7 成员:F-CON-01/02/03/06 + F-CODE-07/08 + F-TOOL-08)
2. key 反推无校验:F-CON-03 × 相关 CODE/TOOL 条(F-CON-03 关联字段自记 "D14-6 第四处重复实现债务")
3. 镜像常量注释同步:F-CON-05/06 × F-TOOL-08 × F-TEST-05
4. 静默失败面:F-CODE-02/03 × F-TEST-06(TEST-AUDIT 等式:F-TEST-06 覆盖 F-CODE-02/03/06 + F-TOOL-01/02/03 共 6 成员)

注意:TEST 维度条目(F-TEST-05/06/07)本质是"对应脆弱区缺测试锁定"的元发现,与其成员条目**不是 D-08 真重复**(修复动作不同:一边修代码、一边补测试)——更可能是聚类层互指关系。真重复候选预计极少,判定留给 plan 01 执行时人读。

### 修复里程碑移交物

- `.planning/audit/CONTRACT-TEST-RECIPE.md` — 黄金样本跨语言契约测试设计配方(pytest + node:test 骨架、make 接入点、S-NN 样本值);报告应作为交付物显式引用并移交 FUTURE-02

### 本阶段新建产物落点

- `.planning/audit/CALIBRATION.md`(D-03,新建)
- `.planning/audit/REPORT.md` + 附录(D-14,新建;附录命名 Claude 裁量,建议 `REPORT-APPENDIX-A-traceability.md`、`REPORT-APPENDIX-B-clusters.md` 之类带 REPORT- 前缀便于归档识别)

## Standard Stack

本阶段**零外部依赖、零安装**:全部工作用 git、grep/awk/sed(macOS BSD 工具链)与 Read/Write 完成。

### Core

| 工具 | 版本 | 用途 | 为何标准 |
|------|------|------|---------|
| `git diff --stat 5927f36 -- apps/ scripts/ docs/` | 仓库自带 | 零 diff 验收 | CHARTER D-03 写定命令,Phase 2~4 已三次实跑先例 [VERIFIED: CHARTER.md + HYPOTHESES.md 04-09 实跑记录] |
| `grep -c` 计数等式 | 系统自带 | 计数一致性验收 | HYPOTHESES.md「机械验证命令」范式,Phase 3/4 收口先例 [VERIFIED: COVERAGE.md 完成判定 / TEST-AUDIT.md 总对账] |
| `git show 5927f36:<path>` | 仓库自带 | 若需补引证据(仅 D-16 补录允许) | CHARTER 取证纪律:禁止读工作树取证 |

### Don't Hand-Roll 对应:无需任何脚本框架、无需 Python/Node 工具、无需表格库——所有表都是 Markdown 手写/机械转写,规模(40 行主表、29 行映射表)完全在手工可控范围。若 plan 想用一次性 awk/grep 辅助抽取表行,输出仍须人工复核后写入(判断必须人读,CONTEXT code_context 明示)。

### Package Legitimacy Audit

本阶段不安装任何外部包。**Packages removed due to [SLOP] verdict:** none。**Packages flagged as suspicious [SUS]:** none。

## Architecture Patterns

### 阶段数据流

```
封版输入(只读)                        校准层(plan 01)                组装层(plan 02)            验收层(plan 03/收尾)
─────────────────                    ──────────────────              ─────────────────          ─────────────────
findings/*.md (40+5) ──┬─▶ 跨维度对齐扫描(D-01)─┐
CHARTER.md 锚点 ────────┤   真重复判定(D-08)     ├─▶ 拟调整清单 ──▶ [CHECKPOINT: 用户批量批准 D-02]
                       │   聚类划分(D-05/06)    │                        │
HYPOTHESES.md 29行表 ───┤                        │                        ▼
DO-NOT-FIX.md ─────────┤   判定准则草案(D-09/10)─▶ [CHECKPOINT: 准则批准] ─▶ CALIBRATION.md 落账
COVERAGE/DOC-CLAIMS/   │   逐条套用+抽样呈报(D-12)                        │
TEST-AUDIT/MATRIX ─────┤                                                 ▼
scans/ (9份) ──────────┴──────────────────────────────────▶ REPORT.md + 附录(纯机械汇编,零新判断)
CONTRACT-TEST-RECIPE.md ──────────────────────────────────▶ (报告内移交引用)
                                                                          │
                                                                          ▼
                                                            零 diff + 计数等式 + 秘密反扫 + STATE 收官
```

### Pattern 1: 判断前置、组装机械化

**What:** 所有被授权的新判断(校准调级、真重复并入、聚类归组、上线判定)在 plan 01 完成并经用户批准落账 CALIBRATION.md;plan 02 组装时每个表行字段都有唯一确定来源(台账字段或 CALIBRATION.md 行),不存在"组装时再想一下"的空间。
**When to use:** 全阶段。这是"报告组装阶段不产生新判断"成功判据的结构性保证。
**Example:** RPT-02 表行的"终级严重度"列取值规则:该 ID 在 CALIBRATION.md 有调整记录 → 用终级并标"经校准";无记录 → 原级照抄。

### Pattern 2: 批准交互最小化(yolo 模式适配)

**What:** D-02(校准批量呈报)与 D-12(准则批准 + 判定抽样呈报)合并为**一次** checkpoint:human-verify 交互——单个呈报文档含 ①拟调整清单(ID、原级→新级、理由、锚点) ②真重复并入判定 ③判定准则全文 ④全部 BLOCKER/PRE-LAUNCH 条目与"直觉相厄"条目清单。用户逐项或整批批复后 plan 才落账。
**When to use:** CONTEXT 明示用户偏好批量批准而非逐条打断,且 config `mode: yolo`、`human_verify_mode: end-of-phase`——但 D-02/D-12 的批准是 locked decision,必须显式 checkpoint,不可被 yolo 吞掉。合并/分两次是 Claude 裁量;推荐合并(判定准则本身不依赖校准结果,可同批呈报)。
**注意:** 若校准调级改变某条严重度,判定不受影响(D-09:判定与严重度独立评),因此合并呈报无先后依赖问题。

### Pattern 3: 计数等式先写死、再组装、后复算

**What:** 沿用 HYPOTHESES.md「机械验证命令」范式:plan 里先写死期望值等式(40 条真实发现、45 个 `### F-` 标题、29 行映射、DNF 4 条、聚类成员全覆盖等),组装后逐条实跑并把命令 + 实际输出照录进报告收尾/VERIFICATION。
**Example(可直接进 plan 的验收命令):**

```bash
# 发现底数:期望 45(含 5 条 F-*-00 示例)
grep -hc '^### F-' .planning/audit/findings/*.md | paste -sd+ - | bc
# 真实发现:期望 40
grep -h '^### F-' .planning/audit/findings/*.md | grep -vc '\-00:'
# 报告主表行数 = 40(每条发现有下落,D-07)
# 上线判定三态全填(报告侧):BLOCKER+PRE-LAUNCH+POST-LAUNCH 计数之和 = 40
# 29 条溯源:grep -c '^### HYP-' HYPOTHESES.md = 25;grep -c '^### DNF-' DO-NOT-FIX.md = 4
# 零 diff:git diff --stat 5927f36 -- apps/ scripts/ docs/ | wc -l = 0
# 秘密反扫(报告新文件也要过,COVERAGE 完成判定第 9 条同款):
grep -rE 'OSSAccessKeyId=[0-9A-Za-z]{8,}|Signature=[0-9A-Za-z%+/=]{16,}|LTAI[0-9A-Za-z]{10,}' .planning/audit/ ; test $? -eq 1
```

### Pattern 4: RPT-02 排序规则(需在报告方法声明中写死)

**What:** "按严重度再按工作量排序"存在方向歧义,必须定死并声明:严重度降序(MEDIUM → LOW → INFO;CRITICAL/HIGH 空档照常在词表中声明)、同级内工作量**升序**(S → M → L → XL,小工作量高优先——backlog 语义下"同严重度先修便宜的"),再按 ID 稳定排序。INFO/并入副条自然沉底(D-07/D-08)。
**Why:** 排序方向本身是呈现约定不是新判断,但不声明就会在验收时被质疑;写进方法声明即免争议。同理 RPT-04 的"影响÷工作量"必须用**序数规则**表达(如:先按包内最高严重度降序、同级按包总工作量档升序),严禁折算数字比值(Out of Scope 禁数值评分)。

### Anti-Patterns to Avoid

- **回写封版台账:** 不改 findings/*.md 的任何字段(含上线判定槽、状态槽)——D-03 压过 CHARTER schema 字面预期;一切终态在 CALIBRATION.md + 报告。
- **报告里复制九字段全文或证据片段:** D-15 只允许表行 + 一句概要 + 链回台账;复制会制造双源级差。
- **组装时"顺手"重评某条发现内容或补采新证据:** 仅有的两类被授权判断之外一律汇编;D-16 补录优点也只能引既有台账行号。
- **再次请示 DNF-04 归属:** 已裁定维持(D-13),报告记裁定经过即闭环。
- **给"影响÷工作量"或任何质量维度造数字:** REQUIREMENTS Out of Scope 明禁数值评分与小时估计。

## Common Pitfalls

### Pitfall 1: 上线判定槽两种格式导致机械抽取漏条
**What goes wrong:** 只匹配 `- **上线判定:** (Phase 5 填,留空)` 会漏掉 toolchain.md/test.md 的 18 条裸槽 `- **上线判定:**`。
**How to avoid:** 一律以 `^### F-` 标题为条目锚点做逐条抽取,不依赖槽位文本;计数等式用标题数(45/40)对账。
**Warning signs:** 汇总表行数 ≠ 40。

### Pitfall 2: 以 CONTEXT.md 的严重度计数为准
**What goes wrong:** CONTEXT 的"MEDIUM 19 / LOW 32 / INFO 5"自相矛盾(合计 56);写进 RPT-01 执行摘要即错。
**How to avoid:** 执行摘要计数用组装时现场 grep 实测(校准前 MEDIUM 11 / LOW 26 / INFO 3),叠加 CALIBRATION.md 调整后得终级分布;命令与输出照录。
**Warning signs:** 计数无法通过 `grep -oE '严重度:\*\* (CRITICAL|HIGH|MEDIUM|LOW|INFO)'` 复算。

### Pitfall 3: F-*-00 示例条目混入计数或汇总表
**What goes wrong:** 5 条 schema 示例(F-CON/CODE/TOOL/DOC/TEST-00)带 `### F-` 标题,机械 grep 会计入。
**How to avoid:** 所有抽取统一 `grep -v '\-00:'`;报告方法声明注记"45 条目 = 40 真实 + 5 schema 示例,示例剔除"(Claude 裁量项,CONTEXT 已给方向)。

### Pitfall 4: "RPT 呈现"类 HYP 在报告侧断链
**What goes wrong:** HYP-01/11/18/20/21 不占发现 ID、去向为"RPT 汇总/范围声明呈现";若报告没给它们落点,RPT-08 的 29 行闭环在报告侧验收不过。
**How to avoid:** 执行摘要或范围声明设"存在级观察与范围外事项"小节,逐条点名这 5 个 HYP 并回链 HYPOTHESES.md;RPT-08 附录表中其"报告落点"列填该小节锚点。

### Pitfall 5: 秘密值二次入库
**What goes wrong:** 组装时从 findings 复制证据片段(D-15 本就禁止)可能把签名 URL 模式内容带进 REPORT.md;`.planning/audit/` 一旦提交即永久入库。
**How to avoid:** 报告只引 `path:line @ 5927f36` + 模式名;收尾必跑 COVERAGE 完成判定第 9 条同款秘密反扫(命令见 Pattern 3),期望 exit 1(零命中)。

### Pitfall 6: 把 TEST 元发现误判为 D-08 真重复并入
**What goes wrong:** F-TEST-05/06/07 与其覆盖的代码条目描述同一脆弱区,表面像重复;但修复动作不同(补测试 vs 修代码),不满足 D-08"同一缺陷同一修复动作"。
**How to avoid:** D-08 判定以"修复建议字段是否同一动作"为准;这类关系归聚类层互指(D-06),不并入。

### Pitfall 7: 零 diff 命令通过 ≠ 全部约束满足
**What goes wrong:** 零 diff 命令只保护 apps/scripts/docs 三目录;Makefile、AGENTS.md、pyproject.toml 等根文件同为审计对象但不在命令范围(CHARTER 明示)。
**How to avoid:** 本阶段写入面严格限定 `.planning/`(且审计产物只进 `.planning/audit/`);收尾除零 diff 外加 `git status --porcelain` 复核写入面仅 .planning/。

## Runtime State Inventory

非 rename/refactor 阶段,且零代码改动 — 本节按规则省略(无存储数据、无服务配置、无 OS 注册态、无 secrets 变更、无构建产物受影响;写入面仅 `.planning/` 下新增 Markdown)。

## Code Examples

无代码产出。可复用的"代码"即机械验证命令(见 Pattern 3),全部来自仓库既有先例:

```bash
# Source: .planning/audit/CHARTER.md 零 diff 条款(Phase 2~4 已实跑)
git diff --stat 5927f36 -- apps/ scripts/ docs/        # 期望空输出

# Source: .planning/audit/HYPOTHESES.md 机械验证命令章节
grep -c '^### HYP-' .planning/audit/HYPOTHESES.md      # 25
grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md      # 4

# Source: .planning/audit/COVERAGE.md 完成判定第 9 条(秘密反扫范式)
grep -rE 'OSSAccessKeyId=[0-9A-Za-z]{8,}|Signature=[0-9A-Za-z%+/=]{16,}|LTAI[0-9A-Za-z]{10,}' .planning/audit/
# 期望零命中(exit 1)
```

## State of the Art

不适用(无库/框架选型)。本阶段的"最新实践"即项目自身 Phase 1~4 建立的惯例:封版只读、计数等式验收、`@ 5927f36` 证据格式、中文正文 + 英文术语——全部延续,无演进项。

## Project Constraints (from CLAUDE.md)

- 零 diff 红线:apps/、scripts/、docs/ 相对 `5927f36` 不许任何改动;本阶段只写 `.planning/audit/` 与 `.planning/phases/05-*/`
- 仅审计报告,不改代码;修复留给下一里程碑
- 报告标准:每个发现须有严重度分级、file:line 证据、修复建议与工作量估计(台账已满足;报告表行链回)
- 秘密红线:任何显示/引用不得含秘密值本体(CHARTER 秘密类证据红线同源)
- 中文正文 + 英文 ID/严重度术语(RPT-09)
- GSD workflow enforcement:一切编辑经 GSD 命令流(本阶段即 /gsd-plan-phase → /gsd-execute-phase)
- 禁数值评分 / 小时估计(REQUIREMENTS Out of Scope)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | RPT-02"按严重度再按工作量排序"中工作量取升序(同级先修便宜的) | Pattern 4 | 排序方向颠倒不影响内容正确性;方法声明写死后用户验收时可一句话改排;LOW risk |
| A2 | D-02 校准呈报与 D-12 判定呈报合并为一次 checkpoint 交互 | Pattern 2 | CONTEXT 明示此项为 Claude 裁量;若用户偏好分两次,plan 结构需拆 checkpoint;LOW risk |
| A3 | CHARTER schema 字段 8/9 的台账回填预期被 D-03 取代(不回写 findings/*.md) | 输入盘点 | 若用户实际期望回填台账,需追加一个写台账任务并放弃"封版不动";建议在校准呈报时顺带确认一句;MEDIUM risk |

其余全部关键事实(文件清单、计数、格式、分布)均 [VERIFIED: 直接盘点],无 [ASSUMED] 残留。

## Open Questions

1. **MEDIUM 11 条的精确逐条归属**
   - What we know: 总数 11 已 grep 实测;Phase 3 收口自记 CODE/TOOL 侧 4 条(F-CODE-02/06、F-TOOL-05/06)
   - What's unclear: 其余 7 条在 CON/DOC/TEST 的逐条归属本研究未逐条抄录
   - Recommendation: plan 01 校准扫描第一步就是逐条抽取严重度清单(本就是必做工序),自然解决
2. **聚类预期数量与粒度**(Claude 裁量)
   - What we know: 4 个已知重叠群 + TEST-AUDIT 反向映射等式给出成员关系
   - Recommendation: 预期 4~7 个 CL-NN;不追求全覆盖——无共同根因的孤条不强行入簇,聚类层允许有未入簇发现(D-06 分析层性质)

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | 零 diff 验证、`git show 5927f36` 取证 | ✓ | 仓库自带工作流已在用 | — |
| grep/awk/sed (BSD) | 计数等式、抽取辅助 | ✓ | macOS 自带 | — |
| Node/uv/ffmpeg | 不需要 | — | — | — |

零 diff 当前状态:**本研究会话实跑通过(空输出)** [VERIFIED: 2026-07-05 实跑]。无缺失依赖。

## Validation Architecture

本阶段无代码测试框架适用;验证体系 = 机械 grep/git 门禁(项目既有范式,Phase 3/4 收口先例)。

### Test Framework
| Property | Value |
|----------|-------|
| Framework | bash 机械验证命令(grep/git,无测试框架) |
| Config file | none — 命令写死在 plan 验收步骤与报告收尾章节 |
| Quick run command | `git diff --stat 5927f36 -- apps/ scripts/ docs/`(空输出) |
| Full suite command | Pattern 3 全套计数等式 + 秘密反扫 + 零 diff |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RPT-01 | 摘要计数与台账一致 | 机械 | 严重度分布 grep 复算 = 摘要数字 | ✅(命令即测试) |
| RPT-02 | 40 条全量入表 | 机械 | 报告主表行数 grep = 40 | ✅ |
| RPT-03 | 判定全填、三态之一 | 机械 | 报告内 BLOCKER/PRE-LAUNCH/POST-LAUNCH 计数和 = 40 | ✅ |
| RPT-04 | 工作包成员∪ = 非 INFO 非副条集合 | 机械+人读 | 成员 ID grep 对账 | ✅ |
| RPT-05 | DNF 4 条全登记 | 机械 | 报告 DNF 表行 = 4 | ✅ |
| RPT-06 | 每条优点引台账行号 | 人读 | manual-only(引证核对) | — 人工验收 |
| RPT-07 | 五维度各有置信声明 | 机械 | 五维度小节标题 grep = 5 | ✅ |
| RPT-08 | 29 条溯源闭环 + 无发现显式行 | 机械 | 映射表行 grep = 29(+显式无发现行) | ✅ |
| RPT-09 | 中文正文 + 零 diff | 机械 | 零 diff 命令空输出 + 秘密反扫 exit 1 | ✅ |

### Sampling Rate
- **Per task commit:** 零 diff 快查(quick run)
- **Per wave merge:** 全套计数等式
- **Phase gate:** 全套 + 秘密反扫 + `git status --porcelain` 写入面复核,结果照录报告收尾

### Wave 0 Gaps
None — 验证全部为既有 bash 命令,无需搭建任何测试基础设施。

## Security Domain

本阶段不写代码、不处理输入、不触网;ASVS 常规类目(V2/V3/V4/V5/V6)均不适用。实际安全约束仅两条,均为项目红线的延续:

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 秘密值二次入库(报告复制证据片段带出签名 URL/AK) | Information Disclosure | D-15 不复制片段 + 收尾秘密反扫 `.planning/audit/` 全目录(COVERAGE 第 9 条范式,期望 exit 1) |
| 基线污染(误改 apps/scripts/docs) | Tampering | 写入面限定 .planning/ + 零 diff 命令收尾必跑照录 |

## Sources

### Primary (HIGH confidence — 全部为本仓库封版产物直接盘点)
- `.planning/audit/CHARTER.md` — 基线 SHA、锚点、schema、零 diff 命令、秘密红线
- `.planning/audit/findings/{contract,code,toolchain,docs-config,test}.md` — 45/40 条目逐一 grep 核实
- `.planning/audit/HYPOTHESES.md` — 总对账章节、29 行溯源表、7 处 RPT-06 候选标注、机械验证命令范式
- `.planning/audit/DO-NOT-FIX.md` — DNF-01~04 全文
- `.planning/audit/{COVERAGE,DOC-CLAIMS,TEST-AUDIT,CONTRACT-MATRIX}.md` — 各维度底稿结构与对账等式
- `.planning/audit/{HANDOFF-PHASE4,CONTRACT-TEST-RECIPE}.md`、`.planning/audit/scans/`(9 份,存在性核实)
- `.planning/phases/05-report-calibration-assembly/05-CONTEXT.md`、`.planning/REQUIREMENTS.md`、`.planning/ROADMAP.md`、`.planning/config.json`

### Secondary / Tertiary
无(本阶段无外部技术调研需求,未使用 web 检索)。

## Metadata

**Confidence breakdown:**
- 输入盘点(文件、计数、格式): HIGH — 全部 grep/Read 直接实测
- 架构模式(三段流水线 + checkpoint): HIGH — 直接由 locked decisions 推导,仅呈报合并方式属裁量
- Pitfalls: HIGH — 均由实测格式差异或 locked decision 字面冲突推出

**Research date:** 2026-07-05
**Valid until:** 里程碑收尾前有效(输入全部封版,不随时间漂移;唯一失效条件是有人违规改动封版台账——零 diff 与 git log 可查)
