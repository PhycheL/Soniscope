# Feature Research

**Domain:** Pre-launch codebase audit report (deliverable = structured report, no fixes) — SoniScope milestone
**Researched:** 2026-07-04
**Confidence:** MEDIUM (web research cross-checked across security-audit conventions, internal-audit standards, smart-contract audit report norms, and tech-debt assessment frameworks; no single authoritative spec exists for "audit report as a product," but convergence across sources is strong)

## Context

The "product" of this milestone is a report. "Features" below are report components and audit activities. The user of the product is the next (fix) milestone: every feature is judged by whether it makes the report **credible** (trustworthy severity + evidence) and **directly consumable** (findings convert 1:1 into fix-milestone work items).

## Feature Landscape

### Table Stakes (An Audit Report Is Not Credible Without These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Executive summary (1 page)** | Universal convention: why audited, what was in scope, finding counts by severity, overall verdict ("safe to launch after fixing X?"), expected next step | LOW | Answers the milestone's Core Value question directly: "哪里不一致、哪里有债务、上线有什么风险" |
| **Explicit scope & methodology statement** | Reader must know what was and wasn't examined to trust "no findings" areas; PROJECT.md already excludes target-state contract & pen-testing — the report must restate this | LOW | List the 5 audit dimensions, the audited commit SHA, and the exclusions verbatim |
| **Severity taxonomy defined up front (CRITICAL/HIGH/MEDIUM/LOW/INFO)** | Standard across security, internal-audit, and smart-contract audit practice; undefined severity = arbitrary severity | LOW | Define each level in project terms, e.g. CRITICAL = data loss / silent transcription failure / credential leak; HIGH = launch blocker; MEDIUM = fix soon; LOW = hygiene; INFO = observation, no action required |
| **Severity justified via impact × likelihood** | The accepted methodology (OWASP-style risk rating, Sherlock/CodeHawks conventions): each rating states the damage scenario and how likely it triggers | LOW–MEDIUM | Prevents severity inflation/deflation arguments in the fix milestone; a one-line "Impact: … / Likelihood: …" pair per finding suffices |
| **Per-finding record: ID, title, file:line evidence, description, fix recommendation, effort estimate** | This is the PROJECT.md report standard verbatim, and matches the strongest industry convention (smart-contract audit reports) | MEDIUM | Stable IDs (e.g. `CONTRACT-01`, `DEBT-03`) are what make findings referenceable from the fix milestone's phases |
| **Code evidence as quoted snippets, not just paths** | Reports that assert without showing code get re-litigated; snippet + file:line lets the fix milestone verify instantly | LOW | Keep snippets ≤10 lines; link, don't paste, for long stretches |
| **Effort estimates as relative sizes (S/M/L/XL), not hours** | Tech-debt assessment best practice; fake-precise hour estimates are the #1 estimate credibility killer | LOW | Define sizes once (S ≤ 1h single-file, M = multi-file same component, L = cross-component, XL = needs its own phase) |
| **Contract-consistency matrix (fragment_id / object key / `x-oss-meta-*` × 3 implementations)** | The centerpiece dimension. Standard drift-audit method: extract each implementation's version of the contract, diff field-by-field, present as a matrix | MEDIUM–HIGH | Rows = contract facets (regex/charset, key template, date segment, extension, metadata field names/types, size limits); columns = `fc_shared/sts.py`, `oss_admin.py`+`poller.py`, `utils/audio.js`(+`oss_sign.js`); cells = agree/diverge/absent with line refs. Include round-trip check: FC-signed key → Worker `fragment_id_from_key` parses it? |
| **Findings summary table (all findings, one row each: ID, severity, dimension, title, effort)** | Every audit report convention includes it; it *is* the fix-milestone backlog | LOW | Sort by severity then effort |
| **Coverage of all 5 scoped dimensions, even if a dimension yields few findings** | An audit that silently skips a scoped dimension is an incomplete audit; "examined, nothing found" is a result | — (scoping property) | Contract consistency, code quality/debt, scripts/tooling, docs/config, tests — each gets its own section with an explicit "what was checked" line |
| **Known-lead verification (CONCERNS.md items)** | Auditing while ignoring already-documented leads (issue-cedential domain, committed presigned URL, stale AGENTS.md refs) would make the report look less informed than existing docs | LOW | Each CONCERNS.md lead gets confirmed/refuted/refined with evidence — never just copied |

### Differentiators (What Makes the Report Exceptionally Actionable)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Fix-milestone-ready remediation plan (findings grouped into ordered work packages)** | Converts report → next milestone's phase list with zero translation; grouping by co-located fixes (e.g. "all AGENTS.md/doc-path repairs in one commit") beats per-finding sequencing | MEDIUM | Order by severity-weighted ROI (impact ÷ effort); mark dependencies between packages |
| **Launch-blocker verdict per finding (BLOCKER / PRE-LAUNCH / POST-LAUNCH)** | Production-readiness go/no-go framing on top of severity — severity ≠ urgency (e.g. `ENV='development'` is MEDIUM severity but a hard launch blocker) | LOW | A second one-column classification; directly answers "上线有什么风险" |
| **"Do NOT fix" annotations (booby-trap register)** | This codebase has deliberate traps: `issue-cedential` misspelled domain is load-bearing; `whisper-local` stub is a scope red line. Flagging findings a naive fixer would break is rare in audit reports and extremely valuable here | LOW | Explicit `⚠ intentional — do not "fix"` tag; sourced from CONCERNS.md Fragile Areas + code comments |
| **Cross-component contract test gap analysis with concrete test recipe** | CONCERNS.md notes "good per-component tests; no single cross-component contract test." Recommending the *shared-fixture* pattern (one golden fixture set consumed by pytest and node:test) turns the biggest structural risk into a designed fix | MEDIUM | Differentiator because it recommends the mechanism, not just "add tests"; feeds directly into fix milestone |
| **Positive findings / strengths section** | Audit convention that builds trust and prevents the fix milestone from "improving" things that are already deliberately right (MaskedSecret, single-key STS policy, `.done` state machine, fault-injection tests) | LOW | Also calibrates the reader: report is a fair assessment, not a complaint list |
| **Per-dimension confidence statement** | Honest reports state where the audit looked hardest vs lightest (e.g. miniprogram page-level JS was reviewed statically only, no device runs) | LOW | Prevents over-trusting "no findings" in lightly-audited areas |
| **Traceability: finding → CONCERNS.md lead / requirement mapping** | Shows each Active requirement in PROJECT.md is discharged by named findings or an explicit "no findings"; audit-completeness proof | LOW | A small mapping table at the end |
| **Duplication census beyond the known trio** | The known contract triplication may not be the only duplicated logic (e.g. sha256, date formatting, config parsing across JS/Python). A systematic duplicate-logic sweep differentiates from "audit only what CONCERNS.md said" | MEDIUM | Bounded: only contract-bearing logic, not cosmetic duplication |

### Anti-Features (Deliberately NOT in This Report)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Fixing anything while auditing (even "trivial" typos)** | Feels efficient; some findings are one-liners | Pollutes the audit baseline; user explicitly decided fixes are next milestone; edits mid-audit invalidate line-number evidence; the codebase contains traps where the "obvious fix" breaks production (`issue-cedential`) | Every fix, however small, becomes a finding with a recommendation |
| **Raw linter/static-analysis dumps as findings** | Cheap volume; looks thorough | Research shows 35–91% of raw tool alerts are non-actionable; alert fatigue makes readers ignore real findings; report credibility dies with the first false positive | Human-verify every finding; tools generate *leads*, the report contains only confirmed findings |
| **Target-state contract comparison (vs `docs/fc-transcribe-design.md`)** | FC 直转 is the decided future; tempting to audit against it | User explicitly scoped this out; conflates "current 3 implementations disagree" with "current ≠ future design" — different severities, different fix milestones | One INFO-level note that the cutover milestone will need its own contract analysis; nothing more |
| **Security penetration-test-depth analysis** | Pre-launch anxiety pulls toward it | Out of scope per PROJECT.md; threat-modeling every STS/auth path would consume the milestone | Record security issues found *incidentally* during scoped dimensions, tagged as such |
| **Hour-precise effort estimates per finding** | "Estimate" sounds like hours | False precision; estimates made before fix-milestone planning are guesses; sets up estimate-vs-actual arguments | T-shirt sizes with published definitions |
| **Auditing the vendored `docs/example/start-fc-main/` (29 MB, 1,003 files) line-by-line** | It's in the repo | Not project code; would swamp every metric and grep; its existence is itself the finding | Single finding: "vendored sample repo committed — recommend removal," then exclude from all other analysis |
| **Numeric quality scores (e.g. "codebase: 7.2/10")** | Executives like scores | Unfalsifiable, invites arguing about the number instead of the findings; no methodology behind it survives scrutiny for a solo project | Severity-count summary + per-dimension confidence statement |
| **Findings without a recommendation ("X is bad")** | Faster to write | Unactionable findings are the top reason audit output gets ignored; violates the PROJECT.md report standard | If no fix is recommendable, state why and what decision is needed instead |

## Feature Dependencies

```
[Severity taxonomy definition]
    └──required-by──> [Per-finding severity ratings]
                          └──required-by──> [Findings summary table]
                                               └──required-by──> [Remediation plan / work packages]
                                                                    └──required-by──> [Launch-blocker verdicts]

[Effort-size definitions (S/M/L/XL)]
    └──required-by──> [Per-finding effort estimates] ──required-by──> [Remediation plan ordering]

[Scope & methodology statement]
    └──required-by──> [Per-dimension confidence statements]

[Contract-consistency matrix]
    └──feeds──> [Cross-component contract test gap analysis]
    └──feeds──> [Duplication census] (same extraction technique, wider net)

[Known-lead verification (CONCERNS.md)]
    └──feeds──> ["Do NOT fix" booby-trap register]
    └──feeds──> [Traceability mapping]

[All per-dimension findings] ──required-by──> [Executive summary] (write it last)
```

### Dependency Notes

- **Taxonomy and effort definitions before any finding is written:** retrofitting severity/size definitions after findings exist causes silent re-grading; define once, apply uniformly. This is the strongest ordering constraint — it argues for a "report framework/templates first" phase.
- **Contract matrix feeds the test-gap recipe:** the matrix's facet rows become the shared-fixture test cases; doing the matrix first makes the test recommendation nearly free.
- **Executive summary and remediation plan are synthesis features:** they can only be written after all dimension audits complete — natural final phase.
- **Booby-trap register conflicts with naive auto-fix tooling:** any future automated fix pipeline (e.g. `/gsd-audit-fix`) must consume the do-not-fix tags, or it will break the misspelled live domain.

## MVP Definition

### Launch With (v1 — the report this milestone must ship)

- [ ] Severity taxonomy + effort-size definitions (project-specific, stated in report) — everything else depends on them
- [ ] Contract-consistency matrix across the 3 implementations with round-trip check — the milestone's centerpiece requirement
- [ ] Per-finding records (ID, severity+justification, file:line evidence with snippet, fix recommendation, T-shirt effort) for all 5 dimensions — the PROJECT.md report standard
- [ ] Findings summary table — the fix-milestone backlog
- [ ] CONCERNS.md lead verification (confirm/refute each) — table stakes for informedness
- [ ] Executive summary + scope/exclusions statement — the "can we launch" answer
- [ ] "Do NOT fix" annotations — cheap, and this codebase specifically punishes their absence

### Add After Validation (v1.x — include if audit time allows)

- [ ] Launch-blocker (BLOCKER/PRE-LAUNCH/POST-LAUNCH) column — trigger: user wants a go/no-go answer, not just severities
- [ ] Remediation work packages with ordering — trigger: writing the fix milestone immediately after
- [ ] Cross-component contract test recipe (shared golden fixtures) — trigger: contract matrix reveals ≥1 real divergence
- [ ] Positive findings section — trigger: report reads as unfairly negative without it
- [ ] Traceability mapping table — trigger: audit-milestone acceptance review

### Future Consideration (v2+ — explicitly deferred)

- [ ] Target-state (FC 直转) contract gap analysis — belongs to the cutover milestone by user decision
- [ ] Automated drift detection in CI (contract tests wired into `make test`) — a *fix*, not a report feature
- [ ] Security threat-model / pen-test depth — separate engagement if the app leaves personal-use scope

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Severity taxonomy + effort definitions | HIGH | LOW | P1 |
| Contract-consistency matrix | HIGH | MEDIUM | P1 |
| Per-finding records (evidence + fix + effort) | HIGH | MEDIUM | P1 |
| Findings summary table | HIGH | LOW | P1 |
| Executive summary + scope statement | HIGH | LOW | P1 |
| CONCERNS.md lead verification | HIGH | LOW | P1 |
| "Do NOT fix" register | HIGH | LOW | P1 |
| Launch-blocker verdicts | HIGH | LOW | P2 |
| Remediation work packages | HIGH | MEDIUM | P2 |
| Contract test gap recipe | MEDIUM | MEDIUM | P2 |
| Positive findings section | MEDIUM | LOW | P2 |
| Per-dimension confidence statements | MEDIUM | LOW | P2 |
| Traceability mapping | MEDIUM | LOW | P3 |
| Duplication census beyond known trio | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have — report is not credible/usable without it
- P2: Should have — makes the report exceptionally actionable
- P3: Nice to have — completeness polish

## Competitor Feature Analysis

Closest analogs to "audit report as deliverable":

| Feature | Smart-contract audit reports (Trail of Bits / OpenZeppelin style) | Internal-audit / GRC reports | Our Approach |
|---------|--------------------------------------------------------------|------------------------------|--------------|
| Severity | Critical/High/Medium/Low/Info via impact×likelihood matrix | Risk-rated vs control framework | Same 5-level taxonomy, definitions rewritten in SoniScope terms (data loss, silent skip, credential leak, launch friction) |
| Evidence | Code snippet + file:line per finding, mandatory | Evidence artifact IDs, test method | Snippet + `path:line` per finding, commit SHA pinned in scope statement |
| Status tracking | resolved / acknowledged-with-justification | Remediation tracking register | Deferred to fix milestone; report ships all findings `OPEN`, plus do-not-fix tags |
| Remediation | Recommendation per finding | Remediation roadmap with owners | Recommendation + T-shirt effort per finding; work packages ordered by impact÷effort |
| Scope honesty | Explicit "not reviewed" list + disclaimers | Scope/methodology section | Scope statement restating PROJECT.md exclusions + per-dimension confidence |

## Sources

- [Wiz — What is code auditing?](https://www.wiz.io/academy/application-security/code-auditing), [SentinelOne — Code Security Audit guide](https://www.sentinelone.com/cybersecurity-101/cybersecurity/code-security-audit/), [CodeAnt — Secure Code Audit checklist](https://www.codeant.ai/blogs/source-code-audit-checklist-best-practices-for-secure-code) — report structure: exec summary, findings register, remediation roadmap (MEDIUM confidence, cross-checked)
- [Cyfrin CodeHawks — How to Evaluate Finding Severity](https://docs.codehawks.com/hawks-auditors/how-to-evaluate-a-finding-severity), [Sherlock — Critical/High/Medium/Low in smart contracts](https://sherlock.xyz/post/understanding-critical-high-medium-and-low-vulnerabilities-in-smart-contracts), [Auditing Information Systems — Identifying IS Audit Findings](https://ecampusontario.pressbooks.pub/auditinginformationsystems/chapter/0701/) — impact×likelihood severity methodology (MEDIUM)
- [Cantina — Understanding security review reports](https://cantina.xyz/blog/understanding-smart-contract-security-review-reports-with-real-examples-from-cantina), [ChainSecurity — How to read audit reports](https://www.chainsecurity.com/blog/how-to-read-smart-contract-audit-reports), [CertiK — Smart Contract Audit](https://www.certik.com/products/smart-contract-audit) — per-finding format and resolution-status conventions (MEDIUM)
- [Pactflow — Schemas Can Be Contracts / Drift](https://pactflow.io/blog/schemas-can-be-contracts/), [Contract Drift & Schema Mismatch Detection](https://medium.com/@gunashekarr11/contract-drift-schema-mismatch-detection-the-most-underrated-api-failure-in-modern-systems-c278a2914205), [Interface Contract Testing in C#](https://medium.com/@asher.garland/interface-contract-testing-a-reusable-test-suite-for-interface-first-design-in-c-31ad3da331a9) — cross-implementation contract audit & shared-suite pattern (MEDIUM)
- [Nature Sci Data — (Non-)Actionable Static Analysis Reports](https://www.nature.com/articles/s41597-025-06154-7), [Mitigating False Positive Static Analysis Warnings (TSE)](https://dl.acm.org/doi/10.1109/TSE.2023.3329667), [Empirical Study of Suppressed Warnings](https://software-lab.org/publications/fse2025_suppressions.pdf) — 35–91% non-actionable alerts, alert fatigue → anti-feature: no raw tool dumps (MEDIUM, academic sources)
- [vFunction — Prioritize Tech Debt](https://vfunction.com/blog/how-to-prioritize-tech-debt-strategies-for-effective-management/), [SLR on Technical Debt Prioritization](https://www.sciencedirect.com/science/article/pii/S016412122030220X), [Asana — T-Shirt Sizing](https://asana.com/resources/t-shirt-sizing), [Origami Risk — Audit Findings to Action](https://www.origamirisk.com/resources/insights/from-audit-findings-to-action-best-practices-for-issues-management-and-remediation-tracking/) — effort sizing & prioritization (MEDIUM)
- [Cortex — Production Readiness Checklist](https://www.cortex.io/post/how-to-create-a-great-production-readiness-checklist), [GitScrum — Launch Readiness Go/No-Go](https://docs.gitscrum.com/en/best-practices/launch-readiness-checklist), [IPM — Go/No-Go Checklist](https://instituteprojectmanagement.com/blog/go-no-go-production-readiness-checklist/) — GO/CONDITIONAL GO/NO-GO framing → launch-blocker verdicts (MEDIUM)
- `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md` — project-specific report standard, scope exclusions, known leads (HIGH, first-party)

---
*Feature research for: pre-launch codebase audit report deliverable (SoniScope)*
*Researched: 2026-07-04*
