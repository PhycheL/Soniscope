# Phase 4: 文档配置与测试审计 - Research

**Researched:** 2026-07-05
**Domain:** 纯审计取证方法论(DOC 一致性核对 + TEST 质量/覆盖盘点 + HYP 总对账)——零新代码、零 diff、只产 `.planning/` 产物
**Confidence:** HIGH(全部关键机制在本会话本机实测或按基线 `5927f36` 取证核实)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 测试执行与覆盖率口径
- **D-01(分级执行口径):** 离线门禁 `make test`(pytest + node:test,设计上零云 IO)可作为审计仪器执行,运行结果作证据;真云目标 `test-*`/`verify-*` 继承 Phase 3 D-08 绝不执行,只静读。审"门禁完整性"以实跑观测为证据来源之一。
- **D-02(worktree 基线专区执行):** 全部执行在 `git worktree add <scratchpad> 5927f36` 检出的仓库外基线专区进行(专区内 `make install` + `make test`),结构性保证跑的是基线代码且主工作区零触碰,延续 Phase 2/3 "基线导出 scratchpad" 先例精神。用完 `git worktree remove`,阶段收尾照常跑零 diff 验证。
- **D-03(Python 覆盖率 = 临时注入 pytest-cov):** worktree 专区内命令行临时注入(如 `uv run --with pytest-cov pytest --cov=soniscope_worker --cov=fc_shared ...`),不向仓库写入任何配置;数字与命令、工具版本一起存 `.planning/audit/scans/` 归档,与 Phase 3 D-05 临时分析器同构。
- **D-04(JS 覆盖率也实测):** worktree 专区内 `node --test --experimental-test-coverage` 直跑 `apps/miniprogram/test/*.test.js`(绕过 pytest 桥,不改桥代码),数字标注 experimental 来源,与 Python 侧同格式归档,双语言证据对称。

#### DOC 审计范围与核对方式
- **D-05(全量分层范围):** 权威链深核 = PRD(`docs/v1.0.0 prd/PRD_v1.md`)、tech-spec(`docs/v1.0.0 prd/tech-spec.md`)、runbook 4 份(cloud-setup/deployment-guide/fc-deploy/mvp-acceptance)、AGENTS.md、根 README.md、apps/fc/README.md、apps/miniprogram/README.md、config.js;其余(架构评审、transcribe-approach-comparison、docs/agents/ 3 份)普审级只抓死链/过期声明;原型截图与 drawio 不审内容只记存在。每份文档入覆盖台账,"已审无发现"落到文档粒度可机械验收。
- **D-06(目标态文档只审引用与自洽):** `docs/fc-transcribe-design.md`、`docs/multi-user-design.md` 不做"设计 vs 代码实态"对照(尊重章程 CHARTER-04 排除项),只审引用有效性(死链、旧路径,HYP-02 相关)与明显自相矛盾;HYP-11 以"细化:章程范围外"关闭;覆盖台账显式标注"目标态对照未审(章程排除)"。
- **D-07(可核声明清单式深核):** 每份深核文档先抽取"可与代码/配置对照的声明"成清单(命令、路径、常量、流程步骤、边界声明),逐条标 **agree / drift / dead-ref / 无法静态核实** 四态销号,每条附文档侧与代码侧双行号证据(`@ 5927f36`)。纯云端事实(控制台配置等)标"无法静态核实"不猜测。延续 CONTRACT-MATRIX 范式,直接喂 RPT-07/08。
- **D-08(配置边界 = 小程序三份全入):** config.js 深核(ENV 常量/HYP-14 发布翻转口径、FC 域名、OSS 域名、阈值逐一对照文档声明);`project.config.json` 与 `app.json` 普审(libVersion、appid、页面注册与文档/代码一致性)。Python 侧配置(pyproject.toml/Makefile)Phase 3 已覆盖不重审,仅作声明清单对照的靠山。

#### 测试缺口定级与脆弱区映射
- **D-09(反向映射法定级):** 规划时把 Phase 2/3 全部 22 条发现(F-CON-01~06 / F-CODE-01~08 / F-TOOL-01~08)+ 契约矩阵关键行编成"应重点覆盖面"清单,逐条查现有测试是否兜底;脆弱区无测试 → 缺口定级参照原发现严重度;无关联脆弱区的一般缺口按 CHARTER LOW 锚点("lint/typecheck/测试覆盖缺口"类)。清单逐条销号,可机械验收。
- **D-10(质量普审面清单化):** 仿 Phase 3 D-04,规划时定稿固定质量检查面清单(断言强度、fake 与真实实现漂移风险、隔离惯例、契约常量锁定、泄漏断言覆盖、静默 skip 路径等),每个测试模块(pytest 24+ 文件与 node:test 全部文件)逐面过并入覆盖台账。
- **D-11(门禁完整性三方对照):** 声称(Makefile/README/文档说门禁跑什么)× 静态配置(testpaths、桥接代码、skip 条件)× worktree 实跑观测(collected/passed/skipped 计数)三方逐项对照,任一不一致即缺口候选——静默 skip 使"全绿"≠"全跑"(已知线索:node 缺失时 JS 测试静默跳过 exit 0)。
- **D-12(缺口按面聚合立条):** 一个缺口面一条发现(如"活体路径零自动化覆盖"一条、"页面胶水层无测试"一条),证据字段内列具体模块/行号清单,关联字段链到对应 F-* 脆弱区发现;信噪比与 Phase 3 风格一致,根因聚类留 Phase 5。

#### HYP 关闭与总对账形态
- **D-13(已回填 14 条只机械对账):** Phase 3 已回填的 14 条不复判内容,只验形式合规(每条有状态、有 `@ 5927f36` 证据、去向闭环到发现 ID 或 RPT 候选标注)。
- **D-14(证据已在别处的条目引用回填):** HYP-13 直接引 CONTRACT-MATRIX.md 结论与矩阵行号证据回填(同一基线 SHA,证据仍新鲜);HYP-11 以"细化:章程范围外"关闭并引章程排除项条款。不重复采证,但回填文本明引具体行号/章节。
- **D-15(总对账落 HYPOTHESES.md 尾部):** 新增总对账章节:25/25 状态分布表(证实/证伪/细化计数)+ 机械验证命令(grep 统计状态行)+ 29 条溯源闭环声明(25 HYP + 4 DNF)。延续现有尾注风格,直接喂 RPT-08。
- **D-16(独立新文件,封版产物不动):** 本阶段结构化底稿新建独立文件(如 `.planning/audit/DOC-CLAIMS.md` 与 `.planning/audit/TEST-AUDIT.md`,含反向映射清单),覆盖率等实测输出存 `.planning/audit/scans/`;COVERAGE.md、CONTRACT-MATRIX.md、HANDOFF-PHASE4.md 等已封版产物只读引用不续写(HYPOTHESES.md 例外——它本就是跨阶段回填的活文档)。

### Claude's Discretion
- 质量检查面清单的具体条目与分面粒度(D-10 给方向,定稿留规划)。
- DOC 声明清单的抽取粒度细节(命令类逐条、叙事类可按声明句,满足四态销号即可)。
- 底稿文件的具体命名与内部排版——硬约束只有:逐项可销号、封版产物不动、喂 RPT-07/08。
- 覆盖率数字的呈现粒度(按模块/按包),但禁止阈值判断与质量评分(成功判据 3 + REQUIREMENTS Out of Scope)。
- worktree 专区的具体位置与清理时机;`make test` 若在基线上非绿,结果按 CHARTER 正常定级入台账(无例外协议既定,无需再议)。

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUDIT-03 | docs/、`apps/miniprogram/config.js`、AGENTS.md 等文档配置与代码实态一致性审计 | §审计对象实测清单(深核 10 文档 + 3 配置的基线行数)、§Code Examples 的 `git show`/`git grep` 取证命令、HYP-02 线索已预核实为真(AGENTS.md 旧路径引用 17 处)、DNF-02 闭环锚点 |
| AUDIT-04 | 测试质量与覆盖缺口盘点(pytest 与 node:test 双侧,含 `make test` 门禁完整性) | §测试套件实测清单(pytest 31 文件 / node:test 10 文件)、§Standard Stack 的 worktree + pytest-cov + node coverage 三件套实测验证、§Common Pitfalls 的门禁三方对照已知线索、TESTING.md 勘察底稿要点 |
| AUDIT-05 | CONCERNS.md 每条已知线索被证实/证伪/细化,并附新鲜 file:line 证据 | §HYP 收尾清单(余 11 条逐条列出 + 已回填 14 条机械对账口径)、D-14 引用回填的证据锚点已定位(CONTRACT-MATRIX.md §往返校验结论,行 276 起)、D-15 机械验证 grep 命令已实测格式 |
</phase_requirements>

## Summary

本阶段是纯审计阶段:不装新依赖入仓、不改任何被审文件,产物全部落 `.planning/`。研究回答三个问题:①审计仪器(worktree 基线专区、pytest-cov 临时注入、node 实验性覆盖率)在本机是否真实可用——**全部实测可用**(node v22.18.0 含 `--experimental-test-coverage` 与 `--test-coverage-include/exclude` 旗标、uv 0.8.14 含 `--with`/`--frozen`、git 2.23.0 支持 worktree add/remove);②审计对象的实测底数——深核文档 10 份共约 4,000 行(注意根 README.md 仅 2 行,工作量远小于预期)、pytest 31 个测试文件(worker 24 + fc 7)、node:test 10 个文件;③既有产物中的复用锚点——HYP-13 回填证据在 CONTRACT-MATRIX.md `## 往返校验结论`(行 276 起),HYP-02 线索已预核实为真(基线 AGENTS.md 引用旧路径 `docs/PRD_v1.md`/`docs/tech-spec.md` 共 17 处,实际文件在 `docs/v1.0.0 prd/`),DNF-02 即 `issue-cedential` 闭环条目(`config.js:8-10 @ 5927f36` 行内注释自证)。

主要风险点在执行细节而非方法:worktree 用完后含 `.venv`/缓存等未跟踪文件,`git worktree remove` 会拒绝,须 `--force`;`uv sync`/`uv run` 不加 `--frozen` 可能改写 worktree 内 uv.lock(虽不污染主仓,但破坏"跑的是基线"语义);pytest-cov 测不到子进程里的 node(JS 桥),这正是 D-04 双侧分测的原因;覆盖率数字仅作输入证据,任何"覆盖率低于 X%"式判断都违反成功判据 3。

**Primary recommendation:** 按"worktree 实跑取证 → DOC 四态销号(DOC-CLAIMS.md)→ TEST 检查面台账 + 反向映射(TEST-AUDIT.md)→ 发现入两本台账 → HYP 11 条回填 + 25/25 总对账 → 零 diff 收尾"组织计划;全部执行命令用本文档 §Code Examples 已实测的形式,不再发明。

## Architectural Responsibility Map

本阶段无运行时系统分层,按"审计产物职责"映射(planner 据此分配任务归属):

| Capability | Primary Owner | Secondary | Rationale |
|------------|--------------|-----------|-----------|
| 基线取证(行号证据) | `git show 5927f36:<path>` / `git grep -n <pat> 5927f36`(主仓内执行) | — | CHARTER 硬性规定:证据禁读工作树,worktree 副本仅供"执行",行号证据仍以 git show 提取口径落账 |
| 门禁/覆盖率实跑 | 仓库外 worktree 基线专区(D-02) | — | 结构性保证跑基线代码且主仓零触碰;实跑输出(计数、覆盖率)归 `scans/` |
| DOC 声明清单与四态销号 | 新文件 `.planning/audit/DOC-CLAIMS.md`(D-16,命名可裁量) | 发现正文入 `findings/docs-config.md` | 底稿(证据)与发现(判断)分离,延续 COVERAGE/CONTRACT-MATRIX 范式 |
| TEST 检查面台账 + 反向映射清单 | 新文件 `.planning/audit/TEST-AUDIT.md`(D-16,命名可裁量) | 发现正文入 `findings/test.md` | 同上 |
| 覆盖率实测归档 | `.planning/audit/scans/`(命令 + 工具版本 + 输出) | — | 与 Phase 3 scans/ 三态销号范式同构;仅输入证据,禁评分 |
| HYP 回填与总对账 | `.planning/audit/HYPOTHESES.md`(唯一可续写的既有产物) | 引用 CONTRACT-MATRIX.md / CHARTER.md(只读) | D-15/D-16 明定 |
| 阶段收尾验证 | 主仓执行零 diff 命令 + worktree 清理 | — | CHARTER 零 diff 验证 + D-02 |

## Standard Stack

本阶段的"栈"是审计仪器,不是运行时依赖。全部在本机实测:

### Core
| 工具 | 版本(实测) | 用途 | 验证方式 |
|------|------------|------|----------|
| git worktree | git 2.23.0 | 基线专区检出/清理(D-02) | `git --version` [VERIFIED: 本机];worktree add(≥2.5)/remove(≥2.17)均支持 |
| uv | 0.8.14 | worktree 内 `make install`(= `uv sync`)与 `uv run --with` 临时注入 | `uv --version`;`uv run --help` 确认 `--with`/`--frozen`/`--no-sync` 旗标存在 [VERIFIED: 本机] |
| node | v22.18.0 | `node --test` + `--experimental-test-coverage` 直跑 JS 测试(D-04) | `node --help` 确认 `--experimental-test-coverage`、`--test-coverage-include`、`--test-coverage-exclude`、`--test-coverage-lines` 等旗标全部存在 [VERIFIED: 本机] |
| pytest-cov | 7.1.0(PyPI 最新) | Python 覆盖率临时注入(D-03),**不写入仓库** | `pip index versions pytest-cov` 确认版本链自 0.6 起 15+ 年历史 [VERIFIED: PyPI registry];seam 判定见下方 Package Legitimacy Audit |
| git show / git grep | git 2.23.0 | 全部行号证据的唯一提取来源 | CHARTER 已实测钉定的三条标准命令 [CITED: .planning/audit/CHARTER.md §证据提取命令] |

### Supporting
| 工具 | 用途 | When to Use |
|------|------|-------------|
| `grep -c` 机械计数 | D-15 总对账验证、HYP 状态行统计 | 总对账章节的机械验证命令(格式已实测:HYPOTHESES.md 状态行为 `- **状态:** <状态>`) |
| ffmpeg/ffprobe(本机已装) | 无直接用途——单测全程 fake,不触 ffprobe | 仅作环境记录;`make test` 离线设计不依赖 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| worktree(D-02 锁定) | Phase 3 的 `git archive` 导出 | archive 导出无 .git,无法在专区内跑依赖安装所需的 workspace 语义?实际 uv 不需要 .git;但 worktree 是用户锁定决策,不再议 |
| pytest-cov(D-03 锁定) | `coverage run -m pytest` | coverage.py 直用也可行,但 D-03 明示 pytest-cov;若 `uv run --with pytest-cov` 在 workspace 下有意外,`--with coverage` + `coverage run` 是现成回退 |
| `node --test --experimental-test-coverage` | nyc/c8(npm 包) | 引入 npm 依赖违反"小程序零依赖"实态且需装包;node 内置覆盖率零安装,D-04 已锁定 |

**Installation:** 无任何入仓安装。pytest-cov 仅经 `uv run --with pytest-cov`(ephemeral overlay,不改 `.venv` 声明、不改 pyproject/uv.lock)。

## Package Legitimacy Audit

本阶段唯一涉及的外部包是 pytest-cov(临时注入,不落仓库配置):

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pytest-cov | PyPI | 版本链自 0.6 起(15+ 年),最新 7.1.0 | seam 未取到(pypi 下载数据缺口) | github.com/pytest-dev/pytest-cov(pytest 官方组织)[ASSUMED — seam 未返回 repo 字段] | [SUS](seam 判定,理由:unknown-downloads / no-repository) | Flagged — planner 须在覆盖率任务前加 `checkpoint:human-verify`,或以 D-03 用户点名 + PyPI 版本链核实作为已获确认的依据在计划中显式记录 |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `pytest-cov` [WARNING: seam 判 SUS 系数据缺口(PyPI 生态下载数与 repo 字段未取到),非包本身可疑信号;缓解证据:`pip index versions` 实测确认 54 个历史版本、最新 7.1.0,与 pytest-dev 官方维护的知名插件一致。且 D-03 为用户锁定决策点名该包。planner 应按协议在安装(首次 `uv run --with pytest-cov`)前放一个 human-verify 检查点,或在计划正文注明"D-03 用户点名 = 已确认"并直接执行。]

**跨生态确认:** 用途为 Python/pytest,查证于 PyPI(正确生态)✓。无 postinstall 概念(PyPI wheel)。

## Architecture Patterns

### 阶段工作流(数据流图)

```
主仓(只读取证区)                          仓库外 scratchpad(执行区)
┌─────────────────────────┐               ┌──────────────────────────────┐
│ git show/grep 5927f36    │               │ git worktree add WT 5927f36  │
│  ├→ DOC 声明清单取证      │               │  ├→ make install (uv sync)    │
│  ├→ TEST 静态配置取证     │               │  ├→ make test  → 计数观测      │
│  └→ HYP 回填证据          │               │  ├→ uv run --with pytest-cov… │
└──────────┬──────────────┘               │  └→ node --test --exp-cov …   │
           │                              └──────────┬───────────────────┘
           ▼                                         │ 输出(tee 到 scratchpad)
┌──────────────────────────────────────────────────┐ │
│ .planning/audit/ 写入区                            │◄┘
│  ├ DOC-CLAIMS.md(四态销号底稿)                     │
│  ├ TEST-AUDIT.md(检查面台账 + D-09 反向映射清单)    │
│  ├ scans/coverage-*.md(命令+版本+输出归档)          │
│  ├ findings/docs-config.md(F-DOC-NN)              │
│  ├ findings/test.md(F-TEST-NN)                    │
│  └ HYPOTHESES.md(11 条回填 + 尾部总对账)            │
└──────────┬───────────────────────────────────────┘
           ▼
收尾:git diff --stat 5927f36 -- apps/ scripts/ docs/ (must be empty)
     git worktree remove --force WT
```

### 推荐任务切分模式(供 planner 参考)

三条工作线依赖关系松散,可部分并行:

1. **实跑取证线**(worktree):建区 → install → `make test` 观测 → pytest-cov → node coverage → 归档 scans/ → 拆区。产出喂 D-11 三方对照与覆盖缺口证据。**注意:worktree 实跑必须先于/独立于 DOC/TEST 静态审计,其输出是 AUDIT-04 的输入证据。**
2. **DOC 线**:声明清单抽取(逐文档)→ 四态销号 → F-DOC 发现 + 覆盖台账。与实跑线无依赖。
3. **TEST 线**:反向映射清单编制(22 条 F-* + 矩阵关键行)→ 质量普审面逐模块过 → 门禁三方对照(依赖实跑线输出)→ F-TEST 发现。
4. **HYP 收尾线**:11 条回填(DOC 6 条依赖 DOC 线结论;TEST 4 条依赖 TEST 线结论;HYP-13 纯引用回填可先行)→ 25/25 总对账 → HANDOFF 6 条销号声明 → 零 diff 收尾。**必须最后。**

### Pattern 1: 四态销号声明清单(D-07,延续 CONTRACT-MATRIX 范式)

**What:** 每份深核文档先抽"可对照声明"成表,逐条判 agree / drift / dead-ref / 无法静态核实,双侧行号证据。
**When to use:** 深核 10 文档 + config.js。
**Example(表结构,直接可用):**

```markdown
| # | 文档侧声明 | 文档证据 | 代码/配置侧实态 | 代码证据 | 判定 |
|---|-----------|----------|----------------|----------|------|
| C-01 | "issue-cedential 子域名少一个 r,是阿里云分配的真实 URL" | `apps/miniprogram/config.js:8 @ 5927f36` | 常量值确为该拼写 | `apps/miniprogram/config.js:10 @ 5927f36` | agree(闭环 DNF-02) |
| C-02 | AGENTS.md:"产品范围与验收:docs/PRD_v1.md" | `AGENTS.md:5 @ 5927f36` | 基线该路径无文件,实存 `docs/v1.0.0 prd/PRD_v1.md` | `git ls-tree 5927f36 docs`(无 docs/PRD_v1.md) | dead-ref → HYP-02 |
```

### Pattern 2: 反向映射清单(D-09)

**What:** 行 = 22 条 F-* 发现 + 契约矩阵关键行;列 = 应覆盖行为、现有测试兜底情况(测试文件:行号 或 "无")、缺口定级(参照原发现严重度)。
**22 条 F-* 全集(已从台账实测枚举,planner 直接用):**
F-CON-01~06(contract.md)、F-CODE-01~08(code.md)、F-TOOL-01~08(toolchain.md)。

### Pattern 3: 覆盖率归档格式(scans/ 先例同构)

**What:** 仿 `scans/gates-baseline.md`:头部记基线/依据决策/工具版本,正文记命令原文 + 输出摘要 + 与判断分离的备注;新文件建议 `scans/coverage-pytest.md` 与 `scans/coverage-node.md`(命名可裁量)。JS 侧数字必须标注 "experimental 来源"(D-04)。

### Anti-Patterns to Avoid
- **把覆盖率当评分:** 任何"覆盖率仅 X%,质量差"式表述违反成功判据 3 与 REQUIREMENTS Out of Scope(数值化评分禁令)。正确用法:"模块 M 行覆盖 0%(scans/coverage-pytest.md),该模块承载 F-CODE-02 脆弱区 → 缺口发现 F-TEST-NN,定级参照 F-CODE-02 严重度"。
- **把 DNF 条目立为发现:** `issue-cedential` 拼写(DNF-02)、`whisper-local` 桩(DNF-01)、handler mypy 豁免(DNF-03)在 DOC 核对/HYP-23 处理中只做"核实结论 + 引 DNF 条目闭环",不占 F-* ID。
- **读工作树取证:** 行号证据一律 `git show 5927f36:<path>`;worktree 副本内容虽等价,落账口径仍写 `@ 5927f36`,且 CHARTER 明文"禁止以工作树文件充当行号证据"。
- **续写封版产物:** COVERAGE.md、CONTRACT-MATRIX.md、HANDOFF-PHASE4.md 只读引用;唯一例外 HYPOTHESES.md(活文档)。
- **外推执行放宽:** D-01 只放宽了离线 `make test`;任何 `make test-*`/`verify-*` 真云目标、`scripts/test_asr.py` 等被审脚本绝不执行。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 发现记录格式 | 新 schema | CHARTER 九字段 schema(findings/*.md 已含 F-DOC-00/F-TEST-00 示例条目) | Phase 5 汇总依赖统一 schema;骨架已建好 |
| 覆盖台账结构 | 新表结构 | COVERAGE.md 的"对象/深度/已过面/产出/备注"列式(只读仿写到新文件) | RPT-07/08 直接消费该结构 |
| Python 覆盖率工具 | 自写 trace/统计 | pytest-cov 临时注入(D-03 锁定) | 行覆盖统计的边界情况(分支、动态导入)不值得自研 |
| JS 覆盖率工具 | npm 装 c8/nyc | node 内置 `--experimental-test-coverage`(D-04 锁定) | 小程序侧零 npm 依赖是仓库实态,不引入 |
| 对账验证 | 人工数数 | `grep -c` 机械计数命令(HYPOTHESES.md 头部已有先例等式) | 用户明确要求可机械验收 |
| 基线隔离 | 手工 checkout/复制 | `git worktree add <path> 5927f36`(D-02 锁定) | 结构性保证 + 一条命令清理 |

**Key insight:** 本阶段全部"基建"在 Phase 1-3 已建好(schema、台账骨架、销号范式、scans 归档格式);计划的价值在编清单与逐条销号,任何新格式发明都是浪费且破坏 Phase 5 汇总一致性。

## 审计对象实测底数(基线 5927f36)

规划工作量分配的实测输入(行数 = `git show 5927f36:<path> | wc -l`):

### DOC 深核对象(10 文档 + 1 配置)
| 对象 | 行数 | 备注 |
|------|------|------|
| `docs/v1.0.0 prd/PRD_v1.md` | 869 | 注意路径含空格,命令中须引号 |
| `docs/v1.0.0 prd/tech-spec.md` | 782 | AGENTS.md 17 处旧路径引用的目标实体 |
| `docs/runbook/fc-deploy.md` | 670 | |
| `docs/runbook/deployment-guide.md` | 487 | |
| `docs/runbook/cloud-setup.md` | 461 | config.js 头注声称与其 §3-4 一致(现成声明清单种子) |
| `docs/runbook/mvp-acceptance.md` | 217 | |
| `AGENTS.md` | 452 | HYP-02 主战场:`docs/PRD_v1.md`/`docs/tech-spec.md` 旧路径引用实测 17 处(行 5,6,69,157,337,375,405-424)[VERIFIED: git grep @ 5927f36] |
| `README.md`(根) | 2 | 深核工作量趋近于零 |
| `apps/fc/README.md` | 34 | |
| `apps/miniprogram/README.md` | 35 | |
| `apps/miniprogram/config.js` | 41 | ENV='development' 在行 29;DNF-02 注释在行 8;头注自证与 cloud-setup.md §3-4、tech-spec §3.1 的一致性声明——声明清单直接从注释抽 |

### DOC 普审/引用级对象
- 普审:`docs/architecture/architecture-review-2026-07-02.md`、`docs/transcribe-approach-comparison.md`、`docs/agents/`(domain.md / issue-tracker.md / triage-labels.md);
- 只审引用与自洽(D-06):`docs/fc-transcribe-design.md`(行 5 引旧路径 tech-spec,已预核中一处 dead-ref 候选)、`docs/multi-user-design.md`(行 5、599 引旧路径,同上)[VERIFIED: git grep @ 5927f36];
- 只记存在:`docs/小程序原型/`(4 PNG)、`docs/architecture/soniscope-mvp-architecture.drawio`、`docs/runbook/us-001-manual.html`;
- 普审配置:`apps/miniprogram/project.config.json`、`app.json`。

### TEST 对象
- pytest:`apps/worker/tests/` 24 文件、`apps/fc/tests/` 7 文件(共 31);
- node:test:`apps/miniprogram/test/` 10 文件(chunking/draft_confirm/fault_injection/ids/interruption/oss_sign/redesign_view/uploader/uploads_view/verify);
- 门禁定义:`Makefile:170-171`(test 目标 = 仅 `uv run pytest`)、根 `pyproject.toml`(testpaths = worker/tests + fc/tests;pythonpath = apps/fc/shared)、`apps/worker/tests/test_miniprogram_js.py`(JS 桥,`@pytest.mark.skipif(shutil.which("node") is None)` 即静默 skip 线索,行 24)[VERIFIED: git show @ 5927f36];
- 勘察底稿:`.planning/codebase/TESTING.md`(178 行)——已确认:无 conftest.py、无 unittest.mock(全手写 fake + DI)、无覆盖率配置("None enforced"明文)、JS 测试有"node Page harness + mock wx"模式(uploader.test.js 加载真实 pages 文件——JS 覆盖率会自然含 pages/,对 HYP-24 判断有用)。

### HYP 收尾清单(余 11 条,ID 已核对)
- DOC 6:HYP-02(引用失效——已预核为真,AGENTS.md 17 处 + 设计文档 3 处)、HYP-05(vendored 仓,存在级 LOW/INFO 预期)、HYP-06(四套 AI 工具目录,存在级)、HYP-11(FC 直转轮询计费——D-14 定"细化:章程范围外"关闭)、HYP-14(ENV 翻转口径——HANDOFF 有 2 条移交证据)、HYP-21(转写消费 UI 缺失与 PRD 范围声明一致性);
- TEST 4:HYP-22(活体路径零 CI——HANDOFF 有 1 条移交证据)、HYP-23(handler 行为测试补偿是否充分——只验补偿,不质疑豁免,DNF-03 交叉引用)、HYP-24(pages 胶水层无测试)、HYP-25(scripts/ 门禁外——HANDOFF 有 2 条移交证据含实害样本);
- CON 1:HYP-13(三处契约一致性——D-14 引用回填,证据锚点:CONTRACT-MATRIX.md `## 往返校验结论` 行 276 起 + 组① 行 2/4/5 判定行 [VERIFIED: 本会话 grep])。
- 已回填 14 条(机械对账对象):HYP-01/03/04/07/08/09/10/12/15/16/17/18/19/20。
- HANDOFF-PHASE4.md 6 条移交:DOC 3(HYP-16 半句 / HYP-14 ×2)+ TEST 3(HYP-22 / HYP-25 ×2),每条已含 `@ 5927f36` 证据,销号 = 在对应回填/发现中显式引用。

## Common Pitfalls

### Pitfall 1: worktree 清理被未跟踪文件阻挡
**What goes wrong:** 专区内 `make install` 产生 `.venv/`、pytest 产生 `.pytest_cache/` 等未跟踪文件,`git worktree remove` 报 "contains modified or untracked files" 拒绝执行。
**How to avoid:** 收尾用 `git worktree remove --force <WT>`(或先 `rm -rf` 专区内容再 remove);计划里写死 `--force`。
**Warning signs:** 收尾任务失败、`git worktree list` 残留条目。

### Pitfall 2: uv 在专区内改写 uv.lock
**What goes wrong:** `uv sync`/`uv run` 在依赖解析漂移时可能更新专区内 uv.lock,虽不触主仓,但"实跑基线代码"的语义被破坏(跑的不再是 lock 钉定的依赖版本)。
**How to avoid:** 专区内统一 `uv sync --frozen` 与 `uv run --frozen ...`(Phase 3 gates-baseline.md 先例即用 `--frozen`)。`--with pytest-cov` 与 `--frozen` 可同用(overlay 不入 lock)。
**Warning signs:** 专区内 `git status` 显示 uv.lock modified。

### Pitfall 3: pytest-cov 测不到 JS 桥子进程
**What goes wrong:** `test_miniprogram_js.py` 以子进程跑 node,Python 覆盖率对 JS 完全盲;若只看 pytest-cov 数字会误判 JS 侧"零覆盖"。
**How to avoid:** 这正是 D-04 双侧分测的原因;归档时两份数字并列,注明口径互不重叠。
**Warning signs:** 无——结构性事实,写进 scans/ 备注即可。

### Pitfall 4: node 覆盖率把测试文件自身计入
**What goes wrong:** `--experimental-test-coverage` 默认统计所有已加载文件,`test/*.test.js` 自身与被测源混在报告里,拉高表观覆盖。
**How to avoid:** 加 `--test-coverage-exclude='apps/miniprogram/test/**'`(旗标本机实测存在);或归档时显式分行标注。同时注意 uploader.test.js 会加载 `pages/uploads/uploads.js`——pages/ 出现在覆盖报告中是正常且有价值的信号(HYP-24 证据)。
**Warning signs:** 覆盖报告中出现 `*.test.js` 行。

### Pitfall 5: `make test` 观测的三方对照要素漏采
**What goes wrong:** 只记录 "exit 0 全绿",没记 collected/passed/skipped 计数,D-11 的"全绿≠全跑"判断失去证据(node 在本机存在,skip 不会自然发生,需要静态+反事实观测补齐)。
**How to avoid:** 实跑用 `uv run --frozen pytest -v` 或 `-rs` 保留 skip 原因;另可做一次受控反事实观测:`PATH` 中剔除 node 后单跑 `pytest apps/worker/tests/test_miniprogram_js.py -rs`,实证"node 缺失 → SKIPPED → exit 0"(纯离线,不违反任何红线)。
**Warning signs:** scans/ 归档里只有 "passed" 一个数字。

### Pitfall 6: 路径含空格的取证命令
**What goes wrong:** `git show '5927f36:docs/v1.0.0 prd/PRD_v1.md'` 若不加引号,shell 切词报错。
**How to avoid:** PRD/tech-spec 路径统一引号包裹;写入计划的命令示例直接带引号。

### Pitfall 7: HYP-13 回填的维度归属
**What goes wrong:** HYP-13 是 CON 维度,本阶段无 CON 台账文件;若为它新开发现文件或写入 docs-config.md 会破坏台账布局。
**How to avoid:** HYP-13 只在 HYPOTHESES.md 回填状态(D-14 引 CONTRACT-MATRIX 结论:FC↔Worker 主链样本域内无漂移、小程序侧三条发现 F-CON-01/02/03 已立),不产生任何新 F-* 条目。
**Warning signs:** 计划中出现"为 HYP-13 立新发现"的任务。

### Pitfall 8: 把"文档滞后于目标态设计"当漂移
**What goes wrong:** fc-transcribe-design.md / multi-user-design.md 描述目标态,与代码实态必然不一致;若做实态对照会违反 CHARTER-04 排除项。
**How to avoid:** D-06 已锁定:两文档只审引用有效性与自相矛盾;覆盖台账标"目标态对照未审(章程排除)"。
**Warning signs:** DOC-CLAIMS 清单里出现这两份文档的实态对照行。

## Code Examples

全部命令已在本机或按 CHARTER 先例验证;`<SCRATCH>` 指会话 scratchpad(仓库外)。

### Worktree 基线专区(建/装/跑/拆)
```bash
# 建区(主仓内执行;WT 必须在仓库外)
WT=<SCRATCH>/wt-5927f36
git worktree add "$WT" 5927f36

# 装依赖 + 门禁实跑(专区内;--frozen 防 lock 漂移,Pitfall 2)
cd "$WT"
uv sync --frozen                          # = make install 的钉版形式
uv run --frozen pytest -rs                # 观测 passed/skipped 计数(D-11)
uv run --frozen pytest --collect-only -q | tail -3   # collected 底数

# 拆区(主仓内执行;--force 因 .venv 等未跟踪文件,Pitfall 1)
git -C /Volumes/Data/ProjectCode/my_soniscope worktree remove --force "$WT"
```

### Python 覆盖率(D-03,专区内,零仓库写入)
```bash
# Source: pytest-cov 标准用法 + uv --with overlay(旗标本机实测)
uv run --frozen --with pytest-cov pytest \
  --cov=soniscope_worker --cov=fc_shared \
  --cov-report=term-missing \
  | tee <SCRATCH>/coverage-pytest-raw.txt
# 归档时记录:uv --version、pytest/pytest-cov 版本(uv run --frozen --with pytest-cov pytest --version)
```

### JS 覆盖率(D-04,专区内,绕过 pytest 桥)
```bash
# Source: node v22.18.0 --help 实测旗标
node --test --experimental-test-coverage \
  --test-coverage-exclude='apps/miniprogram/test/**' \
  apps/miniprogram/test/*.test.js \
  2>&1 | tee <SCRATCH>/coverage-node-raw.txt
# 报告中 pages/uploads/uploads.js 会出现(uploader.test.js 加载真实页面)——HYP-24 证据点
```

### DOC 取证(主仓内,CHARTER 标准命令)
```bash
git show '5927f36:docs/v1.0.0 prd/tech-spec.md' | sed -n '1,60p'    # 路径含空格须引号(Pitfall 6)
git grep -n 'docs/PRD_v1.md\|docs/tech-spec.md\|docs/deployment-guide.md' 5927f36 -- AGENTS.md docs/  # HYP-02 全量命中
git ls-tree -r --name-only 5927f36 docs | grep -v 'docs/example/'   # 死链判定的存在性底数
```

### D-15 总对账机械验证(格式已实测)
```bash
grep -c '^### HYP-' .planning/audit/HYPOTHESES.md          # 期望 25
grep -c '^- \*\*状态:\*\*' .planning/audit/HYPOTHESES.md    # 期望 25(每条恰一行状态)
grep -c '^- \*\*状态:\*\* 未验证' .planning/audit/HYPOTHESES.md  # 期望 0(收尾后)
grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md           # 期望 4;25+4=29 对账
```

### 零 diff 收尾(主仓内,CHARTER 写定)
```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/   # 期望空输出;结果记录入阶段产物
git worktree list                                  # 确认专区已清理
```

## State of the Art

无外部技术演进问题——本阶段全部方法承接本仓库 Phase 1-3 自建范式。唯一"新旧"注意点:

| Old Approach | Current Approach | 说明 |
|--------------|------------------|------|
| Phase 3 `git archive` 导出扫描 | Phase 4 `git worktree` 基线专区 | 升级原因:本阶段需要在基线上**执行**(install + test),archive 副本可用但 worktree 一条命令建/拆更干净(D-02 用户锁定) |
| node coverage 仅 lines | node v22 支持 `--test-coverage-include/exclude` 过滤 | 本机 v22.18.0 已具备,报告可控噪 [VERIFIED: node --help] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `uv run --frozen --with pytest-cov pytest --cov=fc_shared ...` 在本 workspace 布局下能正确统计 fc_shared(经 pythonpath 导入的非安装包) | Code Examples | 若 `--cov=fc_shared` 不出数,改用 `--cov=apps/fc/shared`(路径形式)即可;建议计划首个覆盖率任务先对单个测试文件冒烟(如 `pytest apps/fc/tests/test_sts.py --cov=fc_shared`)再全量跑 |
| A2 | pytest-cov 的 repo 为 github.com/pytest-dev/pytest-cov(官方组织) | Package Legitimacy Audit | seam 未返回 repo 字段;若不实,风险极低(PyPI 15 年版本链已核) |
| A3 | 基线上 `make test` 为绿 | Architecture Patterns | 未预跑(执行留给阶段任务);若非绿,D-05 裁量条款已定:按 CHARTER 正常定级入台账,不阻塞 |

## Open Questions (RESOLVED)

1. **DOC 声明清单的总条数规模**
   - What we know:深核对象共约 4,050 行文档 + 41 行 config.js;runbook 类命令/路径声明密度高。
   - What's unclear:四态销号清单最终会有多少条(估 100-200 条量级)。
   - Recommendation:planner 按文档拆任务(PRD+tech-spec 一组、runbook 4 份一组、AGENTS+README×3+config 三份一组),避免单任务清单过长;抽取粒度属 Claude 裁量,叙事句可按声明句合并。
   - **RESOLVED:** 已被计划采纳 — 04-03(PRD + tech-spec)/ 04-04(runbook 4 份)/ 04-05(AGENTS + README×3 + config 三份与收口)正是按本条建议的分组拆任务;抽取粒度按 Claude 裁量落入各任务 action。

2. **`project.config.json` appid 与文档口径**
   - What we know:CLAUDE.md 记 appid `wx3f973c7297728b0c`、libVersion 3.5.5;普审即可(D-08)。
   - What's unclear:appid 是否算"无法静态核实"的云端事实(微信平台侧登记不可静读)。
   - Recommendation:文档↔配置互对可静态核实;配置↔微信平台真值标"无法静态核实",不猜测。
   - **RESOLVED:** 已被计划采纳 — 04-05 Task 2 逐字落实本口径:文档↔配置互对静态核实;配置↔微信平台真值(appid 登记、合法域名平台侧配置)标『无法静态核实』,不猜测。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git(worktree add/remove) | D-02 基线专区 | ✓ | 2.23.0 | — |
| uv(--with/--frozen) | D-03 覆盖率注入、make install | ✓ | 0.8.14 | — |
| node(--experimental-test-coverage + include/exclude 旗标) | D-04 JS 覆盖率、JS 桥测试 | ✓ | v22.18.0 | — |
| pytest-cov(PyPI 可达) | D-03 | ✓(registry 实测 7.1.0) | ephemeral 注入 | `--with coverage` + coverage run |
| ffmpeg/ffprobe | 无(单测全 fake) | ✓ | 已装 | 不需要 |
| python3 | uv 托管解释器(requires-python >=3.11) | ✓ | 系统 3.13.2;uv 按 lock 解析 | — |
| 磁盘空间(worktree 副本 ≈ 仓库工作树大小,含 29MB vendored) | D-02 | ✓(scratchpad 可用) | — | — |

**Missing dependencies with no fallback:** 无。

## Validation Architecture

> workflow.nyquist_validation = true。本阶段产物是审计文档,"测试"= 机械验收命令(全部只读、离线)。

### Test Framework
| Property | Value |
|----------|-------|
| Framework | 无代码测试框架;机械验收 = grep 计数 + git diff 零 diff + 文件存在性检查 |
| Config file | none(不适用) |
| Quick run command | 见下表逐项命令 |
| Full suite command | 阶段收尾:零 diff + 总对账 grep 全套 |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUDIT-03 | DOC 发现入台账,深核文档全销号,`issue-cedential`/HYP-02 两线索有核实结论 | 机械检查 | `grep -c '^### F-DOC-' .planning/audit/findings/docs-config.md`(≥1 计示例条);`grep -c 'DNF-02' .planning/audit/DOC-CLAIMS.md`(≥1);四态销号清单中无空判定格(`grep -c '待定\|TODO' DOC-CLAIMS.md` → 0) | ❌ DOC-CLAIMS.md 本阶段新建 |
| AUDIT-04 | TEST 缺口入台账,含门禁完整性,覆盖率仅证据 | 机械检查 | `ls .planning/audit/scans/coverage-*.md`;`grep -ci '评分\|score' .planning/audit/findings/test.md` → 0(无评分语言);反向映射清单 22 行逐条有兜底判定 | ❌ TEST-AUDIT.md 本阶段新建 |
| AUDIT-05 | 25/25 HYP 状态齐备、无"未验证"、总对账章节存在 | 机械检查 | `grep -c '^- \*\*状态:\*\* 未验证' .planning/audit/HYPOTHESES.md` → 0;`grep -c '^- \*\*状态:\*\*'` → 25;`grep -c '总对账' HYPOTHESES.md` ≥1 | ✅ HYPOTHESES.md 已存在(续写) |
| (硬约束) | 零 diff | 机械检查 | `git diff --stat 5927f36 -- apps/ scripts/ docs/` → 空 | ✅ |

### Sampling Rate
- **Per task commit:** 相关产物文件的 grep 抽查(上表单项命令,< 1 秒)
- **Per wave merge:** 零 diff 快查 + HYP 状态计数
- **Phase gate:** 全套机械验收 + `git worktree list` 无残留

### Wave 0 Gaps
- 无框架安装需求。唯一"Wave 0"性质任务:worktree 专区建立 + `make test` 冒烟(A1 假设的 pytest-cov 单文件冒烟并入首个覆盖率任务)。

## Security Domain

本阶段不写运行时代码,ASVS 各类(V2 认证/V3 会话/V4 访问控制/V5 输入验证/V6 密码学)均不适用于新增面。有效的安全控制只有一条,且是 CHARTER 硬约束:

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 审计产物二次泄露秘密值 | Information Disclosure | CHARTER 秘密类证据红线:只写 `path:line @ 5927f36` + 模式名,绝不复制值本体(哪怕已过期)。HYP-25/F-TOOL-05 相关的 test_asr.py 签名 URL 在 TEST 台账中引用时同样只引位置(HANDOFF 已示范该写法) |
| 实跑越界触云 | Elevation of Privilege(误操作面) | D-01 分级口径:仅 `make test`(设计零云 IO,TESTING.md 核实全 fake);任何 `test-*`/`verify-*` 目标与 scripts/ 被审脚本不执行 |

## Sources

### Primary (HIGH confidence)
- 本机工具实测:`node --help`(coverage 旗标)、`uv --version`/`uv run --help`(--with/--frozen)、`git --version`、`pip index versions pytest-cov` — 全部本会话执行
- 基线取证:`git show 5927f36:{Makefile,pyproject.toml,apps/worker/tests/test_miniprogram_js.py,apps/miniprogram/config.js,AGENTS.md,...}`、`git ls-tree -r 5927f36`、`git grep -n ... 5927f36` — 审计对象底数与线索预核全部据此
- `.planning/audit/CHARTER.md`、`HYPOTHESES.md`、`DO-NOT-FIX.md`、`HANDOFF-PHASE4.md`、`COVERAGE.md`(头部+范式)、`CONTRACT-MATRIX.md`(结构+§往返校验结论定位)、`findings/*.md`(F-* 全集枚举)、`scans/gates-baseline.md`(归档先例)
- `.planning/codebase/TESTING.md` — TEST 维度勘察底稿

### Secondary (MEDIUM confidence)
- gsd-tools package-legitimacy seam 对 pytest-cov 的判定(SUS,数据缺口所致)

### Tertiary (LOW confidence)
- A1(pytest-cov 对 pythonpath 包的统计口径)、A2(pytest-cov repo 归属)——见 Assumptions Log

## Project Constraints (from CLAUDE.md)

- 本里程碑**不新增功能、不改代码**——仅审计报告;修复留下一里程碑(零 diff 硬约束与之同源)
- 报告标准:每个发现须有严重度分级、file:line 证据、修复建议与工作量分档(CHARTER 九字段落实)
- 契约一致性以三处实现现状互审为准,不引入目标态设计(D-06 的章程依据)
- Makefile 是唯一命令入口惯例——但本阶段 Phase 3 先例(scans/gates-baseline.md)已确立"审计仪器直调实体命令、不经 make"的口径,worktree 内 `make install`/`make test` 按 D-02 原样执行
- 中文正文 + 英文 ID/严重度术语(RPT-09,与本研究文档风格一致)

## Metadata

**Confidence breakdown:**
- 审计仪器可用性(worktree/uv/node/pytest-cov): HIGH — 全部本机实测旗标与版本
- 审计对象底数(文档行数/测试文件数/HYP 清单): HIGH — 全部按基线 SHA 取证
- 方法范式(四态销号/反向映射/归档格式): HIGH — 直接复用 Phase 1-3 已封版先例
- pytest-cov 对 fc_shared 的统计口径: MEDIUM — 未预跑,已给冒烟步骤与回退(A1)

**Research date:** 2026-07-05
**Valid until:** 基线 `5927f36` 不变即长期有效(全部结论钉在基线;工具版本结论以本机环境为限)
