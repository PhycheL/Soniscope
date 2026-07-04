# Phase 1: 审计章程与基线 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 1-审计章程与基线
**Areas discussed:** 基线钉定与 SHA 引用策略, 扫描排除清单边界

灰色地带初选(multiSelect,4 项候选):用户选择「基线钉定与 SHA 引用策略」「扫描排除清单边界」;未选「严重度定标锚点」「发现台账的形态与位置」(归 Claude's Discretion)。

---

## 基线钉定与 SHA 引用策略

### Q1: 审计基线钉哪个 SHA?

| Option | Description | Selected |
|--------|-------------|----------|
| 钉当前 HEAD 5927f36 (Recommended) | 工作树干净、三份删除文档已入库,此刻就是干净基线;全程统一引用 | ✓ |
| 钉 Phase 1 章程定稿时的 HEAD | 基线包含章程本身,但 SHA 需二次回填 | |
| 打 git tag 钉基线 | tag 名代替裸 SHA,可读性更好 | |

**User's choice:** 钉当前 HEAD 5927f36

### Q2: 证据引用的具体格式?

| Option | Description | Selected |
|--------|-------------|----------|
| 短 SHA + 支持行范围 (Recommended) | `path:line @ 5927f36`,多行 `path:10-25 @ 5927f36`;章程声明一次全 SHA | ✓ |
| 省略 SHA 只写 path:line | 全局声明 SHA,证据更简洁,但单条传播时丢基线信息 | |
| 每条证据附完整可执行命令 | `git show` 式一键复现,最严谨但最啰嗦 | |

**User's choice:** 短 SHA + 支持行范围

### Q3: 零 diff 规则如何机械验证、何时验证?

| Option | Description | Selected |
|--------|-------------|----------|
| 每阶段结束验证一次 (Recommended) | 章程写定验证命令,Phase 2-5 每阶段收尾执行并记录 | ✓ |
| 仅 Phase 5 最终验证 | 成本最低,但中途污染发现太晚 | |
| git hook 强制拦截 | 最硬但侵入性强 | |

**User's choice:** 每阶段结束验证一次

### Q4: 审计中途发现紧急问题的基线例外协议?

| Option | Description | Selected |
|--------|-------------|----------|
| 无例外,只升级不动手 (Recommended) | 任何发现只进台账标 BLOCKER,不中断审计 | ✓(强化版) |
| 允许修复后重钉基线 | 灵活但成本高,污染"不边审边改"原则 | (首答误选,用户要求重答) |
| hotfix 分支隔离 | 基线完整但双分支同步负担 | |

**User's choice:** 无例外(用户重答并强化):任何发现(含 CRITICAL)一律只进台账,不中断审计;**云端操作也绝不自己动手,同样只进台账**。
**Notes:** 用户首次误选"允许修复后重钉基线",主动中断要求重答;最终答案比推荐项更严格,明确云端操作也在禁区。

---

## 扫描排除清单边界

### Q1: 除 vendored docs/example/start-fc-main/ 外,哪些也列入排除清单?(多选)

| Option | Description | Selected |
|--------|-------------|----------|
| scripts/ralph/ agent 元工具 | 非产品代码;AUDIT-02 范围缩为 scripts/ 减 ralph/ | ✓ |
| .claude/.cursor/.codex/.agents 四套 AI 工具目录 | 脚手架副本,漂移问题可作存在级发现 | ✓ |
| openspec/ 工作流状态 | 开发过程制品,非产品/文档权威链 | ✓ |
| build/、tests/audio/ 二进制与产物 | 仅 manifest/描述文件纳入文档一致性审计 | ✓ |

**User's choice:** 全部四项排除

### Q2: 秘密/凭证扫描是否穿透排除清单?

| Option | Description | Selected |
|--------|-------------|----------|
| 穿透所有排除目录 (Recommended) | 全仓库跑秘密模式扫描,命中才人工核实 | ✓ |
| 仅穿透自有代码,vendored 不扫 | 官方样板不含本项目凭证,减噪 | |
| 不穿透,排除即彻底排除 | 规则最简单,但有漏凭证风险 | |

**User's choice:** 穿透所有排除目录
**Notes:** 用户中断要求重答此问,重答后仍确认同一选项。

### Q3: CONCERNS.md 已标注"故意设计"的条目转假设清单时怎么处理?

| Option | Description | Selected |
|--------|-------------|----------|
| 同样转假设,验证后入 Do-NOT-fix (Recommended) | 与"线索是假设不是答案"原则一致 | |
| 直接预录入 Do-NOT-fix 表 | 已有充分文档佐证,省力,后续不再验证 | ✓ |

**User's choice:** 直接预录入 Do-NOT-fix 表

### Q4: 被排除目录的"存在级"问题是否仍进台账?

| Option | Description | Selected |
|--------|-------------|----------|
| 是,存在级发现照常进台账 (Recommended) | vendored 膨胀、四套工具漂移等各记一条(LOW/INFO) | ✓ |
| 否,排除目录零发现 | 仅在范围声明列出排除项 | |

**User's choice:** 是,存在级发现照常进台账

---

## Claude's Discretion

- **严重度定标锚点** — 未选讨论;遵循 CHARTER-02 的"影响×可能性"格式,细节由规划/研究定
- **发现台账形态与位置** — 未选讨论;唯一硬约束:不得写入 apps/、scripts/、docs/(零 diff)

## Deferred Ideas

None — discussion stayed within phase scope.
