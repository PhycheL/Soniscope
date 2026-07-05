# Requirements: SoniScope — 上线前代码审计里程碑

**Defined:** 2026-07-04
**Core Value:** 在正式上线前,拿到一份可信、有证据、分级明确的审计报告,准确回答"现有代码哪里不一致、哪里有债务、上线有什么风险"。

## v1 Requirements

Requirements for this milestone's audit report. Each maps to roadmap phases.

### 审计章程与框架 (CHARTER)

- [x] **CHARTER-01**: 审计基线钉住当前 HEAD SHA,报告中所有证据以 `path:line @ SHA` 形式引用
- [x] **CHARTER-02**: 定义项目化五级严重度体系(CRITICAL/HIGH/MEDIUM/LOW/INFO),每级用 SoniScope 场景术语定义(数据丢失/静默转写失败/凭证泄漏等),每个评级附"影响×可能性"一行理由
- [x] **CHARTER-03**: 定义 S/M/L/XL 工作量分档及判定标准(S ≤单文件、M=同组件多文件、L=跨组件、XL=需独立阶段);禁止小时级精确估计
- [x] **CHARTER-04**: 报告含范围与方法声明:五个审计维度、审计 SHA、明确排除项(FC 直转目标态对照、渗透测试深度、vendored `docs/example/` 逐行审计)
- [x] **CHARTER-05**: 统一发现记录 schema(ID、维度、严重度+理由、file:line@SHA 证据片段、修复建议、工作量、关联发现)与扫描排除清单,在所有维度审计开始前定稿

### 契约一致性 (CONTRACT)

- [x] **CONTRACT-01**: fragment_id / object key / `x-oss-meta-*` 契约在 FC(`fc_shared`)、Worker(`oss_admin.py`/`poller.py`)、小程序(`utils/`)三处实现逐字段抽取为漂移矩阵(行=契约要素,列=实现,格=agree/diverge/absent + 行号)
- [x] **CONTRACT-02**: 完成往返校验(FC 签发的 object key → Worker `fragment_id_from_key` 可否解析),所有分歧按 良性/潜伏/活跃失配/覆盖洞 四类分类,含生产者-消费者宽严分析
- [x] **CONTRACT-03**: 重复逻辑普查:系统排查已知三处之外的契约相关跨语言重复实现(sha256、日期格式、配置解析等),仅限承载契约的逻辑
- [x] **CONTRACT-04**: 若矩阵发现真实分歧,产出共享黄金样本跨语言契约测试(pytest + node:test 共用样本)的设计配方 — 仅设计,不实现

### 各维度审计 (AUDIT)

- [x] **AUDIT-01**: 三层主体代码(apps/miniprogram、apps/fc、apps/worker)技术债与脆弱区域盘点;工具输出仅作线索,每条发现均经人工核实(原始 linter 输出不直接进报告)
- [x] **AUDIT-02**: scripts/、Makefile、fc_deploy 等部署与验证工具链审计
- [ ] **AUDIT-03**: docs/、`apps/miniprogram/config.js`、AGENTS.md 等文档配置与代码实态一致性审计
- [ ] **AUDIT-04**: 测试质量与覆盖缺口盘点(pytest 与 node:test 双侧,含 `make test` 门禁完整性)
- [ ] **AUDIT-05**: `.planning/codebase/CONCERNS.md` 每条已知线索被证实/证伪/细化,并附新鲜 file:line 证据(线索是假设,不是答案)

### 报告组装 (RPT)

- [ ] **RPT-01**: 一页执行摘要:审计缘由、范围、按严重度的发现计数、总体上线判定
- [ ] **RPT-02**: 发现汇总表(ID、严重度、维度、标题、工作量),按严重度再按工作量排序 — 即修复里程碑的 backlog
- [ ] **RPT-03**: 每个发现附 BLOCKER / PRE-LAUNCH / POST-LAUNCH 上线阻断判定(严重度≠紧迫度)
- [ ] **RPT-04**: 修复工作包:发现按共同修复位置分组、按影响÷工作量排序、标注工作包间依赖,可直接作为修复里程碑的阶段清单
- [ ] **RPT-05**: "Do NOT fix" 登记表:核实过的故意设计(`issue-cedential` 在用域名、`whisper-local` 桩、handler mypy 豁免等),标注 `⚠ intentional — do not "fix"`
- [ ] **RPT-06**: 优点盘点章节:刻意为之且正确的设计(MaskedSecret、单键 STS、`.done` 状态机等),防止修复里程碑误"优化"
- [ ] **RPT-07**: 分维度置信声明:每个维度审到多深、哪些区域仅轻度覆盖
- [ ] **RPT-08**: 可追溯映射表:发现 ↔ CONCERNS.md 线索 ↔ 本里程碑需求,含各维度"已检查,无发现"显式记录
- [ ] **RPT-09**: 报告语言为中文正文 + 英文 ID/严重度术语(与仓库中文注释习惯一致)

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### 后续里程碑

- **FUTURE-01**: 对照 `docs/fc-transcribe-design.md` 的目标态契约差距分析 — 归 FC 直转切换里程碑
- **FUTURE-02**: 跨组件契约测试落地并接入 `make test` — 归修复里程碑(本次仅出设计配方)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| 审计期间修复任何问题(哪怕一行) | 污染基线与行号证据;用户明确决定修复统一留给下一个里程碑;仓库存在"显而易见的修复"会破坏生产的陷阱 |
| 渗透测试级安全审计 | 非本次审计维度;顺带发现的安全问题仍记录并标注"顺带发现" |
| 逐行审计 vendored `docs/example/start-fc-main/`(29MB, 1003 文件) | 非项目代码;其存在本身作为一条发现,并从所有扫描中排除 |
| 数值化质量评分(如 "7.2/10") | 不可证伪,引发对数字而非发现的争论 |
| 小时级工作量估计 | 假精确;统一用 S/M/L/XL 分档 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHARTER-01 | Phase 1 | Complete |
| CHARTER-02 | Phase 1 | Complete |
| CHARTER-03 | Phase 1 | Complete |
| CHARTER-04 | Phase 1 | Complete |
| CHARTER-05 | Phase 1 | Complete |
| CONTRACT-01 | Phase 2 | Complete |
| CONTRACT-02 | Phase 2 | Complete |
| CONTRACT-03 | Phase 2 | Complete |
| CONTRACT-04 | Phase 2 | Complete |
| AUDIT-01 | Phase 3 | Complete |
| AUDIT-02 | Phase 3 | Complete |
| AUDIT-03 | Phase 4 | Pending |
| AUDIT-04 | Phase 4 | Pending |
| AUDIT-05 | Phase 4 | Pending |
| RPT-01 | Phase 5 | Pending |
| RPT-02 | Phase 5 | Pending |
| RPT-03 | Phase 5 | Pending |
| RPT-04 | Phase 5 | Pending |
| RPT-05 | Phase 5 | Pending |
| RPT-06 | Phase 5 | Pending |
| RPT-07 | Phase 5 | Pending |
| RPT-08 | Phase 5 | Pending |
| RPT-09 | Phase 5 | Pending |

**Coverage:**

- v1 requirements: 23 total(原统计 "20" 有误,实际计数 CHARTER 5 + CONTRACT 4 + AUDIT 5 + RPT 9 = 23,已修正)
- Mapped to phases: 23
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-04*
*Last updated: 2026-07-04 after roadmap creation (traceability mapped)*
