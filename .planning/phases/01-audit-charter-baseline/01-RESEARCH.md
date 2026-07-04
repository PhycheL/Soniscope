# Phase 1: 审计章程与基线 - Research

**Researched:** 2026-07-04
**Domain:** 代码审计方法学(章程/基线/严重度体系)— 纯文档产出阶段,零外部依赖
**Confidence:** HIGH(仓库事实全部本地机械验证;唯一外部引用为行业惯例,MEDIUM)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**基线钉定与 SHA 引用策略**
- **D-01:** 审计基线钉当前 HEAD `5927f36`(全 SHA `5927f362785d44b085a791ca387732991012ce5a`,分支 `ralph/soniscope-mvp-claude`)。全程 5 个阶段所有证据统一引用这一个 SHA;后续 `.planning/` 提交推进 HEAD 不影响行号有效性(受零 diff 规则保护)。main 落后 53 提交且无独立提交,审计对象即当前分支 tip。
- **D-02:** 证据引用格式:`path:line @ 5927f36`,多行证据用 `path:10-25 @ 5927f36`。章程文档开头声明一次完整 SHA,正文统一用 7 位短 SHA。
- **D-03:** 零 diff 机械验证:章程中写定验证命令(`git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空),Phase 2–5 每阶段收尾执行一次并记录结果,发现污染可定位到阶段。
- **D-04:** 基线**无例外协议**(用户明确,比推荐项更严格):任何发现(含 CRITICAL,如泄露的有效凭证)一律只进台账并标 BLOCKER,不中断审计、不重钉基线;**云端操作(如账号中删凭证、改环境变量)也绝不由审计者动手**,同样只进台账。

**扫描排除清单边界**
- **D-05:** 扫描排除清单共五项:`docs/example/start-fc-main/`(vendored,29MB)、`scripts/ralph/`(agent 元工具)、`.claude/`+`.cursor/`+`.codex/`+`.agents/`(四套 AI 工具目录)、`openspec/`(工作流状态)、`build/`+`tests/audio/`(产物与二进制;fixture manifest/描述文件仍纳入文档一致性审计)。
- **D-06:** AUDIT-02 的 scripts/ 审计范围相应缩窄为:`scripts/test_asr.py`、`scripts/fetch_test_fixtures.py`、`scripts/gen_worker_config.sh`(即 scripts/ 减去 ralph/)。
- **D-07:** 秘密/凭证扫描**穿透所有排除目录**:对全仓库(含 vendored、四套工具目录、scripts/ralph/)跑秘密模式扫描(LTAI 长期 AK、`OSSAccessKeyId=` 签名 URL、appsecret 等),命中后人工核实才进台账。
- **D-08:** CONCERNS.md 中已标注"故意设计/不要修"的条目(`whisper-local` 桩、`issue-cedential` 域名、handler mypy 豁免等)**直接预录入 RPT-05 Do-NOT-fix 登记表初稿**,不再转为待验证假设、后续阶段不再花力气验证。其余 CONCERNS.md 线索照常转为未验证假设清单。
- **D-09:** 被排除目录的"存在级"问题照常进台账(如 vendored 仓库膨胀、四套工具目录漂移、scripts/ralph/ 在仓,严重度预计 LOW/INFO),但不逐文件审计。

### Claude's Discretion
用户未选择讨论以下两项,由研究/规划阶段按需求文档(CHARTER-02、CHARTER-05)常规处理:
- **严重度定标锚点**:CRITICAL~INFO 五级的 SoniScope 场景锚定示例、顺带安全发现是否升级等细节——遵循 CHARTER-02 的"影响×可能性"格式要求即可。
- **发现台账形态与位置**:台账文件格式(Markdown/结构化)、ID 规则、存放位置——唯一硬约束:零 diff 规则下台账与报告**不得写入 apps/、scripts/、docs/**,应放在 `.planning/` 或其他不受零 diff 约束的位置。

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHARTER-01 | 审计基线钉住当前 HEAD SHA,所有证据以 `path:line @ SHA` 形式引用 | 基线 SHA `5927f36` 已本地验证存在且解析为全 SHA;工作树干净、旧 dirty-tree 阻塞已自行解除(见"关键事实验证");零 diff 命令已实测输出为空 |
| CHARTER-02 | 项目化五级严重度体系,SoniScope 场景术语 + "影响×可能性"一行理由 | 五级 CRITICAL/HIGH/MEDIUM/LOW/INFO 与 影响×可能性 矩阵是行业标准做法(OWASP Risk Rating);本文提供 SoniScope 场景锚点建议表(Claude's Discretion 区域) |
| CHARTER-03 | S/M/L/XL 工作量分档及判定标准,禁止小时估计 | 判定标准已由需求文本锁死(S ≤单文件、M=同组件多文件、L=跨组件、XL=需独立阶段),章程只需成文+配 SoniScope 示例;无需外部研究 |
| CHARTER-04 | 范围与方法声明:五个审计维度、审计 SHA、明确排除项、零 diff 规则 | 五维度映射已从 REQUIREMENTS.md 推导(见"五个审计维度");D-05 排除清单九条路径全部实测存在;排除项措辞素材齐备 |
| CHARTER-05 | 统一发现记录 schema 与扫描排除清单,在所有维度审计开始前定稿 | 提供 schema 字段设计、ID 规则建议、台账目录布局建议(含 Phase 2/3 并行写入的防冲突设计);CONCERNS.md 30 条线索已逐条盘点并给出 假设/Do-NOT-fix 分流建议 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **仅审计报告,不改代码** — 修复留给下一里程碑;本阶段所有产物必须落在 `.planning/`,严禁触碰 `apps/`、`scripts/`、`docs/`
- **报告标准**:每个发现必须有严重度分级、文件/行号证据、修复建议与工作量估计
- **审计基准**:契约一致性以三处实现现状互相对照,不引入目标态设计(FC 直转设计文档不作为对照基准)
- **双语言仓库**:Python 3.11+(mypy-strict/ruff)与小程序 JS,审计判断标准需分别适配(Phase 1 只需在章程中声明这一点)
- **中文正文 + 英文术语/ID** 的仓库文档习惯(RPT-09 已锁定),章程文档保持一致
- **GSD workflow enforcement**:所有文件变更须经 GSD 命令入口
- **Out of Scope 硬禁令**(REQUIREMENTS.md):禁止小时级估计、禁止数值化质量评分(如 "7.2/10")、禁止渗透测试级审计、禁止逐行审计 vendored 目录

## Summary

Phase 1 是一个**纯文档阶段**:产出审计章程(基线声明、五级严重度、S/M/L/XL 分档、发现 schema、排除清单、范围与方法)和假设清单,不安装任何包、不写任何代码、不碰任何业务文件。风险不在技术,而在两点:(1) 章程条款必须精确到"任何审计者可直接套用而无需再作解释"——模糊措辞会在 Phase 2–5 造成口径漂移,Phase 5 校准成本剧增;(2) 产物落点必须严格避开零 diff 保护区。

本次研究完成了全部仓库事实的机械验证:基线 SHA `5927f36` 存在且可解析全 SHA;工作树干净(STATE.md 中记录的 dirty-tree 阻塞已确认自行解除,3 份旧文档的删除已随提交入库);零 diff 验证命令实测输出为空(当前 HEAD `1f42395` 领先基线 2 个 `.planning/` 提交,不污染基线);D-05 排除清单九条路径全部存在;CONCERNS.md 共 30 条线索待分流。外部研究确认:五级严重度 + 影响×可能性格式与行业惯例(OWASP Risk Rating、主流审计机构分级)完全一致,章程可放心引用而无需发明。

**Primary recommendation:** 在 `.planning/audit/` 下建 4 类产物(CHARTER.md、HYPOTHESES.md、findings/ 目录骨架、DO-NOT-FIX.md 初稿);证据一律从 `git show 5927f36:<path>` 读取而非工作树,使行号天然免疫 HEAD 推进;CONCERNS.md 30 条线索按 D-08 分流为 ~4 条 Do-NOT-fix 预录入 + ~26 条编号假设(HYP-NN)。

## Architectural Responsibility Map

本阶段无运行时架构;"tier" 映射为产物文档与其下游消费者。

| Capability | Primary Tier (产物) | Secondary Tier (消费者) | Rationale |
|------------|--------------------|------------------------|-----------|
| 基线声明 + SHA 引用格式 + 零 diff 规则 (CHARTER-01) | `.planning/audit/CHARTER.md` | Phase 2–5 全部证据引用 | 单一权威文件,开头声明全 SHA 一次(D-02) |
| 五级严重度体系 (CHARTER-02) | CHARTER.md 严重度章节 | Phase 2–4 定级、Phase 5 校准 | 与 schema 同文件,避免多文件口径分裂 |
| S/M/L/XL 工作量分档 (CHARTER-03) | CHARTER.md 工作量章节 | Phase 2–4 估档、RPT-02/04 排序 | 同上 |
| 范围与方法声明 (CHARTER-04) | CHARTER.md 范围章节 | RPT-01 执行摘要、RPT-07 置信声明 | 五维度 + 排除项 + 无例外协议(D-04)一处成文 |
| 发现记录 schema + 排除清单 (CHARTER-05) | CHARTER.md schema 章节 + `findings/` 目录骨架 | Phase 2/3 并行写入、Phase 5 汇总 | schema 在章程,台账按维度分文件防并行写冲突 |
| CONCERNS.md → 假设清单 (成功判据 5) | `.planning/audit/HYPOTHESES.md` | Phase 4 AUDIT-05 关闭线索 | 独立文件,每条 HYP-NN 标注待验证维度 |
| Do-NOT-fix 预录入 (D-08) | `.planning/audit/DO-NOT-FIX.md` | Phase 5 RPT-05 登记表 | D-08 明确直接预录入,不走假设流程 |

## Standard Stack

### Core

本阶段**零外部依赖、零安装**。全部产出为 Markdown 文档,唯一工具是 git(证据引用与零 diff 验证)与文件写入。

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| git | 2.23.0(本机实测)[VERIFIED: `git --version`] | SHA 解析、`git show`/`git grep` 按基线取证、零 diff 验证 | 仓库已有;git 2.23 完全支持所需的 `rev-parse`/`diff --stat <sha> -- <paths>`/`show <sha>:<path>`/`grep <pattern> <sha>` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (无) | — | — | — |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Markdown 台账 | JSON/YAML 结构化台账 | 结构化便于机器聚合(Phase 5 排序),但违背仓库"中文正文文档"习惯、审阅摩擦大;推荐 Markdown 表格 + 严格 schema 字段顺序,Phase 5 需要时可脚本解析表格 |
| `git show SHA:path` 取证 | 直接读工作树文件 | 工作树当前与基线一致(零 diff 实测通过),读工作树暂时等价;但 `.planning/` 提交会持续推进 HEAD,**从 SHA 取证是结构性免疫,读工作树是靠纪律** — 章程应规定前者为标准做法 |

**Installation:**
```bash
# 无需安装任何东西
```

## Package Legitimacy Audit

**不适用** — 本阶段不安装任何外部包(npm/PyPI/crates 均无)。无 SLOP/SUS 风险面。

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │  基线事实 (本研究已机械验证)            │
                    │  5927f36 = 5927f362…12ce5a           │
                    │  工作树干净 / 零 diff 通过              │
                    └──────────────┬──────────────────────┘
                                   │
  .planning/codebase/CONCERNS.md ──┤ (30 条线索)
  .planning/codebase/STRUCTURE.md ─┤ (排除清单路径依据)
  REQUIREMENTS.md CHARTER-01~05 ───┤ (验收条款)
  CONTEXT.md D-01~D-09 ────────────┘ (锁定决策)
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  Phase 1 产出 (.planning/audit/)      │
                    │                                     │
                    │  CHARTER.md ──── 基线/严重度/工作量/    │
                    │       │          schema/排除/范围方法  │
                    │       │                              │
                    │  HYPOTHESES.md ─ HYP-NN 假设清单       │
                    │  DO-NOT-FIX.md ─ D-08 预录入初稿       │
                    │  findings/ ───── 5 维度台账骨架(空)    │
                    └──────┬──────────────┬───────────────┘
                           │              │
              Phase 2/3 (并行证据收集)   Phase 4 (关闭假设)
                           │              │
                           └──────┬───────┘
                                  ▼
                         Phase 5 (校准+报告, RPT-05 吃 DO-NOT-FIX)
```

### Recommended Project Structure

```
.planning/audit/
├── CHARTER.md          # CHARTER-01~05 全部规则:基线声明(全 SHA 一次)、
│                       # 严重度体系、S/M/L/XL、发现 schema、扫描排除清单、
│                       # 范围与方法声明、零 diff 验证命令、D-04 无例外协议、
│                       # D-07 秘密扫描穿透规则(含模式清单)
├── HYPOTHESES.md       # CONCERNS.md → 未验证假设清单(HYP-NN,标注待验证维度)
├── DO-NOT-FIX.md       # RPT-05 登记表初稿(D-08 预录入,标 ⚠ intentional)
└── findings/           # 发现台账骨架(Phase 1 建目录+表头+1 条 schema 示例)
    ├── contract.md     # Phase 2 写入 (F-CON-NN)
    ├── code.md         # Phase 3 写入 (F-CODE-NN)
    ├── toolchain.md    # Phase 3 写入 (F-TOOL-NN)
    ├── docs-config.md  # Phase 4 写入 (F-DOC-NN)
    └── test.md         # Phase 4 写入 (F-TEST-NN)
```

**为何台账按维度分文件而非单文件:** ROADMAP 明确 Phase 2 与 Phase 3 同波次可并行执行;单一 FINDINGS.md 会造成并行写入冲突。按维度分文件后每个阶段只写自己的文件,Phase 5 汇总时合并。这是规划期就该锁定的结构决策。

**位置合规性:** `.planning/audit/` 不在 `apps/`、`scripts/`、`docs/` 之下,满足零 diff 硬约束(用户唯一硬约束)。`commit_docs: true`,产物随 `.planning/` 提交入库不污染基线(已实测:领先基线 2 个提交时零 diff 仍通过)。

### Pattern 1: 五个审计维度(CHARTER-04 的维度定义)

**What:** 范围声明需列出"五个审计维度"。从 REQUIREMENTS.md 需求分组直接推导:

| # | 维度 | 英文短码(供发现 ID) | 对应需求 | 执行阶段 |
|---|------|---------------------|----------|----------|
| 1 | 契约一致性 | CON | CONTRACT-01~04 | Phase 2 |
| 2 | 组件代码(技术债/脆弱区) | CODE | AUDIT-01 | Phase 3 |
| 3 | 部署与验证工具链 | TOOL | AUDIT-02 | Phase 3 |
| 4 | 文档配置一致性 | DOC | AUDIT-03 | Phase 4 |
| 5 | 测试质量与覆盖 | TEST | AUDIT-04 | Phase 4 |

**When to use:** 章程范围声明、发现 ID 前缀、RPT-07 分维度置信声明的骨架。
[VERIFIED: 从 .planning/REQUIREMENTS.md 需求分组推导,与 ROADMAP 阶段划分一致]

### Pattern 2: 证据从基线 SHA 直接读取(免疫 HEAD 推进)

**What:** 所有 `path:line @ 5927f36` 证据从 `git show 5927f36:<path>` 提取,而非读工作树。零 diff 验证(D-03)保留为每阶段收尾的污染检测手段,但取证本身不依赖工作树干净。

**When to use:** 章程"证据提取方法"条款;Phase 2–5 所有取证操作。

**Example:**
```bash
# 按基线读文件(带行号)
git show 5927f36:apps/fc/shared/fc_shared/sts.py | sed -n '90,110p'

# 按基线全仓库 grep(天然穿透排除目录 — 满足 D-07 秘密扫描穿透)
git grep -nE 'LTAI[0-9A-Za-z]{10,}' 5927f36 -- .

# 零 diff 验证(D-03 锁定命令,逐阶段收尾执行并记录)
git diff --stat 5927f36 -- apps/ scripts/ docs/   # 期望输出为空
```
[VERIFIED: 三条命令均已在本仓库实测可用,git 2.23.0]

### Pattern 3: 发现记录 schema(CHARTER-05 字段落地)

**What:** 每条发现一个 Markdown 小节,字段顺序固定:

```markdown
### F-CON-01: <一行标题>

- **维度:** 契约一致性 (CON)
- **严重度:** HIGH — 影响:上传对 Worker 永久不可见(静默数据滞留);可能性:仅在 fragment_id 格式变更时触发,当前格式下不触发
- **证据:** `apps/fc/shared/fc_shared/sts.py:95-102 @ 5927f36`
  > (引用的代码片段,从 git show 提取)
- **修复建议:** <一段>
- **工作量:** M(同组件多文件)
- **关联发现:** F-CODE-03;关联线索: HYP-07
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft | calibrated(Phase 5 校准后)
```

**设计说明:**
- 前 7 个字段即 CHARTER-05 锁定清单(ID、维度、严重度+理由、file:line@SHA 证据、修复建议、工作量、关联发现)。
- 追加 `上线判定`(RPT-03 需要,Phase 5 填)与 `状态`(Phase 5 校准留痕需要,ROADMAP Phase 5 判据 1 要求"校准调整有记录可查")两个字段,现在建槽避免 Phase 5 改 schema 返工。追加字段不违反 CHARTER-05(其为最小字段集)。
- `关联发现` 同时承载 发现↔发现 与 发现↔HYP 链接,喂 RPT-08 可追溯映射表。

**ID 规则(Claude's Discretion,推荐):** `F-<维度短码>-NN`(F-CON-01、F-CODE-01…)。加 `F-` 前缀与 REQUIREMENTS.md 的 `CONTRACT-NN` 需求 ID 明确区分(CONTEXT.md 提示与现有 ID 风格协调,但 `CONTRACT-01` 已被需求占用,直接复用维度名会撞名)。假设用 `HYP-NN`,Do-NOT-fix 用 `DNF-NN`。

### Anti-Patterns to Avoid

- **章程/台账写进 docs/:** 直觉上"文档进 docs/",但会立即打破零 diff。唯一合法落点是 `.planning/`(用户硬约束)。
- **数值评分混入严重度理由:** "影响×可能性"必须保持定性一行理由;引入 OWASP 数值因子打分(0-9)违反 Out of Scope 的"禁止数值化质量评分"。
- **章程里给严重度留自由裁量措辞:** "视情况可上调/下调"之类措辞违反成功判据 2("任何审计者可直接套用而无需再作解释");边界情况应以锚点示例穷举,而非授权裁量。
- **把 CONCERNS.md 的结论当发现直接抄:** CONCERNS.md 是线索/假设,不是答案(AUDIT-05 原文);Phase 1 只做"转写为假设",不做任何证实/证伪。
- **重新勘察仓库结构:** `.planning/codebase/` 七份地图(2026-07-04 生成)已覆盖目录/组件盘点,排除清单与范围声明直接引用,不重复劳动。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 严重度框架 | 自创评级哲学 | 五级 CRITICAL/HIGH/MEDIUM/LOW/INFO + 影响×可能性(OWASP Risk Rating 的定性用法) | 行业标准,读者零学习成本;需求文本本身就锁定了这个形态 [CITED: owasp.org/www-community/OWASP_Risk_Rating_Methodology] |
| 按基线取证 | 手工快照文件副本 | `git show 5927f36:<path>` / `git grep <pat> 5927f36` | git 原生、可复现、零维护;快照副本会漂移且占空间 |
| 穿透排除目录的秘密扫描 | 自写目录遍历脚本 | `git grep -nE <pattern> 5927f36 -- .`(对 commit 扫描天然覆盖全部已跟踪文件,含 vendored 与工具目录) | D-07 要求穿透;对 SHA 扫描顺带免疫工作树未跟踪垃圾(如 `scripts/__pycache__/`) |
| 零 diff 验证 | 人工比对 | D-03 锁定的 `git diff --stat 5927f36 -- apps/ scripts/ docs/` | 用户已锁定命令,机械且可记录 |

**Key insight:** 这个阶段最大的"hand-roll 诱惑"是发明新方法学。所有标尺(五级、L×I、S/M/L/XL、path:line@SHA)在需求与决策里都已锁形,Phase 1 的工作是**精确成文 + SoniScope 场景锚定**,不是设计。

## 关键事实验证(基线状态)

全部于 2026-07-04 在本仓库机械验证 [VERIFIED: 本地 git 命令]:

| 事实 | 验证结果 |
|------|----------|
| 基线 SHA 存在 | `git rev-parse 5927f36` → `5927f362785d44b085a791ca387732991012ce5a` ✓(与 D-01 全 SHA 一致) |
| 当前 HEAD | `1f42395`,领先基线 2 个提交,均为 `.planning/` 文档提交 |
| 工作树状态 | `git status --porcelain` 输出为空 — **干净**。STATE.md 中 "[Phase 1] Dirty-tree 决定阻塞" 已过时(CONTEXT.md 已核实,本研究再次确认):`docs/PRD_v1.md`、`docs/tech-spec.md`、`docs/deployment-guide.md` 旧路径已不存在,删除已入库,内容迁至 `docs/v1.0.0 prd/`(PRD_v1.md、tech-spec.md 均实测存在)与 `docs/runbook/`(deployment-guide.md 实测存在) |
| 零 diff 命令 | `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空 ✓ — `.planning/` 提交推进 HEAD 不触发污染,证实 D-01 判断 |
| 分支 | `ralph/soniscope-mvp-claude` ✓ |
| D-05 九条排除路径 | `docs/example/start-fc-main/`、`scripts/ralph/`、`.claude/`、`.cursor/`、`.codex/`、`.agents/`、`openspec/`、`build/`、`tests/audio/` — **全部实测存在** |
| D-06 scripts/ 缩窄范围 | `ls scripts/` → `test_asr.py`、`fetch_test_fixtures.py`、`gen_worker_config.sh`、`ralph/`(另有未跟踪 `__pycache__/`,git 取证天然忽略)— 与 D-06 清单一致 |

**章程措辞含义:** CHARTER-01 的 "dirty-tree 处置决定" 按 CONTEXT.md 简化为**记录事实**:基线钉定时工作树干净,旧文档迁移已随提交入库;AGENTS.md 仍引用旧路径一事留给 Phase 4(建议在 HYPOTHESES.md 中立一条 HYP,标注 DOC 维度)。

## 严重度锚点建议(Claude's Discretion — 供规划采纳)

按 CHARTER-02 要求,每级用 SoniScope 场景术语定义,评级理由格式统一为一行 "影响:…;可能性:…"。以下锚点为研究判断 [ASSUMED],规划/执行时可微调措辞但不改级别结构:

| 级别 | SoniScope 场景定义(锚点示例) |
|------|------------------------------|
| **CRITICAL** | 可致用户录音**数据丢失或不可恢复**(如 OSS 对象被删、`.done` 早写导致片段永久跳过);**有效长期凭证泄露**(在库 LTAI AK、WX_APP_SECRET 明文且仍有效);认证被绕过(allowlist 失效) |
| **HIGH** | **静默转写失败**(音频安全但用户无感知得不到转写,如契约活跃失配使上传对 Worker 永久不可见);STS 权限越界(单键策略失效);崩溃恢复产出损坏工件 |
| **MEDIUM** | 潜伏失配(当前参数/格式下不触发,变更即爆);误导性文档可诱发高危误操作(如 runbook 步骤与实态不符);已过期凭证曾入库(泄露习惯风险,如 `scripts/test_asr.py` 过期预签名 URL 先例) |
| **LOW** | 技术债与非关键路径重复实现;文档死链/路径失效;lint/typecheck 覆盖缺口;非热路径性能问题 |
| **INFO** | 存在级观察(vendored 仓库膨胀、四套工具目录漂移 — 呼应 D-09 预期定级);风格不一致;值得记录但无行动必要的事实 |

**顺带安全发现处理建议 [ASSUMED]:** 不设"自动升级"规则——安全发现与其他发现同用 影响×可能性 定级,仅在台账加 `顺带发现(out-of-dimension)` 标注(REQUIREMENTS.md Out of Scope 表要求顺带安全发现"仍记录并标注")。这保持单一定级口径,避免双轨制。

**工作量分档(CHARTER-03 需求文本已锁,直接成文):** S ≤单文件;M = 同组件多文件;L = 跨组件;XL = 需独立阶段。章程配一个 SoniScope 示例即可(如:改 `config.js` 一处常量 = S;`fc_shared` 内多文件调整 = M;fragment_id 格式变更需 FC+Worker+小程序三处同步 = L;实现 `transcribe_audio` 函数 = XL)。

## 秘密扫描模式清单建议(D-07 落地,写入章程)

D-07 要求章程定义穿透式秘密扫描;模式清单建议(源自 CONCERNS.md 安全节与 CLAUDE.md 秘密红线)[VERIFIED: 模式来源均在 CONCERNS.md/CLAUDE.md 有据]:

```bash
# 全部对基线 SHA 扫描,天然穿透 D-05 排除目录(git grep <sha> 覆盖该 commit 全部文件)
git grep -nE 'LTAI[0-9A-Za-z]{10,}' 5927f36 -- .            # 长期 AK ID
git grep -nE 'OSSAccessKeyId=' 5927f36 -- .                  # 签名 URL(test_asr.py 先例模式)
git grep -nE 'Signature=[0-9A-Za-z%+/=]{16,}' 5927f36 -- .   # 签名参数
git grep -niE 'app_?secret\s*[:=]\s*["'"'"'][^"'"'"']{8,}' 5927f36 -- .  # appsecret 字面量
git grep -nE 'SecurityToken=|security_token.{0,4}[:=]\s*["'"'"']' 5927f36 -- .  # STS token
```

章程条款要点:命中 ≠ 发现——**人工核实后才进台账**(D-07 原文);扫描本身在 Phase 3(工具链/代码维度)执行,Phase 1 只定义模式与规则。章程可引用 `scripts/test_asr.py` 曾提交过期预签名 URL 的先例说明穿透理由(CONTEXT.md specifics 明确希望保留此例)。

## CONCERNS.md 线索分流盘点(CHARTER-05 / 成功判据 5 的工作底稿)

CONCERNS.md 共 **30 条**线索 [VERIFIED: 逐节清点]:Tech Debt 7、Known Bugs 0(显式"None detected"——应在 HYPOTHESES.md 记一条"已检查,无已知 bug 线索"的显式记录,喂 RPT-08)、Security 4、Performance 3、Fragile Areas 6、Scaling Limits 2、Dependencies at Risk 2、Missing Critical Features 2、Test Coverage Gaps 4。

**D-08 Do-NOT-fix 预录入(不转假设):** D-08 点名 3 条 + 明确同类 1 条,共建议预录入 4 条:
1. `whisper-local` 桩(Tech Debt 节,"do not fix without a scope decision")
2. `issue-cedential` 拼写域名(Fragile Areas 节)
3. handler.py mypy 豁免(Fragile Areas 节,pyproject.toml 已注释缘由)
4. 小程序接收原始 STS 秘密(Security 节标注 "by design")[ASSUMED — D-08 用"等"字留了口,此条是否入 DNF 由规划确认]

**其余 ~26 条 → HYP-NN 假设清单**,每条标注待验证维度(CON/CODE/TOOL/DOC/TEST)。注意若干条标注 "acceptable for MVP"(fc_deploy 仅 update_code、单用户 allowlist、wsgiref、Worker 串行)——这些**不是** D-08 点名的 Do-NOT-fix,仍应转为假设由 Phase 3/4 核实其"可接受"判断是否成立 [ASSUMED — 分流边界由规划最终定夺]。

注意维度归属示例:AGENTS.md 旧路径引用 → DOC;test_asr.py 过期预签名 URL → TOOL(含安全标注);fragment_id 三处重复 → CON;纯 JS sha256 → CODE。

## Common Pitfalls

### Pitfall 1: 产物落点污染零 diff 保护区
**What goes wrong:** 章程或台账被写到 `docs/audit/` 之类"看起来合理"的位置。
**Why it happens:** "文档进 docs/" 是默认直觉。
**How to avoid:** 计划中把落点写死为 `.planning/audit/`;每个 plan 的验证步骤包含跑一次 D-03 零 diff 命令。
**Warning signs:** 任何任务的文件路径以 `apps/`、`scripts/`、`docs/` 开头。

### Pitfall 2: 章程条款留下解释空间
**What goes wrong:** 严重度定义写成抽象形容词("严重影响系统"),Phase 2/3 两个并行执行者定级口径漂移,Phase 5 校准工作量爆炸。
**Why it happens:** 通用模板语言比场景锚定容易写。
**How to avoid:** 每级严重度必须绑定 SoniScope 具体场景词(数据丢失/静默转写失败/凭证泄漏/存在级观察);边界用锚点示例封死,不写"视情况"类措辞。
**Warning signs:** 严重度表中出现无场景名词的定义行;出现"可酌情""一般来说"。

### Pitfall 3: 顺手修复(哪怕一行)
**What goes wrong:** 写章程时看到 AGENTS.md 死链、STATE.md 过时阻塞,顺手改掉业务区文件。
**Why it happens:** 修复冲动 + "只是文档"错觉。
**How to avoid:** 章程写入 D-04 无例外协议原文级措辞(用户 specifics:"云端操作绝不自己动手,也只是进入台账"——保留这种绝对性);AGENTS.md 死链只进假设清单。注意:更新 `.planning/STATE.md` 里的过时 blocker 是合法的(不在保护区),与业务区修复要区分开。
**Warning signs:** 任何对 `apps/ scripts/ docs/` 的 Edit/Write;任何"顺便"字样。

### Pitfall 4: 假设清单丢失可追溯性
**What goes wrong:** CONCERNS.md 条目转写时合并/改写,Phase 4 无法逐条对账,RPT-08 映射表断链。
**How to avoid:** HYP-NN 与 CONCERNS.md 原节名+条目标题一一对应,30 条(含 Known Bugs 的"无线索"显式记录)全部入账;转换表在 HYPOTHESES.md 头部给出计数核对(30 = 4 DNF + 25 HYP + 1 显式无发现记录,或规划定的实际分流数)。
**Warning signs:** HYP 计数 + DNF 计数 ≠ CONCERNS.md 条目数。

### Pitfall 5: 从工作树而非基线 SHA 取证
**What goes wrong:** Phase 2–5 期间 `.planning/` 提交持续推进 HEAD;若未来某阶段意外污染保护区后才发现,期间从工作树读的行号全部存疑。
**How to avoid:** 章程规定证据提取标准命令为 `git show 5927f36:<path>`;零 diff 检查降级为污染报警器而非取证前提。
**Warning signs:** 计划中出现 Read 工作树文件充当行号证据的取证步骤。

### Pitfall 6: 零 diff 命令覆盖面被误解为"全部审计对象"
**What goes wrong:** D-03 命令只盯 `apps/ scripts/ docs/`;`Makefile`、`AGENTS.md`、`pyproject.toml`、`uv.lock` 等根文件也是审计对象(AUDIT-02/03 明确涉及 Makefile 与 AGENTS.md),但不在该命令保护范围。若有人改根文件,命令不报警。
**How to avoid:** 不改 D-03 锁定命令(用户决策);但因取证统一走基线 SHA(Pitfall 5 的对策),根文件行号证据同样免疫。章程可加一句说明:零 diff 命令保护三个目录,其余审计对象靠"证据一律出自 5927f36"兜底。
**Warning signs:** 章程把零 diff 命令表述为"审计范围等于该命令的路径列表"。

## Code Examples

### 章程基线声明区块(建议模板)
```markdown
## 审计基线

- **基线 commit:** `5927f362785d44b085a791ca387732991012ce5a`(下文简写 `5927f36`)
- **分支:** `ralph/soniscope-mvp-claude`(main 落后 53 提交且无独立提交,审计对象即本分支 tip)
- **钉定时工作树状态:** 干净;docs/ 权威文档迁移(PRD_v1/tech-spec/deployment-guide → `docs/v1.0.0 prd/`、`docs/runbook/`)已随提交入库
- **证据格式:** `path:line @ 5927f36`;多行 `path:10-25 @ 5927f36`;证据一律提取自 `git show 5927f36:<path>`
- **零 diff 验证:** `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出必须为空;Phase 2–5 每阶段收尾执行并记录结果
- **无例外协议:** 任何发现(含 CRITICAL,如泄露的有效凭证)一律只进台账并标 BLOCKER;不中断审计、不重钉基线;云端操作(删凭证、改环境变量等)绝不由审计者执行
```
[VERIFIED: 全部字段值经本地 git 命令核实]

### 取证与验证命令(章程"方法"章节引用)
```bash
git show 5927f36:apps/miniprogram/config.js | sed -n '1,30p'   # 按基线读文件
git grep -n 'fragment_id' 5927f36 -- apps/                      # 按基线检索
git diff --stat 5927f36 -- apps/ scripts/ docs/                 # 零 diff(期望空输出)
```
[VERIFIED: 本仓库实测,git 2.23.0]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 审计报告用数值评分(CVSS 分数、x/10) | 定性 影响×可能性 五级 + 一行理由 | 项目决策(REQUIREMENTS.md Out of Scope) | 不可证伪的数字争论被结构性排除 |
| STATE.md 记录 dirty-tree 阻塞 | 阻塞已自行解除(工作树干净) | 2026-07-04 CONTEXT 讨论核实,本研究复核 | Phase 1 首个任务从"做处置决定"简化为"记录事实" |

**Deprecated/outdated:**
- STATE.md `## Blockers/Concerns` 中的 "[Phase 1] Dirty-tree 决定阻塞" 条目已过时——规划时应安排在 `.planning/STATE.md` 中清除(合法,不在零 diff 保护区)。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 严重度五级的 SoniScope 场景锚点措辞(CRITICAL=数据丢失/有效凭证泄露 等) | 严重度锚点建议 | 低 — 属 Claude's Discretion 区域,规划/执行可调措辞;级别结构由需求锁定 |
| A2 | 顺带安全发现不自动升级、仅加标注 | 严重度锚点建议 | 低 — 若用户偏好升级规则,只改章程一句话 |
| A3 | "小程序接收原始 STS 秘密(by design)" 归入 DNF 预录入(D-08 的"等"字延伸) | CONCERNS 分流盘点 | 低 — 归错侧只是多/少验证一条假设 |
| A4 | "acceptable for MVP" 类条目(fc_deploy 仅 update_code、allowlist、wsgiref、串行 Worker)转假设而非 DNF | CONCERNS 分流盘点 | 中 — 若应入 DNF,Phase 3/4 会白花核实功夫;建议规划时向用户确认或按本建议执行并在 HYPOTHESES.md 标注分流依据 |
| A5 | 台账按维度分 5 文件(防 Phase 2/3 并行写冲突) | Architecture Patterns | 低 — 属台账形态 Discretion;单文件亦可行但有合并冲突风险 |

## Open Questions

1. **D-08 "等" 字的完整 DNF 预录入清单**
   - What we know: 明确点名 3 条(whisper-local、issue-cedential、handler mypy 豁免)。
   - What's unclear: CONCERNS.md 另有 "by design"/"acceptable for MVP" 标注条目是否同列。
   - Recommendation: 采纳本研究分流建议(4 条 DNF + 其余转假设),在 DO-NOT-FIX.md 与 HYPOTHESES.md 各自写明分流依据,Phase 5 组装 RPT-05 时用户可最终裁定——不阻塞规划。

2. **章程单文件 vs 多文件**
   - What we know: 唯一硬约束是落点在 `.planning/`;CHARTER-01~05 五组规则彼此引用密切。
   - Recommendation: 单一 CHARTER.md(全 SHA 声明一次的 D-02 要求天然指向单文件)+ 独立 HYPOTHESES.md / DO-NOT-FIX.md / findings/ 骨架,共 4 类产物;规划按此拆 plan 即可。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | SHA 解析、取证、零 diff 验证 | ✓ | 2.23.0 | — |

**Missing dependencies with no fallback:** 无。本阶段除 git 与文件写入外无任何外部依赖(无 Python/Node 运行需求——不执行任何代码)。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | 无需测试框架 — 纯文档阶段;验证 = shell 机械检查(仓库自有 pytest/node:test 与本阶段无关,不触碰) |
| Config file | none — 无 Wave 0 需求 |
| Quick run command | `git diff --stat 5927f36 -- apps/ scripts/ docs/`(期望空输出) |
| Full suite command | 下表全部 grep/计数检查逐条执行 |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHARTER-01 | 章程含全 SHA 声明与证据格式、无例外协议 | smoke | `grep -c '5927f362785d44b085a791ca387732991012ce5a' .planning/audit/CHARTER.md`(≥1)且 `grep -c '@ 5927f36' .planning/audit/CHARTER.md`(≥1) | ❌ 本阶段产出 |
| CHARTER-02 | 五级严重度全部定义且带影响×可能性格式 | smoke | `for s in CRITICAL HIGH MEDIUM LOW INFO; do grep -q "$s" .planning/audit/CHARTER.md || echo "MISSING $s"; done` | ❌ 本阶段产出 |
| CHARTER-03 | S/M/L/XL 分档成文、无小时估计 | smoke | `grep -qE 'XL' .planning/audit/CHARTER.md && ! grep -qE '[0-9]+\s*(小时|h\b|hours)' .planning/audit/CHARTER.md` | ❌ 本阶段产出 |
| CHARTER-04 | 排除清单九路径 + 五维度 + 零 diff 规则在章程中 | smoke | `for p in start-fc-main scripts/ralph openspec tests/audio; do grep -q "$p" .planning/audit/CHARTER.md || echo "MISSING $p"; done` | ❌ 本阶段产出 |
| CHARTER-05 | schema 七字段齐备;假设清单计数与 CONCERNS.md 对账 | integration | schema 示例字段 grep;HYP+DNF 条目计数 = 30(`grep -c '^### HYP-' .planning/audit/HYPOTHESES.md` 等) | ❌ 本阶段产出 |
| (基线不变量) | 零 diff 保持 | smoke | `test -z "$(git diff --stat 5927f36 -- apps/ scripts/ docs/)"` | ✅ 命令已实测 |

### Sampling Rate
- **Per task commit:** 零 diff quick 检查(空输出)
- **Per wave merge:** 上表全部 grep/计数检查
- **Phase gate:** 全部检查通过 + `/gsd-verify-work` 人工确认章程条款可"无解释直接套用"

### Wave 0 Gaps
- None — 纯文档阶段,无测试基础设施需求;全部验证为现成 shell 命令。

## Security Domain

本阶段不写代码、不处理输入、不接触网络——ASVS 常规类别不适用;但章程本身定义后续安全审计规则,且产物有一个自身安全约束:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | 纯文档产出,无输入面 |
| V6 Cryptography | no | — |

### Known Threat Patterns for 本阶段产物

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 章程/假设清单在引用先例时复制秘密原文(如 test_asr.py 预签名 URL 的完整 Signature) | Information Disclosure | 章程与一切产物引用秘密类证据时只写 `path:line @ SHA` + 模式名,**不复制值本体**;哪怕已过期(项目红线:normalizing leaking tokens) |
| 审计者顺手执行云端操作(删凭证/改 env) | Tampering | D-04 无例外协议原文写入章程,绝对措辞、无裁量 |
| 秘密扫描遗漏 vendored/工具目录 | Information Disclosure | D-07 穿透规则 + `git grep <pattern> 5927f36 -- .` 对 commit 全量扫描 |

## Sources

### Primary (HIGH confidence)
- 本地 git 验证(2026-07-04):`git rev-parse`、`git status --porcelain`、`git diff --stat`、路径存在性、`git --version` — 基线全部事实
- `.planning/phases/01-audit-charter-baseline/01-CONTEXT.md` — D-01~D-09 锁定决策
- `.planning/REQUIREMENTS.md`、`.planning/ROADMAP.md` — CHARTER-01~05 条款、五维度、Out of Scope 禁令
- `.planning/codebase/CONCERNS.md` — 30 条线索逐条清点
- `./.claude/CLAUDE.md` — 项目约束、秘密红线、文档语言习惯

### Secondary (MEDIUM confidence)
- [OWASP Risk Rating Methodology](https://owasp.org/www-community/OWASP_Risk_Rating_Methodology) — 严重度 = Likelihood × Impact 矩阵的规范出处(WebSearch 定位到官方页面)
- 行业审计分级惯例(Atlassian severity levels、Google SCC finding severities、Snyk/GitLab severity docs)— 五级 Critical/High/Medium/Low/Informational 为通行做法,佐证 CHARTER-02 形态无需发明

### Tertiary (LOW confidence)
- 无(未采用任何仅凭训练记忆且无法本地验证的关键主张;A1–A5 假设已单列)

## Metadata

**Confidence breakdown:**
- 基线与仓库事实: HIGH — 全部本地机械验证
- 章程结构/产物布局: HIGH — 由锁定决策与需求直接推导,辅以并行写入冲突分析
- 严重度锚点与 DNF 分流边界: MEDIUM — Claude's Discretion 区域,已在 Assumptions Log 标注供确认
- 行业惯例引用: MEDIUM — WebSearch 定位官方来源,未逐页深读(本阶段不依赖其细节)

**Research date:** 2026-07-04
**Valid until:** 2026-08-04(方法学类内容稳定;唯一时效敏感项是仓库基线状态,已钉 SHA 免疫)
