<!-- GSD:project-start source:PROJECT.md -->

## Project

**SoniScope — 上线前代码审计里程碑**

SoniScope 是一条个人录音转写流水线:WeChat 小程序录音 → Aliyun FC 3.0 函数(签发 STS 凭证、校验上传)→ OSS 私有桶(唯一数据契约)→ 本地 Python Worker 轮询、ffmpeg 标准化、NLS 云端 ASR 转写。项目处于部署上线阶段;本里程碑不新增功能,而是对现有代码进行一次全面审计,产出结构化审计报告,作为正式对外上线前的把关。

**Core Value:** 在正式上线前,拿到一份可信、有证据、分级明确的审计报告,准确回答"现有代码哪里不一致、哪里有债务、上线有什么风险"。

### Constraints

- **产出形态**: 仅审计报告,不改代码 — 用户明确要求修复留给下一个里程碑
- **报告标准**: 每个发现必须有严重度分级、文件/行号证据、修复建议与工作量估计 — 报告要能直接驱动下个里程碑
- **审计基准**: 契约一致性以三处实现的现状互相对照为准,不引入目标态设计 — 用户明确选择
- **技术栈**: Python 3.11+(mypy-strict/ruff)与小程序 JS 双语言仓库 — 审计工具与判断标准需分别适配

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python >=3.11 (3.12 observed in local bytecode) - Worker daemon (`apps/worker/src/soniscope_worker/`), FC serverless functions (`apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`, shared library `apps/fc/shared/fc_shared/`), deployment tooling (`apps/worker/src/soniscope_worker/fc_deploy.py`), scripts (`scripts/`)
- JavaScript (CommonJS, ES6) - WeChat Mini Program client (`apps/miniprogram/`): pages in `apps/miniprogram/pages/`, pure-function utilities in `apps/miniprogram/utils/` (upload queue, chunking, OSS V4 signing, HMAC-SHA256, ULID, logging)
- Make - Single command entry point for the whole repo (`Makefile` at repo root; users never `cd` into subdirectories)
- Shell - `scripts/gen_worker_config.sh` (config generation helper)

## Runtime

- Python 3.11+ locally for the Worker (mypy pinned to `python_version = "3.11"` in `pyproject.toml`)
- Alibaba Cloud FC 3.0 Custom Runtime for serverless functions: start command `python3 app.py`, a threaded WSGI server (`apps/fc/shared/app.py`) delegating to each function's `handler.handler`; listens on `FC_SERVER_PORT`/`PORT`, fallback 9000
- WeChat Mini Program runtime, base library `libVersion: 3.5.5` (`apps/miniprogram/project.config.json`), appid `wx3f973c7297728b0c`
- Node.js (any recent) - only for running Mini Program JS unit tests via `node --test` (invoked from pytest wrapper `apps/worker/tests/test_miniprogram_js.py`; skipped if node missing)
- `uv` with workspace layout: root `pyproject.toml` declares `[tool.uv.workspace] members = ["apps/worker"]`; root project is `package = false` and depends on workspace member `soniscope-worker`
- Lockfile: present (`uv.lock`, revision 3)
- No npm/package.json for the Mini Program - all JS utilities are dependency-free CommonJS modules
- FC function deps are plain `requirements.txt` per function (`apps/fc/issue_credential/requirements.txt`, `apps/fc/verify_upload/requirements.txt`), vendored into the deploy zip by `make deploy-fc`

## Frameworks

- Typer >=0.12 - Worker CLI (`apps/worker/src/soniscope_worker/cli.py`, entry point `soniscope-worker = "soniscope_worker.cli:app"`)
- Pydantic v2 - config schema validation with secret masking (`apps/worker/src/soniscope_worker/config.py`, `MaskedSecret` subclass of `SecretStr`)
- PyYAML >=6 - `config.yaml` parsing
- `wsgiref` (stdlib) - FC custom-runtime HTTP server (`apps/fc/shared/app.py`); no web framework, handlers are raw WSGI callables
- pytest >=8.0 - `testpaths = ["apps/worker/tests", "apps/fc/tests"]` (root `pyproject.toml`); unit tests mock all cloud IO
- `node --test` (Node built-in runner) - Mini Program JS tests in `apps/miniprogram/test/*.test.js`, bridged into `make test` via `apps/worker/tests/test_miniprogram_js.py`
- hatchling - build backend for `soniscope-worker` (`apps/worker/pyproject.toml`)
- mypy >=1.8 strict mode - covers `apps/worker/src`, `apps/worker/tests`, `apps/fc/shared`, `apps/fc/tests` (FC `handler.py` files excluded due to duplicate module names; ruff-only)
- ruff >=0.4 - lint (`E`, `F`, `I`, `UP`, `B`), line-length 100, target py311
- Custom miniprogram linter - `apps/worker/src/soniscope_worker/miniprogram_lint.py` via `make lint-miniprogram` (checks legal-domain URLs, etc.)
- Make - all quality gates and ops commands (`make install/typecheck/lint/test/deploy-fc/...`)

## Key Dependencies

- `alibabacloud-oss-v2` >=1.3.1 - OSS client (download audio, presign URLs, HeadObject); lazy-imported
- `aliyun-python-sdk-core` >=2.16.0 (`aliyunsdkcore`) - POP/RPC API client for NLS filetrans (SubmitTask/GetTaskResult) and CreateToken; lazy-imported
- `alibabacloud-sts20150401` >=1.2.0 + `alibabacloud-tea-openapi` >=0.4.4 - STS AssumeRole (also FC issue-credential runtime dep)
- `alibabacloud-fc20230330` >=4.7.7 - FC 3.0 management SDK, used ONLY by deploy tooling (`fc_deploy.py`); never packaged into function code
- `apps/fc/issue_credential/requirements.txt`: `alibabacloud-sts20150401`, `alibabacloud-tea-openapi`
- `apps/fc/verify_upload/requirements.txt`: `alibabacloud-oss-v2`
- Shared module `fc_shared` is vendored into each function's zip at package root by `fc_deploy.py` (`SHARED_PARENT = ("apps", "fc", "shared")`)
- `ffmpeg` / `ffprobe` - required on the Worker host for audio format detection and non-WAV→WAV transcoding (`apps/worker/src/soniscope_worker/audio.py`, checked by `verify_prep.py` `REQUIRED_TOOLS`)
- All cloud SDKs are lazy-imported behind Protocol interfaces (e.g. `NlsBackend`, `StsIssuer`, `FcApi`, `OssSource`) so unit tests inject fakes and never touch the network

## Configuration

- `SONISCOPE_HOME` - runtime data root, resolved from process env var first, then upward-searched `.env` file (`apps/worker/src/soniscope_worker/paths.py`); no `.env` currently committed at repo root
- `$SONISCOPE_HOME/config.yaml` - Worker config, must be chmod 600, validated by Pydantic (`config.py`). Sections: `oss` (endpoint/bucket/AK), `poll.interval_seconds`, `transcriber` (name/provider/model/params_version/api_endpoint/appkey/AK/upload_mode/local.enabled)
- FC deploy credentials: `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET` env vars (never in git)
- FC runtime env vars (set in FC console, names documented in `apps/fc/shared/fc_shared/env.py`): `OSS_BUCKET`, `OSS_REGION`, `OSS_ENDPOINT`, `WX_APPID`, `WX_APP_SECRET`, `OPENID_ALLOWLIST`, plus `RAM_ROLE_ARN`/`ALIYUN_AK_ID`/`ALIYUN_AK_SECRET` (issue-credential), `ALIYUN_AK_ID`/`ALIYUN_AK_SECRET` (verify-upload), optional `MAX_UPLOAD_BYTES` (default 52428800 = 50 MB)
- Mini Program config: `apps/miniprogram/config.js` (single source of truth for FC URLs, OSS upload URL, region, chunking threshold `CHUNK_MAX_DURATION_SECONDS = 600`, `ENV` flag)
- `pyproject.toml` (root) - uv workspace, mypy strict, ruff, pytest config (`pythonpath = ["apps/fc/shared"]` so FC tests can import `fc_shared`)
- `apps/worker/pyproject.toml` - hatchling wheel packaging `src/soniscope_worker`
- `Makefile` - only supported command interface (`make install`, `make test`, `make deploy-fc FUNCTION=...`, ~40 verification targets)
- `apps/miniprogram/project.config.json` - WeChat DevTools build settings (es6, minify, urlCheck)

## Platform Requirements

- macOS/Linux with Python >=3.11, `uv`, `ffmpeg`/`ffprobe`, Node.js (for JS tests), min 50 GiB free disk (`verify_prep.py` `MIN_DISK_BYTES`)
- WeChat DevTools for the Mini Program
- `SONISCOPE_HOME` directory pre-created and exported (or in `.env`)
- Worker: long-running local process on user machine (`make worker-run`), polling OSS every `poll.interval_seconds`
- FC functions: Alibaba Cloud FC 3.0, region `cn-beijing`, 0.35 vCPU / 512 MB, anonymous HTTP trigger (auth enforced in-app via openid allowlist)
- Mini Program: WeChat platform, legal domains registered per `apps/miniprogram/config.js`
- No CI pipeline detected (no `.github/` directory)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Language Split

- **Python 3.11+** (primary): `apps/worker/src/soniscope_worker/`, `apps/fc/shared/fc_shared/`, `apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`
- **JavaScript (WeChat miniprogram, CommonJS, ES5-ish)**: `apps/miniprogram/utils/`, `apps/miniprogram/pages/`, `apps/miniprogram/test/`

## Naming Patterns

- `snake_case.py` module names, one domain concern per module: `poller.py`, `transcriber.py`, `oss_admin.py`, `fc_deploy.py`
- FC function entry points are always `handler.py` inside the function directory (`apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`) — same filename by convention; this is why they are ruff-only, not mypy-checked (module name collision, noted in `pyproject.toml`)
- Test files: `test_<module>.py` mirroring the module under test
- `snake_case.js` for utils: `upload_queue.js`, `oss_sign.js`, `fault_injection.js`
- Tests: `<module>.test.js` in `apps/miniprogram/test/`
- Miniprogram pages use the WeChat four-file convention: every page in `app.json` must have `.js/.json/.wxml/.wxss` (enforced by `miniprogram_lint.py`)
- Python: `snake_case`. Private helpers prefixed with `_` (`_collect_validation_errors` in `config.py`, `_write_config` in tests)
- Pure predicate/check functions named `check_*` (in `miniprogram_lint.py`), `is_*`, `assert_*` (in `fc_live.py`: `assert_credential_complete`, `assert_status_error`)
- JS: `camelCase` (`classifyFcResponse`, `uploadFragment`, `buildPostObjectForm`)
- Module-level constants in `UPPER_SNAKE_CASE`, often exported and asserted in tests: `RETRY_DELAYS_SECONDS`, `RESIGN_THRESHOLD_SECONDS` (`nls.py`); `RETRY_DELAYS_MS`, `MAX_UPLOAD_RETRIES` (`uploader.js`)
- Stable error codes as string constants: `INVALID_CODE`, `OPENID_NOT_ALLOWED`, `SIZE_EXCEEDED`, `STS_ISSUE_FAILED` in `apps/fc/shared/fc_shared/errors.py` — shared verbatim between Python FC handlers and miniprogram JS (`uploader.js` branches on the same strings)
- Private module constants prefixed with `_`: `_SENSITIVE_SUBSTRINGS`, `_REDACTED` (`audit.py`), `_AK_ID_RE` (`miniprogram_lint.py`)
- `PascalCase` classes. Pydantic v2 `BaseModel` subclasses for config (`SoniScopeConfig`, `OSSConfig`, `TranscriberConfig` in `config.py`)
- Custom exceptions end in `Error`: `ConfigError`, `RuntimeHomeError`, `FcHttpError`, `FcConfigError`, `NlsTranscribeError`, `ProbeError`
- `@dataclass(frozen=True)` for small value objects: `LintIssue` in `miniprogram_lint.py`

## Code Style

- `ruff` — config in root `pyproject.toml`: `target-version = "py311"`, `line-length = 100`, rules `E, F, I, UP, B`
- `mypy --strict` for `apps/worker/src`, `apps/worker/tests`, `apps/fc/shared`, `apps/fc/tests` (see `[tool.mypy]` in `pyproject.toml`). All functions fully type-annotated, including tests (`-> None` on every test function)
- Cloud SDK modules (`alibabacloud_*`, `aliyunsdkcore`) have `ignore_missing_imports` overrides — they are lazy-imported optional runtime deps
- Modern typing syntax: `Path | None`, `list[str]`, `dict[str, object]` (no `Optional`/`List`)
- `from __future__ import annotations` in most modules (20 of 26 in `soniscope_worker/`); include it in new modules
- CommonJS `require`/`module.exports`, no build step, no semicolon-free/prettier tooling detected — 2-space indent, single quotes, trailing function-expression style (`function () {}` over arrows in several files)
- Chinese comments referencing user stories and AC numbers (e.g., "AC#3")

## Import Organization

## Error Handling

- Domain-specific exception per failure category, raised with actionable Chinese messages that tell the operator what to fix: `ConfigError` in `config.py` includes the missing-field list and a chmod hint
- Chain exceptions: `raise ConfigError(...) from exc`
- Collect-all-then-fail: validation errors are aggregated and reported in one shot rather than failing on the first (`_collect_validation_errors` in `config.py`)
- CLI boundary converts exceptions to exit codes: catch `(ConfigError, RuntimeHomeError)`, `typer.echo(str(exc), err=True)`, `raise typer.Exit(code=1) from exc` (`cli.py`)
- FC HTTP boundary: `FcHttpError(status, error_code, message=...)` carries a client-safe JSON `payload` with a stable `error` code (`apps/fc/shared/fc_shared/errors.py`). Messages must never contain secrets
- Retry with fixed backoff schedule constants: 5s → 15s → 45s, max 3 attempts — mirrored in Python (`nls.py` `RETRY_DELAYS_SECONDS`) and JS (`uploader.js` `RETRY_DELAYS_MS`) and asserted in tests

## Secrets Handling (project red line)

- Config secrets typed as `MaskedSecret(SecretStr)` — repr/str shows only first/last 4 chars (`config.py`); plaintext retrieved only via `.get_secret_value()`
- `mask_secret()` helper for any ad-hoc display (`config.py`)
- FC structured logs pass through `fc_shared/audit.py`: `log_event(event, **fields)` auto-redacts fields matching `SENSITIVE_FIELD_NAMES`/substrings (`secret`, `token`, `appkey`, ...); openid is logged only as `hash_openid()` sha256 prefix
- `miniprogram_lint.py` scans miniprogram source for hardcoded long-term AK IDs (`LTAI...`) and secret-looking literals
- Tests assert absence of plaintext secrets in output (`test_config.py::test_secret_not_leaked_in_repr_and_summary`, leak-detection tests in `test_verify_upload_live.py`)

## Logging

- **Worker CLI/daemon:** output via `typer.echo`; long-running functions accept an injected `log: Callable[[str], None] = print` parameter (`poller.py::run_worker_run`) so tests can capture output
- **FC functions:** structured stdout lines via `fc_shared/audit.py::log_event()` — `event=<name> key=value ...`, sorted keys, `None` omitted, sensitive fields redacted. FC runtime ships stdout to the log service
- **Miniprogram:** injected `logger` dep in utils; only non-sensitive fields (object_key, status, error codes) — see comments in `apps/miniprogram/utils/uploader.js`

## Comments

- Module docstring: purpose + owning user story (US-NNN) + key invariants
- Section dividers inside larger files: `# ── 段落名 ─────` (see `errors.py`, `audit.py`)
- Inline comments explain *why*, especially deliberate oddities — e.g., the intentionally misspelled `issue-cedential` FC subdomain has a comment warning not to "fix" it (`miniprogram_lint.py`)
- Constants are annotated with the spec/AC they implement

## Function Design

- Prefer pure functions for anything testable; push IO to an orchestration layer or injected dependency. This "纯逻辑 + IO 注入" (pure logic + injected IO) split is the codebase's core pattern, stated explicitly in `miniprogram_lint.py` and `uploader.js` docstrings
- Dependency injection via constructor/parameter, typed as protocols where needed (`FcLiveProbes` protocol in `fc_live.py`; backend objects in `nls.py`)
- Keyword-only args for options: `def __init__(self, *, poll_sequence=...)`; `def __init__(self, status, error_code, *, message="", **extra)`
- Functions that produce reports return `(lines, exit_code)` tuples and let the CLI print (`verify_prep.py::run_verify_prep`)

## Module Design

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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

- **OSS object is the only data contract** between mini program, FC, and Worker: audio body + `x-oss-meta-*` metadata (session-id, chunk-seq, chunk-total, recorded-at, duration, original-format, sha256).
- **Local disk file state machine is the Worker's authoritative state**: progress judged by `manifest.json`, intermediate files, and a 0-byte `.done` marker — never a DB.
- **Pure logic + injected IO** layering everywhere: Python uses Protocols (`OssSource`, `Transcriber`, `StsIssuer`); mini program JS injects `deps` (wx adapters) into pure functions. Unit tests never touch the network.
- **Atomic three-step write protocol**: temp file → atomic `rename` → write `.done` last. `inbox/`, `tmp/`, `fragments/` must live on the same filesystem.
- **Idempotency by `.done`**: normal polling skips any fragment whose `.done` exists; only explicit `retranscribe` (`apps/worker/src/soniscope_worker/retranscribe.py`) re-processes.

## Layers

- Purpose: Recording, interruption protection, drafts, local cache, silent login, STS upload, verify, upload list. Deliberately thin — no business auth, no long-term keys.
- Location: `apps/miniprogram/`
- Contains: `pages/` (wx Page IO + rendering), `utils/` (pure logic modules), `config.js` (real cloud URLs, single source of truth)
- Depends on: FC endpoints and OSS upload domain declared in `apps/miniprogram/config.js`
- Used by: End user via WeChat
- Purpose: The only trusted gateway — exchange wx code for openid, enforce `OPENID_ALLOWLIST`, issue single-object-key STS, verify uploads via HeadObject.
- Location: `apps/fc/`
- Contains: One directory per function (`issue_credential/`, `verify_upload/`) each with a WSGI `handler.py` + `requirements.txt`; shared logic in `apps/fc/shared/fc_shared/`
- Depends on: `fc_shared` (vendored into each package at deploy time by `soniscope_worker.fc_deploy.package_function`), Aliyun STS/OSS SDKs, WeChat `jscode2session`
- Used by: Mini program (`utils/uploader.js`, `utils/verify.js`)
- Purpose: Long-term audio backup and the transport between device and Worker. Bucket `soniscope-audio`, region `cn-beijing`, private.
- Location: No code — contract encoded in `apps/worker/src/soniscope_worker/oss_admin.py` (`object_key_for`) and `apps/fc/shared/fc_shared/sts.py`
- Contains: Objects at `recordings/<YYYY-MM-DD>/<fragment_id>.wav` (key always `.wav` even if source is m4a/mp3/aac/amr)
- Used by: Mini program (PutObject via STS), FC (HeadObject), Worker (list/head/get — never delete)
- Purpose: Poll OSS, download, ffmpeg standardize, cloud ASR (Aliyun NLS), write fragment artifacts to `$SONISCOPE_HOME`.
- Location: `apps/worker/src/soniscope_worker/` (package `soniscope-worker`, run as `python -m soniscope_worker`)
- Contains: Pipeline modules plus a large set of live-test / E2E verification modules invoked via CLI subcommands
- Depends on: `alibabacloud-oss-v2`, `pydantic>=2`, `typer`, `pyyaml`, system `ffmpeg`/`ffprobe`; config from `$SONISCOPE_HOME/config.yaml`
- Used by: Operator via `make worker-run` and other make targets

## Data Flow

### Primary Request Path (record → transcript on disk)

### Crash Recovery Flow

### Explicit Re-transcription Flow

- Mini program: 8-state upload queue in wx storage key `soniscope:upload_queue` — `draft → queued → uploading → pending_verify → verified`, plus `upload_failed`, `manual_retry`, `manual_verify` (`apps/miniprogram/utils/upload_queue.js`)
- Worker: file-presence state machine per fragment dir — completion means exactly 5 artifacts: `audio.wav`, `manifest.json`, `transcript.json`, `transcript.txt`, `.done`
- FC: fully stateless; all config from environment variables (`apps/fc/shared/fc_shared/env.py`)

## Key Abstractions

- Purpose: IO boundary for OSS — exposes only list/head/download, structurally excluding any delete capability (security red line R-07)
- Examples: `apps/worker/src/soniscope_worker/poller.py` (`OssSource`, `RealOssSource` with lazy SDK import; tests inject `FakeSource`)
- Pattern: Protocol injection; cloud SDKs imported lazily so unit tests never load them
- Purpose: Pluggable ASR — pipeline depends only on the Protocol; `create_transcriber` dispatches on `config.yaml` `transcriber.name`
- Examples: `apps/worker/src/soniscope_worker/transcriber.py` (`CloudSpeechTranscriber`, `WhisperLocalTranscriber` placeholder raising `NotImplementedError`), `nls.py` (real Aliyun NLS)
- Pattern: Protocol + factory; `TranscriptResult` in-memory struct derives the 5-field `transcript.json`
- Purpose: Single auth/validation/audit path shared by both FC functions (`authorize_request`: JSON → wx code → openid → allowlist; stable error codes; `hash_openid` / `is_sensitive` log redaction)
- Examples: `apps/fc/shared/fc_shared/auth.py`, `env.py`, `errors.py`, `http.py`, `audit.py`, `sts.py`, `head.py`, `wechat.py`
- Pattern: Vendored at deploy time into each function zip root by `soniscope_worker.fc_deploy.package_function` (not pip-installed)
- Purpose: All IO (`wx.login`, `wx.request`, `wx.uploadFile`, timers) funneled through a `deps` object; pure functions (e.g. `classifyFcResponse`) are node-testable without WeChat runtime
- Examples: `apps/miniprogram/utils/uploader.js`, `utils/verify.js`, `utils/queue_runtime.js`
- Pattern: Dependency injection at the function argument level; pages provide real wx adapters
- Purpose: Bidirectional derivation `fragment_id ↔ recordings/<date>/<id>.wav`, validated by round-trip (`fragment_id_from_key` checks `object_key_for(id) == key`)
- Examples: `apps/worker/src/soniscope_worker/oss_admin.py` (`object_key_for`), `poller.py` (`fragment_id_from_key`), `apps/fc/shared/fc_shared/sts.py` (`object_key_for`)
- Pattern: Duplicated by design across FC and Worker (FC packages cannot import the worker package)

## Entry Points

- Location: `apps/miniprogram/app.js` (App launch: generates persistent `device_short_id`), pages registered in `apps/miniprogram/app.json`
- Triggers: WeChat client launch
- Responsibilities: Global env config, device ID, error logging
- Location: `apps/fc/shared/app.py` — custom runtime start command `python3 app.py`; threaded WSGI server delegating to the function-local `handler.handler` (`apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`)
- Triggers: Anonymous HTTP trigger (business auth enforced by openid allowlist in `fc_shared.authorize_request`); GET is a liveness probe used by deploy verification
- Responsibilities: STS issuance / upload verification
- Location: `apps/worker/src/soniscope_worker/__main__.py` → `cli.py` (Typer app; also console script `soniscope-worker`)
- Triggers: `make worker-run` (`run` command → `poller.run_worker_run`), plus ~30 verification subcommands (see `Makefile`)
- Responsibilities: Main poll loop, config check, dir init, deploy/rollback/log tooling, all live/E2E test commands
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

### Writing final artifacts before `.done`, or `.done` early

### Direct cloud SDK / wx API calls inside pure logic

### Bypassing the Makefile with ad-hoc scripts

## Error Handling

- FC: `FcHttpError`/`FcConfigError` with stable codes (`INVALID_CODE` 401, `OPENID_NOT_ALLOWED` 403, `SIZE_EXCEEDED` 400, `OBJECT_NOT_FOUND`, `SIZE_MISMATCH`, `SERVER_MISCONFIGURED` 500) — `apps/fc/shared/fc_shared/errors.py`; any STS issuance failure collapses to a generic 500 to avoid leaking secrets
- Mini program: network/5xx → exponential backoff 5s/15s/45s max 3 tries; 4xx → immediate fail with code; exhausted retries → `manual_retry`/`manual_verify` states (`apps/miniprogram/utils/uploader.js`, `utils/verify.js`)
- Worker: any pipeline stage failure → no `.done`, error log carries `fragment_id` + stage constant (`pipeline.py` `STAGE_*`); download failures delete `.part` for redownload next cycle; transcode failures archived to `inbox/failed/`

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| agent-browser | Automates browser interactions for web testing, form filling, screenshots, and data extraction. Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, test web applications, or extract information from web pages. | `.claude/skills/agent-browser-skill/SKILL.md` |
| openspec-apply-change | Implement tasks from an OpenSpec change. Use when the user wants to start implementing, continue implementation, or work through tasks. | `.claude/skills/openspec-apply-change/SKILL.md` |
| openspec-archive-change | Archive a completed change in the experimental workflow. Use when the user wants to finalize and archive a change after implementation is complete. | `.claude/skills/openspec-archive-change/SKILL.md` |
| openspec-explore | Enter explore mode - a thinking partner for exploring ideas, investigating problems, and clarifying requirements. Use when the user wants to think through something before or during a change. | `.claude/skills/openspec-explore/SKILL.md` |
| openspec-propose | Propose a new change with all artifacts generated in one step. Use when the user wants to quickly describe what they want to build and get a complete proposal with design, specs, and tasks ready for implementation. | `.claude/skills/openspec-propose/SKILL.md` |
| openspec-sync-specs | Sync delta specs from a change to main specs. Use when the user wants to update main specs with changes from a delta spec, without archiving the change. | `.claude/skills/openspec-sync-specs/SKILL.md` |
| prd | "为新功能生成 Product Requirements Document (PRD)。在规划功能、启动新项目或需要创建 PRD 时使用。触发词：创建一个prd" | `.claude/skills/prd/SKILL.md` |
| ralph | "将 PRD 转换为 prd.json 格式，供 Ralph 自主 agent 系统使用。当你已有 PRD 并需要将其转换为 Ralph 的 JSON 格式时使用。触发词：将prd 转成 prd.json" | `.claude/skills/ralph/SKILL.md` |
| ask-matt | Ask which skill or flow fits your situation. A router over the skills in this repo. | `.agents/skills/ask-matt/SKILL.md` |
| code-review | Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes — Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/PRD asked for?). Runs both reviews in parallel sub-agents and reports them side by side. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to "review since X". | `.agents/skills/code-review/SKILL.md` |
| codebase-design | Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary. | `.agents/skills/codebase-design/SKILL.md` |
| diagnosing-bugs | Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow. | `.agents/skills/diagnosing-bugs/SKILL.md` |
| domain-modeling | Build and sharpen a project's domain model. Use when the user wants to pin down domain terminology or a ubiquitous language, record an architectural decision, or when another skill needs to maintain the domain model. | `.agents/skills/domain-modeling/SKILL.md` |
| edit-article | Edit and improve articles by restructuring sections, improving clarity, and tightening prose. Use when user wants to edit, revise, or improve an article draft. | `.agents/skills/edit-article/SKILL.md` |
| grill-me | A relentless interview to sharpen a plan or design. | `.agents/skills/grill-me/SKILL.md` |
| grill-with-docs | A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go. | `.agents/skills/grill-with-docs/SKILL.md` |
| grilling | Grill the user relentlessly about a plan or design. Use when the user wants to stress-test a plan before building, or uses any 'grill' trigger phrases. | `.agents/skills/grilling/SKILL.md` |
| handoff | Compact the current conversation into a handoff document for another agent to pick up. | `.agents/skills/handoff/SKILL.md` |
| implement | "Implement a piece of work based on a PRD or set of issues." | `.agents/skills/implement/SKILL.md` |
| improve-codebase-architecture | Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick. | `.agents/skills/improve-codebase-architecture/SKILL.md` |
| loop-me | Grill me about specs for the workflows I want to build, within this workspace. | `.agents/skills/loop-me/SKILL.md` |
| obsidian-vault | Search, create, and manage notes in the Obsidian vault with wikilinks and index notes. Use when user wants to find, create, or organize notes in Obsidian. | `.agents/skills/obsidian-vault/SKILL.md` |
| prototype | Build a throwaway prototype to answer a design question. Use when the user wants to sanity-check whether a state model or logic feels right, or explore what a UI should look like. | `.agents/skills/prototype/SKILL.md` |
| research | Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent. | `.agents/skills/research/SKILL.md` |
| setup-matt-pocock-skills | Configure this repo for the engineering skills — set up its issue tracker, triage label vocabulary, and domain doc layout. Run once before first use of the other engineering skills. | `.agents/skills/setup-matt-pocock-skills/SKILL.md` |
| "source-command-create-rules" | "通过分析代码库创建全局规则（AGENTS.md）" | `.agents/skills/source-command-create-rules/SKILL.md` |
| tdd | Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests. | `.agents/skills/tdd/SKILL.md` |
| teach | Teach the user a new skill or concept, within this workspace. | `.agents/skills/teach/SKILL.md` |
| to-issues | Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices. | `.agents/skills/to-issues/SKILL.md` |
| to-prd | Turn the current conversation into a PRD and publish it to the project issue tracker — no interview, just synthesis of what you've already discussed. | `.agents/skills/to-prd/SKILL.md` |
| triage | Move issues and external PRs through a state machine of triage roles — categorise, verify, grill if needed, and write agent-ready briefs. | `.agents/skills/triage/SKILL.md` |
| writing-great-skills | Reference for writing and editing skills well — the vocabulary and principles that make a skill predictable. | `.agents/skills/writing-great-skills/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
