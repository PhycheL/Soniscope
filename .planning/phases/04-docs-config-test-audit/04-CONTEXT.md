# Phase 4: 文档配置与测试审计 - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

以代码实态(基线 `5927f36`)为基准完成三件事:① docs/、`apps/miniprogram/config.js` 等配置、AGENTS.md 与代码实态的一致性审计(AUDIT-03),发现入 `.planning/audit/findings/docs-config.md`,含 `issue-cedential` 拼写域名与 AGENTS.md 引用已删除文档两条线索的核实结论;② pytest 与 node:test 双侧测试质量与覆盖缺口盘点,含 `make test` 门禁完整性(AUDIT-04),发现入 `.planning/audit/findings/test.md`,缺口严重度参照 Phase 2/3 脆弱区发现定级;③ HYPOTHESES.md 余 11 条(DOC 6:HYP-02/05/06/11/14/21;TEST 4:HYP-22/23/24/25;CON 1:HYP-13)全部回填为证实/证伪/细化之一,并完成 25 条总对账(AUDIT-05)。同时销号 HANDOFF-PHASE4.md 的 6 条移交线索(DOC 3 + TEST 3)。

里程碑硬约束延续:零 diff(apps/、scripts/、docs/ 相对 5927f36 不许任何改动,阶段收尾跑零 diff 验证)、无例外协议(任何发现只进台账)、CHARTER 九字段 schema、证据格式 `path:line @ 5927f36`、覆盖率测量结果仅作输入证据不作质量评分(成功判据 3)、中文正文 + 英文 ID/严重度术语。

**执行口径为本阶段专属放宽(Phase 3 D-08 显式留给本阶段的决定):** 离线门禁 `make test` 可作为审计仪器执行;真云目标(`test-*`/`verify-*`)与被审脚本继续绝不执行,零云 IO 不变。

</domain>

<decisions>
## Implementation Decisions

### 测试执行与覆盖率口径
- **D-01(分级执行口径):** 离线门禁 `make test`(pytest + node:test,设计上零云 IO)可作为审计仪器执行,运行结果作证据;真云目标 `test-*`/`verify-*` 继承 Phase 3 D-08 绝不执行,只静读。审"门禁完整性"以实跑观测为证据来源之一。
- **D-02(worktree 基线专区执行):** 全部执行在 `git worktree add <scratchpad> 5927f36` 检出的仓库外基线专区进行(专区内 `make install` + `make test`),结构性保证跑的是基线代码且主工作区零触碰,延续 Phase 2/3 "基线导出 scratchpad" 先例精神。用完 `git worktree remove`,阶段收尾照常跑零 diff 验证。
- **D-03(Python 覆盖率 = 临时注入 pytest-cov):** worktree 专区内命令行临时注入(如 `uv run --with pytest-cov pytest --cov=soniscope_worker --cov=fc_shared ...`),不向仓库写入任何配置;数字与命令、工具版本一起存 `.planning/audit/scans/` 归档,与 Phase 3 D-05 临时分析器同构。
- **D-04(JS 覆盖率也实测):** worktree 专区内 `node --test --experimental-test-coverage` 直跑 `apps/miniprogram/test/*.test.js`(绕过 pytest 桥,不改桥代码),数字标注 experimental 来源,与 Python 侧同格式归档,双语言证据对称。

### DOC 审计范围与核对方式
- **D-05(全量分层范围):** 权威链深核 = PRD(`docs/v1.0.0 prd/PRD_v1.md`)、tech-spec(`docs/v1.0.0 prd/tech-spec.md`)、runbook 4 份(cloud-setup/deployment-guide/fc-deploy/mvp-acceptance)、AGENTS.md、根 README.md、apps/fc/README.md、apps/miniprogram/README.md、config.js;其余(架构评审、transcribe-approach-comparison、docs/agents/ 3 份)普审级只抓死链/过期声明;原型截图与 drawio 不审内容只记存在。每份文档入覆盖台账,"已审无发现"落到文档粒度可机械验收。
- **D-06(目标态文档只审引用与自洽):** `docs/fc-transcribe-design.md`、`docs/multi-user-design.md` 不做"设计 vs 代码实态"对照(尊重章程 CHARTER-04 排除项),只审引用有效性(死链、旧路径,HYP-02 相关)与明显自相矛盾;HYP-11 以"细化:章程范围外"关闭;覆盖台账显式标注"目标态对照未审(章程排除)"。
- **D-07(可核声明清单式深核):** 每份深核文档先抽取"可与代码/配置对照的声明"成清单(命令、路径、常量、流程步骤、边界声明),逐条标 **agree / drift / dead-ref / 无法静态核实** 四态销号,每条附文档侧与代码侧双行号证据(`@ 5927f36`)。纯云端事实(控制台配置等)标"无法静态核实"不猜测。延续 CONTRACT-MATRIX 范式,直接喂 RPT-07/08。
- **D-08(配置边界 = 小程序三份全入):** config.js 深核(ENV 常量/HYP-14 发布翻转口径、FC 域名、OSS 域名、阈值逐一对照文档声明);`project.config.json` 与 `app.json` 普审(libVersion、appid、页面注册与文档/代码一致性)。Python 侧配置(pyproject.toml/Makefile)Phase 3 已覆盖不重审,仅作声明清单对照的靠山。

### 测试缺口定级与脆弱区映射
- **D-09(反向映射法定级):** 规划时把 Phase 2/3 全部 22 条发现(F-CON-01~06 / F-CODE-01~08 / F-TOOL-01~08)+ 契约矩阵关键行编成"应重点覆盖面"清单,逐条查现有测试是否兜底;脆弱区无测试 → 缺口定级参照原发现严重度;无关联脆弱区的一般缺口按 CHARTER LOW 锚点("lint/typecheck/测试覆盖缺口"类)。清单逐条销号,可机械验收。
- **D-10(质量普审面清单化):** 仿 Phase 3 D-04,规划时定稿固定质量检查面清单(断言强度、fake 与真实实现漂移风险、隔离惯例、契约常量锁定、泄漏断言覆盖、静默 skip 路径等),每个测试模块(pytest 24+ 文件与 node:test 全部文件)逐面过并入覆盖台账。
- **D-11(门禁完整性三方对照):** 声称(Makefile/README/文档说门禁跑什么)× 静态配置(testpaths、桥接代码、skip 条件)× worktree 实跑观测(collected/passed/skipped 计数)三方逐项对照,任一不一致即缺口候选——静默 skip 使"全绿"≠"全跑"(已知线索:node 缺失时 JS 测试静默跳过 exit 0)。
- **D-12(缺口按面聚合立条):** 一个缺口面一条发现(如"活体路径零自动化覆盖"一条、"页面胶水层无测试"一条),证据字段内列具体模块/行号清单,关联字段链到对应 F-* 脆弱区发现;信噪比与 Phase 3 风格一致,根因聚类留 Phase 5。

### HYP 关闭与总对账形态
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审计规则(Phase 1 定稿,全部硬约束)
- `.planning/audit/CHARTER.md` — 基线 `5927f36`、证据格式、九字段发现 schema、发现 ID 规则、严重度锚点(TEST 缺口 LOW 锚点在此)、S/M/L/XL 分档、扫描排除清单、零 diff 验证命令(阶段收尾必跑)
- `.planning/audit/HYPOTHESES.md` — 余 11 条待回填(DOC 6 + TEST 4 + CON 1)与已回填 14 条的机械对账对象;总对账章节写入点(D-15)
- `.planning/audit/DO-NOT-FIX.md` — 4 条故意设计(`issue-cedential` 域名、`whisper-local` 桩、handler mypy 豁免等),DOC 核对与 HYP-23 处理时不得当作发现;`issue-cedential` 线索的"核实结论"须引用 DNF 条目闭环
- `.planning/REQUIREMENTS.md` — AUDIT-03/04/05 完整需求文本与 Out of Scope 表(禁小时估计、禁数值评分)
- `.planning/ROADMAP.md` — Phase 4 目标与 4 条成功判据

### Phase 2/3 移交输入(本阶段必须销号/引用)
- `.planning/audit/HANDOFF-PHASE4.md` — 6 条移交线索全文(DOC 3:HYP-16 文档一致性半句、HYP-14 ×2;TEST 3:HYP-22、HYP-25 ×2),每条含 `@ 5927f36` 行号证据
- `.planning/audit/CONTRACT-MATRIX.md` — HYP-13 引用回填的证据源(D-14);矩阵行中"文档契约声明不进矩阵、属 Phase 4"的交接条款(Phase 2 D-04)
- `.planning/audit/COVERAGE.md` — Phase 3 封版覆盖台账,反向映射清单(D-09)与"已审无发现"引用源,只读不续写
- `.planning/audit/findings/contract.md`、`findings/code.md`、`findings/toolchain.md` — 22 条既有发现(F-CON-01~06 / F-CODE-01~08 / F-TOOL-01~08),反向映射清单的输入与新发现关联字段的链接目标

### 台账写入点
- `.planning/audit/findings/docs-config.md` — DOC 维度发现(骨架已建)
- `.planning/audit/findings/test.md` — TEST 维度发现(骨架已建)
- `.planning/audit/scans/` — 覆盖率实测输出、命令与工具版本归档(Phase 3 三态销号范式延续)

### 审计对象(按基线 5927f36 读)
- 深核文档:`docs/v1.0.0 prd/PRD_v1.md`、`docs/v1.0.0 prd/tech-spec.md`、`docs/runbook/cloud-setup.md`、`docs/runbook/deployment-guide.md`、`docs/runbook/fc-deploy.md`、`docs/runbook/mvp-acceptance.md`、`AGENTS.md`、`README.md`、`apps/fc/README.md`、`apps/miniprogram/README.md`
- 深核配置:`apps/miniprogram/config.js`;普审配置:`apps/miniprogram/project.config.json`、`apps/miniprogram/app.json`
- 普审文档:`docs/architecture/architecture-review-2026-07-02.md`、`docs/transcribe-approach-comparison.md`、`docs/agents/`(3 份);只审引用与自洽:`docs/fc-transcribe-design.md`、`docs/multi-user-design.md`
- 测试套件:`apps/worker/tests/`、`apps/fc/tests/`、`apps/miniprogram/test/`;门禁定义:`Makefile`(test 目标)、根 `pyproject.toml`(pytest/mypy/ruff 配置)、`apps/worker/tests/test_miniprogram_js.py`(JS 桥,静默 skip 线索)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `git worktree add <path> 5927f36` — 基线专区执行的现成机械手段(D-02);Phase 2/3 的 scratchpad 导出先例升级版
- `git show 5927f36:<path>` / `git grep -n <pat> 5927f36 -- docs/` — CHARTER 实测可用取证命令,DOC 声明清单取证直接用
- Phase 2/3 的"清单逐条销号 + 命令/结果存档"可验收范式(CONTRACT-MATRIX 普查节、scans/ 三态销号)— DOC 四态销号与反向映射清单直接沿用该结构
- `.planning/codebase/TESTING.md` — 测试地图(框架、组织、fake 模式、无 conftest、无覆盖率配置等),TEST 维度普审的勘察底稿

### Established Patterns
- 测试套件全程注入 fake、零云 IO(TESTING.md 核实)——`make test` 离线可执行的口径依据;JS 测试经 `test_miniprogram_js.py` 子进程桥接,node 缺失静默 skip(D-11 已知线索)
- 仓库无 pytest-cov/覆盖率配置——覆盖率工具只能临时注入(D-03),这一"无覆盖率门禁"事实本身是 AUDIT-04 的审计对象之一
- 发现文档风格:中文正文 + 英文 ID/严重度术语,与 Phase 1/2/3 产物一致

### Integration Points
- HYPOTHESES.md 总对账(D-15)→ Phase 5 RPT-08 可追溯映射表的直接输入
- DOC-CLAIMS/TEST-AUDIT 底稿 + scans/ 归档 → Phase 5 RPT-07 分维度置信声明
- 新发现关联字段 → 既有 22 条 F-* 发现(反向映射,D-09)与 DNF 条目(`issue-cedential` 闭环)
- 阶段收尾:跑零 diff 验证命令(`git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空)并记录结果;worktree 专区清理

</code_context>

<specifics>
## Specific Ideas

- 用户在执行口径上选择了"分级":这是对 Phase 3 全静态口径的**有意放宽**(离线门禁可跑),但真云红线不动——规划时不得把放宽外推到任何 `test-*`/`verify-*` 真云目标或被审脚本。
- 执行环境用户选了比推荐更强的结构性保证(worktree 基线专区而非工作区直跑+前后验证),延续其一贯"结构性保证优于运行时前提"的偏好(Phase 2 D-06、Phase 3 D-16 同源)。
- 覆盖完成判定延续用户一贯要求:"系统排查完成"必须可机械验收——DOC 四态销号清单、TEST 检查面台账、反向映射清单、25/25 对账表均为此而设,不接受主观"查过了"。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 4-文档配置与测试审计*
*Context gathered: 2026-07-05*
