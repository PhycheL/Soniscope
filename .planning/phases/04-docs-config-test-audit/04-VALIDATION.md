---
phase: 4
slug: docs-config-test-audit
status: draft
nyquist_compliant: false
wave_0_complete: false
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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (由 planner 在 PLAN.md 生成后回填) | — | — | AUDIT-03/04/05 | — | N/A(审计阶段,零 diff) | 机械验收命令 | grep/git diff 命令 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.(审计阶段不新增测试文件;`make test` 仅作审计仪器在 worktree 专区执行。)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 纯云端事实声明标注"无法静态核实" | AUDIT-03 | 控制台配置无法静态取证 | 人工确认清单条目标注了四态之一且未猜测 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
