---
phase: 2
slug: contract-extraction-drift
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-04
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 (Python) + node --test (JS) — existing repo infrastructure |
| **Config file** | `pyproject.toml` (root) |
| **Quick run command** | `make test` |
| **Full suite command** | `make test && make lint && make typecheck` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make test`
- **After every plan wave:** Run `make test && make lint && make typecheck`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-T1 | 02-01 | 1 | CONTRACT-01 | T-02-01/02 | 证据仅 path:line + 模式名,零 diff | doc check | `grep -o '@ 5927f36' .planning/audit/CONTRACT-MATRIX.md \| wc -l` ≥ 12 且 `git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空 | ✅ | ⬜ pending |
| 02-01-T2 | 02-01 | 1 | CONTRACT-01 | T-02-01/02 | 同上 | doc check | `grep -c 'x-oss-meta-' CONTRACT-MATRIX.md` ≥ 7 且引用总数 ≥ 30 | ✅ | ⬜ pending |
| 02-02-T1 | 02-02 | 2 | CONTRACT-01 | T-02-01/02 | 同上 | doc check | 9 个错误码/reason 字符串逐一 grep 命中 | ✅ | ⬜ pending |
| 02-02-T2 | 02-02 | 2 | CONTRACT-01 | T-02-01/02 | 同上 | doc check | 4 个镜像常量标识符 grep 命中 | ✅ | ⬜ pending |
| 02-02-T3 | 02-02 | 2 | CONTRACT-03 | T-02-01/02 | 扫描输出入档前过目 | doc check | `grep -c 'git grep' CONTRACT-MATRIX.md` ≥ 5 + 移交/无新发现行命中 | ✅ | ⬜ pending |
| 02-03-T1 | 02-03 | 3 | CONTRACT-02 | T-02-03/04 | 基线导出 + __file__ 断言 + 零云 IO | harness + doc check | `grep -c '^\| S-' CONTRACT-MATRIX.md` ≥ 11 + status 仅 .planning/ | ✅ | ⬜ pending |
| 02-03-T2 | 02-03 | 3 | CONTRACT-02 | T-02-03/04 | 显式 TZ,样本全合成 | harness + doc check | TZ=Asia/Shanghai 与 TZ=America/New_York 记录 grep 命中 | ✅ | ⬜ pending |
| 02-04-T1 | 02-04 | 4 | CONTRACT-02 | T-02-01/05 | 九字段留痕,DNF 负面清单前置 | doc cross-check | `grep -c '^### F-CON-' findings/contract.md` ≥ 1 + HYP-13/Postel 命中 | ✅ | ⬜ pending |
| 02-04-T2 | 02-04 | 4 | CONTRACT-04 | T-02-02 | 纯纸面设计,零 diff | doc check | RECIPE 存在(含 S-NN + make test)或矩阵含"无需配方" | ✅ | ⬜ pending |
| 02-04-T3 | 02-04 | 4 | CONTRACT-01..04 | T-02-02/05 | 零 diff 记录 + 机械对账 | smoke + doc check | `git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空 + 对账行命中 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. This phase produces audit findings documents, not product code; the execution-evidence harness described in RESEARCH.md (Validation Architecture) runs read-only against the frozen baseline `5927f36` and requires no new test files in the repo.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drift matrix line-number evidence accuracy | CONTRACT-01 | Findings docs cite file:line against frozen baseline; correctness is judged by re-checking citations, not by a test suite | Spot-check each matrix row's citation with `git show 5927f36:<path>` |
| Round-trip key parse conclusion | CONTRACT-02 | Executed via ad-hoc harness (git archive export + repo .venv python + node), output recorded into findings doc | Follow harness recipe in 02-RESEARCH.md Validation Architecture |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — no test infra needed, per RESEARCH)
- [x] No watch-mode flags
- [x] Feedback latency < 90s (all doc checks < 5s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved by planner 2026-07-05 (10 tasks mapped across 4 plans)
