# Phase 1: 审计章程与基线 - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

在任何证据收集开始前,定稿审计的全部标尺与边界:审计基线 SHA 与引用格式、五级严重度体系、S/M/L/XL 工作量分档、统一发现记录 schema、扫描排除清单、范围与方法声明,以及将 `.planning/codebase/CONCERNS.md` 全部线索转为待验证假设清单。本阶段只产出规则文档,不收集任何审计证据、不碰任何业务代码。

**关键事实更新(讨论中核实):** ROADMAP/STATE 记录的 "dirty-tree 阻塞"(3 份 docs 已删未提交)已自行解除——当前工作树干净,旧路径 `docs/PRD_v1.md`、`docs/tech-spec.md`、`docs/deployment-guide.md` 的删除已随提交入库,内容迁至 `docs/v1.0.0 prd/` 与 `docs/runbook/`。CHARTER-01 的 dirty-tree 处置决定简化为"记录此事实即可";AGENTS.md 仍引用旧路径一事留给 Phase 4 审计。

</domain>

<decisions>
## Implementation Decisions

### 基线钉定与 SHA 引用策略
- **D-01:** 审计基线钉当前 HEAD `5927f36`(全 SHA `5927f362785d44b085a791ca387732991012ce5a`,分支 `ralph/soniscope-mvp-claude`)。全程 5 个阶段所有证据统一引用这一个 SHA;后续 `.planning/` 提交推进 HEAD 不影响行号有效性(受零 diff 规则保护)。main 落后 53 提交且无独立提交,审计对象即当前分支 tip。
- **D-02:** 证据引用格式:`path:line @ 5927f36`,多行证据用 `path:10-25 @ 5927f36`。章程文档开头声明一次完整 SHA,正文统一用 7 位短 SHA。
- **D-03:** 零 diff 机械验证:章程中写定验证命令(`git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空),Phase 2–5 每阶段收尾执行一次并记录结果,发现污染可定位到阶段。
- **D-04:** 基线**无例外协议**(用户明确,比推荐项更严格):任何发现(含 CRITICAL,如泄露的有效凭证)一律只进台账并标 BLOCKER,不中断审计、不重钉基线;**云端操作(如账号中删凭证、改环境变量)也绝不由审计者动手**,同样只进台账。

### 扫描排除清单边界
- **D-05:** 扫描排除清单共五项:`docs/example/start-fc-main/`(vendored,29MB)、`scripts/ralph/`(agent 元工具)、`.claude/`+`.cursor/`+`.codex/`+`.agents/`(四套 AI 工具目录)、`openspec/`(工作流状态)、`build/`+`tests/audio/`(产物与二进制;fixture manifest/描述文件仍纳入文档一致性审计)。
- **D-06:** AUDIT-02 的 scripts/ 审计范围相应缩窄为:`scripts/test_asr.py`、`scripts/fetch_test_fixtures.py`、`scripts/gen_worker_config.sh`(即 scripts/ 减去 ralph/)。
- **D-07:** 秘密/凭证扫描**穿透所有排除目录**:对全仓库(含 vendored、四套工具目录、scripts/ralph/)跑秘密模式扫描(LTAI 长期 AK、`OSSAccessKeyId=` 签名 URL、appsecret 等),命中后人工核实才进台账。
- **D-08:** CONCERNS.md 中已标注"故意设计/不要修"的条目(`whisper-local` 桩、`issue-cedential` 域名、handler mypy 豁免等)**直接预录入 RPT-05 Do-NOT-fix 登记表初稿**,不再转为待验证假设、后续阶段不再花力气验证。其余 CONCERNS.md 线索照常转为未验证假设清单。
- **D-09:** 被排除目录的"存在级"问题照常进台账(如 vendored 仓库膨胀、四套工具目录漂移、scripts/ralph/ 在仓,严重度预计 LOW/INFO),但不逐文件审计。

### Claude's Discretion
用户未选择讨论以下两项,由研究/规划阶段按需求文档(CHARTER-02、CHARTER-05)常规处理:
- **严重度定标锚点**:CRITICAL~INFO 五级的 SoniScope 场景锚定示例、顺带安全发现是否升级等细节——遵循 CHARTER-02 的"影响×可能性"格式要求即可。
- **发现台账形态与位置**:台账文件格式(Markdown/结构化)、ID 规则、存放位置——唯一硬约束:零 diff 规则下台账与报告**不得写入 apps/、scripts/、docs/**,应放在 `.planning/` 或其他不受零 diff 约束的位置。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与路线图(定义本阶段验收)
- `.planning/REQUIREMENTS.md` — CHARTER-01~05 的完整需求文本与 Out of Scope 表(禁止小时估计、禁止数值评分等)
- `.planning/ROADMAP.md` — Phase 1 目标与 5 条成功判据;零 diff 总规则声明

### 假设清单的唯一来源
- `.planning/codebase/CONCERNS.md` — 全部待转换线索(tech debt、安全、脆弱区、覆盖缺口);D-08 决定其中"故意设计"条目直接进 Do-NOT-fix 表
- `.planning/codebase/STRUCTURE.md` — 目录用途地图,排除清单(D-05)的路径依据

### 项目权威文档(章程范围声明需引用其现状)
- `docs/v1.0.0 prd/PRD_v1.md` — 产品范围权威(已从 docs/PRD_v1.md 迁移)
- `docs/v1.0.0 prd/tech-spec.md` — 技术细节权威(已从 docs/tech-spec.md 迁移)
- `AGENTS.md` — AI 开发红线;注意其仍引用已迁移的旧文档路径(Phase 4 审计对象,章程只记事实)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.planning/codebase/` 七份地图(2026-07-04 生成)——章程的范围声明与排除清单可直接引用其目录/组件盘点,无需重新勘察
- `git diff --stat 5927f36 -- apps/ scripts/ docs/` — 零 diff 验证的现成机械手段(D-03)

### Established Patterns
- 仓库注释与文档习惯为中文正文 + 英文术语/ID(RPT-09 已锁定报告同样风格),章程文档应保持一致
- REQUIREMENTS.md 已用 `CHARTER-NN`/`CONTRACT-NN` 式 ID——发现 ID 规则设计时宜与此风格协调(具体留给规划)

### Integration Points
- 章程产物是 Phase 2–5 所有审计工作的输入:严重度体系、schema、排除清单在证据收集开始前必须定稿(ROADMAP Phase 1 目标)
- CONCERNS.md → 假设清单的转换结果是 Phase 4(AUDIT-05)关闭线索的工作底稿
- Do-NOT-fix 预录入条目(D-08)直接流入 Phase 5 的 RPT-05 登记表

</code_context>

<specifics>
## Specific Ideas

- 用户对基线例外的态度非常明确:"云端操作绝不自己动手,也只是进入台账"——章程措辞应保留这种绝对性(无例外、无自由裁量)。
- 秘密扫描穿透规则源于 `scripts/test_asr.py` 曾提交过期预签名 URL 的先例——章程可引用此例说明为何穿透。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-审计章程与基线*
*Context gathered: 2026-07-04*
