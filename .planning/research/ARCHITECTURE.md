# Architecture Research

**Domain:** Systematic codebase audit (report-only milestone) over a multi-tier, two-language repo with N-way duplicated data contracts
**Researched:** 2026-07-04
**Confidence:** MEDIUM (audit phase structure corroborated across multiple independent methodology sources; contract-tracing organization is a synthesis of contract-testing and cross-deployment audit practice; repo-specific facts are HIGH — sourced from `.planning/codebase/`)

## Standard Architecture

Professional code audits (security firms, internal audit practice, compliance audits) converge on the same macro-structure: **scoping/inventory → evidence collection via per-dimension passes → finding classification → consolidated reporting**, with each phase producing artifacts that feed the next. For SoniScope, one extra first-class component is needed that generic audits treat as optional: a **cross-cutting contract tracing pass**, because the system's defining property is "OSS object as the only data contract, re-implemented in 3 places."

### System Overview (audit passes as components)

```
┌──────────────────────────────────────────────────────────────────────┐
│ PASS 0 — BASELINE & INVENTORY (must be first)                        │
│  freeze commit SHA · enumerate audit units · define severity rubric  │
│  + finding schema · import CONCERNS.md leads as UNVERIFIED hypotheses│
└──────┬───────────────────────────────────────────────────────────────┘
       │ scope list, rubric, hypothesis backlog
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ WAVE A — EVIDENCE COLLECTION (parallelizable)                        │
│ ┌──────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│ │ P1 Contract      │ │ P2 Per-component│ │ P3 Scripts & toolchain  │ │
│ │ extraction       │ │ deep dives      │ │ (scripts/, Makefile,    │ │
│ │ (build contract  │ │ (miniprogram JS,│ │  fc_deploy, live/E2E    │ │
│ │  matrices from   │ │  FC Python,     │ │  verification modules)  │ │
│ │  all 3 impls)    │ │  Worker Python) │ │                         │ │
│ └────────┬─────────┘ └────────┬────────┘ └────────────┬────────────┘ │
└──────────┼────────────────────┼───────────────────────┼──────────────┘
           │ contract matrices  │ raw findings          │ raw findings
           ▼                    ▼                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ WAVE B — CROSS-REFERENCING PASSES (need Wave A outputs)              │
│ ┌──────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│ │ P4 Contract diff │ │ P5 Docs/config  │ │ P6 Test audit           │ │
│ │ & divergence     │ │ consistency vs  │ │ (quality + gaps mapped  │ │
│ │ classification   │ │ code-truth      │ │  to fragile areas found │ │
│ │ (N-way matrix)   │ │ from Wave A     │ │  in Wave A)             │ │
│ └────────┬─────────┘ └────────┬────────┘ └────────────┬────────────┘ │
└──────────┼────────────────────┼───────────────────────┼──────────────┘
           │ divergence findings│ findings              │ findings
           ▼                    ▼                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ P7 — CONSOLIDATION & SEVERITY CALIBRATION (single sequential pass)   │
│  dedupe · cluster by root cause · cross-reference · re-rank ALL      │
│  findings against the rubric in one sitting · verify evidence links  │
└──────┬───────────────────────────────────────────────────────────────┘
       │ calibrated findings register
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ P8 — REPORT ASSEMBLY                                                 │
│  executive summary · findings register by severity · contract        │
│  coverage matrix · remediation roadmap (next-milestone input)        │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Pass | Responsibility | Boundary (what it covers / does NOT cover) |
|------|----------------|--------------------------------------------|
| P0 Baseline & inventory | Freeze the audited commit, enumerate every file into an audit unit (main code / scripts / docs-config / tests / excluded), define severity rubric + finding record schema, import `.planning/codebase/CONCERNS.md` leads as *unverified hypotheses* | Does NOT produce findings — only scope, rubric, and a hypothesis backlog |
| P1 Contract extraction | For each contract family, extract the *de facto* contract from each implementation into a normalized table (element × implementation, with file:line per cell) | Extraction only — no judging. Covers: fragment_id grammar & object-key mapping, `x-oss-meta-*` fields, FC HTTP request/response/error-code surface, Worker disk state machine artifacts, miniprogram queue states, config values (config.js ↔ FC env ↔ config.yaml) |
| P2 Per-component deep dives | Code quality, tech debt, fragile areas, error handling, dead code per tier: `apps/miniprogram/`, `apps/fc/`, `apps/worker/` | Stays inside one component; anything crossing a boundary is handed to P1/P4 as a contract lead, not judged locally |
| P3 Scripts & toolchain | `scripts/`, `Makefile`, `fc_deploy.py`, live/E2E verification modules, packaging/vendoring path | Includes ops fidelity (deploy/rollback/backup); excludes docs (P5) and the main pipeline (P2) |
| P4 Contract diff & divergence | Cell-wise diff of P1 matrices; classify each divergence (see Pattern 1); producer/consumer tolerance analysis | Consumes P1 output only; current-state vs current-state — explicitly NOT vs `docs/fc-transcribe-design.md` target design (out of scope per PROJECT.md) |
| P5 Docs/config consistency | `docs/`, `AGENTS.md`, `config.js` comments, runbooks vs the code-truth established in Wave A (dead links, stale authority chain, `issue-cedential` documentation adequacy) | Judges docs against code, never code against docs |
| P6 Test audit | Test quality (assertion strength, fake fidelity) + coverage gaps, prioritized by fragile areas surfaced in P2/P4 | Does NOT re-audit product code; maps risk found elsewhere to test coverage |
| P7 Consolidation & calibration | Dedupe, cluster multi-symptom findings under one root cause, cross-link related findings, apply severity rubric to the *whole* register in one sitting, attach effort estimates | The only pass allowed to change severity; no new evidence gathering |
| P8 Report assembly | Executive summary, register ordered by severity, contract coverage matrix, remediation roadmap sequenced for the fix milestone | Formatting/synthesis only; zero new judgments |

## Recommended Project Structure (audit artifacts)

The audit's "codebase" is its evidence trail. Keep intermediate artifacts on disk so passes can run in separate sessions/agents and findings stay evidence-linked:

```
.planning/audit/                      # working artifacts (or phase dirs per GSD convention)
├── 00-baseline.md                    # commit SHA, scope inventory, exclusions + reasons
├── 00-rubric.md                      # severity definitions + finding record schema
├── 00-hypotheses.md                  # CONCERNS.md leads, each marked UNVERIFIED
├── contracts/
│   ├── fragment-id-object-key.md     # extraction matrix: element × {miniprogram, FC, Worker}
│   ├── oss-metadata.md               # x-oss-meta-* writers vs readers
│   ├── fc-http-api.md                # request/response/error codes vs classifyFcResponse
│   ├── worker-state-machine.md       # 5-artifact + .done contract: writers vs readers (pipeline/recovery/retranscribe)
│   └── config-values.md              # config.js ↔ FC env vars ↔ config.yaml ↔ docs
├── findings/
│   ├── P2-miniprogram.md             # raw findings, one file per pass (append-only)
│   ├── P2-fc.md
│   ├── P2-worker.md
│   ├── P3-toolchain.md
│   ├── P4-contract-divergence.md
│   ├── P5-docs-config.md
│   └── P6-tests.md
└── REPORT.md                         # final deliverable (P8)
```

### Structure Rationale

- **contracts/ separate from findings/:** extraction matrices are *evidence*, reusable by the next (fix) milestone and by the future FC-direct cutover milestone; findings are *judgments* on that evidence. Keeping them apart lets P7 re-verify any judgment against its matrix.
- **One findings file per pass:** passes can run as parallel agents without merge conflicts; consolidation (P7) reads all and owns the merged register.
- **Append-only during collection:** no finding edited after the pass ends until P7 — prevents severity drift and lost evidence.

## Architectural Patterns

### Pattern 1: Contract matrix with divergence taxonomy (the core of N-way contract tracing)

**What:** For each contract family, organize the audit **by contract, not by component**. Build a table: rows = contract elements (e.g., fragment_id regex, key prefix, `.wav` extension rule, each `x-oss-meta-*` field, each error code), columns = implementations, cells = exact observed behavior + file:line. Then diff cell-wise and classify every divergence into one of four classes:

1. **Benign** — intentional, documented (e.g., miniprogram only *previews* the key; FC is authoritative)
2. **Latent** — currently compatible, but breaks silently if one side changes (the classic "silent divergence" problem cross-deployment auditors flag)
3. **Active mismatch** — inconsistent today; produces wrong behavior now
4. **Coverage hole** — an element one implementation handles and another ignores entirely

**When to use:** whenever ≥2 independent implementations encode the same convention with no machine-checked single source of truth — exactly SoniScope's `object_key_for` in `fc_shared/sts.py`, `oss_admin.py`, and the JS key preview.

**Trade-offs:** extraction is tedious and feels like "not finding bugs yet" — but per-component review provably misses cross-lane contract defects; only multi-file, contract-centric comparison surfaces them. The matrix is also directly reusable when the `transcribe-audio` parser is added later.

**Example (fragment_id family, sketch):**

```markdown
| Element              | miniprogram (JS)           | FC (fc_shared/sts.py)      | Worker (oss_admin/poller)   | Verdict |
|----------------------|----------------------------|----------------------------|------------------------------|---------|
| id grammar           | ulid.js + device.js @L..   | _FRAGMENT_ID_RE @L..       | fragment_id_from_key @L..    | ?       |
| key template         | audio.js preview @L..      | object_key_for @L..        | object_key_for @L..          | ?       |
| extension rule       | always .wav?               | always .wav                | expects .wav                 | ?       |
| date component TZ    | device local?              | which clock?               | parsed from key              | ?       |
```

### Pattern 2: Producer/consumer tolerance analysis (Postel analysis)

**What:** For every contract element, record which side *produces* and which *consumes*, then compare acceptance sets, not intent. Direction determines severity: producer stricter than consumer = safe slack; **consumer stricter than producer = silent data loss** (SoniScope's known worst-case: `fragment_id_from_key` returns `None` → object skipped forever, invisible).

**When to use:** during P4 for every row of every matrix. It converts "the regexes differ" (observation) into "uploads with X-shaped ids are permanently invisible to the Worker" (impact statement with a severity).

**Trade-offs:** requires reasoning about actual value spaces (what can `ulid.js` + `device_short_id` actually emit?) rather than reading code side-by-side — slower, but it's the difference between a diff report and an audit.

### Pattern 3: Findings register with a fixed record schema

**What:** Every finding, from every pass, uses one schema from day one (defined in P0):

```yaml
id: AUD-042
pass: P4-contract
title: "..."
severity: P2          # provisional until P7; final after calibration
confidence: verified  # verified (evidence in hand) | suspected (needs repro)
evidence: [apps/fc/shared/fc_shared/sts.py:47, apps/worker/src/soniscope_worker/poller.py:112]
impact: "..."         # concrete failure mode, not category name
recommendation: "..."
effort: S|M|L
related: [AUD-017]
```

**When to use:** always — PROJECT.md's report standard (severity + file:line evidence + fix suggestion + effort estimate) is exactly this schema; enforcing it at collection time makes P7/P8 mechanical.

**Trade-offs:** none meaningful; the only cost is discipline during deep dives.

### Pattern 4: Hypothesis-driven start, evidence-gated findings

**What:** The existing codebase map (`CONCERNS.md`) already lists ~20 leads (`issue-cedential` domain, committed presigned URL, stale AGENTS.md references, duplicated contract logic…). Import them in P0 as a hypothesis backlog, but **no hypothesis enters the findings register until re-verified with current file:line evidence** during the relevant pass. Passes also *must not* limit themselves to the backlog.

**When to use:** whenever an audit follows an automated/prior mapping exercise — the map is intelligence, not evidence.

**Trade-offs:** some duplicate effort re-confirming known items; the payoff is a report where every line is defensible, which is the milestone's entire value ("可信、有证据").

### Pattern 5: Single-sitting severity calibration

**What:** Passes assign *provisional* severities; P7 re-ranks the entire register in one sequential sitting against the P0 rubric, comparing findings *relative to each other* ("is this stale doc link really the same severity as the consumer-stricter regex?"). Rubric anchored to launch-gating semantics:

| Level | Meaning (launch framing) |
|-------|--------------------------|
| P0 Blocker | Launch unsafe: data loss, security exposure, active contract mismatch on the happy path |
| P1 High | Breaks under likely real conditions, or latent divergence with silent-failure mode |
| P2 Medium | Concrete failure path exists but bounded/recoverable; debt that will tax the next milestone |
| P3 Low | Quality/consistency issues, stale docs, style debt |
| P4 Info | Observations, intentional stubs (e.g., `whisper-local`), context for future milestones |

**When to use:** always in multi-pass audits, and doubly so when passes run as parallel agents — independent graders drift; a single calibration pass restores comparability (standard practice in security-audit finding classification).

**Trade-offs:** P7 must be sequential and by one "voice"; that's the point.

## Data Flow

### Findings/evidence flow between passes

```
CONCERNS.md leads ──► P0 hypothesis backlog ──┐ (UNVERIFIED tags)
                                              ▼
Repo @ frozen SHA ──► P1 contract matrices ──► P4 divergence findings
                 └──► P2/P3 raw findings ────┐
P1+P2 code-truth ──► P5 docs findings ───────┤
P2/P4 fragile areas ──► P6 test-gap findings ┤
                                              ▼
                    P7 consolidated + calibrated register
                                              ▼
                    P8 REPORT.md ──► next milestone (fix) backlog
```

- **Downstream, never upstream:** later passes may consume earlier artifacts; no pass edits an earlier pass's file. If P5 discovers a code issue, it files it in its own findings file tagged for P7 to re-home.
- **Evidence links are the join key:** every finding points at file:line in the frozen SHA; contract findings additionally point at a matrix row. P7 rejects findings with dangling evidence.
- **The report is a projection**, not new content: P8 reorders/summarizes the register; disagreements found while writing the report go back to P7, not into prose.

### Key data flows

1. **Lead → hypothesis → verified finding:** prior-map items travel with an UNVERIFIED tag until a pass attaches fresh evidence.
2. **Matrix row → divergence class → severity:** contract findings derive severity from divergence class + producer/consumer direction (Pattern 2), making contract severities mechanically defensible.
3. **Fragile area → test-gap:** P6 prioritizes coverage-gap findings by whether the gap sits on top of a P2/P4 fragile area (e.g., "no cross-component contract test" gains severity because P4 found latent divergence there).

## Suggested Build Order (audit-phase dependency structure)

| Order | Phase | Depends on | Parallel? |
|-------|-------|------------|-----------|
| 1 | P0 Baseline, inventory, rubric | — | No (gates everything) |
| 2 | P1 Contract extraction; P2 miniprogram / FC / Worker deep dives; P3 toolchain | P0 | Yes — up to 5 parallel lanes |
| 3 | P4 contract diff; P5 docs/config; P6 tests | P4←P1; P5←P1+P2 (code-truth); P6←P2+P4 (fragile areas) | Yes among themselves |
| 4 | P7 consolidation + calibration | all findings files | No (single sitting) |
| 5 | P8 report assembly | P7 register | No |

**Ordering rationale:**
- P0 first because scope drift and inconsistent severity are the two classic audit failure modes; both are prevented only by upfront definition.
- Contract extraction (P1) in the *first* parallel wave, not after component dives — it's this audit's headline dimension and its matrices feed three later passes.
- Docs (P5) and tests (P6) deliberately *after* code passes: docs are judged against code-truth, and test-gap severity is meaningless without knowing where the fragile code is.
- Consolidation strictly before report: writing the report from uncalibrated findings bakes drift into the deliverable.

## Anti-Patterns

### Anti-Pattern 1: Auditing contracts component-by-component

**What people do:** Review `apps/fc/` fully, then `apps/worker/`, then miniprogram, noting contract code in each as they go.
**Why it's wrong:** Cross-lane contract defects are invisible in single-component review; each implementation looks locally correct. Divergence only appears when the three are laid side-by-side per element.
**Do this instead:** Pattern 1 — a dedicated contract pass organized by contract family, with the per-component passes explicitly forbidden from adjudicating cross-boundary questions.

### Anti-Pattern 2: Fixing while auditing

**What people do:** "This stale AGENTS.md link takes 30 seconds to fix" — and the baseline starts moving under the audit.
**Why it's wrong:** Evidence (file:line at the frozen SHA) goes stale, findings become unreproducible, and the report loses its "trustworthy snapshot" property. PROJECT.md already made this a hard constraint.
**Do this instead:** Everything — even one-line fixes — goes into the register with an effort estimate; the next milestone burns the list down.

### Anti-Pattern 3: Trusting the prior map as findings

**What people do:** Copy CONCERNS.md items into the report with severities attached.
**Why it's wrong:** The map was generated for orientation, not adjudication; files may have changed, and unverified claims poison the credibility of verified ones sitting next to them.
**Do this instead:** Pattern 4 — hypothesis backlog, evidence gate.

### Anti-Pattern 4: Per-pass severity finalization

**What people do:** Each deep-dive lane ships final severities; the report concatenates them.
**Why it's wrong:** Parallel lanes (especially parallel agents) calibrate differently; a "High" from the docs lane and a "High" from the contract lane won't mean the same thing, and the fix milestone will sequence work wrongly.
**Do this instead:** Pattern 5 — provisional at collection, single-sitting global calibration at P7.

### Anti-Pattern 5: Flat findings list without root-cause clustering

**What people do:** Report 6 separate findings that are all symptoms of "docs moved, references not updated."
**Why it's wrong:** Inflates counts, obscures the actual remediation unit, makes effort estimates wrong (6×S vs 1×M).
**Do this instead:** P7 clusters by root cause; the register keeps symptoms as evidence under one parent finding with `related:` links.

## Integration Points

### Inputs (external to the audit)

| Source | Integration pattern | Notes |
|--------|---------------------|-------|
| `.planning/codebase/*` (7 docs) | Read-only intelligence feeding P0's inventory and hypothesis backlog | Especially CONCERNS.md (leads) and ARCHITECTURE.md (contract family enumeration) |
| Repo at frozen commit | Sole evidence source | Freeze the SHA in P0; note the currently-uncommitted `docs/` deletions — decide in P0 whether the working tree or HEAD is the audited state and record it |
| `make lint` / `make typecheck` / `make test` output | Cheap automated evidence for P2/P6 | Run once at P0 against the frozen SHA; attach outputs as baseline evidence |

### Internal boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| P1 ↔ P2 lanes | P2 forwards contract-shaped observations to P1's matrix files as *leads*; never adjudicates them | Prevents double-judging and contradictory verdicts |
| Wave A ↔ Wave B | Files on disk only (`contracts/`, `findings/`) | Enables separate sessions/agents per pass |
| P7 ↔ everything | P7 reads all, owns the merged register; earlier files become immutable | Single-writer consolidation |
| P8 ↔ next milestone | REPORT.md remediation roadmap is the fix-milestone's requirements input | Effort estimates + severity ordering must be present per PROJECT.md constraints |

## Scaling Considerations (audit sizing for this repo)

| Repo reality | Adjustment |
|--------------|------------|
| ~3 main components + tests, single developer, no DB/queue | Full-breadth, moderate-depth audit is feasible in one milestone; don't sample — inventory shows the surface is enumerable |
| `docs/example/start-fc-main/` (29 MB vendored sample) | Exclude from deep dives in P0 with a recorded reason; file one finding about its presence, don't audit its contents |
| ~30 Worker CLI/verification modules | P3 may triage: deep-dive deploy/rollback path (production-critical), lighter pass on probe scripts already flagged low-risk |
| Two languages (mypy-strict Python, WeChat JS) | Per-language checklists inside P2 (e.g., mypy exclusions, lazy-import discipline for Python; deps-injection purity, wx-API leakage for JS) — one rubric, language-specific evidence tools |

## Sources

- [Vaadata — Source Code Audit: Understanding the Methodology & Process](https://www.vaadata.com/en/blog/understanding-source-code-audit-methodology-and-process/) — phase structure of professional source-code audits (MEDIUM)
- [Code Compliance Authority — The Code Compliance Audit Process: Steps, Evidence, and Reporting](https://codecomplianceauthority.com/code-compliance-audit-process) — five-phase model (scoping → evidence → testing → classification → report), finding record fields, report anatomy (MEDIUM)
- [Internal Auditing: A Practical Approach — Audit Methodology and Execution](https://ecampusontario.pressbooks.pub/internalauditing/chapter/08-01-audit-methodology-and-execution/) — evidence chains, working-paper discipline, findings consolidation (MEDIUM)
- [Chainscore Labs — Cross-Chain Protocol Auditing](https://chainscorelabs.com/blog/smart-contract-auditing-and-best-practices/cross-chain-protocol-auditing) and [Blockchain App Factory — Cross-Chain Smart Contract Audits](https://medium.com/predict/cross-chain-smart-contract-audits-how-to-secure-multi-network-deployments-eb0abc1c08dc) — comparing N deployed implementations, "silent divergence" detection, intentional-vs-unintentional difference classification (MEDIUM)
- [Zuplo — Guide to Contract Testing for API Reliability](https://zuplo.com/learning-center/guide-to-contract-testing-for-api-reliability) — producer/consumer contract verification framing (MEDIUM)
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md`, `.planning/PROJECT.md` — repo facts, contract families, known leads, milestone constraints (HIGH — first-party)

---
*Architecture research for: SoniScope pre-launch codebase audit milestone*
*Researched: 2026-07-04*
