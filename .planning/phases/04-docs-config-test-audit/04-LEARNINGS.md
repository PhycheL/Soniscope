---
phase: 04
phase_name: "docs-config-test-audit"
project: "SoniScope — 上线前代码审计里程碑"
generated: "2026-07-05"
counts:
  decisions: 9
  lessons: 5
  patterns: 9
  surprises: 6
missing_artifacts:
  - "UAT.md"
---

# Phase 04 Learnings: docs-config-test-audit

## Decisions

### 多计划共担的需求不在单计划勾选,留阶段收尾统一销号
AUDIT-04 由 04-01/02/06/07/08 五计划共担,各计划完成自己的证据链份额后显式声明"不在此勾选",需求整体状态由阶段收尾统一处理;worktree 模式执行的计划也不触碰共享的 REQUIREMENTS.md/STATE.md。

**Rationale:** 单计划勾选共担需求会造成"部分完成即标完成"的假信号;并行 worktree 计划写共享簿记文件还会产生合并冲突——Phase 2 的簿记遗漏教训在此被制度化为显式决策。
**Source:** 04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-08-SUMMARY.md

---

### make test 非绿按预置裁量条款照记不阻塞,判断留判断层计划
门禁实跑得 exit=2(2 条 FAILED,均为 SONISCOPE_HOME 未设置的环境依赖),按计划预置的"若非绿照记不阻塞"条款如实归档环境观测,定级判断留给 04-08 判断层。

**Rationale:** 取证计划遇到非预期结果时,预置裁量条款让执行者不必停摆升级;"照记不判断"保持证据层与判断层分离——该现象最终成为 F-TEST-04 门禁信号失真发现的一部分。
**Source:** 04-01-SUMMARY.md, 04-08-SUMMARY.md

---

### 覆盖率工具经 ephemeral --with 注入,包合法性走 blocking-human
pytest-cov 经 `uv run --frozen --with pytest-cov` 临时注入(零仓库配置写入),注入前设 blocking-human 检查点由用户核验 PyPI 归属(pytest-dev)后批准,批准记录写入归档文件头。

**Rationale:** 沿 Phase 3 仪器包先例:第三方包引入交人裁决;ephemeral 注入使覆盖率采集不在 pyproject.toml/uv.lock 留任何痕迹,零 diff 与零配置写入双守住。
**Source:** 04-02-SUMMARY.md

---

### PRD 转引 tech-spec 的声明由 tech-spec 节承接,避免双计
文档声明清单编号时,PRD 转引 tech-spec 章节的声明不在 PRD 节重复登记,PRD 节只核 PRD 直接给出字面值/行为的声明。

**Rationale:** 权威链上游转引下游的内容若双计,同一失实会被记两条、对账数字虚胀;按"谁直接声明谁承接"划分归属保持清单可对账。
**Source:** 04-03-SUMMARY.md

---

### 同根因多处命中聚合一条发现,census 全量行号入条目
三文件"现状/后续 story"滞后叙述聚合一条 F-DOC-05;全仓 10 文件 ≈47 处旧路径死链聚合一条 F-DOC-06(HYP-02);反向映射 21 条测试缺口按共同根因归 5 条 F-TEST;三个门禁信号失真点(JS 桥静默 skip/typecheck 恒红/环境依赖)合并 F-TEST-04。

**Rationale:** 逐处立条会让台账被同一根因的重复条目淹没,修复里程碑要的是"一个根因一个工单";聚合条目内保留 census 全量行号,粒度信息不丢失。
**Source:** 04-05-SUMMARY.md, 04-08-SUMMARY.md

---

### 自带懒创建语义的引用判非死链
domain.md/issue-tracker.md 引用的 CONTEXT.md、docs/adr/、.scratch/ 在基线不存在,但文档明示 "proceed silently"(懒创建语义)——判非死链,已审无发现。

**Rationale:** 死链的定义是"声称存在而不存在";声明自身携带"不存在则静默继续/按需创建"语义的引用不构成失实,机械 grep 命中要过语义判断。
**Source:** 04-05-SUMMARY.md

---

### 假设证伪后按实态缩窄立条,不按原表述立条
HYP-24("页面胶水层无自动化测试")被专项核实证伪(3/3 注册页均被 node 测试真实加载)后,缺口候选面按实态缩窄为"选择性驱动,未驱动路径无自动化"立 F-TEST-02(LOW),批次导语显式记录原表述证伪。

**Rationale:** 按已证伪的原表述立条会把假发现写进台账;证伪不等于零缺口——缩窄后的残余事实仍值得入账,但严重度与表述必须跟着证据走。
**Source:** 04-08-SUMMARY.md, 04-09-SUMMARY.md

---

### HYP-13 采用 D-14 引用回填:零新采证零新立条
核心假设 HYP-13(契约三处重复)回填"证实"时,四要素证据全部引用 CONTRACT-MATRIX 既有行(Phase 2 产物),不重复采证、不新立条——去向指向既有 F-CON-01/02/03。

**Rationale:** 跨阶段假设的证据在上游阶段已封版时,引用回填避免重复劳动与版本分叉;台账间的引用链本身就是 RPT-08 溯源要求的形态。
**Source:** 04-09-SUMMARY.md

---

### 三方对照框架允许按实跑观测扩行
D-11 门禁完整性三方对照计划列 5 项,执行中发现 gate-run 实跑的环境依赖现象(干净环境 make test 非绿)在 5 项框架无处安放,依计划"至少覆盖以下对照项"的措辞增设第 6 行并补静态侧依赖面证据。

**Rationale:** 对照框架的"至少"措辞给执行者留了扩行授权;实跑观测暴露的新对照维度应入表而非塞进备注,否则三方对照的完备性声明失真。
**Source:** 04-08-SUMMARY.md

---

## Lessons

### 计划指定的 grep 模式可能零命中,检索方法本身要按实态修正并入档
计划指定 `git grep "require.*pages/"` 检索页面加载,实际零命中——JS 测试一律经 `path.resolve` 变量 + `require(INDEX_PAGE)` 形态加载。改用"路径常量定义 + require(<VAR>)"双检索还原完整加载矩阵,并把检索方法备注写入 HYP-24 专项节防后续复核踩同一坑。

**Context:** 零命中不等于零存在;字面模式检索在有中间变量的代码上系统性漏报——这次修正直接推翻了 HYP-24 的假设前提,是本阶段最重要的单条事实发现,也暴露 TESTING.md 漏记 4 处 harness 加载。
**Source:** 04-07-SUMMARY.md

---

### 计划预列的枚举数要以基线实际枚举为准
HYP-23 错误码计划预列 7 个,`errors.py @ 5927f36` 实际枚举 9 个(另有 INVALID_REQUEST、HEAD_OBJECT_FAILED);按计划明示"以实际枚举为准"扩为 9 行逐码登记。上游 census 数字同样如此:设计文档旧路径预核 3 处、全量实测 4 处,以实测为准并注明修正来源。

**Context:** 研究/计划阶段的枚举与计数只能当下限提示;执行时全量核对基线是唯一权威——"以实际为准"条款应成为所有枚举类任务的标准授权。
**Source:** 04-07-SUMMARY.md, 04-05-SUMMARY.md, 04-09-SUMMARY.md

---

### worktree 执行模式下,主仓未跟踪文件对计划上下文不可达
04-06 执行时发现计划 `<context>` 引用的 04-PATTERNS.md 在主仓为未跟踪文件,未随基线提交进入执行 worktree,引用不可达;以其余齐备上下文(COVERAGE.md 仿写范式等)执行,产出不受影响。

**Context:** 给 worktree 执行的计划引用上下文文件时,必须确认该文件已提交——untracked 文件在主仓可见但在 worktree 里不存在;这是 worktree 隔离模式的固有边界。
**Source:** 04-06-SUMMARY.md

---

### 需求簿记滞后是跨阶段复发现象
04-VERIFICATION 再次记录 REQUIREMENTS.md 中 AUDIT-04/AUDIT-05 复选框仍为 Pending(与 Phase 2 的 CONTRACT-01/03 同款),定性为"阶段收尾簿记滞后,应由 orchestrator 统一更新,不构成目标缺口"。

**Context:** 多计划共担 + worktree 隔离的组合下,需求勾选天然滞后于实质完成;本阶段已把"留收尾统一销号"写成显式决策,验证者按此口径不再判缺口——处置方式趋于成熟。
**Source:** 04-VERIFICATION.md, 04-08-SUMMARY.md

---

### 占位态措辞要与收口 gate 协同设计
04-06 建骨架时保证"补证中"字样仅出现在 2 个表行单元格(说明性文字零出现),并预验证 `grep -c '补证中'` = 表行计数——04-07 收口时负向 grep 直接可用,零占位残留可机械证明。04-03 同款:占位词只出现在覆盖总表状态列,04-05 收口负向 grep 直接跑。

**Context:** 占位词若散落在说明文字里,收口时的"零残留"检查会误报;写占位时就约束其出现位置,是让"未完成→完成"转换可机械验收的前提。
**Source:** 04-06-SUMMARY.md, 04-03-SUMMARY.md

---

## Patterns

### worktree 基线专区实跑:建区 → 实跑 → 归档 → 拆区
需要实跑基线代码时用 `git worktree add <scratchpad>/wt-5927f36 5927f36`(detached HEAD)+ `uv sync --frozen` 建仓外专区;跨计划复用时记录绝对路径与重建命令;用毕 `git worktree remove --force` + prune,`git worktree list` 确认零残留。

**When to use:** 审计需要执行基线代码(门禁、测试、覆盖率)而主仓必须零触碰时——比 git archive 导出多了完整 git 上下文与依赖安装能力。
**Source:** 04-01-SUMMARY.md, 04-02-SUMMARY.md

---

### 受控反事实观测:证明"全绿 ≠ 全跑"
在 PATH 中剔除 node 后重跑测试桥,观测到 SKIPPED [1] + exit 0——用受控环境变更实证"门禁绿灯下测试可以整体静默跳过",证据入档供门禁完整性判定引用。

**When to use:** 审计门禁/CI 的信号可靠性时——静态读 skipif 只能证明"可能跳过",反事实实跑证明"跳过时信号无异样",后者才是发现的证据强度。
**Source:** 04-01-SUMMARY.md

---

### 四态销号清单:agree / drift / dead-ref / 无法静态核实
文档声明逐条编号(P-NN/T-NN/CS-NN/AG-NN…),每条销为四态之一;每文档节尾对账等式(四数之和 = 条目数),批次与阶段两级机械对账;dead-ref 统一登记指向聚合假设,drift 去向 F-DOC 编号闭环。

**When to use:** 文档与代码实态的一致性审计——四态比二元"对/错"多出"引用失效"与"静态不可判"两个诚实类别,控制台/云端事实照登不猜(零猜测纪律)。
**Source:** 04-03-SUMMARY.md, 04-04-SUMMARY.md, 04-05-SUMMARY.md

---

### D-11 三方对照:声称 × 静态配置 × 实跑观测
门禁完整性逐项取证三方:文档/惯例声称什么、配置静态写了什么、实跑实际发生什么;三方一致判"一致",任一方脱节判"缺口候选"并反填发现编号。

**When to use:** 审计"某机制是否真的在工作"类命题——单看配置会漏执行环境问题,单看实跑会漏声称与配置的错位;三方对照一次性暴露全部脱节维度。
**Source:** 04-08-SUMMARY.md

---

### 锚点先行、回填集中
证据计划(04-03/04/05/07/08)只在各自台账写"HYP 结论锚点"(锚点位置表),HYPOTHESES.md 状态全程不动;收官计划(04-09)统一消费锚点做全部回填。

**When to use:** 多计划并行产出同一假设清单的证据时——单一写入点避免并行冲突,回填时锚点表使证据引用零重复采证;与 Phase 3 的"下落列留收口统一回填"同构。
**Source:** 04-05-SUMMARY.md, 04-08-SUMMARY.md, 04-09-SUMMARY.md

---

### 测量数字只作证据,不作评分,负向 grep 守门
覆盖率归档(73% TOTAL / 92.73% line)明示"不附带任何阈值判断或质量结论";发现条目引用数字时显式标注"仅作证据引用";收口跑 `grep -ci '评分\|score'` = 0 机械验收。

**When to use:** 章程禁止数值化质量评分而审计又需要量化证据时——数字归档与判断禁令可以共存,负向 grep 把红线变成可验收条款。
**Source:** 04-02-SUMMARY.md, 04-08-SUMMARY.md, 04-VERIFICATION.md

---

### 逐码/逐对象补偿核查表:枚举全集 × 覆盖判定
HYP-23 专项以 errors.py 实际枚举的 9 个错误码为行,每行核 handler 入口级行为覆盖(importlib 动态加载绕开 mypy 豁免的补偿机制),9/9 全"有"→ 补偿充分,显式无发现。

**When to use:** 验证"豁免/缺口有无补偿机制"类假设——以基线枚举全集为分母逐项打勾,结论是可对账的完备性证明而非抽样印象。
**Source:** 04-07-SUMMARY.md

---

### 反向映射清单:每条既有发现核测试兜底
22 条 F-* 逐条反查关联测试(有则记 `文件:行号 @ 5927f36`,无则记"无"附 grep 裁决);静读不可定判的行显式占位"补证中",普审后销号定终态;缺口按参照原严重度定级。

**When to use:** 测试审计要回答"已知脆弱点有没有测试守着"时——以发现台账为驱动的反向映射比正向覆盖率更直接命中风险面。
**Source:** 04-06-SUMMARY.md, 04-07-SUMMARY.md

---

### 引用级/存在级审计:排除对象的分级处置
章程排除的目标态文档做"引用级"审计(节首显式标"目标态对照未审(章程排除)",只核现状代码引用实存与明显自相矛盾);vendored/脚手架做"存在级"登记(底数计量:文件数/字节数/blob 漂移抽样),不逐文件审。

**When to use:** 审计范围有排除项但完整性叙事要求"每个对象有下落"时——分级处置让排除项也有可验收的审计动作,而非静默跳过。
**Source:** 04-05-SUMMARY.md

---

## Surprises

### HYP-24 被证伪:三个页面全部被 node 测试真实加载
假设"页面胶水层无自动化测试"经加载矩阵核实不成立——3/3 注册页均被加载,index.js(796 行)被 4 个测试文件的 Page harness 驱动;TESTING.md 也漏记了这 4 处加载。

**Impact:** 25 条假设中唯一的"证伪";F-TEST-02 按缩窄后实态立条(选择性驱动),原表述若未核实直接立条就是假发现。检索方法(变量形态 require)的修正是发现契机。
**Source:** 04-07-SUMMARY.md, 04-09-SUMMARY.md

---

### 干净环境下 make test 非绿:门禁自带环境依赖
worktree 基线专区(干净环境)实跑 make test 得 2 条 FAILED,均因 SONISCOPE_HOME 未设置(RuntimeHomeError)——测试套件对执行机环境有隐性依赖,干净检出即非绿。

**Impact:** "门禁非绿 ≠ 代码错"成为门禁信号失真的第三个实证点,与 JS 桥静默 skip、typecheck 恒红合并为 F-TEST-04(MEDIUM);三方对照因此扩行。
**Source:** 04-01-SUMMARY.md, 04-08-SUMMARY.md

---

### 发布文档完全没有 ENV 生产翻转步骤
deployment-guide 发布流程与附录清单零 ENV 项,全文档检索翻转步骤零命中;唯一记载该风险的 architecture-review 建议从未落入任何 runbook——照文档发布即把 `ENV='development'`(开发者菜单 + 故障注入开关)带给最终用户。

**Impact:** F-DOC-03(MEDIUM)成为 DOC 维度最重发现;修复只需 S 档(发布清单补两行),典型的"低成本修复、高影响遗漏"。
**Source:** 04-04-SUMMARY.md

---

### AGENTS.md 死链密度远超预期:17 处,全仓 47 处
权威文档迁移后,AGENTS.md 单文件 17 处旧路径引用(导航双表整体失效),全仓 census 达 10 文件 ≈47 处;census 过程中还发现预核之外的新命中(multi-user-design.md:600)。

**Impact:** HYP-02 从"个别引用失效"实证为系统性迁移遗漏,聚合立 F-DOC-06;修复是一次批量替换(S 档),但新路径含空格需转义的细节已写进修复建议。
**Source:** 04-05-SUMMARY.md

---

### config.js 深核零 drift:配置与四文档逐字符一致
唯一硬编码真实云值的 config.js 八条声明全 agree——URL/appid/区域等字面值与 cloud-setup/tech-spec/PRD/AGENTS 四文档逐字符一致,头注"本文件为唯一真值源"自证属实。

**Impact:** 配置漂移的最大嫌疑对象被证明干净;issue-cedential 拼写域名五处登记同值,ROADMAP 点名线索以 agree 闭环 DNF-02——审计的价值不只在找问题,也在给"没问题"以证据。
**Source:** 04-05-SUMMARY.md

---

### 9 个错误码全部有 handler 入口级行为覆盖:mypy 豁免的补偿是充分的
HYP-23 专项逐码核查发现:测试用 importlib 唯一模块名动态加载双 handler(绕开 mypy 豁免的行为级补偿),GET/POST/异常三类入口全被驱动,9/9 错误码有覆盖——补偿充分性半句成立,显式无发现。

**Impact:** DNF-03(豁免本身故意)↔ HYP-23(补偿是否充分)的双侧分流在 Phase 1 设计、Phase 4 兑现:豁免未被质疑、补偿被证实,两个判断各自闭环互不污染。
**Source:** 04-07-SUMMARY.md, 04-09-SUMMARY.md
