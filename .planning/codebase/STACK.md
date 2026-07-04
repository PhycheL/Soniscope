# Technology Stack

**Analysis Date:** 2026-07-04

## Languages

**Primary:**
- Python >=3.11 (3.12 observed in local bytecode) - Worker daemon (`apps/worker/src/soniscope_worker/`), FC serverless functions (`apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`, shared library `apps/fc/shared/fc_shared/`), deployment tooling (`apps/worker/src/soniscope_worker/fc_deploy.py`), scripts (`scripts/`)

**Secondary:**
- JavaScript (CommonJS, ES6) - WeChat Mini Program client (`apps/miniprogram/`): pages in `apps/miniprogram/pages/`, pure-function utilities in `apps/miniprogram/utils/` (upload queue, chunking, OSS V4 signing, HMAC-SHA256, ULID, logging)
- Make - Single command entry point for the whole repo (`Makefile` at repo root; users never `cd` into subdirectories)
- Shell - `scripts/gen_worker_config.sh` (config generation helper)

## Runtime

**Environment:**
- Python 3.11+ locally for the Worker (mypy pinned to `python_version = "3.11"` in `pyproject.toml`)
- Alibaba Cloud FC 3.0 Custom Runtime for serverless functions: start command `python3 app.py`, a threaded WSGI server (`apps/fc/shared/app.py`) delegating to each function's `handler.handler`; listens on `FC_SERVER_PORT`/`PORT`, fallback 9000
- WeChat Mini Program runtime, base library `libVersion: 3.5.5` (`apps/miniprogram/project.config.json`), appid `wx3f973c7297728b0c`
- Node.js (any recent) - only for running Mini Program JS unit tests via `node --test` (invoked from pytest wrapper `apps/worker/tests/test_miniprogram_js.py`; skipped if node missing)

**Package Manager:**
- `uv` with workspace layout: root `pyproject.toml` declares `[tool.uv.workspace] members = ["apps/worker"]`; root project is `package = false` and depends on workspace member `soniscope-worker`
- Lockfile: present (`uv.lock`, revision 3)
- No npm/package.json for the Mini Program - all JS utilities are dependency-free CommonJS modules
- FC function deps are plain `requirements.txt` per function (`apps/fc/issue_credential/requirements.txt`, `apps/fc/verify_upload/requirements.txt`), vendored into the deploy zip by `make deploy-fc`

## Frameworks

**Core:**
- Typer >=0.12 - Worker CLI (`apps/worker/src/soniscope_worker/cli.py`, entry point `soniscope-worker = "soniscope_worker.cli:app"`)
- Pydantic v2 - config schema validation with secret masking (`apps/worker/src/soniscope_worker/config.py`, `MaskedSecret` subclass of `SecretStr`)
- PyYAML >=6 - `config.yaml` parsing
- `wsgiref` (stdlib) - FC custom-runtime HTTP server (`apps/fc/shared/app.py`); no web framework, handlers are raw WSGI callables

**Testing:**
- pytest >=8.0 - `testpaths = ["apps/worker/tests", "apps/fc/tests"]` (root `pyproject.toml`); unit tests mock all cloud IO
- `node --test` (Node built-in runner) - Mini Program JS tests in `apps/miniprogram/test/*.test.js`, bridged into `make test` via `apps/worker/tests/test_miniprogram_js.py`

**Build/Dev:**
- hatchling - build backend for `soniscope-worker` (`apps/worker/pyproject.toml`)
- mypy >=1.8 strict mode - covers `apps/worker/src`, `apps/worker/tests`, `apps/fc/shared`, `apps/fc/tests` (FC `handler.py` files excluded due to duplicate module names; ruff-only)
- ruff >=0.4 - lint (`E`, `F`, `I`, `UP`, `B`), line-length 100, target py311
- Custom miniprogram linter - `apps/worker/src/soniscope_worker/miniprogram_lint.py` via `make lint-miniprogram` (checks legal-domain URLs, etc.)
- Make - all quality gates and ops commands (`make install/typecheck/lint/test/deploy-fc/...`)

## Key Dependencies

**Critical (Worker runtime, `apps/worker/pyproject.toml`):**
- `alibabacloud-oss-v2` >=1.3.1 - OSS client (download audio, presign URLs, HeadObject); lazy-imported
- `aliyun-python-sdk-core` >=2.16.0 (`aliyunsdkcore`) - POP/RPC API client for NLS filetrans (SubmitTask/GetTaskResult) and CreateToken; lazy-imported
- `alibabacloud-sts20150401` >=1.2.0 + `alibabacloud-tea-openapi` >=0.4.4 - STS AssumeRole (also FC issue-credential runtime dep)
- `alibabacloud-fc20230330` >=4.7.7 - FC 3.0 management SDK, used ONLY by deploy tooling (`fc_deploy.py`); never packaged into function code

**FC function runtime deps:**
- `apps/fc/issue_credential/requirements.txt`: `alibabacloud-sts20150401`, `alibabacloud-tea-openapi`
- `apps/fc/verify_upload/requirements.txt`: `alibabacloud-oss-v2`
- Shared module `fc_shared` is vendored into each function's zip at package root by `fc_deploy.py` (`SHARED_PARENT = ("apps", "fc", "shared")`)

**System tools (not pip-installable):**
- `ffmpeg` / `ffprobe` - required on the Worker host for audio format detection and non-WAV→WAV transcoding (`apps/worker/src/soniscope_worker/audio.py`, checked by `verify_prep.py` `REQUIRED_TOOLS`)

**Infrastructure:**
- All cloud SDKs are lazy-imported behind Protocol interfaces (e.g. `NlsBackend`, `StsIssuer`, `FcApi`, `OssSource`) so unit tests inject fakes and never touch the network

## Configuration

**Environment:**
- `SONISCOPE_HOME` - runtime data root, resolved from process env var first, then upward-searched `.env` file (`apps/worker/src/soniscope_worker/paths.py`); no `.env` currently committed at repo root
- `$SONISCOPE_HOME/config.yaml` - Worker config, must be chmod 600, validated by Pydantic (`config.py`). Sections: `oss` (endpoint/bucket/AK), `poll.interval_seconds`, `transcriber` (name/provider/model/params_version/api_endpoint/appkey/AK/upload_mode/local.enabled)
- FC deploy credentials: `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET` env vars (never in git)
- FC runtime env vars (set in FC console, names documented in `apps/fc/shared/fc_shared/env.py`): `OSS_BUCKET`, `OSS_REGION`, `OSS_ENDPOINT`, `WX_APPID`, `WX_APP_SECRET`, `OPENID_ALLOWLIST`, plus `RAM_ROLE_ARN`/`ALIYUN_AK_ID`/`ALIYUN_AK_SECRET` (issue-credential), `ALIYUN_AK_ID`/`ALIYUN_AK_SECRET` (verify-upload), optional `MAX_UPLOAD_BYTES` (default 52428800 = 50 MB)
- Mini Program config: `apps/miniprogram/config.js` (single source of truth for FC URLs, OSS upload URL, region, chunking threshold `CHUNK_MAX_DURATION_SECONDS = 600`, `ENV` flag)

**Build:**
- `pyproject.toml` (root) - uv workspace, mypy strict, ruff, pytest config (`pythonpath = ["apps/fc/shared"]` so FC tests can import `fc_shared`)
- `apps/worker/pyproject.toml` - hatchling wheel packaging `src/soniscope_worker`
- `Makefile` - only supported command interface (`make install`, `make test`, `make deploy-fc FUNCTION=...`, ~40 verification targets)
- `apps/miniprogram/project.config.json` - WeChat DevTools build settings (es6, minify, urlCheck)

## Platform Requirements

**Development:**
- macOS/Linux with Python >=3.11, `uv`, `ffmpeg`/`ffprobe`, Node.js (for JS tests), min 50 GiB free disk (`verify_prep.py` `MIN_DISK_BYTES`)
- WeChat DevTools for the Mini Program
- `SONISCOPE_HOME` directory pre-created and exported (or in `.env`)

**Production:**
- Worker: long-running local process on user machine (`make worker-run`), polling OSS every `poll.interval_seconds`
- FC functions: Alibaba Cloud FC 3.0, region `cn-beijing`, 0.35 vCPU / 512 MB, anonymous HTTP trigger (auth enforced in-app via openid allowlist)
- Mini Program: WeChat platform, legal domains registered per `apps/miniprogram/config.js`
- No CI pipeline detected (no `.github/` directory)

---

*Stack analysis: 2026-07-04*
