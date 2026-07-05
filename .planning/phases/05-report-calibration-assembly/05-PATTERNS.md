# Phase 5: 汇总校准与报告组装 - Pattern Map

**Mapped:** 2026-07-05
**Files analyzed:** 4 个新建文档(CALIBRATION.md、REPORT.md、附录 A/B)
**Analogs found:** 4 / 4(全部有强类比;个别章节为部分类比,见"无类比章节"节)

> 本阶段为纯文档阶段,零代码产出。"role/data flow"按文档流水线角色映射;类比对象是 `.planning/audit/` 下 Phase 1~4 封版产物的文档范式(标题结构、ID 约定、表 schema、机械验证命令块)。所有类比文件**只读引用**,严禁回写(D-03 封版纪律)。

## File Classification

| 新建文件 | 角色 | 数据流 | 最近类比 | 匹配度 |
|----------|------|--------|----------|--------|
| `.planning/audit/CALIBRATION.md` | 裁定台账(校准/并入/判定落账) | 批量转写(findings 原级 → 终级,经用户批准) | `.planning/audit/DO-NOT-FIX.md`(逐条裁定条目)+ `HYPOTHESES.md` 状态回填范式 | role-match |
| `.planning/audit/REPORT.md` | 汇编主报告(RPT-01~07 + 收尾验证) | 批量汇编(封版台账 + CALIBRATION → 表行,零新判断) | 组合类比:`TEST-AUDIT.md` 反向映射表(汇总表行)、`DO-NOT-FIX.md`(RPT-05)、`COVERAGE.md` 完成判定(RPT-07/收尾)、`CONTRACT-MATRIX.md` 状态词表(判定准则) | role-match(分章节各有 exact 类比) |
| `.planning/audit/REPORT-APPENDIX-A-traceability.md`(命名 Claude 裁量) | 附录:RPT-08 追溯映射表 | 机械转写(29 行溯源表 + 关联发现补边) | `HYPOTHESES.md` §29 条溯源闭环声明(:289-319) | exact |
| `.planning/audit/REPORT-APPENDIX-B-clusters.md`(命名 Claude 裁量) | 附录:聚类明细(CL-NN 叠加层) | 分组转写(成员 ID 引用,不合并) | `TEST-AUDIT.md` 缺口归属等式(:169)+ `CONTRACT-MATRIX.md` 分组表 + 判定列 | role-match |

另有两类非新建产物:①校准/判定呈报(checkpoint 交互物,可直接复用 CALIBRATION.md 草案结构,不必单独立文件);② STATE.md/ROADMAP 收官更新(GSD 常规流程,无需模式映射)。

## Pattern Assignments

### `.planning/audit/CALIBRATION.md`(裁定台账,批量转写)

**类比:** `.planning/audit/DO-NOT-FIX.md` + `.planning/audit/CHARTER.md`(schema/锚点)

**文件头模式**(DO-NOT-FIX.md:1-8 — 标题 + Created + 基线引用 + 一段自述职责与决策依据):

```markdown
# Do-NOT-fix 登记表(RPT-05 初稿)

**Created:** 2026-07-04
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本表按锁定决策 D-08 预录入:……

所有证据行号提取自 `git show 5927f36:<path>`,不读工作树。
```

CALIBRATION.md 照此写头部,自述改为:依据 D-01~D-04/D-08,记录跨维度对齐调级、真重复并入、工作量重估;findings/*.md 封版不动,本文件是唯一调整记录载体;注记"CHARTER 字段 8/9 台账回填预期由本文件承载(D-03 压过 schema 字面)"。

**逐条裁定条目模式**(DO-NOT-FIX.md:12-18,DNF-01 — 固定字段名、`### ID:` 标题锚点):

```markdown
### DNF-01: `whisper-local` 转写器为故意桩

- **标注:** `⚠ intentional — do not "fix"`
- **来源:** CONCERNS.md §Tech Debt / ...
- **证据:** `apps/worker/src/soniscope_worker/transcriber.py:144-165 @ 5927f36` — ...
- **理由:** CONCERNS.md 原文:"..."。占位实现是……
- **分流依据:** D-08 点名。
```

校准条目按同构五字段改写:`### CAL-NN: <ID> <原级> → <终级>`,字段 = **调整类型**(严重度对齐 / 工作量对齐 / 真重复并入 / 工作包重估)、**原值→终值**、**理由**(引同类条目 ID 对照)、**锚点依据**(引 CHARTER 严重度锚点表或 S/M/L/XL 分档行)、**批准记录**(呈报批次 + 用户批复,D-02)。

**锚点引用基准**(CHARTER.md:110-116 严重度锚点表、:124-131 工作量分档表)——每条调整的"锚点依据"必须指向这两张表的具体行,例如:

```markdown
| **MEDIUM** | 潜伏失配(当前参数/格式下不触发,变更即爆);可诱发高危误操作的误导性文档(...);已过期凭证曾入库(泄露习惯风险) |
```

**用户裁定留痕模式**(DO-NOT-FIX.md:43,DNF-04 分流依据行——"归属留待用户最终裁定"的挂起写法):

```markdown
- **分流依据:** D-08 "等"字延伸(01-RESEARCH.md 假设 A3)——本条**非 D-08 逐字点名**,……;Phase 5 组装 RPT-05 时请用户对此条归属作最终裁定。
```

CALIBRATION.md 的批准记录字段即此模式的闭环端:写"经 D-02 批量呈报,用户于 <日期> 批复(逐条确认 / 整批通过)"。DNF-04 在报告 RPT-05 中记"经用户裁定维持(D-13)",**不再请示**。

**尾部对账模式**(DO-NOT-FIX.md:47 尾注 + HYPOTHESES.md:280-285 机械验证命令):文件尾写斜体总结行 + 期望值等式,例如 `grep -c '^### CAL-' .planning/audit/CALIBRATION.md` = 呈报批准条数。

---

### `.planning/audit/REPORT.md`(汇编主报告,批量汇编)

无单一整体类比;各章节逐一对应既有产物范式:

**文件头 + 方法声明**(仿 COVERAGE.md:1-8 头部——标题/Created/基线/一段"证据与判断分离"自述):方法声明须写死:①"45 条目 = 40 真实 + 5 schema 示例(F-*-00),示例剔除"(findings/contract.md:7-9 示例条自带注记"本条为 schema 示例,Phase 5 汇总时剔除");② RPT-02 排序规则(严重度降序 → 工作量升序 S→M→L→XL → ID 稳定序);③ 终级取值规则(CALIBRATION.md 有记录用终级并标"经校准",无记录原级照抄);④ CHARTER 字段 8/9 槽位由 CALIBRATION.md 承载的取舍注记。

**RPT-03 判定准则章节 → 类比 CONTRACT-MATRIX.md:10-17 状态词表**(先定词表、后逐行套用的范式):

```markdown
### 格子状态词表

| 状态词 | 定义 |
|--------|------|
| `agree` | 该实现与其他参与实现在此契约要素上**语义一致**(字面差异不算分歧,见下) |
| `diverge` | 该实现与其他参与实现存在**语义分歧**——同样输入可产生不同的契约行为 |
| `absent` | 该实现**应参与**此契约要素但未实现(覆盖洞候选,per D-03) |
```

BLOCKER / PRE-LAUNCH / POST-LAUNCH 三级准则照此表形式定义(D-09 方向 + D-10 语境写进定义列),准则全文入报告;每条发现的判定引准则条款 + 一句理由(与严重度独立)。总判定三档词(GO / CONDITIONAL GO / NO-GO)由 D-11 机械推导,推导规则一并写进本章节。

**RPT-02 汇总表 → 类比 TEST-AUDIT.md:117-141 反向映射清单**(逐 F-ID 表行 + 判定/去向列 + 图例先行):

```markdown
**图例:** 兜底列取值 = `文件:行号 @ 5927f36`(有关联测试)或『无』;缺口判定列取值 = 终态(参照原严重度 / 无缺口)或占位态(...)。

| 条目 | 原严重度 | 应重点覆盖行为 | 现有测试兜底(@ 5927f36) | 缺口判定 |
|------|----------|----------------|--------------------------|----------|
| F-CON-01 | LOW | 小程序侧 fragment_id 非法日期(...)应被拒绝 | `apps/worker/tests/test_oss_admin.py:75`、... | 缺口参照原严重度 LOW → F-TEST-05 |
```

RPT-02 表列改为:ID / 终级严重度(经校准标注)/ 维度 / 标题 / 工作量 / 上线判定 / 聚类(CL-NN)/ 处置(进工作包 WP-NN / 并入 F-XX-NN 处理 / acknowledge 无需动作)+ 一句概要。**每行只占表行 + 一句,详情链回封版 findings/*.md,不复制九字段全文**(D-15)。副条处置列写"并入 F-XX-NN 处理"(D-08),INFO 行写 acknowledge 沉底(D-07)。

**RPT-05 DNF 登记表 → 类比 DO-NOT-FIX.md 全文**(DNF-01~04 五字段条目可整体转写为四行表:ID / 标注 `⚠ intentional — do not "fix"` / 一句理由 / 证据链接;DNF-04 行加"经用户裁定维持,D-13")。

**RPT-06 优点盘点 → 类比 HYPOTHESES.md 备注行的候选标注**(HYP-03/04/08/09/10/16/19 七处,如 :96):

```markdown
- **备注:** 双侧脱敏机制(MaskedSecret / is_sensitive+hash_openid)经核实有效,记 RPT-06 优点候选;……
```

每条优点 = 一句陈述 + 引既有台账证据行号(HYPOTHESES 备注行 / COVERAGE 行 / 矩阵 agree 行),**不新采证**(D-16)。

**RPT-07 置信声明 → 类比 COVERAGE.md:130-145 完成判定**(编号条目 = 可复算命令 + 数字 + ✓):

```markdown
1. **覆盖对象总数 63** — `grep -cE '^\| \`' .planning/audit/COVERAGE.md` → **63**(CODE 47 + TOOL 16 = 63,对照 ...)✓
3. **已过面全 9/9** — `grep -c '| 9/9 |' .planning/audit/COVERAGE.md` → **63** = 对象总数 ✓
```

五维度各一小节,引各自底稿的规模数字与"已检查无发现"显式源(CON=矩阵 agree 91 格;CODE/TOOL=COVERAGE 63 对象 9/9 面 + "无发现"行;DOC=DOC-CLAIMS 198 条四态,区分 agree 与"无法静态核实";TEST=TEST-AUDIT 41 模块 8/8 面 + 2 处显式无发现;仪器=scans/ 258 命中销号)。

**RPT-01 执行摘要内"存在级观察与范围外事项"小节**(Pitfall 4 落点):逐条点名 HYP-01/11/18/20/21 并回链 HYPOTHESES.md——写法类比 HYPOTHESES.md:76 的显式负向记录段落("已检查,无已知 bug 线索。……本条为显式负向记录,不设 HYP 编号")。

**收尾验证章节 → 类比 HYPOTHESES.md:334-399 阶段收尾验证(04-09 实跑记录)**(命令 + 实际输出照录 + 期望值命中声明):

````markdown
**1. 零 diff 验证(里程碑硬约束,CHARTER 写定命令):**

```
$ git diff --stat 5927f36 -- apps/ scripts/ docs/
(空输出)
$ git diff --stat 5927f36 -- apps/ scripts/ docs/ | wc -l
0
```

期望空输出——**命中 ✓**(apps/scripts/docs 相对基线零改动,全阶段写入面仅 .planning/)。
````

另照抄 COVERAGE.md:147-155 的补充核查:`git status --porcelain` 输出仅含 `.planning/` 路径的复核结论(Pitfall 7:零 diff 命令不保护根文件)。

---

### `.planning/audit/REPORT-APPENDIX-A-traceability.md`(RPT-08 追溯映射表)

**类比:** `HYPOTHESES.md:287-321` §29 条溯源闭环声明——**exact match,可直接机械转写**:

```markdown
| ID | 状态 | 去向 |
|----|------|------|
| HYP-01 | 证实 | D-12 存在级不占发现 ID → RPT 汇总呈现(FC 直转落差,XL 档;与 HYP-20 同根) |
| HYP-02 | 证实 | → F-DOC-06(LOW,聚合条) |
...
| DNF-04 | 预录入(D-08"等"字延伸) | 小程序接收原始 STS 秘密(by design)——……归属由 Phase 5 RPT-05 用户最终裁定 |
```

附录表在此骨架上加两列:**报告落点**(该 ID 在 REPORT.md 的章节/表行锚点——"RPT 呈现"类 5 条 HYP 填执行摘要"存在级观察"小节锚点,防断链)与**需求映射**(维度→需求固定映射:CON↔CONTRACT-01~03、CODE↔AUDIT-01、TOOL↔AUDIT-02、DOC↔AUDIT-03、TEST↔AUDIT-04、HYP 闭环↔AUDIT-05)。

**"已检查,无发现"显式行范式**(HYPOTHESES.md:321,不计入 29 的照录写法):

```markdown
**Known Bugs 显式无线索行(照录,不计入 29):** "已检查,无已知 bug 线索。" CONCERNS.md 原文:"None detected in application code" — ……本条为显式负向记录,不设 HYP 编号、不计入 29 条对账,喂 RPT-08 的"已检查,无发现"显式行。
```

发现↔发现补边来自 findings 各条 `关联发现` 字段——**格式为自由文本**(如 `F-CON-02`、`关联线索: HYP-13`、`矩阵组① 行 4`、`D14-6`,见 findings/contract.md:37,58,83),须人工转写为规整表,不可纯机械解析。

---

### `.planning/audit/REPORT-APPENDIX-B-clusters.md`(聚类明细 CL-NN)

**类比 1:** `TEST-AUDIT.md:169` 成员归属等式——聚类成员关系的既有实证写法,可直接作为聚类成员对账范式:

```markdown
- 反向映射缺口归属等式:21 = F-TEST-03(1:F-TOOL-05)+ F-TEST-04(1:F-TOOL-06)+ F-TEST-05(7:F-CON-01/02/03/06 + F-CODE-07/08 + F-TOOL-08)+ F-TEST-06(6:F-CODE-02/03/06 + F-TOOL-01/02/03)+ F-TEST-07(6:F-CON-04 + F-CODE-01/04/05 + F-TOOL-04/07)✓
```

**类比 2:** DO-NOT-FIX.md 条目结构 → 每簇一节 `### CL-NN: <根因一句话>`,字段 = 根因陈述 / 成员 ID 清单(引用不合并,D-05)/ 关联工作包(互指不强制对齐,D-06)/ 证据锚(引台账既有行,如 TEST-AUDIT 等式行、F-CON-03 关联字段的 D14-6 记法)。

**已知起点(非结论,plan 01 人读判定):** 重试常量四落点(F-CODE-07 × F-TEST-05 × F-TOOL-08)、key 反推无校验(F-CON-03 × 相关条)、镜像常量注释同步(F-CON-05/06 × F-TOOL-08 × F-TEST-05)、静默失败面(F-CODE-02/03 × F-TEST-06)。**注意 Pitfall 6:** F-TEST-05/06/07 是"缺测试锁定"元发现,与其成员修复动作不同(补测试 vs 修代码),归聚类互指,**不是 D-08 真重复**。

尾部写成员全覆盖对账等式(仿 TEST-AUDIT.md:165-172 总机械对账:每条等式 = 数字 + 分解 + ✓)。

## Shared Patterns

### 1. 文件头三件套 + 职责自述
**Source:** COVERAGE.md:1-8 / TEST-AUDIT.md:1-8 / DO-NOT-FIX.md:1-8
**Apply to:** 全部 4 个新文件
标题 → `**Created:** 日期` → `**基线:** \`5927f36\`(全 SHA 见 CHARTER)` → 一段自述(本文件承载什么/不承载什么、依据哪些 locked decision、取证纪律)。报告类文件补一句"证据与判断分离"边界声明。

### 2. 证据格式与秘密红线
**Source:** CHARTER.md:14-15(格式)、:104(红线)
**Apply to:** 全部新文件的任何证据引用
`path:line @ 5927f36` / `path:10-25 @ 5927f36`;秘密类证据**只写位置 + 模式名,绝不复制值本体**(D-15 同时禁止报告复制任何证据片段——报告只链回台账)。

### 3. 机械验证命令块(期望值先写死 → 实跑 → 照录)
**Source:** HYPOTHESES.md:280-285(命令库)、:334-399(收尾照录范式)、COVERAGE.md:130-145(编号完成判定)
**Apply to:** REPORT.md 收尾章节 + 各文件尾部对账

```bash
grep -hc '^### F-' .planning/audit/findings/*.md | paste -sd+ - | bc   # 期望 45
grep -h '^### F-' .planning/audit/findings/*.md | grep -vc '\-00:'     # 期望 40
grep -c '^### HYP-' .planning/audit/HYPOTHESES.md                       # 25
grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md                       # 4(25+4=29 对账)
git diff --stat 5927f36 -- apps/ scripts/ docs/ | wc -l                 # 0
grep -rE 'OSSAccessKeyId=[0-9A-Za-z]{8,}|Signature=[0-9A-Za-z%+/=]{16,}|LTAI[0-9A-Za-z]{10,}' .planning/audit/  # 零命中(exit 1)
```

新增等式:报告主表行数 = 40;三态判定计数和 = 40;CAL 条数 = 批准条数;附录 A 行数 = 29(+显式无发现行另记);聚类成员并集对账。

### 4. ID 约定与 grep 锚点
**Source:** CHARTER.md:165-169(ID 规则)、findings/*.md `^### F-` 标题锚
**Apply to:** CALIBRATION.md(CAL-NN)、附录 B(CL-NN)、报告表行
新 ID 沿 `<前缀>-NN` 两位编号;凡需计数的实体一律用 `^### ` 标题或表行做唯一 grep 锚点(Pitfall 1 教训:抽取以 `^### F-` 为锚,勿依赖槽位文本——上线判定槽存在带注记/裸槽两种格式,27/18 分布)。

### 5. 逐条销号 + 去向闭环
**Source:** HYPOTHESES.md:323-332(HANDOFF 6 条销号表)、TEST-AUDIT.md:157-163(移交逐条销号)
**Apply to:** 附录 A(29 条落点)、REPORT.md(40 条下落)、CALIBRATION.md(呈报批次闭环)
每个 ID 必须有显式去向;每张表尾跟机械对账行(`X = A + B ✓`)。

### 6. 批次导语 blockquote(方法注记)
**Source:** findings/contract.md:23(`> 02-04 判定产物:……`)、COVERAGE.md:8(基线导出备注)
**Apply to:** 报告各章节头
章节级方法说明用 `>` 引块置于节首(如"本表 40 行 = 45 − 5 示例;终级含 N 条经校准,见 CALIBRATION.md")。

### 7. 中文正文 + 英文 ID/严重度术语 + 尾注
**Source:** 全部 Phase 1~4 产物(RPT-09 明文要求)
**Apply to:** 全部新文件
正文中文;ID(F-CON-01/CL-01/CAL-01)、严重度(MEDIUM/LOW/INFO)、判定词(BLOCKER/PRE-LAUNCH/POST-LAUNCH、GO/CONDITIONAL GO/NO-GO)、工作量档(S/M/L/XL)一律英文原词。文件尾统一斜体总结行:`*文档名: 日期(关键计数摘要)*`(见 COVERAGE.md:158、TEST-AUDIT.md:173)。禁数值评分/小时估计——"影响÷工作量"只用序数规则表达(先按包内最高严重度降序、同级按包总工作量档升序)。

## 无类比章节(部分/无类比,规划时按 RESEARCH 模式自拟)

| 章节 | 角色 | 缺口说明 |
|------|------|----------|
| RPT-01 执行摘要叙事(一页) | 主报告开篇 | 仓库无既有"执行摘要"体裁;结构自拟(缘由/范围引 CHARTER,计数用现场 grep 实测 + CALIBRATION 叠加,总判定三档词机械推导附推导链) |
| RPT-04 修复工作包(WP-NN 执行层) | 主报告章节 | 无既有"排期工作包"文档;分组信号 = findings `修复建议` 字段的修复位置 + `关联发现` 互指;呈现可仿附录 B 簇结构(成员/依赖/包级工作量档 per D-04),排序用序数规则(禁数值比值) |
| CONDITIONAL GO 必做清单 | 执行摘要附属 | Claude 裁量:直接引用全部 PRE-LAUNCH 条目 ID,无需另立实体 |

## Metadata

**类比搜索范围:** `.planning/audit/`(全部 10 份台账 + findings 5 份 + scans 9 份,按行数盘点后精读 7 份)
**精读文件:** CHARTER.md、DO-NOT-FIX.md、HYPOTHESES.md、COVERAGE.md、TEST-AUDIT.md、findings/contract.md、CONTRACT-MATRIX.md(标题/表结构)
**Pattern extraction date:** 2026-07-05
