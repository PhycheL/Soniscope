# Coding Conventions

**Analysis Date:** 2026-07-04

## Language Split

This is a two-language monorepo with distinct convention sets:

- **Python 3.11+** (primary): `apps/worker/src/soniscope_worker/`, `apps/fc/shared/fc_shared/`, `apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`
- **JavaScript (WeChat miniprogram, CommonJS, ES5-ish)**: `apps/miniprogram/utils/`, `apps/miniprogram/pages/`, `apps/miniprogram/test/`

Miniprogram JS is deliberately EXCLUDED from mypy/ruff/pytest direct coverage. It gets its own custom lint (`apps/worker/src/soniscope_worker/miniprogram_lint.py`, run via `make lint`) and node-runner tests bridged into pytest (`apps/worker/tests/test_miniprogram_js.py`).

## Naming Patterns

**Files (Python):**
- `snake_case.py` module names, one domain concern per module: `poller.py`, `transcriber.py`, `oss_admin.py`, `fc_deploy.py`
- FC function entry points are always `handler.py` inside the function directory (`apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`) — same filename by convention; this is why they are ruff-only, not mypy-checked (module name collision, noted in `pyproject.toml`)
- Test files: `test_<module>.py` mirroring the module under test

**Files (JS):**
- `snake_case.js` for utils: `upload_queue.js`, `oss_sign.js`, `fault_injection.js`
- Tests: `<module>.test.js` in `apps/miniprogram/test/`
- Miniprogram pages use the WeChat four-file convention: every page in `app.json` must have `.js/.json/.wxml/.wxss` (enforced by `miniprogram_lint.py`)

**Functions:**
- Python: `snake_case`. Private helpers prefixed with `_` (`_collect_validation_errors` in `config.py`, `_write_config` in tests)
- Pure predicate/check functions named `check_*` (in `miniprogram_lint.py`), `is_*`, `assert_*` (in `fc_live.py`: `assert_credential_complete`, `assert_status_error`)
- JS: `camelCase` (`classifyFcResponse`, `uploadFragment`, `buildPostObjectForm`)

**Variables/Constants:**
- Module-level constants in `UPPER_SNAKE_CASE`, often exported and asserted in tests: `RETRY_DELAYS_SECONDS`, `RESIGN_THRESHOLD_SECONDS` (`nls.py`); `RETRY_DELAYS_MS`, `MAX_UPLOAD_RETRIES` (`uploader.js`)
- Stable error codes as string constants: `INVALID_CODE`, `OPENID_NOT_ALLOWED`, `SIZE_EXCEEDED`, `STS_ISSUE_FAILED` in `apps/fc/shared/fc_shared/errors.py` — shared verbatim between Python FC handlers and miniprogram JS (`uploader.js` branches on the same strings)
- Private module constants prefixed with `_`: `_SENSITIVE_SUBSTRINGS`, `_REDACTED` (`audit.py`), `_AK_ID_RE` (`miniprogram_lint.py`)

**Types:**
- `PascalCase` classes. Pydantic v2 `BaseModel` subclasses for config (`SoniScopeConfig`, `OSSConfig`, `TranscriberConfig` in `config.py`)
- Custom exceptions end in `Error`: `ConfigError`, `RuntimeHomeError`, `FcHttpError`, `FcConfigError`, `NlsTranscribeError`, `ProbeError`
- `@dataclass(frozen=True)` for small value objects: `LintIssue` in `miniprogram_lint.py`

## Code Style

**Formatting/Linting (Python):**
- `ruff` — config in root `pyproject.toml`: `target-version = "py311"`, `line-length = 100`, rules `E, F, I, UP, B`
- `mypy --strict` for `apps/worker/src`, `apps/worker/tests`, `apps/fc/shared`, `apps/fc/tests` (see `[tool.mypy]` in `pyproject.toml`). All functions fully type-annotated, including tests (`-> None` on every test function)
- Cloud SDK modules (`alibabacloud_*`, `aliyunsdkcore`) have `ignore_missing_imports` overrides — they are lazy-imported optional runtime deps
- Modern typing syntax: `Path | None`, `list[str]`, `dict[str, object]` (no `Optional`/`List`)
- `from __future__ import annotations` in most modules (20 of 26 in `soniscope_worker/`); include it in new modules

**Language of comments/docstrings:** Chinese (Simplified). Every module, class, and public function has a Chinese docstring. Module docstrings reference the user story (e.g., "US-002", "US-026") and spec sections (e.g., "tech-spec §4.2"). Follow this — do not write English docstrings.

**JS style (miniprogram):**
- CommonJS `require`/`module.exports`, no build step, no semicolon-free/prettier tooling detected — 2-space indent, single quotes, trailing function-expression style (`function () {}` over arrows in several files)
- Chinese comments referencing user stories and AC numbers (e.g., "AC#3")

## Import Organization

**Order (enforced by ruff `I` / isort):**
1. `from __future__ import annotations` (first)
2. Standard library
3. Third-party (`pytest`, `yaml`, `typer`, `pydantic`)
4. First-party (`soniscope_worker.*`, `fc_shared.*`)

**Absolute imports only** for first-party code: `from soniscope_worker.config import load_config`. No relative imports observed.

**Lazy imports for heavy/optional deps:** CLI subcommands import their implementation module inside the command function body (`apps/worker/src/soniscope_worker/cli.py` — e.g., `from soniscope_worker.poller import run_worker_run` inside `run()`). Cloud SDKs are imported lazily at call sites so unit tests never need them installed.

## Error Handling

**Patterns:**
- Domain-specific exception per failure category, raised with actionable Chinese messages that tell the operator what to fix: `ConfigError` in `config.py` includes the missing-field list and a chmod hint
- Chain exceptions: `raise ConfigError(...) from exc`
- Collect-all-then-fail: validation errors are aggregated and reported in one shot rather than failing on the first (`_collect_validation_errors` in `config.py`)
- CLI boundary converts exceptions to exit codes: catch `(ConfigError, RuntimeHomeError)`, `typer.echo(str(exc), err=True)`, `raise typer.Exit(code=1) from exc` (`cli.py`)
- FC HTTP boundary: `FcHttpError(status, error_code, message=...)` carries a client-safe JSON `payload` with a stable `error` code (`apps/fc/shared/fc_shared/errors.py`). Messages must never contain secrets
- Retry with fixed backoff schedule constants: 5s → 15s → 45s, max 3 attempts — mirrored in Python (`nls.py` `RETRY_DELAYS_SECONDS`) and JS (`uploader.js` `RETRY_DELAYS_MS`) and asserted in tests

## Secrets Handling (project red line)

This codebase treats secret non-leakage as a first-class convention, enforced by code and tests:

- Config secrets typed as `MaskedSecret(SecretStr)` — repr/str shows only first/last 4 chars (`config.py`); plaintext retrieved only via `.get_secret_value()`
- `mask_secret()` helper for any ad-hoc display (`config.py`)
- FC structured logs pass through `fc_shared/audit.py`: `log_event(event, **fields)` auto-redacts fields matching `SENSITIVE_FIELD_NAMES`/substrings (`secret`, `token`, `appkey`, ...); openid is logged only as `hash_openid()` sha256 prefix
- `miniprogram_lint.py` scans miniprogram source for hardcoded long-term AK IDs (`LTAI...`) and secret-looking literals
- Tests assert absence of plaintext secrets in output (`test_config.py::test_secret_not_leaked_in_repr_and_summary`, leak-detection tests in `test_verify_upload_live.py`)

New code touching credentials MUST follow these patterns.

## Logging

**Framework:** No `logging` module. Two conventions:

- **Worker CLI/daemon:** output via `typer.echo`; long-running functions accept an injected `log: Callable[[str], None] = print` parameter (`poller.py::run_worker_run`) so tests can capture output
- **FC functions:** structured stdout lines via `fc_shared/audit.py::log_event()` — `event=<name> key=value ...`, sorted keys, `None` omitted, sensitive fields redacted. FC runtime ships stdout to the log service
- **Miniprogram:** injected `logger` dep in utils; only non-sensitive fields (object_key, status, error codes) — see comments in `apps/miniprogram/utils/uploader.js`

## Comments

**When to Comment:**
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

**Exports:** No `__all__` barrels; consumers import names directly. `fc_shared/__init__.py` exists for package identity. Modules export their constants deliberately so tests can assert against them (e.g., `nls.py` exports `STATUS_SUCCESS`, `MODE_LOG_OSS_URL`).

**Workspace layout:** uv workspace (`[tool.uv.workspace]` in root `pyproject.toml`); business deps live in `apps/worker/pyproject.toml`, dev tools (`mypy`, `ruff`, `pytest`, `types-pyyaml`) in the root `[dependency-groups] dev`. `apps/fc/shared/` is NOT an installed package — it reaches tests via pytest `pythonpath = ["apps/fc/shared"]`.

**Command entry:** the root `Makefile` is the single command entry point (`make install / lint / typecheck / test / worker-run / deploy-fc / test-*`); every target shells out to `uv run python -m soniscope_worker <command>`. New operational commands should be added as Typer subcommands in `apps/worker/src/soniscope_worker/cli.py` plus a Makefile target with a `## help` comment (parsed by `make help`).

---

*Convention analysis: 2026-07-04*
