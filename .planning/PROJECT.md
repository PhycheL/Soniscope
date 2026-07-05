# SoniScope — 上线前代码审计里程碑

## What This Is

SoniScope 是一条个人录音转写流水线:WeChat 小程序录音 → Aliyun FC 3.0 函数(签发 STS 凭证、校验上传)→ OSS 私有桶(唯一数据契约)→ 本地 Python Worker 轮询、ffmpeg 标准化、NLS 云端 ASR 转写。项目处于部署上线阶段;本里程碑不新增功能,而是对现有代码进行一次全面审计,产出结构化审计报告,作为正式对外上线前的把关。

## Core Value

在正式上线前,拿到一份可信、有证据、分级明确的审计报告,准确回答"现有代码哪里不一致、哪里有债务、上线有什么风险"。

## Requirements

### Validated

<!-- 由现有代码库推断(见 .planning/codebase/)。 -->

- ✓ 小程序端录音、草稿确认、静默登录、STS 直传 OSS、上传校验与列表 — existing
- ✓ FC issue-credential:wx code→openid、allowlist、单对象键 STS 签发(≤900s)— existing
- ✓ FC verify-upload:HeadObject 大小/etag 校验 — existing
- ✓ Worker 七阶段幂等流水线:轮询→下载→ffmpeg 标准化→NLS 转写→原子写盘(`.done` 状态机)— existing
- ✓ 启动恢复扫描、manifest/transcript 组装、Typer CLI(Makefile 全目标映射)— existing
- ✓ FC 部署工具链(打包/备份/部署/回滚/日志)与真云 E2E 验证脚本 — existing
- ✓ pytest + node:test 统一 `make test` 门禁;纯逻辑+注入 IO 模式贯穿双语言 — existing
- ✓ 契约一致性审计:51 行漂移矩阵(FC/Worker/小程序三列,236 处 `@ 5927f36` 行号证据)、18 样本往返校验佐证、12 个分歧格四类判定(F-CON-01~06)、重复逻辑普查与跨语言契约测试配方 — Validated in Phase 2: 契约抽取与漂移分析
- ✓ 代码质量与技术债审计:三层主体代码 63 对象(47 CODE + 16 TOOL)全覆盖普审 + 深挖,COVERAGE.md 台账 + F-CODE-01~08 发现,258 条扫描命中三态销号,14 条假设回填 — Validated in Phase 3: 组件与工具链深潜
- ✓ 脚本与工具链审计:scripts/ 三文件与 Makefile 45 目标普审,F-TOOL-01~08 发现(含 HYP-07 过期预签名 URL 证实、mypy 门禁结构性恒红)— Validated in Phase 3: 组件与工具链深潜

### Active

<!-- 本里程碑:审计,仅产出报告,不做修复。 -->

- [ ] 文档与配置一致性审计:docs/、config.js、AGENTS.md 等与代码实态的一致性(含已知的 `issue-cedential` 拼写域名、AGENTS.md 引用已删除文档等线索)
- [ ] 测试代码审计:现有测试质量与覆盖缺口盘点
- [ ] 产出结构化审计报告:每个发现带严重度分级、文件/行号证据、修复建议与工作量估计,可直接作为下一个里程碑(修复)的输入

### Out of Scope

- 修复问题 — 本里程碑仅产出报告;修复(含高危)统一留给下一个里程碑,由报告驱动
- 对照 `docs/fc-transcribe-design.md` 的目标契约审计 — 用户明确选择仅审现状一致性;FC 直转切换障碍分析随切换里程碑再做
- 新功能开发(transcribe-audio FC 函数、多用户等)— 审计里程碑不动功能
- 安全渗透测试级别的审计 — 重点是契约一致性与质量债务;安全问题若在审计中顺带发现仍记录在报告中,但不是主动审计维度

## Context

- 代码库地图已生成:`.planning/codebase/`(STACK、ARCHITECTURE、STRUCTURE、CONVENTIONS、TESTING、INTEGRATIONS、CONCERNS 七份文档,2026-07-04)
- CONCERNS.md 已给出初步线索:fragment_id/object key 契约逻辑在 FC、Worker、小程序三处重复实现;`apps/miniprogram/config.js` 中拼写为 `issue-cedential` 的 FC 域名;`scripts/test_asr.py` 中已提交的(过期)预签名 OSS URL;docs/ 下有未提交的权威文档删除且 AGENTS.md 仍引用它们
- 架构特点:无数据库、无消息队列,OSS 对象是唯一数据契约,Worker 以本地磁盘文件状态机为权威状态 — 契约审计需覆盖对象键、元数据、状态机三类约定
- 项目处于部署阶段(2026-07),FC 直转已定为未来主转写路径,但本审计以现状为基准
- Phase 1(审计章程与基线)已完成(2026-07-04):审计基线钉住 5927f36,CHARTER.md(严重度体系/工作量分档/发现 schema/排除清单)与 HYPOTHESES.md(25 条假设)、DO-NOT-FIX.md(4 条预录入)定稿,验证 13/13 通过
- Phase 2(契约抽取与漂移分析)已完成(2026-07-05):CONTRACT-MATRIX.md 51 行封版,FC↔Worker 主链零漂移;判定分布:潜伏 2(MEDIUM)/覆盖洞 3(LOW)/良性 1(INFO)/活跃失配 0;F-CON-01~06 入台账,CONTRACT-TEST-RECIPE.md 产出,6 条 D14 重复逻辑移交 Phase 3,验证 5/5 通过
- Phase 3(组件与工具链深潜)已完成(2026-07-05):COVERAGE.md 63 对象(47 CODE + 16 TOOL)全落格封版;新发现 F-CODE-01~08(MEDIUM 2:无界重下载循环、uploading 卡死态)+ F-TOOL-01~08(MEDIUM 2:过期预签名 URL 曾入库、mypy 门禁结构性恒红);258 条扫描命中三态销号(确认 15/误报 243),14 条假设回填(累计 14/25,余 11 条留 Phase 4),D14-1~6 全部裁定,HANDOFF-PHASE4.md 封版(DOC 3 + TEST 3),零 diff 红线全程成立,验证 13/13 通过

## Constraints

- **产出形态**: 仅审计报告,不改代码 — 用户明确要求修复留给下一个里程碑
- **报告标准**: 每个发现必须有严重度分级、文件/行号证据、修复建议与工作量估计 — 报告要能直接驱动下个里程碑
- **审计基准**: 契约一致性以三处实现的现状互相对照为准,不引入目标态设计 — 用户明确选择
- **技术栈**: Python 3.11+(mypy-strict/ruff)与小程序 JS 双语言仓库 — 审计工具与判断标准需分别适配

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 仅产出审计报告,不做修复 | 上线前先看全貌,修复由报告统一排期,避免边审边改污染基线 | — Pending |
| 契约审计仅以现状为基准 | FC 直转切换是独立里程碑,目标态对照届时再做,本次聚焦当前一致性 | — Pending |
| 审计范围覆盖全仓库四类代码 | 上线把关需要完整视图:主体代码、脚本工具、文档配置、测试 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-05 after Phase 3 completion*
