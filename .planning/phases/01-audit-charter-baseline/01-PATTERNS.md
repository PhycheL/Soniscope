# Phase 1: 审计章程与基线 - Pattern Map

**Mapped:** 2026-07-04
**Files analyzed:** 9 (8 new + 1 modified)
**Analogs found:** 9 / 9

**注意:** 本阶段是纯文档阶段——不新建任何代码文件。"pattern" 在此指 `.planning/` 内既有 Markdown 文档的结构惯例(头部元数据、ID 体系、条目字段布局、表格、页脚)。所有新文件必须落在 `.planning/audit/`,严禁触碰 `apps/`、`scripts/`、`docs/`(零 diff 硬约束)。

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/audit/CHARTER.md` | 规则/章程文档 (config-doc) | 静态引用(Phase 2–5 只读) | `.planning/REQUIREMENTS.md` + `.planning/ROADMAP.md` | role-match |
| `.planning/audit/HYPOTHESES.md` | 假设台账 (ledger) | 转写(CONCERNS.md → HYP-NN)、Phase 4 回填状态 | `.planning/codebase/CONCERNS.md` | exact(结构来源即转写源) |
| `.planning/audit/DO-NOT-FIX.md` | 登记表 (registry) | 一次预录入、Phase 5 流入 RPT-05 | `.planning/REQUIREMENTS.md` Out of Scope 表 + CONCERNS.md "by design" 条目 | role-match |
| `.planning/audit/findings/contract.md` | 发现台账骨架 (ledger) | append-only(Phase 2 写入 F-CON-NN) | RESEARCH.md Pattern 3 schema + CONCERNS.md 条目布局 | role-match |
| `.planning/audit/findings/code.md` | 发现台账骨架 (ledger) | append-only(Phase 3 写入 F-CODE-NN) | 同上 | role-match |
| `.planning/audit/findings/toolchain.md` | 发现台账骨架 (ledger) | append-only(Phase 3 写入 F-TOOL-NN) | 同上 | role-match |
| `.planning/audit/findings/docs-config.md` | 发现台账骨架 (ledger) | append-only(Phase 4 写入 F-DOC-NN) | 同上 | role-match |
| `.planning/audit/findings/test.md` | 发现台账骨架 (ledger) | append-only(Phase 4 写入 F-TEST-NN) | 同上 | role-match |
| `.planning/STATE.md`(修改) | GSD 状态文件 | 就地更新(清除过时 blocker) | 自身既有结构 | exact |

## Pattern Assignments

### `.planning/audit/CHARTER.md` (章程文档,静态引用)

**Analog:** `.planning/REQUIREMENTS.md`(ID 体系、头部、Out of Scope 表、页脚)+ `.planning/ROADMAP.md`(零 diff 措辞、"what must be TRUE" 判据风格)

**头部元数据 pattern**(`.planning/REQUIREMENTS.md:1-4`):
```markdown
# Requirements: SoniScope — 上线前代码审计里程碑

**Defined:** 2026-07-04
**Core Value:** 在正式上线前,拿到一份可信、有证据、分级明确的审计报告,...
```
→ CHARTER.md 照此:`# 审计章程: SoniScope — 上线前代码审计` + `**Defined:** 日期` + `**基线:** 全 SHA`(D-02 要求全 SHA 只在开头声明一次)。

**ID 体系 pattern**(`.planning/REQUIREMENTS.md:12-16`)——`PREFIX-NN` 加粗、中文正文 + 英文 ID:
```markdown
- [ ] **CHARTER-01**: 审计基线钉住当前 HEAD SHA,报告中所有证据以 `path:line @ SHA` 形式引用
- [ ] **CHARTER-02**: 定义项目化五级严重度体系(CRITICAL/HIGH/MEDIUM/LOW/INFO)...
```
→ 新 ID 前缀避开已占用的 `CONTRACT-NN`(需求 ID):发现用 `F-<维度短码>-NN`、假设用 `HYP-NN`、Do-NOT-fix 用 `DNF-NN`(RESEARCH.md 已论证撞名风险,`01-RESEARCH.md:227`)。

**零 diff 规则措辞 pattern**(`.planning/ROADMAP.md:5`):
```markdown
全程零 diff:apps/、scripts/、docs/ 相对钉住的 SHA 不允许任何改动。
```

**排除项表格 pattern**(`.planning/REQUIREMENTS.md:58-64`,Out of Scope 两列表——排除清单章节直接套用):
```markdown
| Feature | Reason |
|---------|--------|
| 逐行审计 vendored `docs/example/start-fc-main/`(29MB, 1003 文件) | 非项目代码;其存在本身作为一条发现,并从所有扫描中排除 |
| 数值化质量评分(如 "7.2/10") | 不可证伪,引发对数字而非发现的争论 |
| 小时级工作量估计 | 假精确;统一用 S/M/L/XL 分档 |
```
→ D-05 九条排除路径 + D-07 穿透例外用同款两列(或三列加"存在级问题处置")表。

**基线声明区块**——直接复用 RESEARCH.md 已验证模板(`01-RESEARCH.md:347-356`,全部字段值已本地 git 核实):
```markdown
## 审计基线

- **基线 commit:** `5927f362785d44b085a791ca387732991012ce5a`(下文简写 `5927f36`)
- **分支:** `ralph/soniscope-mvp-claude`(main 落后 53 提交且无独立提交,审计对象即本分支 tip)
- **钉定时工作树状态:** 干净;docs/ 权威文档迁移(...)已随提交入库
- **证据格式:** `path:line @ 5927f36`;多行 `path:10-25 @ 5927f36`;证据一律提取自 `git show 5927f36:<path>`
- **零 diff 验证:** `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出必须为空;Phase 2–5 每阶段收尾执行并记录结果
- **无例外协议:** 任何发现(含 CRITICAL...)一律只进台账并标 BLOCKER;...云端操作(删凭证、改环境变量等)绝不由审计者执行
```

**页脚 pattern**(`.planning/REQUIREMENTS.md:101-103`):
```markdown
---
*Requirements defined: 2026-07-04*
*Last updated: 2026-07-04 after roadmap creation (traceability mapped)*
```

---

### `.planning/audit/HYPOTHESES.md` (假设台账,CONCERNS.md 转写)

**Analog:** `.planning/codebase/CONCERNS.md`——既是结构范本又是唯一数据源(30 条线索)

**条目字段布局 pattern**(`.planning/codebase/CONCERNS.md:54-58`,加粗标题 + 固定顺序 bullet 字段):
```markdown
**Committed presigned OSS URL with STS token:**
- Risk: `scripts/test_asr.py` embeds `DEFAULT_FILE_LINK`, a signed OSS GET URL ... (line ~80). ...
- Files: `scripts/test_asr.py`
- Current mitigation: Token is short-lived STS, single-object, already expired; ...
- Recommendations: Replace `DEFAULT_FILE_LINK` with a placeholder ...
```
→ HYP 条目沿用"加粗/`###` 标题 + 固定字段 bullet"形态,字段改为:`- **来源:** CONCERNS.md §节名 / 条目标题`、`- **假设:** ...`、`- **待验证维度:** CON|CODE|TOOL|DOC|TEST`、`- **状态:** 未验证`(Phase 4 回填 证实/证伪/细化)。

**显式"无发现"记录 pattern**(`.planning/codebase/CONCERNS.md:48-50`,Known Bugs 节)——喂 RPT-08 的负向记录先例:
```markdown
## Known Bugs

**None detected in application code.** No TODO/FIXME/HACK markers exist in `apps/` source ...
```
→ HYPOTHESES.md 须为 Known Bugs 节保留一条显式"已检查,无已知 bug 线索"记录(RESEARCH.md 明确要求,`01-RESEARCH.md:297`)。

**计数对账 pattern**(`.planning/REQUIREMENTS.md:96-99`,Coverage 核对——防 Pitfall 4 断链):
```markdown
**Coverage:**
- v1 requirements: 23 total(原统计 "20" 有误,实际计数 ... = 23,已修正)
- Mapped to phases: 23
- Unmapped: 0 ✓
```
→ HYPOTHESES.md 头部照此给转换对账:`30 条 CONCERNS 线索 = N 条 DNF 预录入 + M 条 HYP + 1 条显式无发现记录`,总数必须等于 30。

---

### `.planning/audit/DO-NOT-FIX.md` (RPT-05 登记表初稿)

**Analog:** `.planning/REQUIREMENTS.md:58-64` Out of Scope 表(表格形态)+ CONCERNS.md "by design" 条目(内容来源)

**内容来源条目**(D-08 点名 3 条 + 建议同类 1 条,均在 CONCERNS.md 有原文可引):
- `whisper-local` 桩:`.planning/codebase/CONCERNS.md:31-34`("Intentional per AGENTS.md red line ... do not "fix" without a scope decision")
- `issue-cedential` 拼写域名:`.planning/codebase/CONCERNS.md:98-102`("Any well-meaning "typo fix" ... breaks the miniprogram")
- handler.py mypy 豁免:`.planning/codebase/CONCERNS.md:110-114`(pyproject.toml 已注释缘由)
- 小程序接收原始 STS 秘密(by design):`.planning/codebase/CONCERNS.md:72-75` [规划需确认是否入 DNF,见 RESEARCH.md A3]

**标注措辞** 取 REQUIREMENTS.md RPT-05 原文(`.planning/REQUIREMENTS.md:39`):
```markdown
标注 `⚠ intentional — do not "fix"`
```
→ 每条 DNF-NN 须含:标注、CONCERNS.md 来源引用、`path:line @ 5927f36` 证据(从 `git show` 取,不读工作树)。

---

### `.planning/audit/findings/*.md` × 5 (发现台账骨架)

**Analog:** RESEARCH.md Pattern 3 schema(`01-RESEARCH.md:208-227`,规划的权威 schema)+ CONCERNS.md 条目布局(仓库既有形态佐证)

Phase 1 只建 5 个文件的**表头 + 1 条 schema 示例**,不写真实发现。每文件对应一个维度短码(CON/CODE/TOOL/DOC/TEST),分文件的理由是 Phase 2/3 并行写入防冲突(`01-RESEARCH.md:166`)。

**发现条目 schema**(直接复制 `01-RESEARCH.md:208-220`,九字段固定顺序):
```markdown
### F-CON-01: <一行标题>

- **维度:** 契约一致性 (CON)
- **严重度:** HIGH — 影响:...;可能性:...
- **证据:** `apps/fc/shared/fc_shared/sts.py:95-102 @ 5927f36`
  > (引用的代码片段,从 git show 提取)
- **修复建议:** <一段>
- **工作量:** M(同组件多文件)
- **关联发现:** F-CODE-03;关联线索: HYP-07
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft | calibrated(Phase 5 校准后)
```

**严重度理由一行式** 与 CONCERNS.md 的 Risk/Impact 单行叙述同风格(如 `.planning/codebase/CONCERNS.md:22`:"Hashing multi-MB audio ... can freeze the UI on low-end devices")——定性场景语言,禁止数值评分。

---

### `.planning/STATE.md` (修改:清除过时 blocker)

**Analog:** 自身既有结构。唯一改动点是 Blockers/Concerns 节的过时条目(`.planning/STATE.md:75-77`):
```markdown
### Blockers/Concerns

- [Phase 1] Dirty-tree 决定阻塞:3 份 docs 已删除但未提交,...
```
→ 该 blocker 已被 CONTEXT.md 与 RESEARCH.md 双重核实为过时(工作树干净、删除已入库),规划应安排移除或改写为已解除记录。`.planning/STATE.md` 不在零 diff 保护区,修改合法(`01-RESEARCH.md:326` 明确区分)。同时按 GSD 惯例更新 frontmatter(`.planning/STATE.md:1-18`)的 `last_updated`/`stopped_at` 等字段由执行流程处理。

## Shared Patterns

### 语言与术语惯例
**Source:** 全部 `.planning/` 文档 + CLAUDE.md 约定(RPT-09 已锁定)
**Apply to:** 所有 8 个新文件
中文正文 + 英文 ID/术语(CRITICAL、HIGH、`F-CON-01`、`path:line @ SHA`)。代码路径、命令、SHA 一律反引号包裹。参见 `.planning/REQUIREMENTS.md:13`、`.planning/ROADMAP.md:28-32` 的混排风格。

### 头部元数据 + 页脚斜体戳
**Source:** `.planning/REQUIREMENTS.md:1-4, 101-103`;`.planning/codebase/CONCERNS.md:1-3, 187-189`
**Apply to:** 所有 8 个新文件
```markdown
# <标题>

**<Defined|Analysis Date>:** 2026-07-04
...
---
*<文档名>: 2026-07-04*
```

### 证据引用格式(结构性免疫 HEAD 推进)
**Source:** D-02 + RESEARCH.md Pattern 2(`01-RESEARCH.md:192-202`,三条命令已本仓库实测)
**Apply to:** CHARTER.md 方法章节;DNF/HYP 条目中一切 file:line 引用
```bash
git show 5927f36:apps/miniprogram/config.js | sed -n '1,30p'   # 按基线读文件
git grep -n 'fragment_id' 5927f36 -- apps/                      # 按基线检索
git diff --stat 5927f36 -- apps/ scripts/ docs/                 # 零 diff(期望空输出)
```
证据一律出自 `git show 5927f36:<path>`,不读工作树(Pitfall 5 对策)。

### 秘密类证据"只引位置不引值"
**Source:** RESEARCH.md Security Domain(`01-RESEARCH.md:452`)+ CONCERNS.md 先例条目(`.planning/codebase/CONCERNS.md:54-58` 描述模式但未复制完整签名值)
**Apply to:** CHARTER.md 秘密扫描章节、HYPOTHESES.md、DNF 条目
引用秘密类证据只写 `path:line @ SHA` + 模式名(如 `OSSAccessKeyId=TMP.*`),**绝不复制值本体**,哪怕已过期。

### 计数对账核验
**Source:** `.planning/REQUIREMENTS.md:96-99`(Coverage 核对块,含"原统计有误已修正"的先例)
**Apply to:** HYPOTHESES.md 头部(30 条分流对账)、findings/ 各文件可选
每个台账文档头部给出显式计数等式,机械可验(RESEARCH.md 验证命令:`grep -c '^### HYP-' ...`)。

### 每计划收尾零 diff 验证
**Source:** D-03 + `01-RESEARCH.md:424`(`test -z "$(git diff --stat 5927f36 -- apps/ scripts/ docs/)"`)
**Apply to:** 本阶段每个 plan 的 verification 步骤
所有 plan 收尾跑一次零 diff 命令并记录空输出。

## No Analog Found

无——本阶段全部产物均为 Markdown 文档,`.planning/` 内既有文档覆盖全部结构需求;发现记录 schema 虽无既有实例,但 RESEARCH.md Pattern 3 已给出完整可复制模板(且经与 CHARTER-05 字段清单逐项对齐)。

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| *(none)* | | | |

## Metadata

**Analog search scope:** `.planning/`(REQUIREMENTS.md、ROADMAP.md、STATE.md、codebase/CONCERNS.md)、`01-RESEARCH.md` 内置模板。未搜索 `apps/`/`scripts/`/`docs/`——本阶段不产出代码,且业务区文件与文档结构 pattern 无关。
**Files scanned:** 6(REQUIREMENTS.md、ROADMAP.md、STATE.md、CONCERNS.md、01-CONTEXT.md、01-RESEARCH.md)
**Pattern extraction date:** 2026-07-04
