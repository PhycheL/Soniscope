# Phase 3: 组件与工具链深潜 - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

对三层主体代码(apps/miniprogram、apps/fc、apps/worker)与部署验证工具链(scripts/ 缩窄清单、Makefile、fc_deploy 及 Worker 包内真云验证模块)做技术债与脆弱区盘点(AUDIT-01、AUDIT-02)。发现按 CHARTER 九字段 schema 写入 `.planning/audit/findings/code.md` 与 `findings/toolchain.md`,每条经人工在引用行核实(`path:line @ 5927f36`),原始工具输出不直接充当发现。跨组件契约类观察不在本维度下判断,移交 Phase 2 矩阵/Phase 4 对应维度。

本阶段延续里程碑硬约束:零 diff(apps/、scripts/、docs/ 相对基线 5927f36 不许任何改动,阶段收尾跑零 diff 验证命令)、零云 IO、无例外协议(CRITICAL 也只进台账不动手)。scripts/ 审计范围按 Phase 1 D-06 = `test_asr.py` + `fetch_test_fixtures.py` + `gen_worker_config.sh`。

</domain>

<decisions>
## Implementation Decisions

### 深潜覆盖策略与完成判定
- **D-01(覆盖策略 = 全模块普审 + 线索深挖):** 三层每个源码模块至少完整读一遍并记覆盖台账;14 条 CODE/TOOL 维度 HYP 与 6 条 D14 移交线索命中的区域逐行深挖。"已检查,无发现"落到模块粒度,支撑 RPT-07 分维度置信声明。
- **D-02(覆盖台账 = 独立 COVERAGE.md):** `.planning/audit/COVERAGE.md` 逐模块登记:路径、审计深度(普审/深挖)、产出发现 ID 或显式"无发现"、行数。仿 Phase 2 CONTRACT-MATRIX 先例——证据与判断分离,直接喂 RPT-07/RPT-08。
- **D-03(E2E/真云验证模块归 TOOL 维度):** Worker 包内的 `fc_live.py`、`e2e.py`、`e2e_scenarios.py`、`verify_upload_live.py`、`verify_prep.py`、`sts_escape.py`、`retranscribe.py` 等验证模块按功能归 AUDIT-02"部署与验证工具链",发现入 `findings/toolchain.md`;D14-3 线索落此。严重度按工具级影响定级,不套主链路锚点。
- **D-04(普审关注面清单化):** 规划时定稿一份固定普审检查面清单(静默失败路径、资源/临时文件泄漏、异常吞并、硬编码云值、死代码、注释与实态不符等),每面对应 CHARTER 严重度锚点(数据丢失/静默转写失败/凭证泄漏)。每模块逐面过,COVERAGE.md 标"已过面 N/N"。

### 线索生成工具集边界
- **D-05(工具集 = 现有门禁 + 临时扩展分析器):** 除现有门禁(ruff/mypy/miniprogram_lint)外,临时增跑:ruff 扩大规则集(`--select` 命令行参数)、死代码扫描(vulture)、JS 侧无配置临时 ESLint(顺带量化 HYP-15 的漏报面)。全部命令行临时运行,零仓库写入(不得向仓库添加任何工具配置文件)。
- **D-06(D-07 秘密扫描归本阶段):** Phase 1 章程 D-07 的穿透式秘密扫描(LTAI 长期 AK、`OSSAccessKeyId=` 签名 URL、appsecret 等模式,全仓库含排除目录)随 TOOL 维度执行,与 HYP-07 核实同批。发现只引位置与模式名,不复制任何秘密值本体(含已过期值)。
- **D-07(扫描档案 + 三态销号):** 扫描命令、工具版本、原始输出存 `.planning/audit/scans/`;每条命中标三态销号:确认→成发现(附人工核实证据)/ 误报→记理由 / 移交→标目标维度。可复核,RPT-07 直接引用。
- **D-08(仪器可跑、对象不执行 —— 用户明确选择,比推荐项更严格):** 分析器(ruff/mypy/vulture/临时 ESLint/秘密扫描)作为**审计仪器**可直接命令调用产线索;**被审对象一律不执行**——不跑任何 make 目标(含 make test)、不执行 fc_deploy、不运行 scripts/ 脚本。工具链发现只能来自静读源码,不以"跑通与否"作证据。(注:Phase 4 审 `make test` 门禁完整性时自行决定执行口径,本决定只约束 Phase 3。)

### HYP 假设与"MVP 可接受"自评的处理
- **D-09(本阶段直接回填 HYPOTHESES.md):** CODE/TOOL 维度 HYP 验证到哪条就地回填状态(证实/证伪/细化)+ `file:line @ 5927f36` 证据;Phase 4 只补未触及条目并做总对账。
- **D-10("MVP 可接受"自评本阶段就裁):** HYP-04/09/10/12 等 CONCERNS 自评"可接受"的条目,核实事实后直接评判断是否成立,以**上线语境**(而非开发语境)度量。不成立→正常分级入发现;成立→回填 HYP 并在备注标注 RPT-06 优点/DNF 候选身份(不占发现 ID,见 D-12)。
- **D-11(跨维度顺带证据 = 记录并移交):** 普审中撞见 DOC/TEST 维度 HYP 的证据(如 config.js 的 HYP-14),记入移交清单(file:line@5927f36 + 一句观察)随阶段产物交 Phase 4;HYP 状态不动、不立发现。延续 Phase 2 移交风格。
- **D-12(证伪/可接受成立不立发现):** 只回填 HYPOTHESES.md 状态与证据,COVERAGE.md 对应模块行引用;RPT-08 的"已检查,无发现"从 HYP 表与覆盖台账两处机械引用。发现台账保持"条条是问题"的信噪比。

### D14 重复实现的债务判定口径
- **D-13(三要素判定框架):** 每条重复实现逐条评:① 结构必要性(跨部署单元无法共享 = 故意重复,如 FC↔Worker `object_key_for`;同包/同端内重复 = 可疑);② 兜底机制(测试锁定、单一真值源注释锚点有无);③ 漂移后果(静默丢数据 vs 仅工具失准)。三要素写进发现理由,判定可复核。
- **D-14(严重度锚漂移后果):** 触及主链路数据可见性的(如 D14-6 `fragmentIdFromObjectKey` 无校验切割)参照 CHARTER 主链锚点;纯维护成本/工具失准类(D14-2/D14-3)默认 LOW~MEDIUM。重复落点多、体量大不自动拔高。
- **D-15(逐条独立,聚类留 Phase 5):** 6 条 D14 各自走三要素判定、单独立发现(或单独记"不构成债务"结论),互相用关联发现字段串联;根因聚类是 Phase 5 RPT-04 的职责。RPT-08 要求每条移交线索有明确下落。
- **D-16(HYP-03 允许 scratchpad 微基准):** 仿 Phase 2 D-06:`git show 5927f36:apps/miniprogram/utils/sha256.js` 导出到仓库外临时区,node 对典型体量(10 分钟分片 ≈10MB)计时。结果作辅助证据,标注"Mac 环境非真机,量级参考";静态论证(算法实现、调用链、数据量级)仍为主判据。此为 D-08"对象不执行"的唯一例外类型——基线导出的纯函数佐证执行,与 Phase 2 先例同构。

### Claude's Discretion
- 普审关注面清单的具体条目与分面粒度(D-04 给出方向与锚点对应要求,清单定稿留给规划)。
- 扩展分析器的具体规则集选择与版本(D-05 给出工具类别,ruff `--select` 集合、vulture/ESLint 参数由规划/执行敲定)。
- COVERAGE.md 与 scans/ 目录的内部排版组织——满足逐模块粒度与三态销号可复核即可。
- 发现 ID 前缀沿用 CHARTER 既定规则(F-CODE-NN / F-TOOL-NN 类),无需再议。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审计规则(Phase 1 定稿,全部硬约束)
- `.planning/audit/CHARTER.md` — 基线 `5927f36`、证据格式、`git show`/`git grep` 取证命令、九字段发现 schema、发现 ID 规则、严重度锚点、S/M/L/XL 分档、扫描排除清单、零 diff 验证命令(阶段收尾必跑)
- `.planning/audit/HYPOTHESES.md` — 25 条 HYP 中 CODE 维度 10 条、TOOL 维度 4 条是本阶段核实对象(D-09 就地回填);HYP-03/04/07/08/09/10/12/15/16/17/18/19/25 直接相关
- `.planning/audit/DO-NOT-FIX.md` — 已裁定的故意设计(`issue-cedential` 域名、`whisper-local` 桩、handler mypy 豁免等),普审对照时不得当作发现
- `.planning/REQUIREMENTS.md` — AUDIT-01、AUDIT-02 完整需求文本与 Out of Scope 表(禁小时估计、禁数值评分)
- `.planning/ROADMAP.md` — Phase 3 目标与 4 条成功判据;与 Phase 2/4 的移交分工

### Phase 2 移交输入(本阶段必须销号的线索)
- `.planning/audit/CONTRACT-MATRIX.md` §重复逻辑普查·③债务移交记录 — D14-1~6 六条移交线索全文(sha256 双实现、重试常量四落点、联调工具镜像集群、请求组装两份同构、配置三机制并存、key 反推第四处),含全部行号证据
- `.planning/audit/findings/contract.md` — F-CON-01~06 已有发现(本阶段发现的关联字段需反向引用)

### 台账写入点
- `.planning/audit/findings/code.md` — CODE 维度发现(骨架已建)
- `.planning/audit/findings/toolchain.md` — TOOL 维度发现(骨架已建;D-03 定 E2E/真云验证模块归此)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `git show 5927f36:<path>` / `git grep -n <pat> 5927f36 -- apps/` — CHARTER 实测可用的取证命令,普审取证直接用
- Phase 2 的"命令+结果存档、逐项三态销号"可验收范式(CONTRACT-MATRIX 普查节)— D-07 扫描档案直接沿用该结构
- Phase 2 D-06 基线导出 scratchpad 执行先例 — D-16 微基准照搬其结构性零触碰保证
- 现有门禁命令(ruff/mypy/miniprogram_lint)的配置在根 `pyproject.toml`,是"仪器"基线;其规则集范围本身也是 TOOL 维度审计对象(HYP-15/25)

### Established Patterns
- 纯逻辑 + 注入 IO 是全仓库核心模式 — 普审关注面之一即"该模式被违反处"(直接 SDK/wx 调用混入纯逻辑属 CLAUDE.md 明示反模式)
- 发现文档风格:中文正文 + 英文 ID/严重度术语,与 Phase 1/2 产物一致
- Worker 主体约 26 个 Python 模块(其中约 1/3 是验证工具链,归 TOOL)、小程序 utils 约 10 个 JS 文件 + pages 两页(index.js 796 行为最大单文件)、fc_shared 8 个模块 + 2 个 handler.py

### Integration Points
- HYPOTHESES.md 回填(D-09)→ Phase 4 AUDIT-05 总对账的工作底稿
- 跨维度移交清单(D-11)→ Phase 4 DOC/TEST 维度输入
- COVERAGE.md + scans/ 档案 → Phase 5 RPT-07 分维度置信声明、RPT-08 追溯表
- "可接受成立"的 HYP 备注标记 → Phase 5 RPT-06 优点盘点 / RPT-05 DNF 登记表候选
- 阶段收尾:跑零 diff 验证命令(`git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空)并记录结果

</code_context>

<specifics>
## Specific Ideas

- 用户在执行边界上明确收紧至"全静态,一律不执行"(推翻了首选的"本地只读目标可执行"),随后确认"仪器可跑、对象不执行"口径——规划时不得以任何形式执行被审工具链(连 make test 也不跑),这是用户改选后的明确意志,不是默认推荐。
- 覆盖完成判定延续用户一贯要求:"系统排查完成"必须可机械验收(Phase 2 先例),不接受主观"查过了"——COVERAGE.md 与 scans/ 三态销号即为此而设。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-组件与工具链深潜*
*Context gathered: 2026-07-04*
