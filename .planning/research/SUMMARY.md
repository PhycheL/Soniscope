# Project Research Summary

**Project:** SoniScope — pre-launch codebase audit milestone (report-only)
**Domain:** Two-language codebase audit (Python 3.11 mypy-strict Worker/FC + WeChat miniprogram vanilla JS); deliverable is a structured findings report, no code changes
**Researched:** 2026-07-04
**Confidence:** MEDIUM

## Executive Summary

This milestone's "product" is an audit report, so all four research tracks converge on the same insight: the report is only valuable if it is **credible (every finding evidence-backed at a pinned SHA) and directly consumable (findings convert 1:1 into fix-milestone work items)**. Professional audit practice converges on a macro-structure of scoping/inventory → parallel evidence collection → cross-referencing passes → single-sitting consolidation → report assembly. For SoniScope one component that generic audits treat as optional must be first-class: a **contract-tracing pass organized by contract family, not by component**, because the system's defining property is "OSS object as the only data contract, re-implemented in 3 places" (miniprogram JS, FC Python, Worker Python).

The recommended approach: (1) a setup phase that pins the audited commit, defines a severity rubric calibrated to this deployment (single-user, allowlist-gated MVP — not a generic production web service), defines the finding schema (ID, severity+rationale, file:line@SHA with quoted snippet, fix recommendation, S/M/L effort), and triages CONCERNS.md into an *unverified hypothesis backlog*; (2) parallel evidence-collection passes using **zero-footprint ephemeral tooling** (`uvx`, `npx -y`, brew — never touching `pyproject.toml`/`uv.lock` or adding a `package.json`, since polluting the baseline would corrupt the audit itself); (3) cross-referencing passes (contract divergence classification, docs-vs-code-truth, test-gap mapping); (4) one sequential consolidation/calibration sitting, then report assembly.

The key risks are all audit-process failures, not application risks: dumping raw tool output as findings (35–91% of static-analysis alerts are non-actionable), rating documented MVP tradeoffs as Critical, flagging load-bearing weirdness as bugs (the `issue-cedential` domain is genuinely misspelled by Aliyun and must NOT be "fixed"), fixing during the audit, and duplicate findings across the five overlapping dimensions. Mitigation is structural: tools produce *leads*, humans produce findings; a shared findings ledger with owner-dimensions; a required-reading gate (AGENTS.md + CONCERNS.md Fragile Areas) in every pass; and a zero-diff acceptance rule on `apps/`, `scripts/`, `docs/`.

## Key Findings

### Recommended Stack

The governing principle is **zero-footprint invocation**: every audit tool runs ephemerally so the audited baseline never changes. Python tools via `uvx`/`uv run --with`, JS tools via `npx -y`, binaries via brew; scratch configs live outside the repo. All versions were registry-verified on 2026-07-04 against host Node v22.18.0 / uv 0.8.14.

**Core technologies:**
- **ruff 0.15.20 (CLI `--select` extension)**: Python static analysis beyond the current gate — extends the repo's existing linter with complexity/security/debt rules without editing `pyproject.toml`
- **lizard 1.23.0**: the only mainstream analyzer giving one consistent complexity metric across both Python and JavaScript — essential for comparable two-language findings
- **jscpd 5.0.11**: cross-language duplication detection in a single run, JSON evidence output
- **ast-grep 0.44.1 + ripgrep**: contract-consistency structural extraction — no off-the-shelf "contract drift" tool exists; tooling extracts every contract touchpoint, the three-way comparison is analyst work
- **vulture 2.16 / madge 8.0.0**: dead-code detection (Python / JS respectively; knip cannot model the package.json-less miniprogram)
- **pytest-cov 7.1.0 (via `uv run --with`) + node:test built-in coverage**: coverage as *input evidence*, not a quality verdict; no gates added this milestone
- **lychee 0.24.2 (brew)**: docs link/file-reference integrity — directly evidences the known stale-AGENTS.md-references concern
- **ESLint 10.6.0 (scratch flat config outside repo)**: JS gap probe with manually declared `wx`/`App`/`Page` globals — no maintained WeChat-miniprogram ESLint plugin exists in 2026

Avoid: pylint (ruff overlap), SonarQube (server overhead for one-shot audit), pydoclint (noise on Chinese freeform docstrings), and any dependency added to the repo's own manifests.

### Expected Features

"Features" here are report components, judged by whether they make the report credible and consumable by the fix milestone.

**Must have (table stakes — P1):**
- Severity taxonomy (CRITICAL→INFO) + S/M/L/XL effort definitions, stated up front — everything else depends on them
- **Contract-consistency matrix** (fragment_id / object key / `x-oss-meta-*` × 3 implementations, with round-trip check) — the milestone's centerpiece
- Per-finding records: stable ID, severity justified via impact×likelihood, file:line evidence with quoted snippet (≤10 lines), concrete fix recommendation, T-shirt effort
- Findings summary table (one row per finding) — this *is* the fix-milestone backlog
- CONCERNS.md lead verification (confirm/refute each with fresh evidence, never copy)
- Executive summary + explicit scope/exclusions statement (pinned commit SHA, 5 dimensions, restated PROJECT.md exclusions)
- **"Do NOT fix" booby-trap register** — this codebase specifically punishes its absence (`issue-cedential` domain, `whisper-local` stub, handler mypy exclusions)

**Should have (differentiators — P2):**
- Launch-blocker verdicts (BLOCKER/PRE-LAUNCH/POST-LAUNCH) — severity ≠ urgency (e.g. `ENV='development'` is MEDIUM severity but a hard launch blocker)
- Remediation work packages ordered by impact÷effort — converts report → next milestone's phase list
- Cross-component contract test recipe (shared golden fixtures consumed by pytest and node:test)
- Positive findings section; per-dimension confidence statements

**Defer (v2+ / explicitly out of scope):**
- Target-state (FC 直转) contract gap analysis — belongs to the cutover milestone by user decision
- Pen-test-depth security analysis; automated drift detection in CI (a fix, not a report feature)
- Hour-precise estimates and numeric quality scores — anti-features

### Architecture Approach

Organize the audit as **passes with artifacts on disk**, flowing downstream-only: P0 baseline/rubric → Wave A parallel evidence collection (P1 contract extraction, P2 per-component deep dives, P3 scripts/toolchain) → Wave B cross-referencing (P4 contract divergence, P5 docs-vs-code, P6 test audit) → P7 single-sitting consolidation/calibration → P8 report assembly. Contract matrices (evidence) live separately from findings (judgments); one findings file per pass, append-only, so passes can run as parallel agents without merge conflicts; P7 is the only pass allowed to change severities.

**Major components (passes):**
1. **P0 Baseline & inventory** — freeze SHA, decide the dirty-tree question (3 docs deleted-but-uncommitted), severity rubric, finding schema, CONCERNS.md → hypothesis backlog
2. **P1 Contract extraction + P4 divergence classification** — matrices per contract family (fragment_id/key, `x-oss-meta-*`, FC HTTP surface, Worker `.done` state machine, config values); each divergence classified Benign / Latent / Active mismatch / Coverage hole, with producer/consumer tolerance (Postel) analysis: consumer-stricter-than-producer = silent data loss
3. **P2/P3 Per-component + toolchain dives** — quality/debt/dead code per tier; cross-boundary observations forwarded to the contract lane, never adjudicated locally
4. **P5/P6 Docs & test audits** — docs judged against Wave-A code-truth; test gaps prioritized by fragile areas found earlier
5. **P7/P8 Consolidation & report** — dedupe, root-cause clustering, single-voice severity calibration, then assembly (formatting only, zero new judgments)

### Critical Pitfalls

1. **Tool-output dumping** — define scan scope before any tool run (exclude `docs/example/start-fc-main/` — 29 MB / 1,003 vendor files — and the 4 agent-tooling trees); no finding ships without a human confirming it at the cited line; tools = leads, not findings
2. **Severity miscalibration against the wrong threat model** — rubric must be calibrated to a single-user allowlist-gated MVP; cross-check every High/Critical against CONCERNS.md accepted tradeoffs; >2–3 Criticals is a warning sign
3. **"Fixing" load-bearing weirdness** — required-reading gate (AGENTS.md, CONCERNS.md Fragile Areas) in every pass; the `issue-cedential` URL, whisper-local stub, and handler mypy exclusions are intentional; every finding records an "intentional-design check"
4. **Scope creep (fixing mid-audit, or auditing vs the FC-direct target design)** — zero-diff rule enforced at milestone acceptance; `docs/fc-transcribe-design.md` is reference-prohibited except as a future-consideration annotation
5. **Moving baseline + duplicate findings** — pin SHA day one, cite `path:line @ sha`; shared findings ledger with owner-dimension rule; explicit dedup/reconciliation pass at synthesis

## Implications for Roadmap

Based on research, suggested phase structure (5 phases):

### Phase 1: Audit Charter & Baseline (P0)
**Rationale:** Scope drift and inconsistent severity are the two classic audit failure modes; both are only preventable by upfront definition. Every downstream feature depends on the taxonomy/schema. All 8 pitfalls have their prevention rooted here.
**Delivers:** Pinned commit SHA + dirty-tree decision/inventory; scope inventory with recorded exclusions (`docs/example/`, agent-tooling dirs); calibrated severity rubric + launch-blocker semantics; finding record schema; effort-size definitions; CONCERNS.md triaged into UNVERIFIED hypothesis backlog; baseline `make lint typecheck test` snapshot; zero-diff acceptance rule in writing.
**Addresses:** Severity taxonomy, effort definitions, scope/methodology statement (all P1 table stakes).
**Avoids:** Pitfalls 1, 2, 4, 6, 7, 8 (all have setup-phase prevention).

### Phase 2: Contract Extraction & Divergence Analysis (P1 + P4)
**Rationale:** The milestone's headline dimension; its matrices feed three later passes (docs audit, test-gap audit, duplication census). Doing it early maximizes reuse. Merging extraction and diff into one phase keeps the evidence and its judgment adjacent while preserving the extract-then-judge discipline.
**Delivers:** Contract matrices (fragment_id/object-key, `x-oss-meta-*` producers/consumers, FC HTTP surface, Worker `.done` state machine, config values) with file:line per cell; cell-wise divergence findings classified Benign/Latent/Active/Coverage-hole; producer/consumer tolerance analysis; round-trip check (FC-signed key → `fragment_id_from_key`).
**Uses:** rg literal inventory → ast-grep structural extraction → manual three-way comparison; jscpd for Python↔Python overlap.
**Avoids:** Pitfall 8 (the matrix is the net-new value CONCERNS.md never executed); Anti-pattern 1 (component-by-component contract review).

### Phase 3: Component & Toolchain Deep Dives (P2 + P3)
**Rationale:** Parallelizable evidence collection; stays inside component boundaries, forwarding contract-shaped observations to Phase 2's matrices as leads. Can run parallel with Phase 2 (both depend only on Phase 1) if executed as separate plans/agents.
**Delivers:** Raw findings files for miniprogram, FC, Worker, and scripts/Makefile/deploy toolchain — quality, debt, dead code, error handling, ops fidelity.
**Uses:** ruff extended-select, vulture, lizard, ESLint scratch config, madge, deptry, pip-audit, scc — all ephemeral, JSON/CSV evidence archived under `.planning/`.
**Avoids:** Pitfall 1 (per-dimension human verification before findings enter the ledger); Pitfall 3 (required-reading gate).

### Phase 4: Docs/Config & Test Audits (P5 + P6)
**Rationale:** Deliberately after code passes — docs are judged against code-truth, and test-gap severity is meaningless without knowing where the fragile code is (e.g., "no cross-component contract test" gains severity because Phase 2 found latent divergence there).
**Delivers:** Docs-vs-code drift findings (lychee offline pass, config.js ↔ FC env ↔ docs cross-checks, `issue-cedential` documentation adequacy); test-quality and coverage-gap findings mapped to fragile areas; coverage measurements (pytest-cov + node:test) as evidence.
**Uses:** lychee, rg cross-checks, coverage tooling from STACK.md.
**Avoids:** Pitfall 5 (schema validation per finding before handoff).

### Phase 5: Consolidation, Calibration & Report Assembly (P7 + P8)
**Rationale:** Parallel lanes calibrate differently; a single sequential sitting restores severity comparability. Writing the report from uncalibrated findings bakes drift into the deliverable. Executive summary and remediation plan are synthesis features that can only be written last.
**Delivers:** Deduped, root-cause-clustered, globally calibrated findings register; final REPORT.md with executive summary, severity-ordered findings table, contract matrix, "do NOT fix" appendix, launch-blocker verdicts, remediation work packages, seeded-vs-net-new provenance counts, per-dimension confidence statements; zero-diff verification against the pinned SHA.
**Avoids:** Pitfalls 2, 6, 7 (calibration, staleness re-check, dedup all live here); Anti-patterns 4 and 5.

### Phase Ordering Rationale

- **Definitions before findings:** retrofitting severity/schema after findings exist causes silent re-grading — the strongest ordering constraint in FEATURES.md, and why Phase 1 gates everything.
- **Contract extraction in the first evidence wave, not after component dives:** it is the audit's headline dimension and its matrices feed docs, test, and duplication analysis downstream.
- **Docs and tests after code:** both are cross-referencing passes that need code-truth and fragile-area inputs (ARCHITECTURE.md Wave B).
- **Consolidation strictly before report, single-voice:** prevents severity drift from parallel lanes; the report is a projection of the register, not new content.
- **Phases 2 and 3 can run as parallel plans** within their wave (files-on-disk boundaries, one findings file per pass, append-only) if the executor supports it.

### Research Flags

Phases likely needing deeper research during planning:
- **None require external/web research.** All tooling is version-verified, and the methodology is fully specified. The analyst-heavy work (contract comparison) has no off-the-shelf tool by design.

Phases with standard patterns (skip research-phase):
- **Phase 1:** pure charter/definition work from PROJECT.md + this research; no unknowns.
- **Phases 2–4:** tool invocations are documented verbatim in STACK.md with verified versions; the comparison method is specified in ARCHITECTURE.md Patterns 1–2. Planning should focus on enumerating contract facets and audit units, not on researching techniques.
- **Phase 5:** mechanical given the finding schema; the calibration rubric is defined in Phase 1.

One planning-time verification worth doing (not research): spot-check the MEDIUM-confidence ecosystem claims from STACK.md (no WeChat-miniprogram ESLint plugin; pip-audit/uv.lock export bridge) when setting up Phase 3's tool runs — fallbacks are already documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | All versions registry-verified against PyPI/npm/GitHub APIs on 2026-07-04 and host-compatibility-checked (HIGH); usage-pattern and ecosystem claims are MEDIUM |
| Features | MEDIUM | No single authoritative spec for "audit report as product," but strong convergence across security-audit, internal-audit, and smart-contract-audit conventions; repo-specific requirements are HIGH (first-party PROJECT.md/CONCERNS.md) |
| Architecture | MEDIUM | Audit phase structure corroborated across multiple independent methodology sources; contract-tracing organization is a synthesis; repo facts HIGH |
| Pitfalls | MEDIUM-HIGH | External research MEDIUM (including academic sources on static-analysis actionability); every pitfall grounded in a specific, directly-observed trap in this repo (HIGH) |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Dirty-tree decision (blocking, Phase 1):** 3 docs are deleted-but-uncommitted in the working tree. Research recommends auditing the working tree as-is and recording the uncommitted state as a docs-dimension finding, but this must be decided and documented on day one — findings validity flips if the deletions are committed or reverted mid-audit.
- **node:test built-in coverage reliability:** the `--experimental-test-coverage` reporter may misattribute lines for the "load real page files" JS test harness; c8 11.0.0 is the documented drop-in fallback. Verify during Phase 4 setup.
- **Toolchain triage depth (Phase 3):** ~30 Worker CLI/verification modules — architecture research suggests deep-diving the deploy/rollback path and lighter passes on low-risk probe scripts; the exact triage line is a Phase 3 planning decision.
- **Bilingual report convention:** PROJECT.md is zh-primary; finding-schema field language must be fixed in Phase 1 to keep the report scannable.

## Sources

### Primary (HIGH confidence)
- PyPI JSON API / npm registry API / GitHub Releases API (2026-07-04) — all tool versions in STACK.md, registry-verified
- Host verification — Node v22.18.0, uv 0.8.14, tool availability, directly observed
- `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/ARCHITECTURE.md`, git working-tree state — report standard, scope exclusions, known leads, contract families, first-party

### Secondary (MEDIUM confidence)
- Smart-contract audit conventions (Trail of Bits/OpenZeppelin style, Cyfrin CodeHawks, Sherlock, Cantina, ChainSecurity) — severity taxonomy, per-finding format, impact×likelihood methodology
- Source-code audit methodology (Vaadata, Code Compliance Authority, internal-audit texts) — phase structure, evidence chains, findings consolidation
- Static-analysis actionability research (Nature Sci Data, TSE, MSR'19) — 35–91% non-actionable alerts; grounds the no-tool-dump rule
- Contract-testing / cross-deployment audit practice (Pactflow, Zuplo, cross-chain audit writeups) — N-way matrix and producer/consumer framing
- Tech-debt prioritization (vFunction, CodeScene, Codacy; T-shirt sizing) — effort-estimate and remediation-ordering conventions
- Node.js official docs via search — built-in test coverage status and thresholds

### Tertiary (LOW confidence)
- Ecosystem-practice claims flagged for spot-checking: absence of a maintained WeChat-miniprogram ESLint plugin; knip's package.json requirement; pip-audit/uv.lock export bridge pattern — fallbacks documented in STACK.md

---
*Research completed: 2026-07-04*
*Ready for roadmap: yes*
