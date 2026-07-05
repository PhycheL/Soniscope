# 附录 A: RPT-08 可追溯映射表(发现 ↔ CONCERNS 线索 ↔ 需求)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文件是 `REPORT.md` 的附录 A(D-14 机械性长内容分文件),承载 **RPT-08 可追溯映射表**:每条发现有下落、每条线索有去向、"已检查,无发现"显式记录在案。数据源两部分:①主表 = `HYPOTHESES.md` §29 条溯源闭环声明表(25 HYP + 4 DNF)**机械转写**,追加"报告落点"与"需求映射"两列;②发现↔发现补边表 = `findings/*.md` 各条 `关联发现` 自由文本字段**人工转写**为规整三列(非纯机械解析)。证据一律只引既有台账行号,不新采证;秘密类只引位置+模式名(CHARTER 秘密红线)。

## 主表: 29 条溯源闭环(25 HYP + 4 DNF)

> 前三列(ID/状态/去向)照录 `HYPOTHESES.md` §29 条溯源闭环声明表;**报告落点**列 = 该 ID 在 `REPORT.md` 的章节锚:落发现的填 `## 发现汇总表` 对应 F-ID 行;存在级/范围外 5 条(HYP-01/11/18/20/21)填 `### 存在级观察与范围外事项`;RPT-06 候选注 `## 优点盘点`;显式无发现的填 `## 分维度置信声明` 对应显式行;DNF 4 条填 `## Do-NOT-fix 登记表`。**需求映射**列按固定映射填写(无需逐条判断):CON↔CONTRACT-01~03、CODE↔AUDIT-01、TOOL↔AUDIT-02、DOC↔AUDIT-03、TEST↔AUDIT-04(以各条 `待验证维度` 定列);DNF 4 条↔RPT-05(Do-NOT-fix 登记表即其交付物);本表 29 条闭环**整体**承载 AUDIT-05(CONCERNS 线索逐条证实/证伪/细化)。行格式:HYP 行以 `| HYP-` 开行、DNF 行以 `| DNF-` 开行(机械对账锚)。

| ID | 状态 | 去向 | 报告落点(REPORT.md) | 需求映射 |
|----|------|------|----------------------|----------|
| HYP-01 | 证实 | D-12 存在级不占发现 ID → RPT 汇总呈现(FC 直转落差,XL 档;与 HYP-20 同根) | `### 存在级观察与范围外事项`(HYP-01 条) | AUDIT-01 |
| HYP-02 | 证实 | → F-DOC-06(LOW,聚合条) | `## 发现汇总表` F-DOC-06 行 | AUDIT-03 |
| HYP-03 | 细化 | RPT-06/加固候选,不占发现 ID(性能面可辩护取舍,正确性有测试锁定) | `## 优点盘点` 第 8 条(纯 JS sha256 文档化取舍) | AUDIT-01 |
| HYP-04 | 证实 | RPT-06 优点候选兼 DNF 候选,不占发现 ID(同模块顺带 F-TOOL-02 独立立项) | `## 优点盘点` 第 7 条(F-TOOL-02 另见 `## 发现汇总表`) | AUDIT-02 |
| HYP-05 | 证实 | → F-DOC-07(INFO) | `## 发现汇总表` F-DOC-07 行 | AUDIT-03 |
| HYP-06 | 证实 | → F-DOC-08(INFO) | `## 发现汇总表` F-DOC-08 行 | AUDIT-03 |
| HYP-07 | 证实 | → F-TOOL-05(MEDIUM) | `## 发现汇总表` F-TOOL-05 行 | AUDIT-02 |
| HYP-08 | 细化 | RPT-06 优点候选;两处细化边界记加固候选不占发现 ID | `## 优点盘点` 第 1 条(双侧秘密脱敏机制) | AUDIT-01 |
| HYP-09 | 证实 | RPT-06 优点候选兼 DNF 候选;无限流面 → F-CODE-05(关联 HYP-17) | `## 优点盘点` 第 2 条(无限流面另见 `## 发现汇总表` F-CODE-05 行) | AUDIT-01 |
| HYP-10 | 证实 | RPT-06 优点候选兼 DNF 候选,不占发现 ID | `## 优点盘点` 第 4 条(单线程免锁简单性) | AUDIT-01 |
| HYP-11 | 细化 | 章程范围外(D-14),不占发现 ID → RPT 范围声明呈现 | `### 存在级观察与范围外事项`(HYP-11 条) | AUDIT-03 |
| HYP-12 | 证实 | DNF 候选,不占发现 ID | `## 分维度置信声明` 置信·CODE"已检查无发现"行(app.py 深挖显式无发现) | AUDIT-01 |
| HYP-13 | 证实 | → F-CON-01/02/03(既有,D-14 引用回填不新立条) | `## 发现汇总表` F-CON-01/02/03 三行 | CONTRACT-01~03 |
| HYP-14 | 证实 | → F-DOC-03(MEDIUM) | `## 发现汇总表` F-DOC-03 行 | AUDIT-03 |
| HYP-15 | 细化 | → F-TOOL-04(LOW) | `## 发现汇总表` F-TOOL-04 行 | AUDIT-02 |
| HYP-16 | 细化 | RPT-06 优点候选兼 DNF 候选;无界重试面 → F-CODE-02(关联);文档口径半句 P-29/T-36 agree | `## 优点盘点` 第 5 条(无界重试面另见 `## 发现汇总表` F-CODE-02 行) | AUDIT-01 |
| HYP-17 | 证实 | → F-CODE-05(LOW) | `## 发现汇总表` F-CODE-05 行 | AUDIT-01 |
| HYP-18 | 细化 | 工具级无独立发现(发现面在 F-TOOL-05);两代 SDK 并存债务观察 → RPT 呈现 | `### 存在级观察与范围外事项`(HYP-18 条) | AUDIT-02 |
| HYP-19 | 证实 | 代码级无发现(外部依赖风险 → RPT 呈现;Protocol 双层隔离记 RPT-06 优点候选) | `## 优点盘点` 第 6 条(外部依赖风险与 `### 存在级观察与范围外事项` HYP-18 条同源呈现) | AUDIT-01 |
| HYP-20 | 证实 | D-12 存在级不占发现 ID → RPT 汇总呈现(与 HYP-01 同根互引) | `### 存在级观察与范围外事项`(HYP-20 条) | AUDIT-01 |
| HYP-21 | 证实 | D-12 存在级不占发现 ID → RPT 汇总呈现(明示 MVP 范围外,PRD 口径一致) | `### 存在级观察与范围外事项`(HYP-21 条) | AUDIT-03 |
| HYP-22 | 证实 | → F-TEST-01(LOW) | `## 发现汇总表` F-TEST-01 行 | AUDIT-04 |
| HYP-23 | 细化 | 显式无发现记录(行为测试补偿充分 9/9;豁免本身 DNF-03,不质疑) | `## 分维度置信声明` 置信·TEST 显式行("HYP-23 结论:补偿充分 9/9") | AUDIT-04 |
| HYP-24 | 证伪 | → F-TEST-02(LOW,证伪后按实态缩窄立条) | `## 发现汇总表` F-TEST-02 行(证伪记录另见 置信·TEST 显式行) | AUDIT-04 |
| HYP-25 | 证实 | → F-TEST-03(MEDIUM) | `## 发现汇总表` F-TEST-03 行 | AUDIT-04 |
| DNF-01 | 预录入(D-08) | whisper-local 故意桩——DOC 核对闭环:DOC-CLAIMS P-24/T-25 agree(闭环 DNF-01),AG-21/AG-34 命中同闭环;Phase 5 RPT-05 用户裁定 | `## Do-NOT-fix 登记表` DNF-01 行 | RPT-05 |
| DNF-02 | 预录入(D-08) | issue-cedential 拼写域名——DOC 核对闭环:DOC-CLAIMS CF-02 核实结论行(五处文档登记逐字符同值,ROADMAP 成功判据 1 点名线索闭环),另 AG-29/AG-38/RF-01/RM-03、CS-08/MA-02/DG-09/DG-16/FD-12 命中均闭环;Phase 5 RPT-05 用户裁定 | `## Do-NOT-fix 登记表` DNF-02 行 | RPT-05 |
| DNF-03 | 预录入(D-08) | FC handler.py mypy 豁免——闭环:HYP-23 交叉引用(补偿充分核实,不质疑豁免本身);CHARTER 双语言适配声明同口径;Phase 5 RPT-05 用户裁定 | `## Do-NOT-fix 登记表` DNF-03 行 | RPT-05 |
| DNF-04 | 预录入(D-08"等"字延伸) | 小程序接收原始 STS 秘密(by design)——闭环:DOC-CLAIMS T-20 语境引用(credential_response 七字段,仅字段名);归属经用户裁定维持(D-13) | `## Do-NOT-fix 登记表` DNF-04 行 | RPT-05 |

**断链自查:** 29 行报告落点列全部非空;存在级/范围外 5 条(HYP-01/11/18/20/21)落点均为 `### 存在级观察与范围外事项` 锚(Pitfall 4 防断链);显式无发现 2 条(HYP-12/23)落 `## 分维度置信声明` 对应显式行;其余 HYP 落 `## 发现汇总表` F-ID 行或 `## 优点盘点` 编号条;DNF 4 条落 `## Do-NOT-fix 登记表`——报告侧无断链。

## "已检查,无发现"显式记录

### Known Bugs 显式无线索行(照录 HYPOTHESES.md,不计入 29)

> **"已检查,无已知 bug 线索。"** CONCERNS.md 原文:"None detected in application code" — `apps/` 源码无 TODO/FIXME/HACK 标记(仅有关于临时文件/占位桩的描述性注释),三套测试套件显式覆盖崩溃恢复、故障注入与幂等路径。本条为显式负向记录,不设 HYP 编号、不计入 29 条对账(照录源:`HYPOTHESES.md:76`,总对账重申 `HYPOTHESES.md:321`)。

### 各维度"已检查,无发现"代表性记录(只引既有行号,不新采证)

| 维度 | 代表性既有记录(行号引用) | 内容 |
|------|--------------------------|------|
| CON | `CONTRACT-MATRIX.md:37` | 矩阵行 1「fragment_id 格式正则」FC/Worker/小程序三端 agree,逐格带行号证据(91 个 agree 格的代表行;全量见矩阵) |
| CODE | `COVERAGE.md:32` | `pipeline.py`(875 行)深挖 9/9 面"无发现"——`.done` 最后写、任一阶段失败不建 `.done`、原子写协议核查通过 |
| TOOL | `COVERAGE.md:88` | `retranscribe.py`(590 行)普审 9/9 面"无发现"——D-03 点名的 `.done` 绕行边界核查通过,误触面受控 |
| DOC | `DOC-CLAIMS.md:235` | FD-09:runbook 部署八步骤 ↔ `fc_deploy.py` 能力面对照 agree,零 drift——文档未声称任何工具不具备的能力(HYP-04 保真度口径闭环) |
| TEST | `TEST-AUDIT.md:153`、`TEST-AUDIT.md:123` | D-11 对照行 4「覆盖率门禁」三方自洽一致(声称面显式自认无门禁,不立条);反向映射 F-CON-05 行"无缺口"(错误码透传行为有断言锁定)——TEST 维度 2 处显式无发现(TEST-AUDIT 总对账点名) |

## 发现↔发现补边表(findings `关联发现` 字段规整转写)

> `findings/*.md` 各条 `关联发现` 字段为自由文本(存在 `F-CON-02`、`关联线索: HYP-13`、`矩阵组① 行 4`、`D14-6` 等多种记法),此处人工转写为规整三列(源 ID / 关系 / 目标引用),不做纯机械解析。关系词表:**关联发现**(F↔F 互指)/ **关联线索**(F → HYP/矩阵/样本)/ **销号来源**(scans/D14/HANDOFF 条目闭环至该 F)/ **严重度参照**(定级规则引用)/ **元发现成员**(F-TEST-05/06/07 缺口归属清单)。`关联发现` 字段为"无"的条目不列行:F-CODE-03、F-CODE-04、F-CODE-06(队列状态机普审产出)、F-TOOL-01、F-TEST-08、F-TEST-09、F-TEST-10(后三条按 CHARTER 锚点独立定级,无交叉引用)。

| 源 ID | 关系 | 目标引用 |
|-------|------|----------|
| F-CON-01 | 关联线索 | HYP-13;矩阵组① 行 2;02-03 样本 S-02/S-04(对照点 a);黄金样本配方覆盖(CONTRACT-TEST-RECIPE.md) |
| F-CON-02 | 关联发现 | F-CON-03(同一 key 族的小程序声部分叉) |
| F-CON-02 | 关联线索 | HYP-13;矩阵组① 行 4;02-03 样本 S-06/S-07/S-18(对照点 c/d);黄金样本配方覆盖 |
| F-CON-03 | 关联发现 | F-CON-02 |
| F-CON-03 | 关联线索 | HYP-13;矩阵组① 行 5;D14-6(第四处重复实现债务,COVERAGE 深挖点裁定销号落点即本条);02-03 样本 S-14/S-18(对照点 b/c);黄金样本配方覆盖 |
| F-CON-04 | 关联线索 | HYP-13;HYP-03(sha256 跨语言双实现关联线索,D14-1);矩阵组① 行 13 |
| F-CON-05 | 关联线索 | HYP-13;Phase 4 DOC 移交(CLAUDE.md 错误码分支声明失实);D14-3(联调工具第二份错误码字面定义) |
| F-CON-06 | 关联发现 | F-CON-05(超限时用户感知依赖错误码透传) |
| F-CON-06 | 关联线索 | HYP-13;矩阵组③ 行 46、组② 行 18/28 size=0 边界注记 |
| F-CODE-01 | 销号来源 | scans/ruff-extended.md #55(ARG001 确认项反填) |
| F-CODE-02 | 关联发现 | F-CON-04(保守告警方案与之同一动作面) |
| F-CODE-02 | 关联线索 | HYP-16 |
| F-CODE-05 | 关联线索 | HYP-17、HYP-09 |
| F-CODE-07 | 销号来源 | D14-2(CONTRACT-MATRIX ③移交记录第 2 条销号) |
| F-CODE-07 | 关联线索 | HYP-13(跨端约定同族);矩阵组③ 行 44-45 |
| F-CODE-08 | 销号来源 | D14-4(CONTRACT-MATRIX ③移交记录第 4 条销号,普查扫描 9 注记) |
| F-TOOL-02 | 关联线索 | HYP-04(能力边界同模块) |
| F-TOOL-03 | 关联发现 | F-CODE-02(残留对象落入其无界重试面) |
| F-TOOL-04 | 关联线索 | HYP-15、HYP-24(页面胶水层无测试,TEST 维度) |
| F-TOOL-05 | 关联线索 | HYP-07(本条即其核实结论,证实)、HYP-25(scripts/ 无门禁,TEST 维度移交) |
| F-TOOL-05 | 销号来源 | scans/secrets.md #14/#15(销号去向闭环至本条) |
| F-TOOL-06 | 关联线索 | HYP-12(app.py 运行时形态,CODE 侧无发现)、HYP-23(handler.py mypy 豁免系故意——本条只针对门禁恒红,不质疑豁免) |
| F-TOOL-06 | 销号来源 | scans/gates-baseline.md #1(销号去向即本条) |
| F-TOOL-07 | 关联线索 | HYP-15(miniprogram_lint 规则面同模块) |
| F-TOOL-08 | 关联发现 | F-CON-05(其关联字段已挂 D14-3,错误码镜像同源) |
| F-TOOL-08 | 销号来源 | D14-3(CONTRACT-MATRIX ③移交记录第 3 条销号) |
| F-TOOL-08 | 关联线索 | HYP-22(联调工具活体路径依赖,TEST 维度移交);矩阵普查表行 50-51、组③ 行 46 辅助线索 |
| F-DOC-01 | 关联线索 | HYP-03(细化:纯 JS 主线程同步哈希半句证实) |
| F-DOC-02 | 关联线索 | HYP-18(细化:两代 SDK 并存、legacy 承载生产主路径证实) |
| F-DOC-03 | 关联线索 | HYP-14(证实方向:发布文档未覆盖翻转步骤;结论行 DOC-CLAIMS.md FD-16) |
| F-DOC-03 | 销号来源 | HANDOFF-PHASE4.md DOC 节第 2、3 条(在此显式销号消费) |
| F-DOC-04 | 关联发现 | F-DOC-05(同文件 AGENTS.md 滞后声明) |
| F-DOC-05 | 关联发现 | F-DOC-04(同文件 AGENTS.md) |
| F-DOC-06 | 关联发现 | F-DOC-04/F-DOC-05(AGENTS.md 同文件) |
| F-DOC-06 | 关联线索 | HYP-02(证实方向:引用失效半句全量坐实;"deletions uncommitted"半句已被基线核实推翻) |
| F-DOC-07 | 关联线索 | HYP-05(证实方向:存在级底数坐实) |
| F-DOC-08 | 关联线索 | HYP-06(证实方向:四目录并存与独立漂移坐实) |
| F-TEST-01 | 关联线索 | HYP-22;TEST-AUDIT.md D-11 对照行 5 |
| F-TEST-02 | 关联线索 | HYP-24(证伪后按实态缩窄立条) |
| F-TEST-03 | 关联线索 | HYP-25 |
| F-TEST-03 | 严重度参照 | F-TOOL-05(MEDIUM;定级规则见 TEST-AUDIT.md 反向映射节首) |
| F-TEST-04 | 严重度参照 | F-TOOL-06(MEDIUM;定级规则同上) |
| F-TEST-04 | 关联线索 | HYP-25 同族门禁完整性;TEST-AUDIT.md D-11 对照行 2/6 |
| F-TEST-05 | 元发现成员 | F-CON-01、F-CON-02、F-CON-03、F-CON-06、F-CODE-07、F-CODE-08、F-TOOL-08(严重度参照组内最高 F-CON-02/03 MEDIUM) |
| F-TEST-06 | 元发现成员 | F-CODE-02、F-CODE-03、F-CODE-06、F-TOOL-01、F-TOOL-02、F-TOOL-03(严重度参照组内最高 F-CODE-02/06 MEDIUM) |
| F-TEST-07 | 元发现成员 | F-CON-04、F-CODE-01、F-CODE-04、F-CODE-05、F-TOOL-04、F-TOOL-07(全组原发现均 LOW,严重度参照) |

## 尾部对账等式(实跑照录,2026-07-05)

```
$ grep -c '^| HYP-' .planning/audit/REPORT-APPENDIX-A-traceability.md
25
$ grep -c '^| DNF-' .planning/audit/REPORT-APPENDIX-A-traceability.md
4
```

25 + 4 = **29** ✓(与 `HYPOTHESES.md` §转换对账 29 条粗体线索底数、`grep -c '^### HYP-'` = 25、`grep -c '^### DNF-'` = 4 全部一致)。

---
*附录 A 可追溯映射表: 2026-07-05(29 条溯源闭环 = 25 HYP + 4 DNF,报告落点全填、需求映射覆盖 CONTRACT-01~03/AUDIT-01~05/RPT-05;Known Bugs 显式无线索行照录 + 五维度"已检查,无发现"代表性记录各一;发现↔发现补边表 46 行规整三列——RPT-08 追溯闭环达成)*
