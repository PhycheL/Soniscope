# Phase 3: 组件与工具链深潜 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 3-组件与工具链深潜
**Areas discussed:** 深潜覆盖策略与完成判定, 线索生成工具集边界, HYP 假设与"MVP 可接受"自评的处理, D14 重复实现的债务判定口径

---

## 深潜覆盖策略与完成判定

| Option | Description | Selected |
|--------|-------------|----------|
| 全模块普审 + 线索处深挖 | 每模块至少过一遍并记覆盖台账,HYP/D14 命中区域逐行深挖 | ✓ |
| 风险驱动:仅从线索出发 | 只审 14 条 HYP + 6 条 D14 涉及的模块与周边 | |
| 全量均匀逐行深审 | 所有模块同等深度逐行 | |

**User's choice:** 全模块普审 + 线索处深挖

| Option | Description | Selected |
|--------|-------------|----------|
| 独立 COVERAGE.md 逐模块登记 | `.planning/audit/` 下新建覆盖台账,每模块一行 | ✓ |
| 覆盖记录写在发现台账附录 | findings 文件尾部加覆盖节 | |
| 不建台账,以计划任务清单为凭 | 靠 PLAN.md 任务销号证明覆盖 | |

**User's choice:** 独立 COVERAGE.md 逐模块登记

| Option | Description | Selected |
|--------|-------------|----------|
| 归 TOOL 维度,与 fc_deploy 同台账 | 按功能定维度,发现入 findings/toolchain.md | ✓ |
| 归 CODE 维度,按物理位置 | apps/worker 内一律入 findings/code.md | |
| 两维度都覆盖,发现就近归档 | 不预先划归属 | |

**User's choice:** Worker 包内真云验证/E2E 模块归 TOOL 维度

| Option | Description | Selected |
|--------|-------------|----------|
| 固定关注面清单,锤定 SoniScope 失效模式 | 定稿普审检查面清单,每面对应 CHARTER 严重度锚点 | ✓ |
| 轻清单:只锁 3-4 个高价值面 | 只定最致命几面,其余靠直觉 | |
| 不清单化,审计者自由裁量 | 只规定产出 schema | |

**User's choice:** 固定关注面清单

---

## 线索生成工具集边界

| Option | Description | Selected |
|--------|-------------|----------|
| 现有门禁 + 临时扩展分析器 | ruff 扩大规则集、vulture、临时 ESLint;全部临时运行零仓库写入 | ✓ |
| 仅现有门禁输出作线索 | 只用 make typecheck/lint 现有报告 | |
| 大满贯:再加安全扫描器 | 额外上 bandit/semgrep | |

**User's choice:** 现有门禁 + 临时扩展分析器

| Option | Description | Selected |
|--------|-------------|----------|
| 归本阶段,随 TOOL 维度执行 | 与 HYP-07 核实同批,命令+命中清单存档 | ✓ |
| 留给 Phase 4 | 与 AUDIT-05 假设关闭一起做 | |
| 独立小任务,不绑维度 | 单独计划任务执行 | |

**User's choice:** D-07 秘密扫描归本阶段执行

| Option | Description | Selected |
|--------|-------------|----------|
| 扫描档案 + 逐命中三态销号 | 命令/版本/原始输出存 scans/,命中标三态 | ✓ |
| 只存命令与命中摘要 | 不留原始输出全文 | |
| 不存档,只在发现里引用 | 工具输出用完即弃 | |

**User's choice:** 扫描档案 + 逐命中三态销号

| Option | Description | Selected |
|--------|-------------|----------|
| 本地只读目标可执行,云 IO 目标纯静审 | make typecheck/lint/test 可执行作证据 | (首答选此,用户主动重答推翻) |
| 全静态,一律不执行 | 连 make test 都不跑,只读源码 | ✓ |
| 含云目标 dry-run/探活 | 部署目标做只读探活 | |

**User's choice:** 全静态,一律不执行(用户要求重新回答后改选,明确意志)

| Option | Description | Selected |
|--------|-------------|----------|
| 仪器可跑、对象不执行 | 分析器作审计仪器可调用;被审对象(make/fc_deploy/scripts)一律不执行 | ✓ |
| 彻底全静态:分析器也不跑 | 推翻扩展分析器决定,线索全靠人工阅读 | |

**User's choice:** 仪器可跑、对象不执行(衔接口径确认)

---

## HYP 假设与"MVP 可接受"自评的处理

| Option | Description | Selected |
|--------|-------------|----------|
| 本阶段直接回填 HYPOTHESES.md | 验证到哪条就地回填,Phase 4 只补漏与总对账 | ✓ |
| 只留证据,Phase 4 统一回填 | 本阶段 HYPOTHESES.md 不动 | |

**User's choice:** 本阶段直接回填

| Option | Description | Selected |
|--------|-------------|----------|
| 本阶段就裁:事实+判断一次到位 | 核实事实后直接评"可接受"是否成立(上线语境) | ✓ |
| 只核事实,判断留 Phase 5 校准 | 价值判断留汇总阶段 | |
| 一律入发现,自评仅作注脚 | 四条全部立发现 | |

**User's choice:** 本阶段就裁

| Option | Description | Selected |
|--------|-------------|----------|
| 记录并移交,不下判定 | 顺带证据记入移交清单交 Phase 4 | ✓ |
| 顺手直接回填该 HYP | 跨维度也回填 | |
| 严格边界,视而不见 | 只审本维度 | |

**User's choice:** 记录并移交

| Option | Description | Selected |
|--------|-------------|----------|
| 不立发现,回填 HYP + 覆盖台账留痕 | 证伪/可接受成立不占发现 ID | ✓ |
| 一律立发现(证伪→INFO) | 仿 Phase 2 D-10 全立 | |
| 只有可接受成立立 INFO/优点,证伪不立 | 两类区分处理 | |

**User's choice:** 不立发现,回填 HYP + 覆盖台账留痕

---

## D14 重复实现的债务判定口径

| Option | Description | Selected |
|--------|-------------|----------|
| 三要素框架:必要性×兜底×漂移后果 | 逐条评结构必要性/兜底机制/漂移后果,写进发现理由 | ✓ |
| 一律算债务,只分严重度 | 6 条全立债务发现 | |
| 严口径:无兜底且后果实才算 | 只有裸奔且后果真实的才立 | |

**User's choice:** 三要素框架

| Option | Description | Selected |
|--------|-------------|----------|
| 锚漂移后果,不锚重复本身 | 主链路数据可见性参照 CHARTER 主链锚点;维护成本类默认 LOW~MEDIUM | ✓ |
| 按落点数量递进 | 落点越多定级越高 | |
| 统一保守定 LOW,留 Phase 5 校准 | 一律 LOW | |

**User's choice:** 锚漂移后果

| Option | Description | Selected |
|--------|-------------|----------|
| 逐条独立,聚类留给 Phase 5 | 每条单独判定单独立发现,关联字段串联 | ✓ |
| 同根因允许合并立发现 | 如 D14-2+D14-3 合一条 | |

**User's choice:** 逐条独立

| Option | Description | Selected |
|--------|-------------|----------|
| 允许 scratchpad 微基准,仿 Phase 2 D-06 | 基线导出仓库外临时区,node 计时作辅助证据 | ✓ |
| 纯静态论证,标置信度 | 只做静态分析,显式标未实测 | |
| 细化移交:标"需真机实测" | 卡顿断言不在本里程碑定论 | |

**User's choice:** 允许 scratchpad 微基准

---

## Claude's Discretion

- 普审关注面清单的具体条目与分面粒度
- 扩展分析器的具体规则集与版本参数
- COVERAGE.md 与 scans/ 目录的内部排版组织
- 发现 ID 前缀沿用 CHARTER 既定规则

## Deferred Ideas

None — discussion stayed within phase scope.
