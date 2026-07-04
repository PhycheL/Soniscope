# Stack Research — Audit Tooling

**Domain:** Two-language codebase audit (Python 3.11 mypy-strict + WeChat miniprogram vanilla JS), report-only milestone
**Researched:** 2026-07-04
**Confidence:** MEDIUM overall — all version numbers verified against PyPI / npm registry / GitHub Releases APIs on 2026-07-04 (primary sources); usage-pattern claims are MEDIUM (web + ecosystem knowledge, cross-checked against host: Node v22.18.0, uv 0.8.14, uvx/npx/brew/rg all present)

## Governing Principle: Zero-Footprint Invocation

This milestone produces a **report only — no code changes**. Adding audit tools to `pyproject.toml`/`uv.lock` or creating a `package.json` would itself change the baseline being audited. Therefore **every tool below is invoked ephemerally**:

- Python tools: `uvx <tool>` or `uv run --with <tool> ...` (injects into the workspace env without touching `pyproject.toml` or `uv.lock`)
- JS tools: `npx -y <tool>` (no `package.json` needed)
- Binaries: `brew install` (host-level, not repo-level)
- Scratch configs (ESLint flat config, jscpd config) live outside the repo or in `.planning/`, never committed to app code

This is the single most important constraint-fit decision: it satisfies "uv workspace, no CI, local Mac, don't pollute the baseline" simultaneously.

## Recommended Stack

### Core Technologies (per audit dimension)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| ruff | 0.15.20 | Python static analysis beyond current gate | Already the repo's linter (>=0.4 pinned). Run `uvx ruff@0.15.20 check apps scripts --select C901,S,PLR,ARG,ERA,T20 --statistics` for the audit pass: `C901` (mccabe complexity), `S` (bandit security), `PLR` (refactor smells), `ARG` (unused arguments), `ERA` (commented-out code — direct tech-debt signal), `T20` (stray prints). CLI `--select` extends rules without editing the committed `pyproject.toml`. One tool covers lint + complexity-flagging + security-lite. |
| mypy (existing) | >=1.8 (repo pin) | Type-consistency baseline | Already strict over worker + fc_shared + tests. Audit action: run `make typecheck` as-is AND note the known exclusion (FC `handler.py` files are mypy-excluded due to duplicate module names) as an audit finding about coverage gaps, not something to fix now. |
| vulture | 2.16 | Python dead-code detection | The standard Python dead-code tool. `uvx vulture apps/worker/src apps/fc scripts --min-confidence 80` for report-grade findings; list 60–79% hits as "possible dead code" with lower severity. Confidence scoring maps directly onto the report's severity-grading requirement. Expect false positives on Typer callbacks and WSGI entry points — verify each hit before reporting. |
| lizard | 1.23.0 | Cross-language complexity metrics | The only mainstream analyzer giving **one consistent CCN/NLOC/function-length metric across both Python and JavaScript** — essential for a two-language audit where findings must be comparable. `uvx lizard apps -l python -l javascript -C 10 --csv` produces an evidence table with file/line, matching the report format requirement. |
| jscpd | 5.0.11 | Cross-language duplication detection | Token-based copy-paste detector that handles Python and JS **in a single run** (`npx -y jscpd apps --min-tokens 50 --reporters consoleFull,json --output .planning/audit-evidence/`). JSON reporter gives file/line pairs for evidence. Engines: Node >=18 (host has 22.18.0). Note: it finds intra-language duplication; the fragment_id/object-key contract triplication is *cross-language semantic* duplication — jscpd evidences the Python↔Python overlap (FC vs Worker), while the JS side needs ast-grep + manual comparison. |
| ast-grep (@ast-grep/cli) | 0.44.1 | Contract-consistency structural search | The core audit (fragment_id / object key / `x-oss-meta-*` in 3 places) is a cross-language structural comparison, and no off-the-shelf "contract drift" tool exists. ast-grep runs AST-level pattern queries over both Python and JS (`npx -y @ast-grep/cli run -p '<pattern>' -l py apps/`), far more precise than regex for extracting every construction/parse site of object keys and metadata headers. Combine with `rg` (already on host) for the literal-string inventory. |
| coverage.py + pytest-cov | 7.15.0 / 7.1.0 | Python test-coverage measurement | Standard, and injectable without touching the workspace: `uv run --with pytest-cov pytest --cov=soniscope_worker --cov=fc_shared --cov-report=json --cov-report=term-missing`. The repo currently enforces **no** coverage (confirmed in `.planning/codebase/TESTING.md`) — the audit measures and reports; it does not add a gate. |
| node:test built-in coverage | Node 22.18.0 (host) | JS test-coverage measurement | `node --test --experimental-test-coverage --test-reporter=lcov --test-reporter-destination=cov.lcov apps/miniprogram/test/*.test.js`. Built into the runner the repo already uses; zero new dependencies. Flag is still named "experimental" in Node 22/24 but is functional and widely used (thresholds since 22.8.0, lcov reporter available). Since the JS tests are normally bridged through pytest, run them directly for coverage collection. |
| lychee | 0.24.2 | Docs link/reference integrity | Rust link checker (`brew install lychee`; not yet on host). Checks both HTTP links and **relative file links** in markdown — directly evidences the known "AGENTS.md references deleted docs" concern: `lychee --offline docs/ AGENTS.md README.md '*.md'`. Use `--offline` first for file-reference drift, then an online pass for external URLs. |
| madge | 8.0.0 | JS dependency graph / dead modules | Works on plain CommonJS file paths — no package.json required: `npx -y madge --circular --orphans apps/miniprogram/utils/`. Finds circular requires and orphan modules in the dependency-free utils layer. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| radon + xenon | 6.0.1 / 0.9.3 | Python Maintainability Index | Only if the report wants an MI score per module (`uvx radon mi apps/worker/src -s`); lizard covers cyclomatic complexity, radon adds MI which lizard lacks. Optional supplement, not primary. |
| ESLint | 10.6.0 | JS static analysis | `npx -y eslint --config /path/outside/repo/eslint.config.mjs 'apps/miniprogram/**/*.js'` with a scratch flat config: `languageOptions: { sourceType: "commonjs", ecmaVersion: 2020, globals: { wx: "readonly", App: "readonly", Page: "readonly", Component: "readonly", getApp: "readonly", getCurrentPages: "readonly" } }` and `js.configs.recommended`. v10 is flat-config-only (eslintrc removed); engines `^20.19.0 || ^22.13.0 || >=24` — host Node 22.18.0 qualifies. Catches unused vars/dead branches in miniprogram code that the existing custom `miniprogram_lint.py` (domain-URL checks only) does not. There is no authoritative maintained WeChat-miniprogram ESLint plugin in 2026 — declare globals manually. |
| pip-audit | 2.10.1 | Dependency vulnerability scan | `uv export --format requirements-txt --no-emit-project > /tmp/reqs.txt && uvx pip-audit -r /tmp/reqs.txt`; also run directly against each FC function's `requirements.txt`. pip-audit does not read `uv.lock` natively — the `uv export` bridge is the standard pattern. Security is a "record if found" dimension per PROJECT.md, so one pass suffices. |
| deptry | 0.25.1 | Unused/missing declared dependencies | `uvx deptry apps/worker` — flags declared-but-unused and used-but-undeclared deps in the uv workspace. Fits the scripts/tooling audit dimension. Expect the lazy-import pattern (cloud SDKs behind Protocols) to need `--ignore` tuning or manual verification of hits. |
| scc | latest (brew) | LOC/language inventory baseline | `brew install scc; scc apps scripts` for the report's scope/size overview table. Cosmetic but cheap. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| ripgrep (rg, on host) | Contract literal inventory | `rg -n 'x-oss-meta-|fragment_id|fragmentId' apps/` is the first evidence pass for the contract audit; feed hits into the ast-grep structural comparison. |
| Existing `make` gates | Baseline snapshot | Run `make lint typecheck test` first and record the green/red state — the audit report's "current baseline" section comes free from the repo's own gates. |
| jq / python3 (host) | Evidence post-processing | jscpd/coverage/lizard JSON outputs → severity-graded evidence tables in the report. |

## Installation

```bash
# One-time host binaries (repo untouched)
brew install lychee scc

# Everything else is ephemeral — examples:
uvx ruff@0.15.20 check apps scripts --select C901,S,PLR,ARG,ERA,T20 --statistics
uvx vulture apps/worker/src apps/fc scripts --min-confidence 80
uvx lizard apps -l python -l javascript -C 10 --csv
uv run --with pytest-cov pytest --cov=soniscope_worker --cov=fc_shared --cov-report=json
npx -y jscpd apps --min-tokens 50 --reporters consoleFull,json
npx -y @ast-grep/cli --version
npx -y madge --circular --orphans apps/miniprogram/utils/
npx -y eslint --config <scratch>/eslint.config.mjs 'apps/miniprogram/**/*.js'
node --test --experimental-test-coverage apps/miniprogram/test/*.test.js
uv export --format requirements-txt --no-emit-project > /tmp/reqs.txt && uvx pip-audit -r /tmp/reqs.txt
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| ruff `S` rules | standalone bandit | Only if you need bandit plugins ruff hasn't ported; for a one-shot audit ruff's S set is sufficient and avoids a second tool/report format |
| ast-grep | Semgrep | Semgrep has richer cross-file taint rules, but is heavier (login nags, slower), and the contract audit needs structural *extraction*, not taint analysis — ast-grep's pattern syntax is faster to iterate locally |
| lizard | radon (Python) + eslint `complexity` rule (JS) | If you want per-language idiomatic tools; costs you metric comparability across the two languages |
| node:test built-in coverage | c8 11.0.0 | If the built-in reporter's line attribution proves unreliable for the "load real page files" test harness, `npx -y c8 node --test ...` is the drop-in fallback |
| jscpd | PMD CPD | CPD is battle-tested but requires a JVM on the host; jscpd is npx-runnable and covers both languages |
| lychee | markdown-link-check (npm) | If avoiding a brew install matters more than speed/file-link accuracy; lychee is faster and better at relative-path checking |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| knip 6.24.0 | Requires a package.json-rooted project with entry points — the miniprogram deliberately has no package.json; knip cannot model it | ESLint `no-unused-vars` + madge orphan detection + manual require-graph review (utils/ surface is small) |
| pylint | ~90% overlap with ruff rules at 10–100x the runtime; two overlapping Python linters produce duplicate findings that inflate the report | ruff with extended `--select` |
| SonarQube / sonar-scanner | Server + database + quality-profile setup for a one-shot local audit with no CI is pure overhead; its value is longitudinal tracking, which this milestone doesn't need | The per-dimension CLI tools above, outputs archived as evidence |
| pydoclint 0.9.1 | Enforces Google/NumPy/Sphinx docstring styles; this codebase uses freeform Chinese docstrings — it would generate near-total noise | Docs-drift checking via lychee + rg cross-checks of documented constants/env vars/URLs against code |
| Adding pytest-cov / eslint / jscpd to pyproject.toml or a new package.json | Changes the audited baseline; violates the report-only constraint | `uvx`, `uv run --with`, `npx -y` ephemeral invocation |
| Coverage thresholds / new CI gates | This milestone measures and reports; gating decisions belong to the fix milestone | `--cov-report=json` snapshots archived with the report |
| Injecting a year into tool web searches or trusting training-data versions | Registry state moves fast (ruff was 0.4.x when the repo pinned it; it's 0.15.20 now) | Registry JSON APIs (`pypi.org/pypi/<pkg>/json`, `registry.npmjs.org/<pkg>/latest`) at audit time |

## Stack Patterns by Variant

**For the contract-consistency dimension (the milestone's core):**
- Use `rg` literal inventory → ast-grep structural extraction → manual three-way comparison table (miniprogram JS vs FC Python vs Worker Python)
- Because no automated tool compares semantics across languages; tooling's job here is exhaustive, evidence-grade *extraction* (file/line for every contract touchpoint), and the comparison itself is analyst work

**For the code-quality/tech-debt dimension:**
- Use ruff extended-select + vulture + lizard + jscpd, all with JSON/CSV output archived under `.planning/` evidence
- Because machine-generated file/line findings satisfy the report's "evidence + severity" contract directly

**For the docs/config drift dimension:**
- Use lychee `--offline` for file-reference rot, then targeted rg cross-checks: FC URLs in `apps/miniprogram/config.js` vs deployed function names (the `issue-cedential` typo), env var names in docs vs `apps/fc/shared/fc_shared/env.py`, Makefile targets vs docs
- Because docs-vs-code drift has no off-the-shelf tool; it is scripted greps plus judgment, with lychee automating the one mechanically checkable class (dangling references)

**For the test-quality dimension:**
- Use coverage measurement (pytest-cov + node built-in) as *input evidence*, not as the quality verdict; pair with manual review against the repo's own documented conventions (fakes-not-mocks, secret-leak assertions, mypy-strict tests)
- Because line coverage alone misrepresents a codebase whose live/cloud verification tier (`make test-*`/`verify-*`) is intentionally outside pytest

## Version Compatibility

| Package | Compatible With | Notes |
|-----------|-----------------|-------|
| eslint@10.6.0 | Node ^20.19.0 \|\| ^22.13.0 \|\| >=24 | Host Node v22.18.0 ✓ (verified from npm engines field) |
| jscpd@5.0.11 | Node >=18 | Host ✓ |
| node:test coverage | Node >=18.15 (thresholds >=22.8) | Host v22.18.0 ✓; flag still `--experimental-*` named |
| pytest-cov@7.1.0 | pytest >=8 (repo has >=8.0), coverage 7.x | `uv run --with pytest-cov` resolves against the existing workspace env ✓ |
| uvx tools (ruff/vulture/lizard/radon/pip-audit/deptry) | uv 0.8.14 (host) | Isolated tool envs; zero interaction with `uv.lock` ✓ |
| ruff@0.15.20 CLI `--select` | repo's committed ruff config | CLI select *extends* the run without editing `pyproject.toml`; note findings from new rule groups are audit findings, not gate failures |

## Sources

- PyPI JSON API (`pypi.org/pypi/<pkg>/json`), 2026-07-04 — versions for ruff 0.15.20, vulture 2.16, radon 6.0.1, xenon 0.9.3, lizard 1.23.0, coverage 7.15.0, pytest-cov 7.1.0, pip-audit 2.10.1, deptry 0.25.1, pydoclint 0.9.1 — registry-verified (primary source)
- npm registry API (`registry.npmjs.org`), 2026-07-04 — jscpd 5.0.11, eslint 10.6.0 (+engines field), madge 8.0.0, knip 6.24.0, @ast-grep/cli 0.44.1, c8 11.0.0, markdownlint-cli2 0.23.0 — registry-verified (primary source)
- GitHub Releases API — lychee v0.24.2 — registry-verified (primary source)
- Node.js docs (nodejs.org/api/test.html, learn/test-runner/collecting-code-coverage) via WebSearch — built-in coverage status, thresholds since 22.8.0, lcov reporter — MEDIUM (official docs surfaced via search; seam provider tier LOW, upgraded rationale: nodejs.org is the authoritative source)
- Host verification (local commands) — Node v22.18.0, uv 0.8.14, uvx/npx/brew/rg present, lychee/ast-grep not yet installed — HIGH (directly observed)
- Ecosystem-practice claims (no WeChat-miniprogram ESLint plugin, knip package.json requirement, pip-audit/uv.lock bridge, no off-the-shelf docs-drift tool) — MEDIUM (web + model knowledge, not independently cross-verified; flag for spot-checking during audit phase setup)

---
*Stack research for: SoniScope pre-launch audit milestone (tooling to conduct the audit)*
*Researched: 2026-07-04*
