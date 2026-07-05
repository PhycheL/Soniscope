# Phase 5: 汇总校准与报告组装 - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

对前四阶段产出的 **40 条真实发现**(F-CON-01~06 / F-CODE-01~08 / F-TOOL-01~08 / F-DOC-01~08 / F-TEST-01~10;现级分布约 MEDIUM 19 / LOW 32 / INFO 5,无真实 CRITICAL/HIGH——计数含 F-*-00 schema 示例,组装时剔除)完成去重、根因聚类、单一口径严重度与工作量校准,并组装满足 RPT-01~09 全部需求的最终审计报告。报告组装阶段**不产生新判断**(RPT-03 上线判定与校准调整是本阶段被授权的例外,均有批准机制约束,见 decisions)。

输入已全部就绪:HYPOTHESES.md 25/25 闭环(证实 17/细化 7/证伪 1)、DNF 4 条、COVERAGE.md / DOC-CLAIMS.md / TEST-AUDIT.md / CONTRACT-MATRIX.md 台账、scans/ 九份归档、CONTRACT-TEST-RECIPE.md。

里程碑硬约束延续:零 diff(apps/、scripts/、docs/ 相对 5927f36 不许任何改动,阶段收尾跑零 diff 验证,RPT 成功判据 5 显式要求)、报告与全部产物只落 `.planning/audit/`(CHARTER 硬约束)、证据格式 `path:line @ 5927f36`、中文正文 + 英文 ID/严重度术语(RPT-09)、禁数值评分/小时估计。findings/*.md 等封版产物只读引用不回写。

</domain>

<decisions>
## Implementation Decisions

### 校准权限与调整口径
- **D-01(校准范围 = 仅修跨维度不一致):** 先做同类发现横向对齐扫描,只对"同类问题在不同维度定了不同级"的条目调整到统一 CHARTER 锚点;单条发现的原定级默认信任,不做全量复核。最小化"新判断"风险,与 ROADMAP"不产生新判断"措辞对齐。
- **D-02(批准机制 = 批量呈报一次批准):** 扫描后把全部拟调整项(ID、原级→新级、理由、锚点依据)一次性列表呈报用户,逐条确认或整批通过后才落账;不逐条实时请示,也不先斩后奏。
- **D-03(落账 = 独立 CALIBRATION.md):** 新建 `.planning/audit/CALIBRATION.md` 记录每条调整(ID、原级→终级、理由、锚点);findings/*.md 封版不动;报告以终级为准并标注"经校准"。延续"封版产物只读不续写"惯例(Phase 4 D-16 同源)。
- **D-04(工作量同法 + 工作包重估):** 单条发现的 S/M/L/XL 与严重度同法——仅修跨维度不一致,并入 D-02 同一批呈报;RPT-04 工作包层面另按包重估一个整体档(包内共修一处时总量 < 各条之和),两层都有记录。

### 去重与聚类形态
- **D-05(ID 全保留,聚类作叠加层):** 40 条发现 ID 不合并不退役(追溯链与 RPT-08 映射表不断),新建聚类层(如 CL-NN)引用成员 ID;RPT-02 汇总表仍按条列、加聚类列;重叠处用关联字段互指。
- **D-06(聚类与工作包两层分开):** 根因聚类是分析层(按同一成因分组,回答"为什么会有这类问题",喂 RPT-01 摘要叙事);RPT-04 修复工作包是执行层(按共同修复位置分组、标依赖、按影响÷工作量排序,可直接排期)。两层互相引用但不强制对齐。
- **D-07(INFO 全量入表标"无需动作"):** 40 条全部进 RPT-02 表保证"每条发现有下落"(RPT-08 追溯闭环最直接);INFO/良性行的处置列标 acknowledge/无需修复,排序自然沉底,不进工作包。
- **D-08(真重复 = 主条+副条标注):** 两条 ID 实质描述同一缺陷同一修复动作时,选证据更完整的一条为主条(携严重度/工作量进排序),副条保留在表但处置列标"并入 F-XX-NN 处理",不单独进工作包;并入判定入 CALIBRATION.md 同批呈报(D-02)。

### 上线判定口径
- **D-09(准则先行,逐条套用):** 规划时先写定三级判定准则(方向:BLOCKER = 上线即触发的数据丢失/泄密/主链路不可用;PRE-LAUNCH = 首批真实用户前必需,否则排障/运维成本高;POST-LAUNCH = 其余),准则全文写进报告;每条判定引准则条款 + 一句理由,与严重度独立评(严重度≠紧迫度,REQUIREMENTS 明示)。
- **D-10(上线语境 = 小范围真实用户,allowlist 扩容):** 判定以"邀请制加人、非作者用户无法自救(不会重录、不看日志)"为语境。判定重心:数据不丢、静默失败可发现,**加上**用户可感知的卡死态与无提示失败(如 F-CODE-06 uploading 死态在此语境下权重升高);开放注册级的滥用/频控风险不按公开口径拔高。
- **D-11(总判定 = 三档词机械推导):** RPT-01 总体上线判定由判定结果推导:有 BLOCKER→NO-GO;无 BLOCKER 有 PRE-LAUNCH→CONDITIONAL GO(附必做清单);全 POST-LAUNCH→GO。结论可复核、不依赖主观拿捏,用户在验收时确认。
- **D-12(判定批准 = 准则批准 + 抽样呈报):** 判定准则先呈用户批准;逐条套用后只呈报非平凡项——全部 BLOCKER 与 PRE-LAUNCH 条目、与严重度直觉相厄的条目(如 MEDIUM 却 POST-LAUNCH);POST-LAUNCH 大盘不逐条过。可与 D-02 校准呈报合并为一次交互或分两次,由规划定。

### 报告文件结构与内容边界
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审计规则(Phase 1 定稿,全部硬约束)
- `.planning/audit/CHARTER.md` — 基线 `5927f36`、严重度锚点(校准对齐的裁定基准)、S/M/L/XL 分档标准、九字段 schema、ID 规则、"台账与报告一律落 `.planning/audit/`"条款、零 diff 验证命令(阶段收尾必跑)
- `.planning/audit/DO-NOT-FIX.md` — DNF-01~04 全文,RPT-05 登记表的直接来源;DNF-04 归属已裁定维持(D-13)
- `.planning/REQUIREMENTS.md` — RPT-01~09 完整需求文本、Out of Scope 表(禁数值评分/小时估计)、v2 FUTURE-01/02
- `.planning/ROADMAP.md` — Phase 5 目标与 5 条成功判据("校准调整有记录可查""报告组装阶段不产生新判断"的原始措辞)

### 发现台账(封版只读,报告的单一真值源)
- `.planning/audit/findings/contract.md` — F-CON-01~06(+00 示例)
- `.planning/audit/findings/code.md` — F-CODE-01~08(+00 示例)
- `.planning/audit/findings/toolchain.md` — F-TOOL-01~08(+00 示例)
- `.planning/audit/findings/docs-config.md` — F-DOC-01~08(+00 示例)
- `.planning/audit/findings/test.md` — F-TEST-01~10(+00 示例)

### 追溯与置信声明的输入(RPT-07/08)
- `.planning/audit/HYPOTHESES.md` — 25/25 闭环状态 + 尾部总对账章节(29 条溯源:25 HYP + 4 DNF),RPT-08 映射表的直接输入;Phase 3 标注的"RPT-06 优点候选"备注在此
- `.planning/audit/COVERAGE.md` — Phase 3 封版覆盖台账(63 对象),RPT-07 CODE/TOOL 维度置信声明与"已检查无发现"引用源
- `.planning/audit/DOC-CLAIMS.md` — 23 对象 198 条声明四态销号,RPT-07 DOC 维度置信声明输入
- `.planning/audit/TEST-AUDIT.md` — 41 测试模块 8 面台账 + D-09 反向映射清单,RPT-07 TEST 维度置信声明输入
- `.planning/audit/CONTRACT-MATRIX.md` — 51 行矩阵 + 普查记录,RPT-07 CON 维度置信声明与 agree 行"已检查无发现"引用源
- `.planning/audit/scans/`(9 份)— 覆盖率实测、门禁实跑、扫描三态销号归档,置信声明的仪器证据
- `.planning/audit/HANDOFF-PHASE4.md` — 6 条移交线索销号记录(追溯闭环佐证)
- `.planning/audit/CONTRACT-TEST-RECIPE.md` — 跨语言契约测试设计配方,修复里程碑输入(FUTURE-02),报告中作为交付物引用

### 本阶段新建产物落点
- `.planning/audit/CALIBRATION.md` — 校准/并入/工作量调整记录(D-03,新建)
- `.planning/audit/REPORT.md` + 附录文件 — 最终报告(D-14,新建;具体命名规划定)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 全部输入为 `.planning/audit/` 下结构化 Markdown 台账,机械可解析(`### F-XX-NN` 标题、九字段字段名统一)——去重扫描与汇总表生成可脚本辅助,但判定必须人读
- HYPOTHESES.md 尾部总对账的"机械验证命令"范式(grep 计数等式)——报告的计数一致性验收可沿用
- CHARTER 零 diff 验证命令(`git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空)——阶段收尾必跑并记录

### Established Patterns
- "封版产物只读不续写"(Phase 4 D-16 同源)→ 本阶段一切调整落新文件 CALIBRATION.md,findings/*.md 不回写(D-03)
- "清单逐条销号 + 可机械验收"是用户一贯要求 → 40 条发现在 RPT-02 表全量有下落(D-07)、29 条 HYP/DNF 溯源闭环、"已检查无发现"显式记录,均须可 grep 验证
- 发现文档风格:中文正文 + 英文 ID/严重度术语,与 Phase 1~4 产物一致(RPT-09 明文要求)
- 用户偏好"结构性保证优于运行时前提"与批量批准而非逐条打断(D-02/D-12 与 yolo 模式适配)

### Integration Points
- RPT-02 汇总表 = 修复里程碑 backlog;RPT-04 工作包 = 修复里程碑阶段清单(D-06 两层分开,工作包为排期单元)
- CONTRACT-TEST-RECIPE.md → 修复里程碑 FUTURE-02 的直接输入,报告应显式移交
- 已知重叠群(聚类扫描起点):重试常量四落点(F-CODE-07 × F-TEST-05 × F-TOOL-08)、key 反推无校验(F-CON-03 × F-CODE/F-TOOL 相关条)、镜像常量注释同步(F-CON-05/06 × F-TOOL-08 × F-TEST-05)、静默失败面(F-CODE-02/03 × F-TEST-06)
- 阶段收尾:零 diff 验证 + STATE.md 收官;本阶段是里程碑最后一个 phase,报告交付后走 milestone 收尾流程

</code_context>

<specifics>
## Specific Ideas

- 用户对本阶段"新判断"的授权是精确的:校准调级(批量呈报批准)与上线判定(准则批准+抽样呈报)是仅有的两类被授权判断,其余一律汇编既有结论——规划时不得引入第三类新判断(如重评发现内容、新采证据)。
- DNF-04 裁定已完成(维持 DNF),这是 Phase 1 显式挂起等待本阶段的事项——报告 RPT-05 中应记"经用户裁定维持"闭环,不要再次请示。
- 上线语境定为"小范围真实用户(allowlist 扩容)"而非最保守口径——判定时滥用/频控类(F-CODE-05)不按公开注册拔高,但用户可感知的失败态(F-CODE-06 等)权重上调。
- 总体上线判定用三档词(GO / CONDITIONAL GO / NO-GO)机械推导,用户验收确认——报告交付时这句结论必须已在,不留"待裁定"占位。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 5-汇总校准与报告组装*
*Context gathered: 2026-07-05*
