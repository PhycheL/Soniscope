# Phase 4: 文档配置与测试审计 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 4-文档配置与测试审计
**Areas discussed:** 测试执行与覆盖率口径, DOC 审计范围与核对方式, 测试缺口定级与脆弱区映射, HYP 关闭与总对账形态

---

## 测试执行与覆盖率口径

### Q1: 被审测试套件本身能不能执行?

| Option | Description | Selected |
|--------|-------------|----------|
| 分级口径(推荐) | 离线门禁 make test 可作为审计仪器执行,结果作证据;真云目标 test-*/verify-* 继承 Phase 3 绝不执行 | ✓ |
| 全静态延续 | 完全继承 Phase 3 D-08,一律不执行,含 make test | |
| 离线可跑+单条真云探活 | 额外允许最小真云存活探针 | |

### Q2: make test 在什么环境里跑?

| Option | Description | Selected |
|--------|-------------|----------|
| 工作区直跑+前后零 diff 验证(推荐) | 成本最低,前后两次零 diff 验证控风险 | |
| git worktree 基线检出专区跑 | 结构性保证跑的是基线且主工作区零触碰,代价是额外 uv 环境 | ✓ |
| 你决定 | | |

**Notes:** 用户选择了比推荐更强的结构性保证方案,延续 Phase 2/3 先例精神。

### Q3: Python 侧覆盖率怎么测量?

| Option | Description | Selected |
|--------|-------------|----------|
| 临时注入 pytest-cov(推荐) | uv run --with pytest-cov 命令行临时注入,零配置写入 | ✓ |
| 只做静态映射 | 不跑运行时覆盖率 | |
| 双轨:实测数字+静态映射 | | |

### Q4: JS 侧覆盖率怎么处理?

| Option | Description | Selected |
|--------|-------------|----------|
| 也实测(推荐) | node --test --experimental-test-coverage 直跑,标注 experimental 来源 | ✓ |
| JS 侧只静态映射 | | |
| 你决定 | | |

---

## DOC 审计范围与核对方式

### Q1: 范围清单怎么划?

| Option | Description | Selected |
|--------|-------------|----------|
| 全量分层(推荐) | 权威链深核 + 其余普审 + 每份入覆盖台账 | ✓ |
| 权威链+线索驱动 | 只深核四大件 + HYP 点名文档 | |
| 你决定 | | |

### Q2: 目标态设计文档怎么处理?

| Option | Description | Selected |
|--------|-------------|----------|
| 只审引用与自洽(推荐) | 不做设计 vs 实态对照(尊重章程排除项),审死链与自相矛盾 | ✓ |
| 完全跳过 | | |
| 全量对照 | 违反章程排除项,不推荐 | |

### Q3: 逐声明深核怎么做才可机械验收?

| Option | Description | Selected |
|--------|-------------|----------|
| 可核声明清单式(推荐) | 抽取可对照声明成清单,agree/drift/dead-ref/无法静态核实 四态销号 | ✓ |
| 通读+发现制 | 章节粒度台账,声明级遗漏不可证 | |
| 你决定 | | |

### Q4: 配置一侧边界怎么定?

| Option | Description | Selected |
|--------|-------------|----------|
| 小程序三份全入(推荐) | config.js 深核 + project.config.json/app.json 普审;Python 侧配置 Phase 3 已覆盖不重审 | ✓ |
| 只审 config.js | | |
| 你决定 | | |

---

## 测试缺口定级与脆弱区映射

### Q1: 缺口严重度"参照脆弱区定级"怎么系统化?

| Option | Description | Selected |
|--------|-------------|----------|
| 反向映射法(推荐) | 22 条 F-* 发现 + 矩阵关键行编成"应重点覆盖面"清单逐条查测试兜底 | ✓ |
| 正向盘点法 | 按测试套件结构逐模块盘点 | |
| 双向 | | |

### Q2: 测试质量审哪些面?

| Option | Description | Selected |
|--------|-------------|----------|
| 清单化普审面(推荐) | 仿 Phase 3 D-04 固定检查面清单,每测试模块逐面过 | ✓ |
| 线索驱动深挖 | 只挖 HYP 点名处 | |
| 你决定 | | |

### Q3: make test 门禁完整性用什么判据?

| Option | Description | Selected |
|--------|-------------|----------|
| 三方对照(推荐) | 声称 × 静态配置 × 实跑观测,任一不一致即缺口候选 | ✓ |
| 静态+声称两方 | 不用实跑作判据 | |
| 你决定 | | |

### Q4: 缺口发现按什么粒度立条?

| Option | Description | Selected |
|--------|-------------|----------|
| 按缺口面聚合(推荐) | 一面一条,证据字段列模块清单,关联链 F-* | ✓ |
| 逐模块立条 | 发现数量膨胀 | |
| 你决定 | | |

---

## HYP 关闭与总对账形态

### Q1: Phase 3 已回填 14 条要不要复核?

| Option | Description | Selected |
|--------|-------------|----------|
| 机械对账不复判(推荐) | 只验形式合规(状态/证据/去向闭环),不重审判断 | ✓ |
| 抽查复核 | | |
| 全量复核 | | |

### Q2: "证据已在别处"条目(HYP-13/HYP-11)要不要重新采证?

| Option | Description | Selected |
|--------|-------------|----------|
| 引用既有产物回填(推荐) | HYP-13 引 CONTRACT-MATRIX 行号证据;HYP-11 以"细化:范围外"关闭引章程条款 | ✓ |
| 重新独立采证 | | |
| 你决定 | | |

### Q3: 25 条总对账验收产物长什么样?

| Option | Description | Selected |
|--------|-------------|----------|
| HYPOTHESES.md 尾部对账章节(推荐) | 状态分布表 + 机械验证命令 + 29 条溯源闭环声明 | ✓ |
| 独立对账文件 | | |
| 你决定 | | |

### Q4: 本阶段结构化底稿放哪?

| Option | Description | Selected |
|--------|-------------|----------|
| 独立新文件,封版产物不动(推荐) | 新建 DOC-CLAIMS.md / TEST-AUDIT.md 类文件;COVERAGE.md 等封版产物只读 | ✓ |
| 续写 COVERAGE.md | 破坏封版状态且粒度不同 | |
| 你决定 | | |

---

## Claude's Discretion

- 质量检查面清单的具体条目与分面粒度
- DOC 声明清单的抽取粒度细节
- 底稿文件具体命名与内部排版(硬约束:逐项可销号、封版产物不动、喂 RPT-07/08)
- 覆盖率数字呈现粒度(禁阈值判断与质量评分)
- worktree 专区位置与清理时机;make test 非绿结果按 CHARTER 正常入台账

## Deferred Ideas

None — discussion stayed within phase scope.
