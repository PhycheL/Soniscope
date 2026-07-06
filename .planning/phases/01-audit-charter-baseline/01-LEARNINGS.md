---
phase: 01
phase_name: "audit-charter-baseline"
project: "SoniScope — 上线前代码审计里程碑"
generated: "2026-07-05"
counts:
  decisions: 8
  lessons: 4
  patterns: 7
  surprises: 3
missing_artifacts:
  - "UAT.md"
---

# Phase 01 Learnings: audit-charter-baseline

## Decisions

### 完整基线 SHA 全文只声明一次,正文统一短 SHA
CHARTER.md 头部声明完整基线 SHA `5927f362785d44b085a791ca387732991012ce5a` 恰一次,正文其余处一律用短 SHA `5927f36`,证据引用统一为 `path:line @ 5927f36` 短格式(锁定决策 D-02)。

**Rationale:** 单一权威声明点避免全文多处 SHA 漂移;短格式引用降低证据书写成本且可 grep 机械核验(完整 SHA grep -c 必须恰为 1)。
**Source:** 01-01-PLAN.md, 01-01-SUMMARY.md

---

### 严重度边界以锚点示例封死,不留裁量措辞
五级严重度(CRITICAL/HIGH/MEDIUM/LOW/INFO)每级绑定 SoniScope 具体场景锚点(数据丢失/静默转写失败/凭证泄漏/存在级观察等);无法对号入座的发现取影响最接近的锚点级别并在理由中写明对应关系,全文禁止"视情况""可酌情"类措辞。

**Rationale:** 章程条款模糊会造成 Phase 2/3 并行执行者口径漂移,Phase 5 校准成本剧增;锚点封死边界使任何审计者可直接套用。
**Source:** 01-01-SUMMARY.md, 01-01-PLAN.md

---

### 顺带安全发现不设自动升级规则
审计维度之外顺带发现的安全问题不自动升级严重度,与其他发现同用影响×可能性定级,仅在台账加 "顺带发现(out-of-dimension)" 标注。

**Rationale:** 保持全部发现使用同一把严重度标尺,避免为安全类别引入例外裁量通道。
**Source:** 01-01-SUMMARY.md

---

### 九字段 schema 预留 Phase 5 槽位
发现记录 schema 在 CHARTER-05 要求的七字段之上追加「上线判定」(BLOCKER/PRE-LAUNCH/POST-LAUNCH,Phase 5 填)与「状态」(draft/calibrated)两槽。

**Rationale:** 在 schema 定稿时就为 Phase 5 校准建槽,避免届时改 schema 导致全部台账返工。
**Source:** 01-01-SUMMARY.md

---

### DNF-04 以 D-08 "等"字延伸归入 Do-NOT-fix,写明假设性质
小程序接收原始 STS 秘密(by design)不在 D-08 点名的三条之内,按 RESEARCH A3 假设以 D-08 "等"字延伸归入 DNF-04,条目内明示该分流依据属假设性质,供 Phase 5 用户最终裁定归属。

**Rationale:** 分流依据不足以锁死时,记录假设并把裁定权显式交还用户,而非静默视为定论。
**Source:** 01-02-SUMMARY.md, 01-02-PLAN.md

---

### HYP 待验证维度分布采纳 plan 建议,零调整
25 条 HYP 的维度标注(CON 1 / CODE 10 / TOOL 4 / DOC 6 / TEST 4)逐条核对后全部采纳 plan 建议清单,未发现更合理归属。

**Rationale:** plan 允许执行者按更合理判断调整,但每条必须恰一个维度;逐条核对确认建议成立后按原样执行,保持计划与产出一致。
**Source:** 01-02-SUMMARY.md

---

### handler.py mypy 豁免采用双侧交叉引用分流
同一主题(FC handler.py 的 mypy strict 豁免)拆为两侧:DNF-03 承接"豁免本身是故意设计",HYP-23(TEST 维度)仅验证"行为测试补偿是否充分",两侧互相以 ID 交叉引用。

**Rationale:** 故意设计的事实与其补偿措施的充分性是两个独立命题;拆开可让 Do-NOT-fix 不阻断对补偿充分性的验证。
**Source:** 01-02-SUMMARY.md, 01-02-PLAN.md

---

### HYP-02 假设范围收窄至未被证伪的半句
CONCERNS.md 原条目含 "deletions uncommitted" 半句已被基线核实推翻(工作树干净、删除已入库),HYP-02 备注写明仅"引用失效"半句待 Phase 4 验证。

**Rationale:** 保持 1:1 转写可追溯性的同时,不把已证伪的事实当作待验证假设,避免 Phase 4 浪费验证工作量。
**Source:** 01-02-SUMMARY.md

---

## Lessons

### 上游研究文档的条目计数需机械命令复核
01-RESEARCH.md 曾统计 CONCERNS.md 线索为 30 条,实为 29 条(Fragile Areas 节误计,实为 5 条)。最终以机械计数命令 `grep -cE '^\*\*[^*]+:\*\*$' .planning/codebase/CONCERNS.md` 输出 29 为准,并在 HYPOTHESES.md 头部记录 30→29 勘误。

**Context:** 人工统计的清单条目数会出错;对账等式(HYP+DNF=源条目数)必须锚定在可重跑的 grep 命令上,而不是上游文档里的手写数字。
**Source:** 01-02-PLAN.md, 01-02-SUMMARY.md

---

### 项目状态文档可能滞后于仓库事实
STATE.md 中记录的 Phase 1 dirty-tree 阻塞(3 份 docs 已删未提交)经 CONTEXT 讨论与 RESEARCH 双重核实已不成立:工作树干净,删除已随提交入库,内容迁至 `docs/v1.0.0 prd/` 与 `docs/runbook/`。本阶段将该条目改写为已解除记录。

**Context:** 后续阶段读到的项目状态若与基线事实不一致会误导执行;发现状态记录过时时应改写为事实记录并指向权威来源(CHARTER.md 审计基线章节),而非删除。
**Source:** 01-02-SUMMARY.md, 01-VERIFICATION.md

---

### ROADMAP 判据措辞与锁定决策的分流需在验证时显式论证为非缺口
ROADMAP 判据 5 表述为"全部线索转为未验证假设清单",实际 29 条中 4 条按锁定决策 D-08 预录入 DO-NOT-FIX.md。验证报告需显式论证:对账等式覆盖全部 29 条、追溯链完整、ROADMAP Phase 5 判据本身要求该登记表存在——分流是需求侧明文预期的结构化,而非范围缩减。

**Context:** 成功判据的字面措辞与实际结构化产出不逐字吻合时,验证环节要主动给出"非缺口"论证,否则会被误判为线索丢失。
**Source:** 01-VERIFICATION.md

---

### 1:1 标题沿用规则的约束范围要在计划里写清
DNF 四条的中文标题与 CONCERNS.md 英文标题不逐字一致——1:1 标题沿用规则(Pitfall 4)在 PLAN 中仅约束 25 条 HYP,DNF 中文标题系 PLAN Task 1 逐字指定,且每条"来源"字段保留原英文标题,可追溯性未受损。

**Context:** 可追溯性规则若只覆盖部分产物,需依赖"来源"字段兜底;验证时残差(sort+diff 后恰为 4 条 DNF)可作为分流完整性的机械证明。
**Source:** 01-VERIFICATION.md

---

## Patterns

### 台账头部对账块:总数等式 + 机械计数命令 + 勘误记录
HYPOTHESES.md 头部写明 `29 = 4 DNF + 25 HYP` 对账等式、生成该数字的 grep 命令原文、以及 30→29 勘误说明,任何人可独立重跑核验。

**When to use:** 任何"源清单 → 分流产物"的转写任务,需要保证零合并零遗漏且事后可机械复核时。
**Source:** 01-02-SUMMARY.md

---

### 证据一律出自 git show <SHA>:<path>,免疫 HEAD 推进
所有行号证据从 `git show 5927f36:<path>` 提取并核实,禁止以工作树文件充当行号证据;DNF 四条证据行号经该方式逐条核实后填写。

**When to use:** 审计/取证类工作中需要引用在长周期内保持稳定的文件行号时——基线钉定后 HEAD 继续推进也不影响证据有效性。
**Source:** 01-01-SUMMARY.md, 01-02-SUMMARY.md

---

### 台账按维度分文件,支撑并行写入防冲突
findings/ 按五个审计维度分五个文件(contract/code/toolchain/docs-config/test),Phase 2 与 Phase 3 并行执行时各自只写自己维度的文件,Phase 5 汇总合并。

**When to use:** 多个并行执行者需要向同一类台账追加记录时,按写入者归属拆分文件以避免合并冲突。
**Source:** 01-01-SUMMARY.md

---

### 秘密类证据红线:只引位置与模式名,绝不复制值本体
涉及凭证/签名/token 的证据只写 `path:line @ 5927f36` + 模式名(如 `OSSAccessKeyId=TMP.*`),值本体哪怕已过期也不复制;automated verify 中配秘密模式负向 grep 门守住红线。

**When to use:** 任何会入库(git 提交)的审计文档引用秘密相关证据时——复制值本体即构成二次泄露。
**Source:** 01-01-SUMMARY.md, 01-02-SUMMARY.md

---

### Automated verify 组合正向断言 + 负向 grep 门 + 不变量检查
每个 task 的自动验证组合三类检查:正向内容断言(五级术语齐、ID 前缀齐、字段齐)、负向禁令(裁量措辞"视情况/可酌情"零命中、"数字+小时"正则零命中、秘密模式零命中)、全程不变量(`git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空)。

**When to use:** 纯文档产出任务的验收——文档内容断言全部可 grep 机械化,禁令与不变量防止执行者越界。
**Source:** 01-01-PLAN.md, 01-02-PLAN.md, 01-VERIFICATION.md

---

### 显式"已检查,无发现"负向记录
CONCERNS.md Known Bugs 节无线索,不静默跳过,而是在 HYPOTHESES.md 写一条显式"已检查,无已知 bug 线索"记录,注明喂 RPT-08 的"已检查,无发现"行。

**When to use:** 审计/排查类工作中某检查项结果为空时——显式负向记录区分"查过没有"与"没查",支撑最终报告的完整性论证。
**Source:** 01-02-SUMMARY.md, 01-02-PLAN.md

---

### HYP 条目五字段固定格式
每条假设固定五字段:来源(原节名+原条目标题,1:1 禁止合并改写)/ 假设(改写为一句可证实/证伪的陈述,不下结论)/ 待验证维度(恰一个短码)/ 状态(初始"未验证")/ 备注(可选,记录分流依据或范围收窄)。

**When to use:** 把未经验证的线索清单转为后续阶段的工作底稿时——"线索是假设不是答案"确保验证阶段不被预设结论污染。
**Source:** 01-02-SUMMARY.md, 01-02-PLAN.md

---

## Surprises

### 上游研究文档把 29 条线索数成了 30 条
01-RESEARCH.md 的分流盘点统计为 30 条,机械计数实为 29 条,差异源于 Fragile Areas 节误计(实为 5 条)。

**Impact:** 若按 30 条组装对账等式会永远无法闭合;最终在 HYPOTHESES.md 头部记录勘误并以机械计数命令为准,Phase 4 对账基准得以稳固。
**Source:** 01-02-PLAN.md, 01-02-SUMMARY.md

---

### STATE.md 宣示的 dirty-tree 阻塞已被事实推翻
项目状态中记录的"3 份 docs 已删未提交"阻塞经双重核实(CONTEXT 讨论 + RESEARCH 工作树核实)已不存在——工作树干净,删除早已随提交入库。

**Impact:** 原以为需要处置的基线阻塞实际已自行解除,CHARTER-01 的 dirty-tree 处置从"处理方案"简化为"记录事实";HYP-02 假设范围据此收窄。
**Source:** 01-02-SUMMARY.md, 01-VERIFICATION.md

---

### 两个 plan 并行创建同一目录未发生冲突
plan 01-01 与 01-02 同属 wave 1 并行执行,均需创建 `.planning/audit/` 目录;因 01-01 在隔离 worktree 中工作且 01-02 以 `mkdir -p` 幂等处理,实际零冲突。

**Impact:** 验证了"幂等目录创建 + worktree 隔离"组合足以支撑同波次 plan 对同一父目录的并行写入,后续波次可沿用。
**Source:** 01-02-SUMMARY.md
