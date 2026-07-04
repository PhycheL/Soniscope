<!-- refreshed: 2026-07-04 -->
# Architecture

**Analysis Date:** 2026-07-04

## System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    WeChat Mini Program (device)                  │
│  Record → draft confirm → silent login → STS upload → verify    │
│  `apps/miniprogram/` (pages + pure-logic utils)                  │
└────────┬────────────────────────────────────────┬───────────────┘
         │ POST /issue-credential                 │ POST /verify-upload
         ▼                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              Aliyun FC 3.0 top-level Web Functions               │
│  `apps/fc/issue_credential/handler.py`  (STS single-key issue)  │
│  `apps/fc/verify_upload/handler.py`     (HeadObject verify)     │
│  shared auth/env/http/audit: `apps/fc/shared/fc_shared/`        │
└────────┬────────────────────────────────────────────────────────┘
         │ STS credential (oss:PutObject, single object key, ≤900s)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│         Aliyun OSS private bucket `soniscope-audio`              │
│  Object = the ONLY data contract: audio body + `x-oss-meta-*`   │
│  Key: `recordings/<YYYY-MM-DD>/<fragment_id>.wav`               │
└────────┬────────────────────────────────────────────────────────┘
         │ poll / HeadObject / download (NEVER DeleteObject)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Python Worker (local Mac host process)              │
│  `apps/worker/src/soniscope_worker/`                             │
│  poll → download → ffmpeg standardize → cloud ASR (NLS) →       │
│  atomic write to local disk file state machine ($SONISCOPE_HOME)│
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Mini program pages | Recording UI, draft confirm, upload list rendering, wx storage IO | `apps/miniprogram/pages/index/index.js`, `apps/miniprogram/pages/uploads/uploads.js` |
| Mini program utils | Pure logic: upload orchestration, queue state machine, OSS V4 form signing, chunking, ULID/fragment IDs, sha256 | `apps/miniprogram/utils/uploader.js`, `upload_queue.js`, `oss_sign.js`, `chunking.js`, `ulid.js` |
| FC `issue-credential` | wx code→openid auth, allowlist, size check, AssumeRole single-key STS | `apps/fc/issue_credential/handler.py` |
| FC `verify-upload` | Same auth, then HeadObject size/etag verification | `apps/fc/verify_upload/handler.py` |
| FC shared package | Auth, env loading, error codes, JSON HTTP helpers, redacted audit logging, STS/Head logic | `apps/fc/shared/fc_shared/` |
| FC custom runtime | Tiny threaded WSGI server delegating to `handler.handler` | `apps/fc/shared/app.py` |
| Worker pipeline | End-to-end fragment processing (7 stages, idempotent) | `apps/worker/src/soniscope_worker/pipeline.py` |
| Worker poller | OSS list/head/download, sha256 check, `.done` skip | `apps/worker/src/soniscope_worker/poller.py` |
| Worker audio | ffprobe detection, ffmpeg standardize to WAV | `apps/worker/src/soniscope_worker/audio.py` |
| Worker transcriber | `Transcriber` Protocol + factory (`cloud-speech` real, `whisper-local` placeholder) | `apps/worker/src/soniscope_worker/transcriber.py`, `nls.py` |
| Worker recovery | Startup scan: clean `.part`/`.tmp`, re-transcribe incomplete fragments | `apps/worker/src/soniscope_worker/recovery.py` |
| Worker manifest | `manifest.json` / `transcript.json` schema assembly | `apps/worker/src/soniscope_worker/manifest.py` |
| Worker CLI | Typer app; every make target maps to a subcommand | `apps/worker/src/soniscope_worker/cli.py` |
| FC deploy tooling | Package (vendoring `fc_shared`), backup, deploy, rollback, logs | `apps/worker/src/soniscope_worker/fc_deploy.py` |
| Live/E2E verification | Real-cloud probes and acceptance scripts | `apps/worker/src/soniscope_worker/fc_live.py`, `verify_upload_live.py`, `verify_prep.py`, `e2e.py`, `e2e_scenarios.py`, `sts_escape.py`, `retranscribe.py` |

## Pattern Overview

**Overall:** Four-tier pipeline architecture (device → serverless auth gateway → object storage as message bus → local worker), coordinated purely through OSS objects and a local-disk file state machine. No database, no message queue, no server-side API beyond two stateless FC functions.

**Key Characteristics:**
- **OSS object is the only data contract** between mini program, FC, and Worker: audio body + `x-oss-meta-*` metadata (session-id, chunk-seq, chunk-total, recorded-at, duration, original-format, sha256).
- **Local disk file state machine is the Worker's authoritative state**: progress judged by `manifest.json`, intermediate files, and a 0-byte `.done` marker — never a DB.
- **Pure logic + injected IO** layering everywhere: Python uses Protocols (`OssSource`, `Transcriber`, `StsIssuer`); mini program JS injects `deps` (wx adapters) into pure functions. Unit tests never touch the network.
- **Atomic three-step write protocol**: temp file → atomic `rename` → write `.done` last. `inbox/`, `tmp/`, `fragments/` must live on the same filesystem.
- **Idempotency by `.done`**: normal polling skips any fragment whose `.done` exists; only explicit `retranscribe` (`apps/worker/src/soniscope_worker/retranscribe.py`) re-processes.

## Layers

**Mini program (device layer):**
- Purpose: Recording, interruption protection, drafts, local cache, silent login, STS upload, verify, upload list. Deliberately thin — no business auth, no long-term keys.
- Location: `apps/miniprogram/`
- Contains: `pages/` (wx Page IO + rendering), `utils/` (pure logic modules), `config.js` (real cloud URLs, single source of truth)
- Depends on: FC endpoints and OSS upload domain declared in `apps/miniprogram/config.js`
- Used by: End user via WeChat

**FC functions (cloud compute layer):**
- Purpose: The only trusted gateway — exchange wx code for openid, enforce `OPENID_ALLOWLIST`, issue single-object-key STS, verify uploads via HeadObject.
- Location: `apps/fc/`
- Contains: One directory per function (`issue_credential/`, `verify_upload/`) each with a WSGI `handler.py` + `requirements.txt`; shared logic in `apps/fc/shared/fc_shared/`
- Depends on: `fc_shared` (vendored into each package at deploy time by `soniscope_worker.fc_deploy.package_function`), Aliyun STS/OSS SDKs, WeChat `jscode2session`
- Used by: Mini program (`utils/uploader.js`, `utils/verify.js`)

**OSS (cloud storage layer):**
- Purpose: Long-term audio backup and the transport between device and Worker. Bucket `soniscope-audio`, region `cn-beijing`, private.
- Location: No code — contract encoded in `apps/worker/src/soniscope_worker/oss_admin.py` (`object_key_for`) and `apps/fc/shared/fc_shared/sts.py`
- Contains: Objects at `recordings/<YYYY-MM-DD>/<fragment_id>.wav` (key always `.wav` even if source is m4a/mp3/aac/amr)
- Used by: Mini program (PutObject via STS), FC (HeadObject), Worker (list/head/get — never delete)

**Worker (backend process layer):**
- Purpose: Poll OSS, download, ffmpeg standardize, cloud ASR (Aliyun NLS), write fragment artifacts to `$SONISCOPE_HOME`.
- Location: `apps/worker/src/soniscope_worker/` (package `soniscope-worker`, run as `python -m soniscope_worker`)
- Contains: Pipeline modules plus a large set of live-test / E2E verification modules invoked via CLI subcommands
- Depends on: `alibabacloud-oss-v2`, `pydantic>=2`, `typer`, `pyyaml`, system `ffmpeg`/`ffprobe`; config from `$SONISCOPE_HOME/config.yaml`
- Used by: Operator via `make worker-run` and other make targets

## Data Flow

### Primary Request Path (record → transcript on disk)

1. Record + interruption-safe stop, draft saved locally (`apps/miniprogram/pages/index/index.js`, `utils/audio.js`, `utils/draft.js`)
2. User confirms draft → frozen into upload queue with fragment_id `<YYYYMMDDTHHMMSS>_<deviceShortId>_<ulid>` (`utils/upload_queue.js`, `utils/ulid.js`, `utils/ids` logic in `utils/device.js`)
3. `uploadFragment`: silent `wx.login` → POST `/issue-credential` → classify response → OSS PostObject direct upload with `x-oss-meta-*` fields, exponential backoff 5s/15s/45s (`apps/miniprogram/utils/uploader.js`, `utils/oss_sign.js`)
4. POST `/verify-upload` → FC HeadObject compares expected_size; queue state moves `pending_verify → verified` (`apps/miniprogram/utils/verify.js`, `apps/fc/verify_upload/handler.py`, `apps/fc/shared/fc_shared/head.py`)
5. Worker polls `recordings/` every `poll.interval_seconds`, skips `.done`, downloads to `inbox/<id>.part`, sha256-verifies against `x-oss-meta-sha256` (`apps/worker/src/soniscope_worker/poller.py`)
6. Standardize to `audio.wav` via ffprobe/ffmpeg; failures archived to `inbox/failed/` (`apps/worker/src/soniscope_worker/audio.py`)
7. Manifest draft written atomically (`apps/worker/src/soniscope_worker/manifest.py`, `pipeline.py` stage `manifest-draft`)
8. Transcribe via `Transcriber` — cloud NLS, default `upload_mode=oss-url` signed URL, fallback direct upload (`apps/worker/src/soniscope_worker/transcriber.py`, `nls.py`)
9. Atomic writes: `transcript.json` (via `tmp/`), `transcript.txt`, final `manifest.json`, then 0-byte `.done` last (`apps/worker/src/soniscope_worker/pipeline.py`, `recovery.py:atomic_write_json`)

### Crash Recovery Flow

1. On startup, recovery scan cleans `inbox/*.part`, `inbox/*.wav.tmp`, `tmp/*.transcript.json.tmp` (`apps/worker/src/soniscope_worker/recovery.py`)
2. Fragments with `audio.wav` but no `.done` are re-transcribed to completion
3. Fragments missing manifest draft are left for the next OSS poll to re-download (objects are never deleted)

### Explicit Re-transcription Flow

1. `make retranscribe FRAGMENT_ID=<id>` or `ARGS="--all-from <date> --upgrade"` (`apps/worker/src/soniscope_worker/retranscribe.py`)
2. `--force` re-transcribes unconditionally; `--upgrade` only when model/params_version differ; without flags, `.done` fragments are skipped
3. This is the ONLY path that overrides `.done` idempotency — normal polling never auto-retranscribes on model changes

**State Management:**
- Mini program: 8-state upload queue in wx storage key `soniscope:upload_queue` — `draft → queued → uploading → pending_verify → verified`, plus `upload_failed`, `manual_retry`, `manual_verify` (`apps/miniprogram/utils/upload_queue.js`)
- Worker: file-presence state machine per fragment dir — completion means exactly 5 artifacts: `audio.wav`, `manifest.json`, `transcript.json`, `transcript.txt`, `.done`
- FC: fully stateless; all config from environment variables (`apps/fc/shared/fc_shared/env.py`)

## Key Abstractions

**`OssSource` Protocol (Worker):**
- Purpose: IO boundary for OSS — exposes only list/head/download, structurally excluding any delete capability (security red line R-07)
- Examples: `apps/worker/src/soniscope_worker/poller.py` (`OssSource`, `RealOssSource` with lazy SDK import; tests inject `FakeSource`)
- Pattern: Protocol injection; cloud SDKs imported lazily so unit tests never load them

**`Transcriber` Protocol + factory:**
- Purpose: Pluggable ASR — pipeline depends only on the Protocol; `create_transcriber` dispatches on `config.yaml` `transcriber.name`
- Examples: `apps/worker/src/soniscope_worker/transcriber.py` (`CloudSpeechTranscriber`, `WhisperLocalTranscriber` placeholder raising `NotImplementedError`), `nls.py` (real Aliyun NLS)
- Pattern: Protocol + factory; `TranscriptResult` in-memory struct derives the 5-field `transcript.json`

**`fc_shared` package:**
- Purpose: Single auth/validation/audit path shared by both FC functions (`authorize_request`: JSON → wx code → openid → allowlist; stable error codes; `hash_openid` / `is_sensitive` log redaction)
- Examples: `apps/fc/shared/fc_shared/auth.py`, `env.py`, `errors.py`, `http.py`, `audit.py`, `sts.py`, `head.py`, `wechat.py`
- Pattern: Vendored at deploy time into each function zip root by `soniscope_worker.fc_deploy.package_function` (not pip-installed)

**Injected-deps pure functions (mini program JS):**
- Purpose: All IO (`wx.login`, `wx.request`, `wx.uploadFile`, timers) funneled through a `deps` object; pure functions (e.g. `classifyFcResponse`) are node-testable without WeChat runtime
- Examples: `apps/miniprogram/utils/uploader.js`, `utils/verify.js`, `utils/queue_runtime.js`
- Pattern: Dependency injection at the function argument level; pages provide real wx adapters

**Fragment ID / object key mapping:**
- Purpose: Bidirectional derivation `fragment_id ↔ recordings/<date>/<id>.wav`, validated by round-trip (`fragment_id_from_key` checks `object_key_for(id) == key`)
- Examples: `apps/worker/src/soniscope_worker/oss_admin.py` (`object_key_for`), `poller.py` (`fragment_id_from_key`), `apps/fc/shared/fc_shared/sts.py` (`object_key_for`)
- Pattern: Duplicated by design across FC and Worker (FC packages cannot import the worker package)

## Entry Points

**Mini program:**
- Location: `apps/miniprogram/app.js` (App launch: generates persistent `device_short_id`), pages registered in `apps/miniprogram/app.json`
- Triggers: WeChat client launch
- Responsibilities: Global env config, device ID, error logging

**FC functions:**
- Location: `apps/fc/shared/app.py` — custom runtime start command `python3 app.py`; threaded WSGI server delegating to the function-local `handler.handler` (`apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`)
- Triggers: Anonymous HTTP trigger (business auth enforced by openid allowlist in `fc_shared.authorize_request`); GET is a liveness probe used by deploy verification
- Responsibilities: STS issuance / upload verification

**Worker CLI:**
- Location: `apps/worker/src/soniscope_worker/__main__.py` → `cli.py` (Typer app; also console script `soniscope-worker`)
- Triggers: `make worker-run` (`run` command → `poller.run_worker_run`), plus ~30 verification subcommands (see `Makefile`)
- Responsibilities: Main poll loop, config check, dir init, deploy/rollback/log tooling, all live/E2E test commands

**Makefile (operator entry point):**
- Location: `Makefile` (repo root) — the single command entry; users never `cd` into subdirectories
- Triggers: `make install|typecheck|lint|test|worker-run|deploy-fc|test-*|verify-*`
- Responsibilities: Every target shells to `uv run python -m soniscope_worker <subcommand>`

## Architectural Constraints

- **Threading:** Worker is a single-threaded poll loop; FC custom runtime uses `ThreadingWSGIServer` with daemon threads (`apps/fc/shared/app.py`); pipeline uses per-fragment file locks (`apps/worker/src/soniscope_worker/locks.py:fragment_lock`)
- **No database / no queue:** Worker state must remain derivable from disk files alone; `inbox/`, `tmp/`, `fragments/` must share one filesystem for atomic rename
- **Runtime/repo separation:** Worker runtime data lives in `$SONISCOPE_HOME` (`/Volumes/Data/software/SoniScope`), never in the repo; config from `$SONISCOPE_HOME/config.yaml` (chmod 600, Pydantic v2 validated, `apps/worker/src/soniscope_worker/config.py`)
- **FC 3.0 has no service layer:** Only two top-level web functions; never create/reference a `soniscope-svc`
- **Handler module naming:** Both FC `handler.py` files share a module name — they are ruff-checked only, excluded from mypy (see `pyproject.toml` comments); `fc_shared` IS in mypy strict scope
- **Real cloud values are canonical:** FC URL subdomain `issue-cedential-ottfirocds` is genuinely misspelled by Aliyun — never "fix" it (`apps/miniprogram/config.js`, `AGENTS.md`)
- **Doc authority chain:** product scope `docs/PRD_v1.md` → tech details `docs/tech-spec.md` → real resources `docs/runbook/cloud-setup.md` → `AGENTS.md` (docs may be moved/renamed; PRD lives under `docs/v1.0.0 prd/`)

## Anti-Patterns

### Calling OSS DeleteObject from Worker business code

**What happens:** A convenience delete of a processed/failed object from Worker code
**Why it's wrong:** Security red line R-07 — OSS is the long-term backup; the `OssSource` Protocol deliberately excludes delete so this cannot compile against the abstraction
**Do this instead:** Never delete from business paths. Test-only deletion goes through `make oss-delete-obj` (`apps/worker/src/soniscope_worker/oss_admin.py`), which requires explicit `--yes`/env opt-in and is labeled test-only

### Writing final artifacts before `.done`, or `.done` early

**What happens:** Writing `transcript.json` in place, or creating `.done` before all 5 artifacts exist
**Why it's wrong:** Crash mid-write leaves a fragment that looks complete; recovery and idempotency both key off `.done` presence
**Do this instead:** Three-step protocol — temp file in `tmp/` → atomic rename → `.done` last (`apps/worker/src/soniscope_worker/recovery.py:atomic_write_json`, `create_done_marker`; orchestration in `pipeline.py`)

### Direct cloud SDK / wx API calls inside pure logic

**What happens:** Importing `alibabacloud_oss_v2` at module top-level or calling `wx.request` inside a util function
**Why it's wrong:** Breaks the "unit tests never touch network" rule (`AGENTS.md` testing rules); mypy has no stubs for cloud SDKs; JS utils become untestable in node
**Do this instead:** Lazy-import SDKs inside `Real*` adapter classes (`poller.py:RealOssSource`), inject IO via Protocols/`deps` objects; real calls only in `make test-*-live` / `verify-*` targets

### Bypassing the Makefile with ad-hoc scripts

**What happens:** Adding a standalone script or second entry point for a verification task
**Why it's wrong:** The Makefile is the single command entry; parallel entry points drift and skip the pass/fail summary conventions
**Do this instead:** Add a Typer subcommand in `apps/worker/src/soniscope_worker/cli.py` plus a `make` target following tech-spec §6.5 naming

## Error Handling

**Strategy:** Stable machine-readable error codes at boundaries; retry taxonomy split by error class; failures never fabricate completion.

**Patterns:**
- FC: `FcHttpError`/`FcConfigError` with stable codes (`INVALID_CODE` 401, `OPENID_NOT_ALLOWED` 403, `SIZE_EXCEEDED` 400, `OBJECT_NOT_FOUND`, `SIZE_MISMATCH`, `SERVER_MISCONFIGURED` 500) — `apps/fc/shared/fc_shared/errors.py`; any STS issuance failure collapses to a generic 500 to avoid leaking secrets
- Mini program: network/5xx → exponential backoff 5s/15s/45s max 3 tries; 4xx → immediate fail with code; exhausted retries → `manual_retry`/`manual_verify` states (`apps/miniprogram/utils/uploader.js`, `utils/verify.js`)
- Worker: any pipeline stage failure → no `.done`, error log carries `fragment_id` + stage constant (`pipeline.py` `STAGE_*`); download failures delete `.part` for redownload next cycle; transcode failures archived to `inbox/failed/`

## Cross-Cutting Concerns

**Logging:** FC uses structured `fc_shared.log_event` with openid hashed (`audit.py:hash_openid`) and `is_sensitive` redaction guard; Worker logs stage-tagged lines via injected `log` callables; mini program uses `apps/miniprogram/utils/logger.js`. Never log AK/Secret/token/full openid; config secrets shown 4-char-masked only (`config.py` SecretStr + `masked_summary`).
**Validation:** Worker config via Pydantic v2 strict schema (`apps/worker/src/soniscope_worker/config.py`); FC requests via `fc_shared.http.require_fields` + typed parsers (`parse_size`); mypy strict across `apps/worker/src`, `apps/worker/tests`, `apps/fc/shared`, `apps/fc/tests`.
**Authentication:** No user system — wx silent login code → `jscode2session` openid → `OPENID_ALLOWLIST` env check (`apps/fc/shared/fc_shared/auth.py`, `wechat.py`); STS policy locked to `oss:PutObject` on one object key, ≤900s (`sts.py:single_key_policy`).

---

*Architecture analysis: 2026-07-04*
