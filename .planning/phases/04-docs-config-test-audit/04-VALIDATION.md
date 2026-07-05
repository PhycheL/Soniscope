---
phase: 4
slug: docs-config-test-audit
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 (workspace) + node:test(仅作审计仪器在 worktree 基线专区执行,不新增测试) |
| **Config file** | 根 `pyproject.toml`(pytest/mypy/ruff)— 零 diff 约束下不得修改 |
| **Quick run command** | 台账机械验收命令(grep 状态行统计、零 diff 验证 `git diff --stat 5927f36 -- apps/ scripts/ docs/`) |
| **Full suite command** | worktree 专区内 `make install && make test`(D-01/D-02,审计仪器,非质量门禁) |
| **Estimated runtime** | ~120 seconds |
| **Validation Architecture** | 见 `04-RESEARCH.md` ## Validation Architecture 节 |

---

## Sampling Rate

- **After every task commit:** 对应清单/台账条目的机械验收命令(grep 四态/状态行计数)
- **After every plan wave:** 零 diff 验证 `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空
- **Before `/gsd-verify-work`:** 25/25 HYP 对账表 + DOC/TEST 台账销号清单全部闭合;worktree 专区已清理
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> Automated Command 为各 PLAN `<verify><automated>` 的摘要(产物路径省略 `.planning/audit/` 前缀);完整命令与 acceptance_criteria 以对应 PLAN.md 为准。File Exists 列:✅ = 验收目标文件既有;🆕 = 本任务自建后即受验。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-T1 worktree 建区与门禁实跑 | 04-01 | 1 | AUDIT-04 | T-04-01, T-04-02 | 仅白名单离线命令,真云目标零执行 | 机械验收 | `git worktree list \| grep -c 'wt-5927f36'` | ✅ | ⬜ pending |
| 04-01-T2 反事实 SKIP 观测与 scans 归档 | 04-01 | 1 | AUDIT-04 | T-04-03 | 归档只含计数,凭证模式只记位置 | 机械验收 | `test -f scans/gate-run-worktree.md && grep -c 'exit=' 该文件 && git diff --stat 5927f36 -- apps/ scripts/ docs/ \| wc -l \| grep -cx '0'` | 🆕 | ⬜ pending |
| 04-02-T1 pytest-cov 包合法性确认 | 04-02 | 2 | AUDIT-04 | T-04-SC | [SUS] 包安装前 blocking-human,不可自动通过 | human checkpoint | N/A(人工 approved 后放行 Task 2) | — | ⬜ pending |
| 04-02-T2 Python 覆盖率实测归档 | 04-02 | 2 | AUDIT-04 | T-04-04, T-04-05 | ephemeral 注入,零仓库配置写入 | 机械验收 | `test -f scans/coverage-pytest.md && grep -c 'pytest-cov' 该文件 && grep -c 'soniscope_worker' 该文件` | 🆕 | ⬜ pending |
| 04-02-T3 JS 覆盖率归档与专区拆除 | 04-02 | 2 | AUDIT-04 | T-04-04, T-04-05 | experimental 标注,拆区零残留 | 机械验收 | `test -f scans/coverage-node.md && grep -ci 'experimental' 该文件 && git worktree list \| grep -c 'wt-5927f36' \| grep -cx '0'` | 🆕 | ⬜ pending |
| 04-03-T1 DOC-CLAIMS.md 骨架 | 04-03 | 1 | AUDIT-03 | T-04-06, T-04-07 | 秘密红线;只写 .planning 两文件 | 机械验收 | `test -f DOC-CLAIMS.md && grep -c 'dead-ref' 该文件 && grep -c 'PRD_v1.md' 该文件` | 🆕 | ⬜ pending |
| 04-03-T2 PRD_v1.md 深核销号 | 04-03 | 1 | AUDIT-03 | T-04-06 | 双行号证据 @ 5927f36,禁读工作树 | 机械验收 | `grep -c '^\| P-' DOC-CLAIMS.md && grep -c 'HYP-21' 该文件 && grep -c 'HYP-16' 该文件` | 🆕 | ⬜ pending |
| 04-03-T3 tech-spec 深核与 F-DOC 立条 | 04-03 | 1 | AUDIT-03 | T-04-06, T-04-07 | DNF 命中不立条,九字段 schema | 机械验收 | `grep -c '^\| T-' DOC-CLAIMS.md && grep -c '04-03 判定产物' findings/docs-config.md` | ✅ | ⬜ pending |
| 04-04-T1 cloud-setup/mvp-acceptance 销号 | 04-04 | 2 | AUDIT-03 | T-04-08 | 真云 make 目标只核对不执行 | 机械验收 | `grep -c '^\| CS-' DOC-CLAIMS.md && grep -c '^\| MA-' 该文件` | ✅ | ⬜ pending |
| 04-04-T2 部署双 runbook 销号 + HYP-14 核对 | 04-04 | 2 | AUDIT-03 | T-04-08, T-04-09 | 凭证段落只记位置+模式名 | 机械验收 | `grep -c '^\| DG-' DOC-CLAIMS.md && grep -c '^\| FD-' 该文件 && grep -c 'HYP-14' 该文件` | ✅ | ⬜ pending |
| 04-04-T3 runbook 批次 F-DOC 立条 | 04-04 | 2 | AUDIT-03 | T-04-10 | MEDIUM 锚点逐条有理由 | 机械验收 | `grep -c '04-04 判定产物' findings/docs-config.md` | ✅ | ⬜ pending |
| 04-05-T1 AGENTS.md + README×3 深核 | 04-05 | 3 | AUDIT-03 | T-04-12 | dead-ref 逐处登记 → HYP-02 | 机械验收 | `grep -c '^\| AG-' DOC-CLAIMS.md && grep -c 'HYP-02' 该文件` | ✅ | ⬜ pending |
| 04-05-T2 config.js 深核 + 两 JSON 普审 | 04-05 | 3 | AUDIT-03 | T-04-11 | 平台真值标『无法静态核实』 | 机械验收 | `grep -c '^\| CF-' DOC-CLAIMS.md && grep -c '核实结论' 该文件 && grep -c 'DNF-02' 该文件` | ✅ | ⬜ pending |
| 04-05-T3 普审/存在级与 DOC 收口 | 04-05 | 3 | AUDIT-03 | T-04-11, T-04-12 | 目标态两文档不做实态对照 | 机械验收 | `grep -c '待审' DOC-CLAIMS.md \| grep -cx '0' && grep -c '目标态对照未审' 该文件 && grep -c '04-05 判定产物' findings/docs-config.md` | ✅ | ⬜ pending |
| 04-06-T1 TEST-AUDIT.md 骨架(8 面 + 41 行) | 04-06 | 1 | AUDIT-04 | T-04-14 | 封版产物只读仿写 | 机械验收 | `test -f TEST-AUDIT.md && grep -c '^\| \`apps/' 该文件 && grep -c '/8' 该文件` | 🆕 | ⬜ pending |
| 04-06-T2 D-09 反向映射清单编制 | 04-06 | 1 | AUDIT-04 | T-04-13 | 秘密类发现只引位置+模式名 | 机械验收 | `grep -c 'F-CON-0\\\|F-CODE-0\\\|F-TOOL-0' TEST-AUDIT.md && grep -c '反向映射' 该文件` | 🆕 | ⬜ pending |
| 04-07-T1 worker 24 文件逐面普审 | 04-07 | 2 | AUDIT-04 | T-04-15, T-04-16 | 纯 git show/grep 静读 | 机械验收 | `grep -c '8/8' TEST-AUDIT.md` | ✅ | ⬜ pending |
| 04-07-T2 fc 7 文件普审 + HYP-23 专项 | 04-07 | 2 | AUDIT-04 | T-04-15 | 只验补偿,不质疑 DNF-03 豁免 | 机械验收 | `grep -c 'HYP-23' TEST-AUDIT.md && grep -c 'DNF-03' 该文件` | ✅ | ⬜ pending |
| 04-07-T3 node 10 文件普审 + 反向映射收敛 | 04-07 | 2 | AUDIT-04 | T-04-15, T-04-16 | 台账行锚定计数,占位清零 | 机械验收 | `test "$(grep -c '^\| \`apps/.*8/8' TEST-AUDIT.md)" -eq "$(grep -c '^\| \`apps/' 该文件)" && grep -c '补证中' 该文件 \| grep -cx '0'` | ✅ | ⬜ pending |
| 04-08-T1 D-11 门禁三方对照表 | 04-08 | 3 | AUDIT-04 | T-04-17 | test_asr.py 只引位置+模式名 | 机械验收 | `grep -c 'D-11' TEST-AUDIT.md && grep -c 'HANDOFF-PHASE4.md TEST' 该文件` | ✅ | ⬜ pending |
| 04-08-T2 F-TEST 按面聚合立条 | 04-08 | 3 | AUDIT-04 | T-04-18 | 覆盖率仅证据,无定性语言 | 机械验收 | `grep -c '04-08 判定产物' findings/test.md && grep -ci '评分\\\|score' 该文件 \| grep -cx '0'` | ✅ | ⬜ pending |
| 04-08-T3 TEST-AUDIT.md 收口对账 | 04-08 | 3 | AUDIT-04 | T-04-19 | 双向指针闭环 | 机械验收 | `grep -c 'F-TEST-' TEST-AUDIT.md && grep -c '✓' 该文件` | ✅ | ⬜ pending |
| 04-09-T1 11 条 HYP 回填 + HANDOFF 销号 | 04-09 | 4 | AUDIT-05 | T-04-20 | 引用回填不重复采证 | 机械验收 | `grep -c '^- \*\*状态:\*\* 未验证' HYPOTHESES.md \| grep -cx '0' && grep -c '04-09 回填' 该文件` | ✅ | ⬜ pending |
| 04-09-T2 D-13 机械对账 + D-15 总对账章节 | 04-09 | 4 | AUDIT-05 | T-04-21 | 出入走勘误行,不改史 | 机械验收 | `grep -c '总对账' HYPOTHESES.md && grep -c '^### HYP-' 该文件 \| grep -cx '25'` | ✅ | ⬜ pending |
| 04-09-T3 阶段机械收尾验证 | 04-09 | 4 | AUDIT-05 | T-04-22 | 零 diff + worktree 零残留 | 机械验收 | `git diff --stat 5927f36 -- apps/ scripts/ docs/ \| wc -l \| grep -cx '0' && git worktree list \| grep -c 'wt-5927f36' \| grep -cx '0' && grep -c '阶段收尾验证' HYPOTHESES.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.(审计阶段不新增测试文件;`make test` 仅作审计仪器在 worktree 专区执行。)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 纯云端事实声明标注"无法静态核实" | AUDIT-03 | 控制台配置无法静态取证 | 人工确认清单条目标注了四态之一且未猜测 |
| pytest-cov 包合法性确认(04-02 Task 1) | AUDIT-04 | 包合法性协议:[SUS] 包安装前 blocking-human 检查点,不可自动通过 | 打开 pypi.org/project/pytest-cov 目视确认归属 pytest-dev 官方组织后回复 approved |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies(26 任务中 25 项含 `<automated>`;04-02-T1 为 blocking-human 检查点,按协议无自动验收,登记于 Manual-Only 表)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify(唯一非自动任务 04-02-T1 前后任务均有 `<automated>`)
- [x] Wave 0 covers all MISSING references(本阶段无 MISSING 引用;不新增测试文件,`make test` 仅作审计仪器)
- [x] No watch-mode flags
- [x] Feedback latency < 120s(全部验收为 grep/git diff 级命令,< 1s;worktree 全套实跑 ~120s 为上界)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved — 2026-07-05(planner revision 回填:26 任务映射表逐条对应 9 份 PLAN 的 `<verify><automated>`)
