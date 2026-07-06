---
phase: 6
slug: worker
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-06
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 06-RESEARCH.md `## Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 (root `pyproject.toml` `[tool.pytest.ini_options]`) |
| **Config file** | `pyproject.toml` — `testpaths=["apps/worker/tests","apps/fc/tests"]`, `pythonpath=["apps/fc/shared"]` |
| **Quick run command** | `uv run pytest apps/worker/tests/test_quarantine.py -x` |
| **Full suite command** | `make test` (= `uv run pytest`) |
| **Estimated runtime** | ~20 seconds (unit-only, all cloud IO faked) |

Static gates (must pass alongside tests): `make typecheck` (mypy --strict on `apps/worker/src` + tests) and `make lint` (ruff E,F,I,UP,B, line 100).

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest apps/worker/tests/test_quarantine.py -x` + `make typecheck`
- **After every plan wave:** Run `make test` (full pytest incl. test_poller / test_pipeline / test_config / test_recovery regressions) + `make lint`
- **Before `/gsd-verify-work`:** Full suite green + `make typecheck` + `make lint` green + `make test-no-redownload` (D-10 idempotent non-regression) green
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

Task IDs are assigned by the planner; rows below map each phase requirement to its sampling behavior and test. The planner MUST wire each PLAN.md task's `<automated>` verify to the matching command.

| Requirement | Behavior | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|------------|-----------------|-----------|-------------------|-------------|--------|
| WKR-01 | sha256_mismatch / probe / standardize failure each increments the ledger once; ledger persists to disk and re-reads | — | Ledger holds only fragment_id/reason/count/timestamps — no secrets | unit | `pytest apps/worker/tests/test_quarantine.py -k record` | ❌ W0 | ⬜ pending |
| WKR-01 | Multi-round accumulation: same fid failing N consecutive rounds → attempt=N | — | N/A | unit (held-out multi-round) | `pytest .../test_quarantine.py -k accumulate` | ❌ W0 | ⬜ pending |
| WKR-02 | attempt≥threshold fid lands in `plan_downloads` → `skipped_quarantined`, never in to_download | — | N/A | unit | `pytest apps/worker/tests/test_poller.py -k quarantine` | ⚠️ extend existing | ⬜ pending |
| WKR-02 | Threshold from config, default 3; changing config moves the isolation point | — | Config validated by pydantic | unit | `pytest .../test_config.py -k max_fragment` | ⚠️ extend existing | ⬜ pending |
| WKR-02 | `is_quarantined` pure predicate boundary (threshold-1 no, threshold yes) | — | N/A | unit (example+boundary) | `pytest .../test_quarantine.py -k is_quarantined` | ❌ W0 | ⬜ pending |
| WKR-03 | Threshold-crossing round emits exactly one alert line with 4 elements (fid/reason/attempt/next) | T-06 (V7 logging) | Alert carries only non-sensitive structured fields | unit | `pytest .../test_quarantine.py -k alert` | ❌ W0 | ⬜ pending |
| WKR-03 | quarantine-list prints isolation list; clear-quarantine single/--all deletes entries | T-06 (V5 input) | FRAGMENT_ID validated via `object_key_for` round-trip | unit | `pytest .../test_quarantine.py -k cli` | ❌ W0 | ⬜ pending |
| #4 regression | Existing `.done` idempotent-skip path unchanged (D-10) | — | N/A | unit (non-regression) | `make test-no-redownload` + `pytest test_pipeline.py -k done` | ✅ existing | ⬜ pending |
| #4 regression | Success path clears ledger / no false quarantine | — | N/A | unit | `pytest .../test_quarantine.py -k success_clears` | ❌ W0 | ⬜ pending |
| State safety | Startup recovery scan does not delete `inbox/failed/ledger.json` | T-06 (DoS) | Corrupt ledger degrades to `{}`, never kills daemon | unit | `pytest .../test_recovery.py -k ledger` | ⚠️ extend existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/worker/tests/test_quarantine.py` — new file covering WKR-01/02/03 pure predicate, record_failure, alert (4 elements + fires once), CLI list/clear, multi-round accumulation, success clears, corrupt-ledger degradation, disk re-read (restart survival)
- [ ] `apps/worker/tests/test_poller.py` — extend: `plan_downloads(quarantine_check=…)` → `skipped_quarantined`
- [ ] `apps/worker/tests/test_pipeline.py` — extend: `run_pipeline_once` multi-round failure isolation + success clears ledger + D-09 boundary (transcribe/manifest failure NOT counted)
- [ ] `apps/worker/tests/test_config.py` — extend: `max_fragment_failures` default + validation + summary line
- [ ] `apps/worker/tests/test_recovery.py` — extend: recover does not delete ledger.json
- [ ] Framework install: none — pytest/mypy/ruff already in uv workspace

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | All phase behaviors have automated verification | — |

*All phase behaviors have automated verification (Worker is pure-logic + injected-IO; no cloud/network needed in tests).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test_quarantine.py new + 4 existing files extended)
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
