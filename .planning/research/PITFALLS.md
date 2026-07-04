# Pitfalls Research

**Domain:** Pre-launch codebase audit milestone (report-only) — WeChat miniprogram + Aliyun FC + OSS + local Python Worker monorepo
**Researched:** 2026-07-04
**Confidence:** MEDIUM (external research: web-verified MEDIUM; repo-specific groundings: HIGH — read directly from `.planning/codebase/` and `.planning/PROJECT.md`)

This milestone produces an audit REPORT, not code. The pitfalls below are therefore about the *audit process itself* failing — findings that are inflated, miscalibrated, unactionable, stale, or duplicated — not about the application domain. Each pitfall is grounded in a specific trap already visible in this repository.

## Critical Pitfalls

### Pitfall 1: Tool-Output Dumping Instead of Verified Analysis

**What goes wrong:**
The audit runs ruff/mypy/ESLint/grep across the repo and pastes raw output into the report as "findings." Research shows 35–91% of static-analysis warnings are non-actionable, and false-positive rates reach 90%; a raw dump destroys the report's credibility and buries the ~10 findings that matter under hundreds that don't. In this repo the trap is amplified: `docs/example/start-fc-main/` is a 29 MB vendored copy of Alibaba's FC starter repo (1,003 tracked files, its own handlers/configs). Any repo-wide tool run or grep will "find" problems in vendor code that isn't SoniScope's.

**Why it happens:**
Tool output feels like progress and evidence. Verifying each warning (open the file, confirm the issue is real *in context*) is slow and unglamorous, so auditors skip it under time pressure.

**How to avoid:**
- Define an explicit scan scope BEFORE running any tool: `apps/`, `scripts/`, `Makefile`, `docs/` (excluding `docs/example/start-fc-main/`), root configs. Record the exclusion list in the report's methodology section.
- Hard rule: no finding enters the report without a human having opened the cited file and confirmed the issue at that line. Tool output is a *lead list*, not a findings list.
- Report the tool-run statistics separately ("ruff raised N in scope, M verified as real") so triage effort is visible without polluting findings.
- Note that `scripts/` is *deliberately* excluded from mypy/ruff scope (documented in the Makefile lint target comment: "遗留 scripts/ 由各自 story 收口") — a fresh ESLint run over miniprogram JS will similarly dump findings the home-grown `miniprogram_lint.py` was never meant to catch. New-tool output on code that never targeted that tool needs calibrated severity, not 1:1 finding conversion.

**Warning signs:**
- Findings count exceeds ~50 for a codebase this size (three apps, ~single-developer MVP).
- Findings citing paths under `docs/example/` or `.claude/`/`.cursor/`/`.codex/`/`.agents/`.
- Findings whose "evidence" is only a tool name and rule ID with no quoted code.

**Phase to address:**
Audit setup/charter phase (scope + methodology definition, before any dimension audit runs); enforced in every dimension-audit phase.

---

### Pitfall 2: Severity Miscalibration Against the Wrong Threat Model

**What goes wrong:**
Findings get rated against a generic "production web service" rubric instead of this system's actual context: a single-user, allowlist-gated, personal transcription pipeline in MVP deployment. Research identifies threat-model misalignment as the single largest false-positive category (~57% in one audit study). Concretely: "no rate limiting on issue-credential," "wsgiref as FC server," "plaintext config.yaml keys," and "miniprogram receives raw STS secrets" would all rate Critical on a generic rubric — but CONCERNS.md documents each as an accepted, mitigated, or inherent MVP tradeoff (STS is single-object, PutObject-only, ≤900 s; config file permission is checked for 600; allowlist is the explicit auth model).

**Why it happens:**
Severity rubrics are imported from OWASP/pentest templates without adapting the likelihood axis to a one-user system, and auditors reviewing files in isolation lack the design-intent context (research: reviews "lack the full context of the code's purpose," leading to wrong severity).

**How to avoid:**
- Write a severity matrix (likelihood × impact) calibrated to THIS deployment before auditing: e.g., Critical = breaks the upload→transcribe pipeline or leaks credentials usable beyond one object; High = silent data loss or contract mismatch; Medium = drift/debt that will bite the next milestone; Low = hygiene.
- Require documented rationale per rating ("why this severity given single-user MVP context") — standard IS-audit practice.
- Cross-check every High/Critical against CONCERNS.md and AGENTS.md red lines: if the "vulnerability" is a documented accepted tradeoff, report it as "accepted risk — confirm before launch" at reduced severity, not as a defect.
- Asymmetry note: research says missed true H/M findings cost more than triaging false positives — so err toward *including* borderline findings but *rating them honestly*, never inflating severity to get attention.

**Warning signs:**
- More than 2–3 Critical findings in a codebase CONCERNS.md describes as having "no known bugs in application code."
- Severity assigned by tool default (e.g., ESLint "error") rather than project rubric.
- Findings that restate a documented Key Decision or Out-of-Scope item as a defect.

**Phase to address:**
Audit setup phase (define the calibrated severity matrix as a deliverable); report-synthesis phase (severity consistency review across all dimensions).

---

### Pitfall 3: "Fixing" Load-Bearing Weirdness — Context-Free False Positives

**What goes wrong:**
The audit flags intentional oddities as defects with fix recommendations that would break production. This repo has landmines documented precisely because they look like bugs:
- `apps/miniprogram/config.js:10` — the FC domain is genuinely spelled `issue-cedential-...fcapp.run` (Aliyun assigned it; missing "r" is correct). A finding recommending "fix typo" would break the miniprogram against the WeChat domain whitelist and the live function.
- `apps/worker/src/soniscope_worker/transcriber.py:~145` — `WhisperLocalTranscriber.transcribe` raises by design ("本期不部署本地 Whisper", an AGENTS.md red line).
- FC `handler.py` files excluded from mypy strict — deliberate (module-name collision), compensated by behavioral tests.
- `ENV = 'development'` in `config.js:29` — this one IS a real pre-launch finding, but the fix is a release-checklist item, not a code bug.

**Why it happens:**
Auditors (human or AI) pattern-match "typo," "stub raises," "type-check exclusion" to defects without reading inline comments and AGENTS.md. Research categorizes this as "incorrect analysis" false positives — a top-four category.

**How to avoid:**
- Mandatory pre-audit reading: AGENTS.md, `.planning/codebase/CONCERNS.md` (especially "Fragile Areas"), and inline comments at any line being cited. The Fragile Areas section is effectively a pre-published false-positive suppression list.
- Add a report field per finding: "Intentional-design check: [what was consulted to rule out deliberate behavior]."
- Findings on fragile areas must quote the existing warning comment and explain why the finding stands *despite* it, or be reclassified as "documented fragility — recommend guardrail (e.g., test/comment/lint rule), not change."

**Warning signs:**
- A finding recommends editing the `issue-cedential` URL string.
- A finding calls the whisper-local stub or handler mypy exclusion a bug without referencing the documented rationale.
- Fix recommendations that contradict AGENTS.md red lines.

**Phase to address:**
Every dimension-audit phase (required-reading gate in each phase's plan); report-synthesis phase (fragile-area cross-check pass).

---

### Pitfall 4: Scope Creep — Fixing During the Audit, or Auditing Against the Target Design

**What goes wrong:**
Two forms, both explicitly ruled out by PROJECT.md:
1. **Fix creep:** The auditor sees an easy win (AGENTS.md dead links, the expired presigned URL in `scripts/test_asr.py`, committing the pending docs deletions) and fixes it "while here." This pollutes the baseline mid-audit: later audit passes now disagree with earlier ones about the same file, and the report no longer describes any single state of the repo.
2. **Target-state creep:** The contract-consistency audit drifts into comparing current code against `docs/fc-transcribe-design.md` (the FC-direct future architecture). PROJECT.md explicitly scopes contract audit to *current-state mutual consistency* of the three implementations; FC-direct gap analysis belongs to the cutover milestone.

**Why it happens:**
Fixing feels more valuable than documenting; and the FC-direct design doc is prominent (CONCERNS.md's own top item is "FC-direct decided but not implemented"), so it gravitationally pulls the analysis toward "what should be" instead of "what is consistent now."

**How to avoid:**
- Zero-diff rule: the audit milestone produces files only under the report's output directory; `git status` on `apps/`, `scripts/`, `docs/`, root configs must be unchanged (beyond what was already dirty at baseline) at milestone end. Make this a milestone acceptance check.
- Findings that are tempting quick fixes get an "effort: trivial (<15 min)" tag so the fix milestone can batch them day one — the tag is the pressure valve for the fix urge.
- Contract-audit charter states the comparison set explicitly: `fc_shared/sts.py` ↔ `oss_admin.py`/`poller.py` ↔ `utils/audio.js` (+ `x-oss-meta-*` producers/consumers + `.done` state-machine conventions). `docs/fc-transcribe-design.md` is reference-prohibited except as a "future consideration" annotation.

**Warning signs:**
- Any commit during the audit touching `apps/`, `scripts/`, or `docs/` content.
- Findings phrased as "does not implement design doc §X" in the contract-consistency section.
- Findings about the missing `transcribe_audio/` function rated as defects (it's a decided-but-future feature, out of audit scope).

**Phase to address:**
Audit setup phase (zero-diff rule + comparison-set charter in writing); milestone-audit/acceptance (verify zero diff).

---

### Pitfall 5: Findings Without Evidence or Actionable Fixes

**What goes wrong:**
Findings like "test coverage is weak in the miniprogram" or "documentation is inconsistent" with no file/line, no reproduction, no concrete recommendation, and no effort estimate. Pentest-industry consensus: "findings without proof are suggestions, not validated risks." PROJECT.md makes the bar contractual: every finding needs severity + file/line evidence + fix recommendation + effort estimate, because the report is the direct input to the next (fix) milestone's planning. An evidence-free finding cannot be turned into a fix-phase task and will be dropped or re-investigated from scratch — wasting the audit.

**Why it happens:**
Vague findings are cheap to write; precise evidence requires re-locating and quoting code. Effort estimates feel like guesses, so auditors omit them.

**How to avoid:**
- Define a finding schema up front and validate every entry against it: `ID | dimension | severity+rationale | file:line(s) + quoted evidence | impact | fix recommendation (specific enough to become a task) | effort (S <1h / M <1d / L multi-day) | related findings`.
- Effort uses coarse T-shirt buckets, not hours — coarse-but-present beats precise-but-missing, and research confirms effort estimates are what make prioritization possible ("an hour fix vs a two-week refactor is a different conversation").
- Ban aggregate findings: "tests are weak" must decompose into per-gap findings (e.g., "no cross-component contract test for fragment_id round-trip — `apps/fc/tests/test_sts.py` and `apps/worker/tests/test_poller.py` each test their own side only").
- Evidence must survive the reader not having the repo open: quote the relevant line(s), don't just cite them.

**Warning signs:**
- Any finding lacking a file path.
- Fix recommendations starting with "consider," "improve," or "review" without an object.
- Effort column empty or uniformly "M."

**Phase to address:**
Audit setup phase (schema as deliverable); every dimension-audit phase (schema-validation before handing findings to synthesis).

---

### Pitfall 6: Moving Baseline — Auditing a Codebase That Shifts Under You

**What goes wrong:**
Findings reference line numbers and file states that no longer exist by report delivery, making evidence unverifiable and fixes mis-targeted. This repo is *already* in a shifted state at audit start: `docs/PRD_v1.md`, `docs/tech-spec.md`, `docs/deployment-guide.md` are deleted in the working tree but uncommitted (git status shows `D`), and the current branch (`ralph/soniscope-mvp-claude`) is active development. If the docs deletions get committed mid-audit — or reverted — the entire docs-consistency dimension's findings flip validity.

**Why it happens:**
Audits take days; development doesn't pause; and nobody pins the ref, so each audit pass silently reads a different tree.

**How to avoid:**
- Pin the baseline: record the exact commit SHA (and an explicit inventory of uncommitted working-tree deltas — the doc deletions are themselves audit evidence) in the report header on day one. All findings cite `path:line @ <sha>`.
- Decide the dirty-tree question at setup: either (a) audit the working tree as-is and document the uncommitted state as Finding #1 of the docs dimension, or (b) require the team to commit/stash to a clean state first, then pin. Option (a) fits this milestone — the uncommitted doc move + stale AGENTS.md references IS a core expected finding.
- Freeze rule during the audit window: no merges to the audited branch until the report ships; if an urgent change lands, re-verify only the findings touching changed files (git diff against the pinned SHA tells you exactly which).
- Final pass before delivery: `git diff <pinned-sha>` — re-verify any finding whose cited file changed.

**Warning signs:**
- Findings citing line numbers without a SHA.
- Report sections written on different days disagreeing about whether `docs/tech-spec.md` exists.
- `git log` showing commits to `apps/` during the audit window.

**Phase to address:**
Audit setup phase (pin SHA, dirty-tree decision, freeze agreement); report-synthesis phase (diff-based staleness re-verification).

---

### Pitfall 7: Duplicate and Contradictory Findings Across Audit Dimensions

**What goes wrong:**
The milestone has five audit dimensions (contract, code quality, scripts/tooling, docs/config, tests) that overlap heavily, and if run as parallel passes they will each independently discover the same issues — with different severities, evidence, and recommendations. Guaranteed collisions in this repo: AGENTS.md dead links (docs dimension AND tooling dimension, since agents consume it), the fragment_id triple implementation (contract AND code-quality AND test-gap dimensions), `scripts/test_asr.py` (scripts AND security-adjacent AND legacy-SDK debt), the quadruplicated `.claude/`/`.cursor/`/`.codex/`/`.agents/` trees (one issue that naive scanning reports four times). A report where finding #12 and finding #37 are the same issue at different severities is not trustworthy and double-counts the fix milestone's workload.

**Why it happens:**
Parallel auditors (or sequential passes without a shared ledger) have no dedup mechanism; each pass optimizes for completeness within its dimension. Industry tooling (bug-bounty triage, pentest platforms) treats deduplication as a first-class pipeline step for exactly this reason.

**How to avoid:**
- Single shared findings ledger with stable IDs, written to incrementally by every dimension pass; before adding a finding, search the ledger by file path.
- One finding, one owner-dimension: cross-cutting issues get ONE entry with a "surfaces in dimensions: X, Y" field, not N entries.
- Synthesis phase runs an explicit dedup pass: group findings by file path, merge overlaps, and reconcile severity conflicts (conflict = forced re-verification, which also catches miscalibration).
- For the quadruplicated tooling dirs specifically: pre-declare in the charter that agent-scaffolding directories are audited once as a single "duplication drift" finding, not file-by-file.

**Warning signs:**
- Two findings citing the same file:line range.
- Same root cause described with different severities in different report sections.
- Findings count that scales with the number of audit passes rather than with actual issues.

**Phase to address:**
Audit setup phase (shared ledger structure + owner-dimension rule); report-synthesis phase (dedup + severity-reconciliation pass).

---

### Pitfall 8: Re-Discovering CONCERNS.md Without Adding Audit Value

**What goes wrong:**
`.planning/codebase/CONCERNS.md` (2026-07-04, same date as this milestone) already catalogs most known issues — the misspelled domain, the committed presigned URL, the doc-move drift, the contract triplication, coverage gaps. Two opposite failures: (a) the audit copies CONCERNS.md into report format and calls it done — no verification, no severity rationale, no effort estimates, no *new* findings; or (b) the audit ignores CONCERNS.md, spends its budget re-deriving known issues from scratch, and misses the unknown ones.

**Why it happens:**
An existing concerns document is either treated as authoritative (it isn't — it's a codebase-mapping snapshot, not an evidence-graded audit) or as competition to be ignored.

**How to avoid:**
- Treat CONCERNS.md entries as *hypotheses to verify*: each becomes a candidate finding that must independently pass the evidence bar (open the file, confirm line numbers, confirm still true at the pinned SHA) and get severity + effort per the audit rubric. Mark provenance ("seeded from CONCERNS.md, verified" vs "net-new").
- Budget explicitly for net-new discovery: the audit's differentiated value is (1) evidence-grade verification of known concerns, (2) the *contract-consistency current-state matrix* (which CONCERNS.md flags but doesn't execute — it notes "no single cross-component contract test" but never diffs the three implementations field-by-field), and (3) systematic coverage of dimensions CONCERNS.md sampled (every doc↔code claim, every Makefile target, every test file's assertions).
- Report should state the delta explicitly: "N findings seeded from prior mapping and verified, M net-new."

**Warning signs:**
- Report findings match CONCERNS.md 1:1 with no provenance marking and no net-new entries.
- Contract-consistency section contains prose about the triplication but no actual field-by-field comparison table (regex vs regex, key format vs key format, metadata keys produced vs consumed).

**Phase to address:**
Audit setup phase (CONCERNS.md triage into hypothesis list); contract-audit phase (the comparison matrix is the phase's core deliverable, not prose).

---

## Technical Debt Patterns

Shortcuts in the *audit process* that seem reasonable but degrade the report:

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Paste tool output as findings | Fast "coverage" | Alert fatigue; real findings buried; report distrusted | Never — tools produce leads, humans produce findings |
| Skip effort estimates ("we'll size in the fix milestone") | Faster writing | Fix milestone can't be scoped from the report; violates PROJECT.md contract | Never for this milestone |
| Audit HEAD instead of pinning a SHA | No setup friction | Stale line numbers, unverifiable evidence | Only if repo is provably frozen for the whole window |
| Rate severity by tool default | No rubric work | Miscalibrated report; MVP-acceptable tradeoffs rated Critical | Never |
| One mega-finding per theme ("docs are stale") | Shorter report | Unactionable; can't become fix tasks | Only as a summary row linking to itemized findings |
| Skip re-reading AGENTS.md/CONCERNS.md per finding | Saves minutes | Flags load-bearing weirdness as bugs (issue-cedential, whisper stub) | Never in this repo |
| Fix trivial issues inline during audit | Issue gone immediately | Baseline pollution; passes disagree; violates report-only decision | Never this milestone — tag as effort-S instead |

## Integration Gotchas

Tools the audit itself will use, and how they mislead in this repo:

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| ruff / mypy | Running repo-wide and reporting `scripts/` + handler exclusions as violations | Respect `pyproject.toml` scoping; report *the scoping decision itself* (with its documented rationale) once, not each excluded file's warnings |
| ESLint (if introduced for audit) | Dumping hundreds of findings on JS that only ever targeted `miniprogram_lint.py` | Run as a gap *probe*; report classes of uncaught issues with representative examples, calibrated severity |
| grep / repo search | Hits inside `docs/example/start-fc-main/` (1,003 vendor files) and the 4 duplicated agent-tooling trees mistaken for project code | Exclusion list in every search: `docs/example/`, `.claude/`, `.cursor/`, `.codex/`, `.agents/`, `node_modules` |
| git (evidence) | Citing working-tree line numbers while tree is dirty (3 uncommitted doc deletions) | Pin SHA; inventory dirty state on day one; cite `path:line @ sha` |
| CONCERNS.md / codebase docs | Treating as verified findings or as ignorable | Treat as hypothesis seed list; verify each against pinned SHA |
| Live-cloud checks (`make test-fc-live`, real FC domain) | "Verifying" findings by hitting production during the audit, or worse, flagging the live domain string for correction | Audit is static; live checks only if explicitly chartered, never mutations; never touch the `issue-cedential` string |

## Performance Traps

Audit-throughput traps (scale = repo size and finding count, not users):

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Scanning the vendored FC sample repo | Audit passes take forever; findings cite `docs/example/` | Exclusion list defined at setup | Immediately — 29 MB / 1,003 files of vendor code |
| Findings ledger as free-form prose | Dedup and synthesis become manual re-reading of everything | Structured ledger (table/JSON) with IDs from day one | Above ~20 findings |
| Auditing all five dimensions in one giant pass | Context overload; shallow coverage everywhere; no per-dimension completeness claim | One dimension per phase/plan, shared ledger | Always for a five-dimension charter |
| Re-verifying every finding after any repo change | Synthesis stalls | Diff-scoped re-verification (only findings citing changed files) | Any mid-audit commit |
| Line-number-only evidence | Every consumer must open the repo to understand a finding | Quote the evidence inline in the finding | At handoff to fix-milestone planning |

## Security Mistakes

Audit-report-specific security issues:

| Mistake | Risk | Prevention |
|---------|------|------------|
| Quoting secret *values* as evidence (e.g., reproducing the full presigned URL + STS token from `scripts/test_asr.py`, or `config.yaml` key material) | The report itself becomes a new leak vector, committed to git | Evidence for secret findings cites file:line + pattern (`OSSAccessKeyId=TMP.*`) with values redacted/truncated |
| Rating documented, mitigated MVP tradeoffs (allowlist auth, client-side STS, FC env-var secrets) as Critical vulnerabilities | Severity inflation; report distrusted; fix milestone misprioritized | Cross-check against CONCERNS.md "Current mitigation" notes; report as "accepted risk — reconfirm before launch" |
| Skipping security observations because "security audit is out of scope" | Real incidental findings (like the committed presigned-URL pattern) dropped | PROJECT.md rule: security findings discovered incidentally ARE recorded — out-of-scope only means no *active* pentest-style probing |
| Testing findings against the live FC endpoint / production OSS bucket to "prove" them | Production disruption; polluted logs; possible quota burn | Static evidence only; the existing `make test-sts-escape` results can be cited instead of re-run |

## UX Pitfalls

Report-consumer experience (the consumer is the fix-milestone planner — likely an AI agent plus the developer):

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Findings ordered by discovery time or dimension only | Reader can't see what matters; Critical items buried on page 9 | Executive summary + severity-ordered master table, then per-dimension detail |
| No stable finding IDs | Fix milestone can't reference findings in commits/phases | `AUD-001`-style IDs, never renumbered after report freeze |
| Severity without rationale | Reader re-litigates every rating | One-line "why this severity in this deployment context" per finding |
| Mixed languages inconsistently | This repo's docs are bilingual (zh/en); random switching hurts scanability | Pick the project's convention (PROJECT.md is zh-primary) and keep finding schema fields consistent |
| No "not-a-finding" section | Next auditor/agent re-flags the issue-cedential domain and whisper stub forever | Explicit "Verified intentional — do not fix" appendix listing load-bearing weirdness |

## "Looks Done But Isn't" Checklist

- [ ] **Contract-consistency dimension:** Often delivered as prose ("logic is triplicated") — verify it contains an actual field-by-field comparison matrix (fragment_id regex, object-key template, `x-oss-meta-*` keys produced vs consumed, `.done` state-machine transitions) across `fc_shared/sts.py`, `oss_admin.py`/`poller.py`, `utils/audio.js`.
- [ ] **Every finding:** Often missing effort estimate — verify the effort column is populated with S/M/L for 100% of findings (PROJECT.md contract).
- [ ] **Severity ratings:** Often missing rationale — verify each High/Critical has a context-calibrated justification and a CONCERNS.md cross-check.
- [ ] **Evidence:** Often line numbers only — verify quoted code and pinned SHA on every finding.
- [ ] **Dedup:** Often skipped when dimensions ran in parallel — verify no two findings cite the same file:line root cause.
- [ ] **Baseline integrity:** Often unchecked — verify `git diff <pinned-sha>` at delivery and that no product code changed during the audit.
- [ ] **Known-concerns provenance:** Verify the report marks which findings were seeded from CONCERNS.md vs net-new, and that seeded ones were actually re-verified.
- [ ] **Intentional-design appendix:** Verify the "do not fix" list exists (issue-cedential domain, whisper stub, handler mypy exclusion, scripts/ lint scoping).

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Tool-dump report discovered at synthesis | MEDIUM | Triage dump against schema; verify top-severity leads first; demote unverified items to an appendix, never delete silently |
| Severity miscalibration found late | LOW-MEDIUM | Re-rate all findings against the rubric in one sitting (consistency beats individual accuracy); document re-rating in changelog |
| Code was fixed mid-audit | MEDIUM | `git diff` pinned SHA → identify affected findings → re-verify those only; move fixed items to a "resolved during audit" section (don't erase — they're evidence of process breach) |
| Duplicate findings shipped in draft | LOW | Merge under lowest ID, add "supersedes AUD-0xx" note, keep ID tombstones |
| Missing effort estimates at delivery | LOW | One batch estimation pass with the developer (T-shirt sizes, ~2 min/finding) |
| Evidence stale (line drift) | LOW-MEDIUM | Re-anchor citations via `git blame`/search at pinned SHA; if file changed, re-verify finding |

## Pitfall-to-Phase Mapping

Assumes a roadmap shaped like: (1) audit charter/setup → (2..n) dimension audits (contract; code quality; scripts/tooling; docs/config; tests) → (final) synthesis & report QA.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Tool-output dumping | Setup (scope + exclusion list); each dimension phase | Sample 10 findings: each has human-verified quoted evidence; none cite `docs/example/` or agent-tooling dirs |
| Severity miscalibration | Setup (calibrated matrix deliverable) | Synthesis: every H/C finding has rationale + CONCERNS.md cross-check; H/C count sanity-checked |
| Context-free false positives | Each dimension phase (required-reading gate: AGENTS.md + CONCERNS.md Fragile Areas) | "Verified intentional — do not fix" appendix exists; no finding contradicts a documented red line |
| Scope creep (fixing / target-design) | Setup (zero-diff rule; comparison-set charter) | `git diff <pinned-sha>` clean at delivery; contract section contains no `fc-transcribe-design.md` conformance claims |
| Evidence/actionability gaps | Setup (finding schema); each dimension phase | Schema validation: 100% findings have file:line@sha, quoted evidence, concrete fix, S/M/L effort |
| Moving baseline | Setup (pin SHA; dirty-tree inventory; freeze agreement) | Report header contains SHA + dirty-state inventory; staleness re-check ran at synthesis |
| Duplicate/contradictory findings | Setup (shared ledger, owner-dimension rule); Synthesis (dedup pass) | No two findings share root-cause file:line; no severity conflicts across sections |
| CONCERNS.md rediscovery without value | Setup (hypothesis triage); contract phase (comparison matrix) | Report states seeded-vs-net-new counts; matrix table present |

## Sources

- Specification-anchored audit framework — false-positive taxonomy, threat-model misalignment ~57%, severity-preservation asymmetry: [arxiv.org/html/2604.26495v1](https://arxiv.org/html/2604.26495v1) (MEDIUM confidence, cross-checked)
- Non-actionable static-analysis warnings 35–91%, alert fatigue, trust loss: [A Large-Scale Collection Of (Non-)Actionable Static Code Analysis Reports](https://arxiv.org/html/2511.10323), [Nature Scientific Data version](https://www.nature.com/articles/s41597-025-06154-7), [Why don't software developers use static analysis tools to find bugs?](https://www.researchgate.net/publication/261192385_Why_don't_software_developers_use_static_analysis_tools_to_find_bugs), [Challenges with Responding to Static Analysis Tool Alerts (MSR'19)](https://akondrahman.github.io/files/papers/msr19_sat.pdf) (MEDIUM)
- Audit/pentest report quality — evidence standards, documented severity matrix with rationale, consistency, dedup: [Identifying IS Audit Findings](https://ecampusontario.pressbooks.pub/auditinginformationsystems/chapter/0701/), [Dradis on pentest consistency](https://dradis.com/consistency.html), [DeepStrike pentest reporting](https://deepstrike.io/blog/penetration-testing-report), [Wiz pentest report guide](https://www.wiz.io/academy/vulnerability-management/penetration-testing-report) (MEDIUM)
- Technical-debt audit — effort estimates drive prioritization, consolidate findings, document-don't-fix: [Codacy technical debt tracking guide](https://blog.codacy.com/complete-guide-to-technical-debt-tracking-for-engineering-leaders), [CodeScene prioritize-by-impact](https://codescene.com/blog/prioritize-technical-debt-by-impact/), [vFunction how to measure technical debt](https://vfunction.com/blog/how-to-measure-technical-debt/) (MEDIUM)
- Repo-specific groundings (HIGH confidence — read directly): `/Volumes/Data/ProjectCode/my_soniscope/.planning/PROJECT.md`, `/Volumes/Data/ProjectCode/my_soniscope/.planning/codebase/CONCERNS.md`, git status of working tree (2026-07-04)

---
*Pitfalls research for: pre-launch codebase audit milestone (SoniScope)*
*Researched: 2026-07-04*
