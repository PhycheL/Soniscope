# Phase 4: 文档配置与测试审计 - Pattern Map

**Mapped:** 2026-07-05
**Files analyzed:** 7(新建 4 + 续写 3)
**Analogs found:** 7 / 7(全部有强类比,无"无类比"项)

> 本阶段是纯审计阶段:全部产物为 `.planning/audit/` 下的审计台账文档。类比对象不是运行时代码,而是 Phase 1–3 已封版的审计产物——**它们既是格式类比,也是 Phase 5 汇总一致性的硬约束**(03-RESEARCH「Don't Hand-Roll」:任何新格式发明都破坏 Phase 5 汇总)。源码 `apps/`、`scripts/`、`docs/` 一律只读(零 diff,基线 `5927f36`)。

## File Classification

| 新建/续写文件 | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `.planning/audit/DOC-CLAIMS.md`(新建) | 销号清单底稿(证据层) | batch(声明抽取 → 四态逐条销号) | `.planning/audit/CONTRACT-MATRIX.md` | exact(同为"状态词表 + 逐格行号证据 + 机械对账"清单) |
| `.planning/audit/TEST-AUDIT.md`(新建) | 覆盖台账 + 反向映射清单(证据层) | batch(逐模块过面 → 逐条销号) | `.planning/audit/COVERAGE.md` | exact(同为"关注面清单 + 对象台账 + 线索登记"三段结构) |
| `.planning/audit/scans/coverage-pytest.md`(新建) | 仪器实跑归档 | batch(命令 → 输出 → 存档) | `.planning/audit/scans/gates-baseline.md` | exact(同为"实跑门禁/仪器 + 版本 + 输出 + 只存档不判断") |
| `.planning/audit/scans/coverage-node.md`(新建) | 仪器实跑归档 | batch | `.planning/audit/scans/gates-baseline.md` + `scans/vulture.md`(对账等式) | exact |
| `.planning/audit/findings/docs-config.md`(续写 `## 发现` 节) | 发现台账(判断层) | append-only(九字段条目追加) | `.planning/audit/findings/code.md` | exact(同 schema;骨架含 F-DOC-00 示例已建) |
| `.planning/audit/findings/test.md`(续写 `## 发现` 节) | 发现台账(判断层) | append-only | `.planning/audit/findings/code.md` | exact(骨架含 F-TEST-00 示例已建) |
| `.planning/audit/HYPOTHESES.md`(续写:11 条回填 + 尾部总对账) | 假设台账(跨阶段活文档) | in-place 回填 + 尾部追加 | 同文件内已回填的 14 条(自类比) | exact |

**只读引用、严禁续写的封版产物(D-16):** `COVERAGE.md`、`CONTRACT-MATRIX.md`、`HANDOFF-PHASE4.md`、`CHARTER.md`、`DO-NOT-FIX.md`、`findings/contract.md`、`findings/code.md`、`findings/toolchain.md`、`scans/*`(既有 6 份)。

## Pattern Assignments

### `.planning/audit/DOC-CLAIMS.md`(销号清单底稿,batch)

**Analog:** `.planning/audit/CONTRACT-MATRIX.md`(Phase 2 契约漂移矩阵——D-07 明示"延续 CONTRACT-MATRIX 范式")

**文件头模式**(CONTRACT-MATRIX.md:1-6):标题 + `**Created:**` + `**基线:** \`5927f36\`(全 SHA 见 CHARTER)` + 一段说明本文档角色、引用锁定决策编号、声明取证口径:

```markdown
# 契约漂移矩阵

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本矩阵是 Phase 2(契约抽取与漂移分析)的核心证据文档:行 = 契约要素(D-02 逐字段)……全部证据出自 `git show 5927f36:<path>` / `git grep -n <pat> 5927f36 -- apps/`,禁止读工作树取证(D-05)。
```

**状态词定义表模式**(CONTRACT-MATRIX.md:10-17)——DOC-CLAIMS 以 D-07 四态替换词表内容(agree / drift / dead-ref / 无法静态核实),表结构照抄:

```markdown
| 状态词 | 定义 |
|--------|------|
| `agree` | 该实现与其他参与实现在此契约要素上**语义一致**(字面差异不算分歧,见下) |
| `diverge` | …… |
```

**负面清单前置排除模式**(CONTRACT-MATRIX.md:23-29)——DOC 核对必须同构设置(`issue-cedential` → DNF-02 闭环、目标态两文档 → CHARTER 排除项,per D-06 与 RESEARCH Anti-Patterns):

```markdown
### 负面清单(判定前置排除)

以下事项**不得**立为契约分歧(依据 `.planning/audit/DO-NOT-FIX.md` DNF-01~04 与 CHARTER 排除项表):

- **DNF-01~04 已裁定的故意设计**——包括 `issue-cedential` 域名拼写(DNF-02,阿里云分配的真实 URL)……均不立 F-CON。
- **不引入 `docs/fc-transcribe-design.md` 目标态对照**(CHARTER 明确排除项)……
```

**清单行模式**——04-RESEARCH.md Pattern 1 已给出定稿表结构(直接用,双侧行号证据 + 判定态 + 闭环去向):

```markdown
| # | 文档侧声明 | 文档证据 | 代码/配置侧实态 | 代码证据 | 判定 |
|---|-----------|----------|----------------|----------|------|
| C-01 | "issue-cedential 子域名少一个 r,是阿里云分配的真实 URL" | `apps/miniprogram/config.js:8 @ 5927f36` | 常量值确为该拼写 | `apps/miniprogram/config.js:10 @ 5927f36` | agree(闭环 DNF-02) |
| C-02 | AGENTS.md:"产品范围与验收:docs/PRD_v1.md" | `AGENTS.md:5 @ 5927f36` | 基线该路径无文件,实存 `docs/v1.0.0 prd/PRD_v1.md` | `git ls-tree 5927f36 docs`(无 docs/PRD_v1.md) | dead-ref → HYP-02 |
```

单格证据的"状态词 + 行号 + 括注说明"写法参照 CONTRACT-MATRIX.md:38 实例:

```markdown
| 2. fragment_id 日期合法性校验 | agree `apps/fc/shared/fc_shared/sts.py:54-58 @ 5927f36`(正则命中后 `datetime()` 构造校验,非法抛 400 INVALID_REQUEST) | … | absent `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(正则仅形状校验……) | 覆盖洞 → F-CON-01 |
```

**机械对账收口模式**(CONTRACT-MATRIX.md:267-274)——每份深核文档销号完成后与阶段收尾都要有这类"计数 + 复算等式 ✓"节(用户硬要求可机械验收):

```markdown
### ④ 完成判定(机械对账,CONTRACT-03 可复核收口)

- 扫描命令条数:**5**(上节 fenced bash 逐条存档,均可重放……)
- 总命中数:954 + 295 + 30 + 34 + 234 = **1547**(……复算:966 + 581 = 1547 ✓)
- 矩阵行总数:组① 15 + 组② 28 + 组③ 5 + 普查 3 = **51 行**
```

**DOC-CLAIMS 专属增量(无既有先例、由 CONTEXT 决定):** ① 每份文档一节,含 D-05 分层标注(深核/普审/只审引用/只记存在);② 目标态两文档节显式标"目标态对照未审(章程排除)"(D-06);③ "无法静态核实"态用于纯云端事实(appid 平台真值、控制台配置),不猜测(D-07 + RESEARCH Open Question 2)。

---

### `.planning/audit/TEST-AUDIT.md`(覆盖台账 + 反向映射,batch)

**Analog:** `.planning/audit/COVERAGE.md`(Phase 3 覆盖台账——「Don't Hand-Roll」明示"只读仿写到新文件")

**文件头 + 执行区备注模式**(COVERAGE.md:1-8):头部声明"证据与判断分离,发现不入本文件";第 8 行的"基线导出备注"是 worktree 专区备注的直接类比(路径失效可按命令重建):

```markdown
本文档是 Phase 3(组件与工具链深潜)的覆盖台账——证据与判断分离,只登记"哪个对象、审到什么深度、过了哪些面、产出了什么",不承载发现正文(发现入 `findings/code.md` / `findings/toolchain.md`)。……取证方法:证据一律提取自 `git show 5927f36:<path>`……禁读工作树取证。

> **基线导出备注(D-08……):** 仪器扫描对象为基线导出副本,导出命令 `git archive 5927f36 apps scripts | tar -x -C <EXPORT>`,导出路径(会话 scratchpad,仓库外):…… 若会话更替导致该路径失效,按上述命令重导出即可(内容由基线 SHA 唯一决定)。
```

Phase 4 同位置写 worktree 备注:`git worktree add <SCRATCH>/wt-5927f36 5927f36`、专区内 `uv sync --frozen` / `uv run --frozen ...`、收尾 `git worktree remove --force`(04-RESEARCH §Code Examples 已实测)。

**质量检查面清单模式**(COVERAGE.md:10-24)——D-10 清单的直接结构类比:定稿固定分面表、每面锚定 CHARTER 锚点、成为"已过面 N/M"的分母定义:

```markdown
## 普审关注面清单(D-04 定稿,9 面)

以下 9 面为全阶段"已过面 N/9"的分母定义……每面锚定 CHARTER 严重度锚点:

| # | 关注面 | CHARTER 锚点 | 仪器辅助信号 |
|---|--------|--------------|--------------|
| 1 | 静默失败路径(异常吞并、except-pass、错误被忽略) | HIGH 静默转写失败 | ruff S110/BLE/TRY(探针已见 S110 ×1) |
```

Phase 4 分面内容按 D-10 方向定稿(断言强度、fake 漂移风险、隔离惯例、契约常量锁定、泄漏断言覆盖、静默 skip 路径等,条目粒度属 Claude 裁量);"仪器辅助信号"列可指向 scans/coverage-*.md。

**逐对象台账行模式**(COVERAGE.md:30-32)——每个测试模块(pytest 31 文件 + node:test 10 文件)一行,备注列承载证据行号与去向:

```markdown
| 路径 | 行数 | 维度 | 深度 | 已过面 | 产出 | 备注 |
|------|------|------|------|--------|------|------|
| `apps/worker/src/soniscope_worker/pipeline.py` | 875 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-10 证实:串行 for 循环 `pipeline.py:407-441 @ 5927f36`……(回填见 HYPOTHESES.md)。 |
```

"产出"列取值惯例:`无发现` / `F-XXX-NN` / `F-XXX-NN(共证)` / `无发现(D14-N 证据移交)`——Phase 4 对应 `F-TEST-NN` 与"无缺口"。

**反向映射清单模式(D-09)**——结构类比 COVERAGE.md:105-108「深挖点登记(20 处)」表(线索 | 维度 | 命中模块路径 | 下落),行集换为 22 条 F-*(F-CON-01~06 / F-CODE-01~08 / F-TOOL-01~08)+ 契约矩阵关键行:

```markdown
| 线索 | 维度 | 命中模块路径 | 下落 |
|------|------|--------------|------|
| HYP-01 | CODE | apps/fc/ 目录结构(transcribe_audio/ 缺席……) | 已回填(证实,03-04):……见 HYPOTHESES.md |
```

Phase 4 列改为:`F-* 发现 | 应重点覆盖行为 | 现有测试兜底(测试文件:行号 或 "无") | 缺口判定与定级(参照原发现严重度)`。既有测试对 F-* 的兜底证据可从 findings 正文反查(如 F-CODE-07 证据段内已含 `apps/miniprogram/test/uploader.test.js:55-56 @ 5927f36` 字面断言、`apps/worker/tests/test_nls.py:401,449-450 @ 5927f36` 结构断言——findings/code.md:110)。

**门禁三方对照(D-11)专属增量:** 无单一先例,组合两处——声称/静态两方用 CONTRACT-MATRIX 式对照表,实跑观测一方引 scans/coverage-*.md 归档计数(collected/passed/skipped);已知线索静态证据在 HANDOFF-PHASE4.md:19-20(`pyproject.toml:32,50 @ 5927f36`、`Makefile:166-167 @ 5927f36`)与 04-RESEARCH(`test_miniprogram_js.py` skipif 行 24)。

---

### `.planning/audit/scans/coverage-pytest.md` 与 `scans/coverage-node.md`(仪器实跑归档,batch)

**Analog:** `.planning/audit/scans/gates-baseline.md`(实跑门禁归档先例)+ `scans/vulture.md`(紧凑归档 + 对账等式)

**文件头模式**(gates-baseline.md:1-8):标题「扫描档案:…」+ Created/基线 + `per D-NN` 依据句 + 执行环境防护声明 + **工具版本行**:

```markdown
# 扫描档案:现有门禁基线(仓内直调)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-05(现有门禁)/ D-07(命令+版本+输出存档)/ D-08(不经 make,仓内直调实体命令)。……`uv run --frozen` 防 lock 更新,零仓库写入。命中 ≠ 发现:销号列 03-02 填。

**工具版本:** uv 0.8.14 / mypy 2.1.0 (compiled) / ruff 0.15.20 / Python 3.12.11(venv 解释器)……
```

Phase 4 的 per 依据换 D-01/D-02/D-03(pytest 侧)与 D-04(node 侧);工具版本行记 uv / pytest / pytest-cov / node 实测版本(命令:`uv run --frozen --with pytest-cov pytest --version`、`node --version`)。

**命令 + 结果 + 注记模式**(gates-baseline.md:19-31):fenced bash 命令原文 → `**结果:exit=N,…计数**` → 完整/摘要输出 fenced block → `**注记……:** ……此处只存档不判断`:

````markdown
```bash
uv run mypy   # 直调,不经 make;实跑加 --frozen 防 lock 更新
```

**结果:exit=1,1 error / 67 files checked**

**注记(待 03-02 销号核实):** ……属 TOOL 维度观察点,此处只存档不判断。
````

**前后零 diff 快查模式**(gates-baseline.md:10-15)——worktree 方案下主仓不被触碰,但阶段收尾零 diff 仍照跑;归档内记录 worktree 建/拆命令与 `git worktree list` 清理确认即为同构防护记录:

````markdown
## 直调前零 diff 快查(Pitfall 6)

```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/
# 实际输出:(空)——PASS
```
````

**对账等式收尾模式**(vulture.md:33-35):

```markdown
**对账等式:** 确认 1 + 误报 0 + 移交 0 = 命中总数 1 ✓

**移交说明:** 本档无移交项。
```

**Coverage 专属增量(RESEARCH Pattern 3 + 成功判据 3):** ① 数字仅按模块/包罗列,**零阈值判断、零评分语言**(机械验收:`grep -ci '评分\|score' findings/test.md → 0`);② node 侧数字必须标注 "experimental 来源"(`--experimental-test-coverage`);③ 双档案互记口径备注:pytest-cov 测不到 node 子进程、node 报告含 pages/(HYP-24 证据点)、`--test-coverage-exclude='apps/miniprogram/test/**'` 控噪;④ `make test` 观测记 collected/passed/skipped 三计数(`-rs` 保留 skip 原因),供 D-11 三方对照。

---

### `.planning/audit/findings/docs-config.md` 与 `findings/test.md`(发现台账,append-only)

**Analog:** `.planning/audit/findings/code.md`(Phase 3 实战条目)+ 两文件自带骨架(F-DOC-00 / F-TEST-00 示例,docs-config.md:7-19 / test.md:7-19)

**写入位置:** 仅在既有 `## 发现` 标题(两文件均在 :21)之下追加;文件头与 schema 示例条目不动。

**批次导语模式**(code.md:23)——每个执行计划落款一段 blockquote,总结"共 N 条发现 + 显式无发现清单 + DNF 对照命中不立发现 + 移交去向":

```markdown
> 03-03 判定产物(worker 核心 14 模块普审 + 深挖):共 4 条发现——F-CODE-01/02(深挖 4 模块,poller 主证)……DNF-01 对照命中(transcriber.py whisper 桩)按负面清单排除不立发现;……判定过程未撞见安全类顺带发现。
```

**九字段条目模式**(code.md:25-35,完整照抄字段顺序与格式;schema 权威定义在 CHARTER.md:139-163):

```markdown
### F-CODE-01: `process_plan` 声明 `fragments_root` 形参但函数体未使用,遗留 API 面误导调用方

- **维度:** 组件代码 (CODE)
- **严重度:** LOW — 影响:误导性 API 面——……;可能性:仅在新增调用点或重构时触发误用,……
- **证据:** `apps/worker/src/soniscope_worker/poller.py:248-250 @ 5927f36`
  > `def process_plan(plan: PollPlan, source: OssSource, *, inbox_root: Path, fragments_root: Path) -> ObjectOutcome:` — 函数体(:257-292)无任何 `fragments_root` 引用;……
- **修复建议:** 移除 `fragments_root` 形参并同步两个调用点……
- **工作量:** S(poller.py 单文件 + 两调用点同步 + 既有测试)
- **关联发现:** 无;关联线索: scans/ruff-extended.md #55(ARG001 确认项反填)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft
```

**维度行取值:** `- **维度:** 文档配置一致性 (DOC)` / `- **维度:** 测试质量与覆盖 (TEST)`(骨架示例已写死)。

**严重度锚点(CHARTER.md:110-116,DOC/TEST 相关行):**
- MEDIUM —「可诱发高危误操作的误导性文档(如 runbook 步骤与实态不符)」
- LOW —「文档死链/路径失效;lint/typecheck 覆盖缺口」(D-09 一般测试缺口锚点即此)
- INFO —「存在级观察(vendored 仓库膨胀、四套 AI 工具目录漂移)」(HYP-05/06 预期落点)
- 评级理由固定格式(CHARTER.md:118):`严重度 — 影响:…;可能性:…`,禁数值评分。

**缺口按面聚合模式(D-12)**——关联字段承载脆弱区映射,写法参照 code.md:47 / :113:`- **关联发现:** F-CON-04;关联线索: HYP-16`。F-TEST 条目的关联字段链到反向映射命中的 F-*,证据字段内列模块/行号清单(一面一条,不逐模块立条)。

---

### `.planning/audit/HYPOTHESES.md`(11 条回填 + 尾部总对账,in-place)

**Analog:** 同文件已回填的 14 条(HYP-01/03/04/07/08/09/10/12/15/16/17/18/19/20)

**回填操作模式:** 把该条 `- **状态:** 未验证` 行替换为结论行,并在其后插入 `- **证据:**` 行、改写/追加 `- **备注:**` 行(含去向闭环 + 回填计划号落款)。三种状态各有实例:

证实(HYPOTHESES.md:25-27,HYP-01):

```markdown
- **状态:** 证实 — 基线 apps/fc 仅两函数目录,transcribe_audio 零代码,现役转写路径完全在 Worker 侧(nls filetrans)。
- **证据:** `git ls-tree 5927f36 apps/fc` → 仅 issue_credential/、verify_upload/……`apps/worker/src/soniscope_worker/transcriber.py:168-183 @ 5927f36`(工厂仅 cloud-speech/whisper-local 两分支……)
- **备注:** ……按 D-12 存在级处理不占发现 ID,供 RPT 汇总呈现……。03-04 回填。
```

细化(半句证实/半句证伪的拆分写法,HYPOTHESES.md:153,HYP-15):

```markdown
- **状态:** 细化 — "只捕获被教会的规则"半句证实:……;"静默通过即有漏报实害"半句在基线上证伪:ESLint 量化底数为 0 error / 29 warning 且逐条核实全为仓库惯例误报(无一真实缺陷)。
```

引用回填(D-14,HYP-13/HYP-11 专用;先例是 HYP-03 引 scans/microbench-sha256.md 的写法,HYPOTHESES.md:43):证据行明引既有产物章节/行号而不重复采证——HYP-13 引 `CONTRACT-MATRIX.md ## 往返校验结论`(:276 起,总结论 :307-309「FC↔Worker 主链在样本域内无漂移……分叉全部位于小程序声部」+ 组① 行 2/4/5 判定行);HYP-11 引 CHARTER.md:43(排除项表首行「FC 直转目标态对照……不引入目标态设计」),状态写「细化 — 章程范围外」。

**备注行的去向闭环词汇**(D-13 机械对账的三类合法去向,均有先例):`→ F-XXX-NN`(HYP-07:84)/ `不占发现 ID(D-12),记 RPT-06/DNF 候选`(HYP-09:102)/ `移交销号引用 HANDOFF-PHASE4.md`(HYP-16:164)。HANDOFF 6 条移交(DOC 3 + TEST 3,HANDOFF-PHASE4.md:12-20)的销号 = 在对应 HYP 回填/发现证据中显式引用该条。

**尾注总对账模式(D-15):** 现有尾注(HYPOTHESES.md:248)是斜体单段落 + 回填进度对账:

```markdown
*未验证假设清单: 2026-07-04(25 条 HYP + 1 条 Known Bugs 显式无线索记录;对账 25 + 4 DNF = 29,Phase 4 AUDIT-05 逐条回填)。回填进度:已回填 14 条(03-03:HYP-10 证实、……)——Phase 3 回填集 14 条……累计 14/14 全部闭环 ✓;余 11 条未验证(均属 Phase 4 维度:DOC 6 + TEST 4 + CON 1)。*
```

D-15 要求的总对账为**新增章节**(非仅改尾注):25/25 状态分布表(证实/证伪/细化计数)+ 机械验证命令 + 29 条溯源闭环声明。机械验证命令直接用 04-RESEARCH 已实测格式(状态行 grep 模式必须与现有行首格式 `- **状态:** ` 严格一致):

```bash
grep -c '^### HYP-' .planning/audit/HYPOTHESES.md          # 期望 25
grep -c '^- \*\*状态:\*\*' .planning/audit/HYPOTHESES.md    # 期望 25
grep -c '^- \*\*状态:\*\* 未验证' .planning/audit/HYPOTHESES.md  # 期望 0(收尾后)
grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md           # 期望 4;25+4=29 对账
```

对账头部先例(HYPOTHESES.md:8-12「转换对账」节)可作分布表 + 机械计数命令的排版参照。注意 :12 有勘误行先例——若对账中发现历史计数出入,同样以勘误行处理而非改史。

## Shared Patterns

### 证据格式与取证纪律(全部产物)
**Source:** `CHARTER.md:14-15,56-64`
**Apply to:** 所有 7 个文件的每一条证据

```markdown
- **证据格式(per D-02):** 单行证据 `path:line @ 5927f36`;多行证据 `path:10-25 @ 5927f36`。
- **证据提取方法:** 证据一律提取自 `git show 5927f36:<path>`,禁止以工作树文件充当行号证据。
```

worktree 副本仅供"执行",行号证据落账口径仍写 `@ 5927f36`(04-RESEARCH Anti-Patterns)。路径含空格须引号:`git show '5927f36:docs/v1.0.0 prd/PRD_v1.md'`(Pitfall 6)。

### 秘密类证据红线
**Source:** `CHARTER.md:104`;实战示范 `HYPOTHESES.md:82-84`(HYP-07,"值本体略,per CHARTER 秘密红线")与 `HANDOFF-PHASE4.md:20`(test_asr.py 签名 URL 只引位置)
**Apply to:** TEST-AUDIT.md 与 findings/test.md 引用 `scripts/test_asr.py:80` 时;DOC-CLAIMS.md 引用任何含凭证模式的文档段落时

> 引用秘密类证据只写 `path:line @ 5927f36` + 模式名(如 `OSSAccessKeyId=` 签名 URL 模式),绝不复制值本体——哪怕已过期。

### DNF 负面清单闭环
**Source:** `DO-NOT-FIX.md:20-25`(DNF-02 即 `issue-cedential` 条目)+ COVERAGE.md config.js 行(:77)的对照写法
**Apply to:** DOC-CLAIMS.md 的 config.js 节(核实结论引 DNF-02 闭环,不占 F-ID);HYP-23 处理引 DNF-03(`DO-NOT-FIX.md:28-35`,含"仅验证行为测试补偿充分,不质疑豁免本身"的两侧交叉引用条款)

```markdown
| `apps/miniprogram/config.js` | 41 | CODE | 普审 | 9/9 | 无发现 | DNF-02 对照:`issue-cedential` 拼写域名(`config.js:10 @ 5927f36`)系 Aliyun 真实分配值(`:8` 注释明示勿"修正"),负面清单排除不立发现。 |
```

### "只存档不判断 / 证据与判断分离"分层
**Source:** `scans/gates-baseline.md:31,39`(注记只存档)、`COVERAGE.md:6`(台账不承载发现正文)
**Apply to:** scans/coverage-*.md(纯输入证据,禁评分)、DOC-CLAIMS.md 与 TEST-AUDIT.md(底稿=证据层)vs findings/*.md(判断层)——判断只在 findings 立条,底稿行以 `→ F-DOC-NN` / `→ HYP-NN` 指针链接。

### 尾注封版落款
**Source:** `HANDOFF-PHASE4.md:23`、`DO-NOT-FIX.md:47`、`CONTRACT-MATRIX.md` 各节完成判定
**Apply to:** 新建 4 文件收尾

```markdown
---
*Phase 4 移交清单: 2026-07-05(6 条移交:DOC 3(……)+ TEST 3(……);每条含去向 + 一句观察 + `@ 5927f36` 行号证据……)*
```

格式:`*<文档角色>: <日期>(<机械对账摘要,含计数等式>)*`。

### 语言与术语
**Source:** 全部 Phase 1–3 产物一致风格
**Apply to:** 全部产物——中文正文;ID(F-DOC-NN/HYP-NN/DNF-NN)、严重度(CRITICAL/HIGH/MEDIUM/LOW/INFO)、状态词(agree/drift/dead-ref、draft/calibrated)、工作量(S/M/L/XL)用英文。

### 阶段收尾验证
**Source:** `CHARTER.md:16-22`(零 diff 命令写定)+ `gates-baseline.md:10-15`(记录格式)
**Apply to:** 阶段最后一个计划

```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/   # 期望空输出;结果记录入阶段产物
git worktree list                                  # 确认专区已清理(remove 须 --force,Pitfall 1)
```

## No Analog Found

无——本阶段全部产物在 Phase 1–3 产物中均有 exact 类比。仅两处是"组合类比"而非单一先例,已在上文标注:

| 产物内部构件 | 组合来源 | 说明 |
|--------------|----------|------|
| TEST-AUDIT.md 门禁三方对照节 | CONTRACT-MATRIX 对照表结构 + scans/ 实跑计数归档 | 三方(声称×静态×实跑)对照本身是 D-11 新形态,但两种构件均有先例 |
| DOC-CLAIMS.md 分层覆盖标注(深核/普审/只审引用/只记存在) | COVERAGE.md「深度」列(普审/深挖) | 二值深度扩为四层,列式沿用 |

## Metadata

**Analog search scope:** `.planning/audit/`(全部 9 个 md + findings/ 5 + scans/ 6)、`.planning/phases/04-docs-config-test-audit/`(CONTEXT/RESEARCH)
**Files scanned:** 11 个类比产物读取(CHARTER、CONTRACT-MATRIX、COVERAGE、DO-NOT-FIX、HANDOFF-PHASE4、HYPOTHESES、findings/code+docs-config+test、scans/gates-baseline+vulture)
**Pattern extraction date:** 2026-07-05
