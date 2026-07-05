---
phase: 2
slug: contract-extraction-drift
status: draft
nyquist_compliant: false
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
| (filled by planner) | — | — | CONTRACT-01..04 | — | N/A (audit report phase — no product code changes) | manual/harness | see RESEARCH.md harness (git archive export + repo .venv + node) | ✅ | ⬜ pending |

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
