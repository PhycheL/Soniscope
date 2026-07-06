# Milestone v1.0 — Project Summary

**Generated:** 2026-07-05
**Purpose:** Team onboarding and project review
**Milestone:** SoniScope — 上线前代码审计里程碑(audit-only,零代码改动)

---

## 1. Project Overview

**SoniScope** 是一条个人录音转写流水线:

> WeChat 小程序录音 → Aliyun FC 3.0 函数(签发 STS 凭证、校验上传)→ OSS 私有桶(唯一数据契约)→ 本地 Python Worker 轮询、ffmpeg 标准化、NLS 云端 ASR 转写

本里程碑(v1.0)**不写任何功能代码**,而是在正式对外上线前对现有代码做一次全面审计,产出结构化审计报告作为上线把关。核心价值:准确回答"现有代码哪里不一致、哪里有债务、上线有什么风险"。

**里程碑状态:全部完成并通过审计**(5/5 阶段,25/25 计划,23/23 需求,gsd-audit-milestone 判定 PASSED)。

**最终答案(审计结论):总体上线判定 CONDITIONAL GO** — 40 条发现中 BLOCKER 0 / PRE-LAUNCH 3 / POST-LAUNCH 37;上线前必做仅 3 条:

| 必做发现 | 严重度 | 内容 | 工作包 |
|----------|--------|------|--------|
| F-CODE-02 | MEDIUM | 持久性失败对象(sha256 失配/转码失败)无界重下重试,无计数/隔离/告警 | WP-03 |
| F-CODE-06 | MEDIUM | 小程序上传队列 `uploading` 死态:进程中断后残留项无任何恢复通道 | WP-04 |
| F-DOC-03 | MEDIUM | 发布文档零 ENV 生产翻转步骤——照文档发布即把开发者菜单/故障注入开关带给最终用户 | WP-07 |

### 硬约束(全程成立)

- **零 diff 红线:** `apps/`、`scripts/`、`docs/` 相对钉住的基线 SHA `5927f362785d44b085a791ca387732991012ce5a` 全程零改动(每阶段收尾 + 里程碑审计独立复跑均为空)
- **秘密红线:** 凭证类证据只写 `path:line @ 5927f36` + 模式名,绝不复制值本体;全部审计产物反扫零命中
- **只报告不修复:** 全部发现进台账,修复(含 3 条 PRE-LAUNCH)统一留给下一个里程碑

---

## 2. Architecture & Technical Decisions

### 审计方法架构(本里程碑构建的东西)

- **Decision:** 基线钉定 + `git show <SHA>` 取证,禁止读工作树充当证据
  - **Why:** 证据行号免疫 HEAD 推进;审计期间任何人的改动都不会污染证据链
  - **Phase:** 1(章程条款),全程执行

- **Decision:** 五级严重度(CRITICAL~INFO)每级绑定 SoniScope 场景锚点,零裁量措辞;工作量只用 S/M/L/XL,禁止小时估计与数值评分
  - **Why:** 多阶段多执行者并行审计,锚点封死边界防口径漂移 — Phase 5 校准零调整证明该体系有效
  - **Phase:** 1

- **Decision:** 证据层与判断层物理分离 — scans/(工具输出线索池)→ findings/(人工核实的发现)→ CALIBRATION.md(经批准的判定)→ REPORT.md(零新判断的机械组装)
  - **Why:** 258 条工具命中 94% 是误报,原始输出不许直接充当发现;判断集中在单一经批准的台账,报告组装可跨文件机械复核
  - **Phase:** 3(scans/findings 分离)、5(判断前置、组装机械化)

- **Decision:** 一切完成判定走机械对账等式(行首锚 grep 计数 + 命令与输出照录)
  - **Why:** "查过了"不可验收;等式(如 25 HYP + 4 DNF = 29 CONCERNS 线索)让任何人可独立复算 — 里程碑审计正是靠独立重跑这些等式判 PASSED
  - **Phase:** 1 起全程,5 收尾 8 项门禁集大成

- **Decision:** 执行佐证跑在仓外基线副本(git archive / git worktree + `__file__` 来源断言),不替代静态判据
  - **Why:** 行为证据支撑严重度定级,但契约判定以代码文本为准;来源断言防误 import 工作树
  - **Phase:** 2(harness)、3(微基准)、4(worktree 门禁/覆盖率实跑)

- **Decision:** 第三方工具包(vulture/eslint/pytest-cov)引入前走 blocking-human 检查点,ephemeral 方式调用(uvx/npx/`uv run --with`)
  - **Why:** 供应链决策交人;临时注入零仓库配置写入
  - **Phase:** 3、4

### 被审系统的关键架构事实(供新人理解 SoniScope 本体)

- OSS 对象是三端唯一数据契约(key 模板 `recordings/<YYYY-MM-DD>/<id>.wav` + 7 个 `x-oss-meta-*` 字段);契约逻辑在 FC/Worker/小程序三处刻意重复实现(跨部署单元无法共享)
- Worker 以本地磁盘文件状态机为权威状态(`.done` 最后写,幂等),无数据库无队列
- FC 是唯一信任网关(wx code→openid→allowlist→单对象键 STS ≤900s)
- **审计证实:** FC↔Worker Python 主链契约 100% 无漂移;全部漂移集中在小程序 JS 声部(日期校验缺失、双入参可产出错位 key、第四处无校验反推)

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 1 | 审计章程与基线 | ✅ Complete (2026-07-04, 13/13 verified) | 钉住基线 5927f36,定稿 CHARTER.md(严重度/工作量/schema/排除清单)+ 29 条 CONCERNS 线索分流为 25 HYP + 4 DNF |
| 2 | 契约抽取与漂移分析 | ✅ Complete (2026-07-05, 5/5 verified) | 51 行三列漂移矩阵(236 处行号证据)+ 18 样本双语言往返校验 + 12 分歧格四类判定 → F-CON-01~06,契约测试配方成文 |
| 3 | 组件与工具链深潜 | ✅ Complete (2026-07-05, 13/13 verified) | 63 对象(47 CODE + 16 TOOL)9 面全覆盖普审 + 深挖,258 条扫描命中三态销号(确认仅 15)→ F-CODE-01~08 + F-TOOL-01~08 |
| 4 | 文档配置与测试审计 | ✅ Complete (2026-07-05, 7/7 verified) | 198 条文档声明四态销号 + 41 测试模块 8 面台账 + 双语言覆盖率实测 + 门禁三方对照 → F-DOC-01~08 + F-TEST-01~10;HYPOTHESES 25/25 闭环 |
| 5 | 汇总校准与报告组装 | ✅ Complete (2026-07-05, 14/14 verified) | 校准零调整零并入(经用户 approve-all)、5 簇聚类、9 工作包、40 条三态判定 → REPORT.md + 附录 A/B,CONDITIONAL GO |

依赖关系:Phase 2 与 Phase 3 同属证据收集波次(均仅依赖 Phase 1);Phase 4 需两者的代码实态输入;Phase 5 汇总收官。

---

## 4. Requirements Coverage

**23/23 satisfied,0 partial,0 orphaned**(里程碑审计三源交叉核对:REQUIREMENTS.md × 各阶段 VERIFICATION × PLAN 认领)。

- ✅ **CHARTER-01~05**(5 条)— 审计章程:基线 SHA、五级严重度、S/M/L/XL 分档、范围与方法、发现 schema — Phase 1
- ✅ **CONTRACT-01~04**(4 条)— 契约一致性:漂移矩阵、往返校验 + 四类判定 + Postel 分析、重复逻辑普查、黄金样本测试配方 — Phase 2
- ✅ **AUDIT-01~02**(2 条)— 三层主体代码 + 部署验证工具链盘点(工具输出仅作线索,逐条人工核实)— Phase 3
- ✅ **AUDIT-03~05**(3 条)— 文档配置一致性、双语言测试质量/覆盖缺口、CONCERNS 假设清单全闭环 — Phase 4
- ✅ **RPT-01~09**(9 条)— 最终报告:执行摘要、汇总表 backlog、三态判定、工作包、DNF 表、优点盘点、置信声明、追溯映射、语言约定 — Phase 5

**Milestone audit verdict: PASSED**(`.planning/v1.0-MILESTONE-AUDIT.md`)— 需求 23/23、阶段 5/5、集成链 7/7 WIRED、E2E 流 7/7。

---

## 5. Key Decisions Log

| # | Decision | Phase | Rationale / Outcome |
|---|----------|-------|---------------------|
| 1 | 仅产出审计报告,不做修复 | 里程碑 | 上线前先看全貌,修复由报告统一排期,避免边审边改污染基线 |
| 2 | 契约审计仅以三处现状互相对照,不引入 FC 直转目标态 | 里程碑 | 目标态对照留给切换里程碑;本次聚焦当前一致性 |
| 3 | 完整 SHA 全文只声明一次,正文统一短 SHA `5927f36` | 1 (D-02) | 单一权威声明点,grep -c = 1 可机械核验 |
| 4 | 无例外协议:任何发现(含 CRITICAL)只进台账,不中断审计、不动云端 | 1 (D-04) | 绝对措辞防裁量;泄露凭证也只登记不处置 |
| 5 | CONCERNS 29 条线索分流:4 条故意设计预录入 DNF、25 条转未验证假设 | 1 (D-08) | 故意设计不占验证工作量;对账等式 25+4=29 保零遗漏 |
| 6 | "diverge 指语义分歧,不是字面差异";chunk_total null→"0"→None 判 agree | 2 | 防机械判定制造伪发现 |
| 7 | 状态词(静态事实)与四类归类(影响判断)分离;7 错误码 absent 格裁良性合并单条 F-CON-05 | 2 (D-12) | 证据先封、判断后置;同根因合并防台账膨胀 |
| 8 | 258 条工具命中逐条人工核实,批量定性禁止 | 3 | 最终确认率仅 6%(15/258)——工具输出只配当线索池 |
| 9 | "可接受自评"经上线语境裁定成立后记优点/DNF 候选,不占发现 ID | 3 (D-10) | 区分"设计取舍成立"与"取舍范围内的独立缺陷" |
| 10 | D14 重复逻辑走三要素框架(结构必要性/兜底机制/漂移后果),"不构成债务"也是正式下落 | 3 (D-13) | 重复 ≠ 债务;三要素把裁定变成可复核论证 |
| 11 | 共担需求留阶段收尾统一销号;worktree 计划不触碰共享簿记文件 | 4 | 修复 Phase 2 暴露的簿记滞后问题,防并行合并冲突 |
| 12 | 假设证伪后按实态缩窄立条(HYP-24 → F-TEST-02) | 4 | 证伪 ≠ 零缺口,但表述必须跟证据走 |
| 13 | 校准"零调整/零并入"作为显式合法结果落账(带锚点依据) | 5 (D-01/D-08) | 校准产出是"裁定过程可查",不是"必须改点什么" |
| 14 | findings 封版不回写;上线判定槽由 CALIBRATION.md 承载 | 5 (D-03/A3) | 保持 Phase 2-4 产物零改动的可验证性 |
| 15 | 批准交互最小化:五组校准内容合并单次 checkpoint,用户 approve-all | 5 (D-02/D-12) | 全里程碑实质人工判断点仅 3 处:包合法性 ×2 + 校准批复 ×1 |

---

## 6. Tech Debt & Deferred Items

### 审计报告本身的发现(= 下一里程碑的 backlog)

40 条发现(MEDIUM 11 / LOW 26 / INFO 3,零 CRITICAL/HIGH),已组织为 9 个修复工作包(WP-01~09)+ 3 条 INFO acknowledge;5 个根因簇:key 派生多实现 / 契约镜像注释同步 / 失败路径静默化 / 门禁声明失真 / 文档叙述滞后。代表性 MEDIUM 发现:

- **F-CODE-02 / F-CODE-06 / F-DOC-03** — 3 条 PRE-LAUNCH 必做(见 §1)
- **F-TOOL-05** — `scripts/test_asr.py` 曾提交已过期预签名 STS URL(凭证入库习惯风险)
- **F-TOOL-06** — `make typecheck` 仓内结构性恒红(app.py 部署态导入),门禁二值信号早已失效
- **F-CON-02/03** — 小程序侧 key 派生潜伏失配:错位 key 上传后 Worker 静默跳过,数据滞留 OSS 无告警
- **F-TEST-03/04/05/06** — scripts/ 全静态门禁外、门禁信号无守护、契约镜像常量无对称锁定、失败/恢复路径无测试兜底

**Do-NOT-fix 登记表(4 条,防误"修"):** whisper-local 故意桩、`issue-cedential` 拼写域名(Aliyun 真实分配值)、FC handler mypy 豁免(行为测试补偿已证充分)、小程序接收原始 STS 秘密(by design,经用户裁定维持)。

**移交物:** `CONTRACT-TEST-RECIPE.md` — 黄金样本跨语言契约测试设计配方(修复里程碑拿到即可写代码)。

### 里程碑流程自身的 tech debt(5 项,全部 warning/Info 级)

- F-TEST-02 证据字段未自含 `@ 5927f36` 锚点(链条可追溯但不自含)
- F-DOC-07/08 证据用 `git ls-tree` 输出而非 `path:line @ SHA`(存在级普查,可辩护)
- SUMMARY frontmatter 普遍缺 requirements-completed 字段(需求认领实录在 PLAN,无孤儿)
- COVERAGE.md 完成判定 #3 grep 命令自匹配(声明 63 实返 64,实质为真)
- `make test` 2 条环境依赖失败(SONISCOPE_HOME unset)— 既有现象,已入台账 F-TEST-04

### 流程经验(各阶段 LEARNINGS.md 已提取,共 128 条)

复发主题值得注意:①对账命令自指计数(Phase 2/3/5 各现一次,对策=行首锚定/字符类拆字);②上游预核数字与全量实测有差(30→29 线索、7→9 错误码、3→4 死链),一律以基线实测为准;③需求簿记滞后(Phase 2 发现 → Phase 4 制度化)。

---

## 7. Getting Started

### 读审计成果(本里程碑的交付物)

1. **先读** `.planning/audit/REPORT.md` — 执行摘要 + CONDITIONAL GO 判定 + 40 行汇总表(即修复 backlog)+ WP-01~09
2. **追溯细节:** 附录 A(发现↔线索↔需求 29 行闭环)、附录 B(聚类明细)、`CALIBRATION.md`(判定唯一来源)
3. **单条发现详情:** `.planning/audit/findings/{contract,code,toolchain,docs-config,test}.md`(九字段 schema,F-*-00 为示例)
4. **支撑台账:** `CHARTER.md`(读懂严重度/证据格式的钥匙)、`CONTRACT-MATRIX.md`、`COVERAGE.md`、`DOC-CLAIMS.md`、`TEST-AUDIT.md`、`HYPOTHESES.md`、`scans/`

### 跑 SoniScope 本体

- **命令入口:** 仓根 `Makefile` 是唯一支持的命令面(`make install / test / typecheck / lint / worker-run / deploy-fc FUNCTION=...`)——用户永不 `cd` 进子目录
- **测试:** `make test`(pytest 567 用例 + node:test 126 用例经 pytest 桥);注意已知问题:需 `SONISCOPE_HOME` 已设,`make typecheck` 当前结构性恒红(F-TOOL-06)
- **关键目录:** `apps/worker/src/soniscope_worker/`(Worker 流水线)、`apps/fc/`(两个 FC 函数 + `shared/fc_shared/`)、`apps/miniprogram/`(小程序,`utils/` 纯逻辑 + `pages/` IO)
- **配置:** Worker 读 `$SONISCOPE_HOME/config.yaml`(chmod 600);小程序真值源 `apps/miniprogram/config.js`;FC 全靠环境变量(`fc_shared/env.py`)
- **从哪看起:** `apps/worker/src/soniscope_worker/pipeline.py`(七阶段流水线)、`apps/fc/shared/fc_shared/sts.py`(契约核心 `object_key_for`)、`apps/miniprogram/utils/uploader.js`(上传编排)

### 下一步(修复里程碑)

按 REPORT.md 汇总表排期:先做 3 条 PRE-LAUNCH(WP-03/04/07),再按严重度降序消化 POST-LAUNCH;对照 DNF 表避免误"修"故意设计;用 CONTRACT-TEST-RECIPE.md 落地跨语言契约测试。

---

## Stats

- **Timeline:** 2026-07-04 → 2026-07-05(约 2 天)
- **Phases:** 5 / 5 complete(25/25 plans,52/52 phase must-haves verified)
- **Commits:** 180(自最早 phase 提交起)
- **Files changed:** 110(+19,067 / −86)— 全部落 `.planning/`,产品代码零改动(零 diff 红线)
- **Contributors:** Bemied(+ Claude agents via GSD workflow)
- **审计规模:** 63 代码对象 × 9 关注面、198 条文档声明、41 测试模块 × 8 面、258 条工具命中逐条销号、25 条假设闭环、40 条发现、双语言覆盖率实测(pytest 73% / node 92.73%)
