# Codebase Structure

**Analysis Date:** 2026-07-04

## Directory Layout

```
my_soniscope/
├── apps/
│   ├── miniprogram/              # WeChat mini program frontend (JS, no build step)
│   │   ├── app.js / app.json / app.wxss   # App entry, page registry, global styles
│   │   ├── config.js             # Real cloud URLs & constants (single source of truth)
│   │   ├── pages/                # index (record), uploads (queue list), dev (fault injection)
│   │   ├── utils/                # Pure-logic modules (node-testable, IO injected)
│   │   └── test/                 # Node-based unit tests for utils
│   ├── fc/                       # Aliyun FC 3.0 web functions
│   │   ├── issue_credential/     # STS issuance function (handler.py + requirements.txt)
│   │   ├── verify_upload/        # Upload verification function (handler.py + requirements.txt)
│   │   ├── shared/               # app.py (custom runtime) + fc_shared/ package (vendored at deploy)
│   │   └── tests/                # pytest for handlers + fc_shared
│   └── worker/                   # Python Worker (uv workspace member, package soniscope-worker)
│       ├── pyproject.toml        # Worker deps (typer, pydantic, oss/sts/fc SDKs)
│       ├── src/soniscope_worker/ # All Worker modules
│       └── tests/                # pytest, one test file per module
├── scripts/                      # Cross-component ops scripts + ralph agent harness
├── tests/audio/                  # Shared audio fixtures (binaries fetched, not committed)
├── docs/                         # PRD, tech design docs, runbook, architecture reviews
├── build/fc/                     # deploy-fc packaging output/backups/logs (gitignored)
├── openspec/                     # OpenSpec change workflow (changes/, specs/, config.yaml)
├── pyproject.toml                # Root uv workspace (no direct business deps)
├── Makefile                      # Single command entry point for everything
├── AGENTS.md                     # AI agent development rules and red lines
└── README.md
```

## Directory Purposes

**`apps/miniprogram/`:**
- Purpose: Device-side recording, drafts, upload queue, verify, status UI
- Contains: wx `pages/` (thin IO + render), `utils/` pure logic, `test/` node tests
- Key files: `apps/miniprogram/config.js` (FC/OSS URLs, `CHUNK_MAX_DURATION_SECONDS`, `ENV` flag), `utils/uploader.js` (upload orchestration), `utils/upload_queue.js` (8-state queue), `utils/oss_sign.js` (OSS V4 PostObject signing), `utils/verify.js`, `utils/draft.js`, `utils/chunking.js`, `utils/ulid.js`, `utils/fault_injection.js` (dev-only)

**`apps/fc/`:**
- Purpose: Two stateless FC 3.0 top-level web functions plus shared package
- Contains: `issue_credential/handler.py`, `verify_upload/handler.py` (WSGI handlers), `shared/app.py` (custom runtime entrypoint `python3 app.py`), `shared/fc_shared/` (`auth.py`, `env.py`, `errors.py`, `http.py`, `audit.py`, `sts.py`, `head.py`, `wechat.py`)
- Key files: `apps/fc/shared/fc_shared/__init__.py` re-exports the entire public API; handlers use only `fc_shared.*` names

**`apps/worker/src/soniscope_worker/`:**
- Purpose: The Worker package — pipeline modules AND all live/E2E verification commands
- Contains: pipeline core (`poller.py`, `pipeline.py`, `audio.py`, `manifest.py`, `transcriber.py`, `nls.py`, `recovery.py`, `locks.py`, `retranscribe.py`), infrastructure (`cli.py`, `config.py`, `paths.py`, `fixtures.py`, `oss_admin.py`, `latency.py`), tooling/verification (`fc_deploy.py`, `fc_live.py`, `verify_upload_live.py`, `verify_prep.py`, `e2e.py`, `e2e_scenarios.py`, `sts_escape.py`, `ops.py`, `miniprogram_lint.py`)
- Key files: `cli.py` (Typer app, all subcommands), `pipeline.py` (7-stage fragment pipeline), `config.py` (Pydantic v2 config schema)

**`scripts/`:**
- Purpose: Standalone helper scripts outside the Worker package
- Contains: `scripts/fetch_test_fixtures.py` (download/verify audio fixtures), `scripts/gen_worker_config.sh`, `scripts/test_asr.py` (legacy), `scripts/ralph/` (autonomous agent harness: `ralph.py`, `prd.json`, dashboards — not product code)

**`tests/audio/`:**
- Purpose: Shared audio fixtures for ASR/pipeline tests; binaries fetched via `python3 scripts/fetch_test_fixtures.py`, verified against `tests/audio/fixtures.manifest.json` sha256s
- Contains: `sample-20s.wav/.m4a`, `sample-54s.wav`, `sample-25min.wav` + `.md` descriptors

**`docs/`:**
- Purpose: Product and technical authority documents
- Contains: `docs/v1.0.0 prd/` (PRD), `docs/runbook/` (`cloud-setup.md` real resources, `fc-deploy.md`, `deployment-guide.md`, `mvp-acceptance.md`, `us-001-manual.html`), `docs/architecture/` (review + drawio), design comparisons (`fc-transcribe-design.md`, `transcribe-approach-comparison.md`, `multi-user-design.md`)
- Note: authority order is PRD → tech-spec → runbook → `AGENTS.md`

**`build/fc/`:**
- Purpose: `make deploy-fc` artifacts — per-function zips, `backup/<timestamp>/`, `logs/`
- Generated: Yes
- Committed: No (gitignored per convention; some artifacts currently present in working tree)

**`openspec/`:**
- Purpose: OpenSpec change-driven workflow state (`changes/archive/`, `specs/`, `config.yaml`)
- Generated: Partially (by opsx skills)
- Committed: Yes

## Key File Locations

**Entry Points:**
- `apps/miniprogram/app.js`: Mini program App entry (device ID bootstrap)
- `apps/fc/shared/app.py`: FC custom runtime WSGI server (`python3 app.py`)
- `apps/worker/src/soniscope_worker/__main__.py`: `python -m soniscope_worker` → Typer CLI
- `Makefile`: Operator entry for every command (install, quality gates, worker, deploy, live tests)

**Configuration:**
- `pyproject.toml` (root): uv workspace, mypy strict, ruff, pytest config (testpaths + `apps/fc/shared` on pythonpath)
- `apps/worker/pyproject.toml`: Worker dependencies + console script
- `apps/miniprogram/config.js`: FC/OSS URLs, region, chunk threshold, `ENV`
- `apps/miniprogram/app.json` / `project.config.json`: page registry / devtools project config
- `$SONISCOPE_HOME/config.yaml` (outside repo): Worker runtime secrets, chmod 600, schema in `apps/worker/src/soniscope_worker/config.py`

**Core Logic:**
- `apps/worker/src/soniscope_worker/pipeline.py`: fragment processing pipeline
- `apps/worker/src/soniscope_worker/poller.py`: OSS polling/download (`OssSource` Protocol)
- `apps/fc/shared/fc_shared/auth.py`: shared FC request authorization
- `apps/miniprogram/utils/uploader.js`: upload orchestration state machine

**Testing:**
- `apps/worker/tests/`: pytest, mirrors module names (`test_<module>.py`)
- `apps/fc/tests/`: pytest for handlers and `fc_shared`
- `apps/miniprogram/test/`: node tests for `utils/` pure logic (run via worker's `test_miniprogram_js.py`)
- Live/E2E: not in test dirs — implemented as CLI subcommands (`fc_live.py`, `e2e.py`, etc.) exposed as `make test-*` / `make verify-*`

## Naming Conventions

**Files:**
- Python modules: snake_case (`fc_deploy.py`, `verify_upload_live.py`); tests `test_<module>.py`
- FC function dirs: snake_case (`issue_credential/`) but cloud function names kebab-case (`issue-credential`) — make targets use the kebab-case name
- Mini program: snake_case JS utils (`upload_queue.js`, `oss_sign.js`); page quadruplets `<page>.js/.json/.wxml/.wxss`
- JS tests: `<topic>.test.js`

**Directories:**
- Apps split by deployment target: `apps/miniprogram`, `apps/fc/<function>`, `apps/worker`
- Runtime data (outside repo): `fragments/<YYYY-MM-DD>/<fragment_id>/`, `inbox/`, `inbox/failed/`, `tmp/`

**Identifiers:**
- Fragment ID: `<YYYYMMDDTHHMMSS>_<deviceShortId>_<ulid>`
- OSS key: `recordings/<YYYY-MM-DD>/<fragment_id>.wav` (always `.wav`)
- Make targets: `test-*` (live/scenario), `verify-*` (acceptance checks), `*-fc` (deploy ops) — follow tech-spec §6.5, never add parallel entry points

## Where to Add New Code

**New Worker capability (pipeline stage, verification, ops):**
- Primary code: new module in `apps/worker/src/soniscope_worker/<name>.py` (pure logic + injected IO; lazy-import cloud SDKs)
- CLI wiring: add a Typer subcommand in `apps/worker/src/soniscope_worker/cli.py` (lazy import inside the command function)
- Make target: add to `Makefile` with `## help text` comment and `.PHONY` entry
- Tests: `apps/worker/tests/test_<name>.py` (mock/fake all cloud IO)

**New FC endpoint logic:**
- Shared logic: `apps/fc/shared/fc_shared/<module>.py`, re-export from `fc_shared/__init__.py` (keep `__all__` sorted)
- Handler changes: `apps/fc/<function>/handler.py` (WSGI signature; GET stays a liveness probe)
- Tests: `apps/fc/tests/` ; note handlers themselves are ruff-only (excluded from mypy), `fc_shared` is mypy strict
- New third-party deps: `apps/fc/<function>/requirements.txt` (deploy tooling `fc_deploy.py` vendors `fc_shared`, packages per function)

**New mini program behavior:**
- Pure logic: `apps/miniprogram/utils/<name>.js` with IO passed as `deps`
- Page IO/render: `apps/miniprogram/pages/<page>/` quadruplet, registered in `app.json`
- Tests: `apps/miniprogram/test/<name>.test.js`
- New URLs/constants: only in `apps/miniprogram/config.js` (and register domains in WeChat console per its header comment)

**Utilities:**
- Worker shared helpers: `apps/worker/src/soniscope_worker/paths.py` (runtime dirs), `fixtures.py` (sha256/probe), `recovery.py` (atomic writes)
- Cross-component scripts: `scripts/` only if it cannot be a make target backed by a CLI subcommand (prefer the CLI)

## Special Directories

**`build/`:**
- Purpose: FC packaging zips, deploy backups (`build/fc/backup/<timestamp>/`), deploy logs (`build/fc/logs/`)
- Generated: Yes (`make deploy-fc`)
- Committed: No (must be gitignored)

**`tests/audio/`:**
- Purpose: Audio fixture binaries + manifest
- Generated: Fetched via `scripts/fetch_test_fixtures.py` (binaries not committed as new content)
- Committed: Manifest/docs yes; binaries policy is no

**`scripts/ralph/`:**
- Purpose: Ralph autonomous-agent harness (prd.json, progress, dashboards) — meta-tooling, not product code
- Generated: Partially
- Committed: Yes

**`.codex/`, `.claude/`, `.agents/`, `.cursor/`:**
- Purpose: AI tooling configuration (GSD/OpenSpec skills, agents); not part of the product
- Generated: By tool installers
- Committed: Mixed (mostly untracked in current status)

**`$SONISCOPE_HOME` (`/Volumes/Data/software/SoniScope`, outside repo):**
- Purpose: Worker runtime root — `inbox/`, `inbox/failed/`, `fragments/`, `tmp/`, `config.yaml`
- Generated: `make init-dirs`
- Committed: Never (contains secrets and audio data)

---

*Structure analysis: 2026-07-04*
