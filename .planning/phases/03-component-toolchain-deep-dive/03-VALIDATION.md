---
phase: 3
slug: component-toolchain-deep-dive
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-04
revised: 2026-07-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | audit-artifact validation (no product tests written this phase — audit-only milestone) |
| **Config file** | none — validation is grep/schema checks over `.planning/audit/` artifacts; 命令内嵌于各 PLAN 的 `<verify><automated>` 块 |
| **Quick run command** | `git diff --stat 5927f36 -- apps/ scripts/ docs/`(输出必须为空 = 基线零污染) |
| **Full suite command** | 03-07 Task 3 总验收链:完成判定节存在 + COVERAGE 零"待审" + `.planning/audit/` 秘密反扫零命中 + 零 diff + HYPOTHESES 状态行(行首锚定)计数 ≤ 11 |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `git diff --stat 5927f36 -- apps/ scripts/ docs/`(零 diff 快查)
- **After every plan wave:** Run 该计划全部 `<automated>` 命令 + scans/findings 秘密模式反扫
- **Before `/gsd-verify-work`:** 03-07 Task 3 总验收链 must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

> 命令列为各任务 `<automated>` 门禁的核心断言;完整命令链以对应 PLAN 的 `<verify><automated>` 块为准(source: 03-RESEARCH.md §Validation Architecture 机械验收 Map)。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | AUDIT-01/02 | T-03-02 | 基线零 diff,写入仅落 .planning/ | artifact-grep | 零 diff 为空 + ``grep -cE '^\| `' COVERAGE.md`` = 63 + 关注面/深挖点/HANDOFF 节存在 | ✅ | ⬜ pending |
| 03-01-02 | 01 | 1 | AUDIT-01/02 | T-03-SC | 供应链人工把关(uvx/npx 拉取前批准) | human-verify | —(人工批准信号;见 Manual-Only 表) | n/a | ⬜ pending |
| 03-01-03 | 01 | 1 | AUDIT-01/02 | T-03-01 / T-03-SC | scans/ 秘密模式反扫零命中(脱敏管道生效) | artifact-grep | scans/ 五档存在 + 每档含版本行 + 秘密 regex 反扫零命中 + 零 diff | ✅ | ⬜ pending |
| 03-02-01 | 02 | 2 | AUDIT-01/02 | T-03-02 | N/A | artifact-grep | gates-baseline/ruff-extended/vulture 三档各含对账等式 `= .*✓` 且销号列无空行 | ✅ | ⬜ pending |
| 03-02-02 | 02 | 2 | AUDIT-01/02 | T-03-01 | secrets.md 销号表无匹配值本体 | artifact-grep | eslint/secrets 两档对账等式 + scans/ 秘密反扫零命中 + 零 diff | ✅ | ⬜ pending |
| 03-03-01 | 03 | 3 | AUDIT-01 | T-03-01 | 证据片段不截秘密样例值 | artifact-grep | awk:COVERAGE 中 pipeline/nls/cli/poller 四行无"待审" + 含 9/9 | ✅ | ⬜ pending |
| 03-03-02 | 03 | 3 | AUDIT-01 | T-03-02 | N/A | artifact-grep | awk:COVERAGE CODE 维度 soniscope_worker 全 14 行无"待审" | ✅ | ⬜ pending |
| 03-03-03 | 03 | 3 | AUDIT-01 | T-03-02 | N/A | artifact-grep | HYP-10/16/19 状态非"未验证"且各含 5927f36 证据 + 零 diff | ✅ | ⬜ pending |
| 03-04-01 | 04 | 4 | AUDIT-01 | T-03-01 | FC 凭证/STS 证据不含样例秘密值 | artifact-grep | awk:COVERAGE apps/fc 12 行无"待审" + 零 diff | ✅ | ⬜ pending |
| 03-04-02 | 04 | 4 | AUDIT-01 | T-03-01 | N/A | artifact-grep | awk:COVERAGE apps/miniprogram 21 行无"待审" + HANDOFF 含 HYP-14 | ✅ | ⬜ pending |
| 03-04-03 | 04 | 4 | AUDIT-01 | T-03-02 | N/A | artifact-grep | HYP-01/08/09/12/17/20 状态非"未验证"且各含 5927f36 证据 + 零 diff | ✅ | ⬜ pending |
| 03-05-01 | 05 | 5 | AUDIT-02 | T-03-01 | N/A | artifact-grep | awk:COVERAGE 中 verify_prep/fc_deploy/retranscribe/fc_live 四行无"待审" | ✅ | ⬜ pending |
| 03-05-02 | 05 | 5 | AUDIT-02 | T-03-02 | N/A | artifact-grep | awk:COVERAGE TOOL 维度 soniscope_worker 全 12 行无"待审" | ✅ | ⬜ pending |
| 03-05-03 | 05 | 5 | AUDIT-02 | T-03-02 | N/A | artifact-grep | HYP-04/15 状态非"未验证"且各含 5927f36 证据 + 零 diff | ✅ | ⬜ pending |
| 03-06-01 | 06 | 6 | AUDIT-02 | T-03-01 | HYP-07 证据只写位置+模式名,无 URL 值本体 | artifact-grep | awk:COVERAGE scripts/ 三行无"待审" + findings/ 签名 URL 模式反扫零命中 | ✅ | ⬜ pending |
| 03-06-02 | 06 | 6 | AUDIT-02 | T-03-02 | N/A | artifact-grep | awk:COVERAGE Makefile 行无"待审" + HYP-07/18 状态非"未验证"含 5927f36 证据 + 零 diff | ✅ | ⬜ pending |
| 03-07-01 | 07 | 7 | AUDIT-01/02 | T-03-03 | 微基准仅 scratchpad 执行(来源断言) | artifact-grep | microbench-sha256.md 存在且含"非真机" + HYP-03 状态非"未验证"且含 5927f36 | ✅ | ⬜ pending |
| 03-07-02 | 07 | 7 | AUDIT-01/02 | T-03-02 | N/A | artifact-grep | D14-1~6 在 findings//COVERAGE 各有下落 + 深挖点登记节零"待审" | ✅ | ⬜ pending |
| 03-07-03 | 07 | 7 | AUDIT-01/02 | T-03-01 | .planning/audit/ 全目录秘密反扫零命中 | artifact-grep | 完成判定节存在 + 全表零"待审" + 秘密反扫零命中 + 零 diff + ``grep -c '^- \*\*状态:\*\* 未验证' HYPOTHESES.md`` ≤ 11 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*File Exists ✅ = 验收命令为自足 shell 断言(grep/awk/git diff),无测试文件依赖,无 Wave 0 前置。*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. 本阶段验收全为自足 shell 断言(grep/awk/git diff over `.planning/audit/` 工件),无测试文件、fixture 或框架安装需 Wave 0 创建;台账骨架(findings/*.md 含 F-*-00 schema 示例)与 CHARTER/HYPOTHESES/DO-NOT-FIX 均已在 Phase 1/2 就绪(见 03-RESEARCH.md §Wave 0 Gaps: None)。

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| vulture/eslint 临时仪器包合法性批准(03-01 Task 2) | AUDIT-01/02(D-05 仪器前置) | 供应链人工把关——包合法性检查点不可自动通过(不受 auto_advance 影响) | 核对 pypi.org/project/vulture 指向 github.com/jendrikseipp/vulture、npmjs.com/package/eslint 为 eslint 官方 org,认可 03-RESEARCH.md §Package Legitimacy Audit 结论后回复 "approved"(或指定兜底方案) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies(19 任务中 18 个 artifact-grep 门禁;唯一例外 03-01 Task 2 为 blocking-human 检查点,已入 Manual-Only 表)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify(每任务均有 `<automated>` 门禁)
- [x] Wave 0 covers all MISSING references(无 MISSING 引用——验收命令自足)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner revision 2026-07-05(per checker nyquist_compliance feedback)
