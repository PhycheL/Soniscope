# Roadmap: SoniScope — 上线前代码审计里程碑

## Overview

本里程碑不写功能代码,产出一份可信、有证据、分级明确的上线前审计报告。路线是先钉基线、定标尺(Phase 1),再并行收集证据——契约漂移矩阵(Phase 2)与组件/工具链深潜(Phase 3)——然后以代码实态为基准审文档配置与测试并关闭 CONCERNS.md 假设清单(Phase 4),最后单一口径汇总校准、组装报告(Phase 5)。全程零 diff:apps/、scripts/、docs/ 相对钉住的 SHA 不允许任何改动。

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: 审计章程与基线** - 钉住审计 SHA,定稿严重度体系、工作量分档、发现 schema 与范围声明 (completed 2026-07-04)
- [ ] **Phase 2: 契约抽取与漂移分析** - 三处实现的契约漂移矩阵、往返校验、分歧分类与重复逻辑普查
- [ ] **Phase 3: 组件与工具链深潜** - 三层主体代码与部署工具链的债务/脆弱区盘点,人工核实进台账
- [ ] **Phase 4: 文档配置与测试审计** - 以代码实态为基准审 docs/config/AGENTS.md 与双语言测试,关闭 CONCERNS.md 假设清单
- [ ] **Phase 5: 汇总校准与报告组装** - 去重、根因聚类、单一口径校准,产出最终审计报告

## Phase Details

### Phase 1: 审计章程与基线

**Goal**: 审计的所有标尺与边界在任何证据收集开始前定稿,后续每条发现都有统一的度量与引用基准
**Depends on**: Nothing (first phase)
**Requirements**: CHARTER-01, CHARTER-02, CHARTER-03, CHARTER-04, CHARTER-05
**Success Criteria** (what must be TRUE):

  1. 审计基线 commit SHA 已钉住并记录,dirty-tree 处置决定(3 份已删未提交文档)已成文,后续所有证据可以 `path:line @ SHA` 形式引用
  2. 项目化五级严重度体系(CRITICAL/HIGH/MEDIUM/LOW/INFO,SoniScope 场景术语 + "影响×可能性"理由格式)与 S/M/L/XL 工作量分档定稿,任何审计者可直接套用而无需再作解释
  3. 统一发现记录 schema(ID、维度、严重度+理由、file:line@SHA 证据片段、修复建议、工作量、关联发现)与扫描排除清单(含 vendored `docs/example/start-fc-main/`)定稿
  4. 范围与方法声明成文:五个审计维度、审计 SHA、明确排除项(FC 直转目标态对照、渗透测试深度)与零 diff 验收规则
  5. `.planning/codebase/CONCERNS.md` 全部线索已转为"未验证假设"清单,每条标注待验证维度,等待后续阶段证实/证伪

**Plans**: 2/2 plans complete

Plans:

- [x] 01-01-PLAN.md — 审计章程 CHARTER.md(基线/严重度/工作量/schema/排除清单/范围方法)与 findings/ 五维度台账骨架
- [x] 01-02-PLAN.md — CONCERNS.md 线索分流:DO-NOT-FIX.md 预录入 + HYPOTHESES.md 假设清单 + STATE.md 过时阻塞清理

### Phase 2: 契约抽取与漂移分析

**Goal**: 系统的核心契约(fragment_id / object key / `x-oss-meta-*` 等)在小程序、FC、Worker 三处实现的现状一致性有逐字段的证据矩阵与分歧判定
**Depends on**: Phase 1
**Requirements**: CONTRACT-01, CONTRACT-02, CONTRACT-03, CONTRACT-04
**Success Criteria** (what must be TRUE):

  1. 漂移矩阵完成:每个契约要素 × FC(`fc_shared`)/Worker(`oss_admin.py`/`poller.py`)/小程序(`utils/`)三列,每格标注 agree/diverge/absent 并附行号证据
  2. 往返校验结论在案:FC 签发的 object key 能否被 Worker `fragment_id_from_key` 解析有明确记录
  3. 每条分歧被归入良性/潜伏/活跃失配/覆盖洞四类之一,并附生产者-消费者宽严(Postel)分析
  4. 已知三处之外的契约相关跨语言重复实现(sha256、日期格式、配置解析等)普查完成,结果(含"已检查,无新发现")记录在案
  5. 若矩阵发现真实分歧,共享黄金样本跨语言契约测试(pytest + node:test 共用样本)的设计配方成文——仅设计不实现;若无真实分歧,显式记录"无需配方"

**Plans**: 1/4 plans executed

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — 矩阵骨架与组① OSS 数据面逐字段静态抽取(CONTRACT-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 02-02-PLAN.md — 组② HTTP 契约、组③ 镜像常量抽取与重复逻辑普查(CONTRACT-01/03)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 02-03-PLAN.md — 往返校验执行佐证:基线导出 harness + 样本清单销号(CONTRACT-02)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 02-04-PLAN.md — 四类分歧判定、F-CON 发现、条件配方与零 diff 收尾(CONTRACT-02/04)

### Phase 3: 组件与工具链深潜

**Goal**: 三层主体代码与部署工具链的技术债、脆弱区域全部经人工核实进入发现台账,为后续测试审计与报告提供代码实态基准
**Depends on**: Phase 1
**Requirements**: AUDIT-01, AUDIT-02
**Success Criteria** (what must be TRUE):

  1. apps/miniprogram、apps/fc、apps/worker 三层的债务与脆弱区域发现全部按统一 schema 进入台账,每条经人工在引用行核实
  2. scripts/、Makefile、fc_deploy 等部署与验证工具链的发现进入台账(含 `scripts/test_asr.py` 已提交过期预签名 URL 线索的核实结论)
  3. 台账中不存在原始 linter/工具输出直接充当发现——每条发现均附人工确认的 file:line@SHA 证据片段
  4. 跨组件契约类观察已转交 Phase 2 的漂移矩阵作为线索,未在组件维度内单独下判断

**Plans**: TBD

### Phase 4: 文档配置与测试审计

**Goal**: 文档配置以代码实态为基准的漂移、测试质量与覆盖缺口全部进入台账,CONCERNS.md 假设清单全部关闭
**Depends on**: Phase 2, Phase 3
**Requirements**: AUDIT-03, AUDIT-04, AUDIT-05
**Success Criteria** (what must be TRUE):

  1. docs/、`apps/miniprogram/config.js`、AGENTS.md 与代码实态的一致性发现进入台账(含 `issue-cedential` 拼写域名与 AGENTS.md 引用已删除文档两条线索的核实结论)
  2. pytest 与 node:test 双侧的测试质量与覆盖缺口发现进入台账(含 `make test` 门禁完整性),缺口严重度参照 Phase 2/3 发现的脆弱区域定级
  3. 覆盖率测量结果作为证据归档,仅作输入证据,未被当作质量评分写入发现
  4. CONCERNS.md 假设清单每条状态为证实/证伪/细化之一,均附新鲜 file:line@SHA 证据,无一遗留"未验证"

**Plans**: TBD

### Phase 5: 汇总校准与报告组装

**Goal**: 全部发现经单一口径校准后组装成可直接驱动修复里程碑的最终审计报告
**Depends on**: Phase 4
**Requirements**: RPT-01, RPT-02, RPT-03, RPT-04, RPT-05, RPT-06, RPT-07, RPT-08, RPT-09
**Success Criteria** (what must be TRUE):

  1. 发现台账完成去重、根因聚类与单一口径严重度校准,校准调整有记录可查;报告组装阶段不产生新判断
  2. 最终报告含一页执行摘要(审计缘由、范围、按严重度的发现计数、总体上线判定)与按严重度再按工作量排序的发现汇总表——即修复里程碑 backlog
  3. 每个发现带 BLOCKER/PRE-LAUNCH/POST-LAUNCH 上线阻断判定;修复工作包按共同修复位置分组、按影响÷工作量排序并标注工作包间依赖
  4. 报告含 "Do NOT fix" 登记表(`issue-cedential` 在用域名、`whisper-local` 桩、handler mypy 豁免等)、优点盘点章节、分维度置信声明与可追溯映射表(发现↔CONCERNS.md 线索↔需求,含"已检查,无发现"显式记录)
  5. 报告为中文正文 + 英文 ID/严重度术语,且 apps/、scripts/、docs/ 相对钉住 SHA 的零 diff 验证通过

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5(Phase 2 与 Phase 3 同属证据收集波次,均仅依赖 Phase 1,可作为并行计划执行)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 审计章程与基线 | 2/2 | Complete    | 2026-07-04 |
| 2. 契约抽取与漂移分析 | 1/4 | In Progress|  |
| 3. 组件与工具链深潜 | 0/? | Not started | - |
| 4. 文档配置与测试审计 | 0/? | Not started | - |
| 5. 汇总校准与报告组装 | 0/? | Not started | - |
