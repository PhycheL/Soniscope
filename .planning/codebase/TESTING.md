# Testing Patterns

**Analysis Date:** 2026-07-04

## Test Framework

**Runner (Python):**
- pytest >= 8.0 (root `pyproject.toml` `[dependency-groups] dev`)
- Config: `[tool.pytest.ini_options]` in root `pyproject.toml`
  - `testpaths = ["apps/worker/tests", "apps/fc/tests"]`
  - `pythonpath = ["apps/fc/shared"]` (makes non-installed `fc_shared` importable in FC tests)

**Runner (Miniprogram JS):**
- Node built-in test runner (`node:test` + `node:assert`), no jest/vitest
- Bridged into pytest: `apps/worker/tests/test_miniprogram_js.py` runs `node --test <files>` as a subprocess (skips if node is missing), so `make test` is the single quality gate

**Assertion Library:**
- Plain `assert` (pytest) with Chinese comments explaining intent
- `pytest.raises(SomeError) as exc_info` + assertions on `str(exc_info.value)`
- JS: `assert.strictEqual` / `assert.deepStrictEqual`

**Run Commands:**
```bash
make test          # pytest 单元测试（mock 云端依赖）— includes JS tests via node
make typecheck     # mypy strict (src AND tests are strictly typed)
make lint          # ruff check apps/ + miniprogram custom lint
uv run pytest apps/worker/tests/test_config.py            # single file
uv run pytest -k test_mask_secret                          # by name
node --test apps/miniprogram/test/uploader.test.js         # JS directly
```

There is a second tier of live/cloud verification that is NOT pytest: Makefile `test-*` / `verify-*` targets (`make test-fc-live`, `make test-transcribe`, `make verify-e2e-integrity`, ...) invoke CLI commands against real cloud resources. Unit tests for those commands' pure logic still live in pytest (`test_fc_live.py`, `test_verify_upload_live.py`, `test_e2e.py`).

## Test File Organization

**Location:**
- Python worker: separate dir `apps/worker/tests/`, one `test_<module>.py` per source module in `apps/worker/src/soniscope_worker/`
- FC: `apps/fc/tests/` covering `apps/fc/shared/fc_shared/` and both `handler.py` files
- Miniprogram: `apps/miniprogram/test/<util>.test.js` mirroring `apps/miniprogram/utils/`
- Audio fixtures: repo-root `tests/audio/` (`sample-20s.wav`, `sample-20s.m4a`, `sample-54s.wav`, `sample-25min.wav`, `fixtures.manifest.json`) — described by `apps/worker/src/soniscope_worker/fixtures.py` and fetched by `scripts/fetch_test_fixtures.py`

**Naming:**
- `test_<module>.py`; test functions `test_<behavior>` with descriptive snake_case (`test_secret_not_leaked_in_repr_and_summary`, `test_init_runtime_dirs_idempotent`)
- No test classes — flat functions grouped by comment dividers: `# --- mask_secret ----` or `# ── 测试夹具 ──`
- JS: `test('中文描述（AC#N）', function () {...})` — descriptions in Chinese, often citing the acceptance criterion

**No conftest.py anywhere** — shared helpers are module-local `_` functions and module-level fixture dicts (e.g., `VALID_CONFIG` in `test_config.py`, `FULL_CRED_BODY` in `test_fc_live.py`).

## Test Structure

**Module docstring states scope + isolation guarantee:**
```python
"""US-026：阿里云 NLS 云端转写器（oss-url / direct、重试、续签、成本日志）测试。

全程注入 FakeBackend + 假时钟，不触网、不调 ffprobe / 云 SDK。
"""
```
Every test module declares its user story and asserts it does not touch the network / real `$SONISCOPE_HOME`.

**Patterns:**
- Setup via pytest built-in fixtures only: `tmp_path`, `monkeypatch` (used in 13 of 24 worker test files). `monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))` is the standard isolation idiom
- All test functions fully typed (`-> None`, `tmp_path: Path`, `monkeypatch: pytest.MonkeyPatch`) — tests are inside mypy strict scope
- `@pytest.mark.parametrize` for input matrices (`test_audio.py:308`, `test_ops.py:67`, `test_head.py`, `test_sts.py`)
- `@pytest.mark.skipif` only for environment availability (`test_miniprogram_js.py:24` — node missing)

## Mocking

**Framework: NONE.** `unittest.mock`/`MagicMock`/`patch` are not used anywhere. The codebase mocks via hand-written fakes + dependency injection.

**Patterns:**
```python
# apps/worker/tests/test_nls.py — fake backend injected where RealNlsBackend would go
class _FakeBackend:
    """可配置的 NLS 后端桩：记录调用、可注入轮询序列 / 异常。"""

    def __init__(self, *, poll_sequence=None, submit_errors=None, ...) -> None:
        self.presign_calls: list[str] = []   # record calls for assertions
        self.submit_calls: list[str] = []

    def submit_oss_url(self, file_link: str) -> str:
        self.submit_calls.append(file_link)
        if self._submit_idx < len(self.submit_errors):
            raise self.submit_errors[self._submit_idx]  # injectable failures
        return f"task-{len(self.submit_calls)}"
```
- Fakes record every call in `*_calls` lists; tests assert on call counts/args
- Failure injection via configurable error sequences (retry-path testing)
- Fake clocks injected alongside fakes for time-dependent logic (retry delays, credential resign thresholds)
- Production code defines injection seams: protocol types (`FcLiveProbes` in `fc_live.py`), backend parameters (`nls.py`), `log: Callable[[str], None]` (`poller.py`), `deps` object in JS (`uploader.js` takes `deps` with `login/requestSts/uploadFile/wait/now/logger`)

**CLI testing:**
```python
from typer.testing import CliRunner
runner = CliRunner()
result = runner.invoke(app, ["check-config"])
assert result.exit_code == 0
assert "secret-plaintext" not in result.stdout   # leak checks are routine
```

**What to Mock:**
- All cloud/IO: OSS, STS, FC HTTP, NLS ASR, wx.* miniprogram APIs, subprocess-heavy tools (ffprobe), wall clock

**What NOT to Mock:**
- Filesystem — use `tmp_path` and real files
- YAML/JSON parsing, Pydantic validation, pure logic — exercised for real
- Never patch module internals; if something can't be faked, add an injection parameter to the production code instead

## Fixtures and Factories

**Test Data:**
```python
# Module-level valid baseline dict + local mutation for failure cases
VALID_CONFIG = {"oss": {...}, "poll": {...}, "transcriber": {...}}   # test_config.py

def _write_config(tmp_path: Path, data: Mapping[str, object], mode: int = 0o600) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    p.chmod(mode)
    return p
```
- Factory helpers are private functions (`_config()`, `_filetrans_resp()` in `test_nls.py`; `makeItem()`/`baseDeps(overrides)` in `uploader.test.js`)

**Location:**
- Inline in each test module (no shared fixture package)
- Binary audio fixtures: `tests/audio/` at repo root, manifest-driven (`fixtures.manifest.json`, parsed by `soniscope_worker/fixtures.py`, validated by `test_fixtures.py`)

## Coverage

**Requirements:** None enforced — no pytest-cov dependency, no coverage config. Quality gates are `make lint` + `make typecheck` + `make test` all green, plus the live `make test-*`/`verify-*` acceptance targets per user story.

## Test Types

**Unit Tests (pytest, `make test`):**
- Fully offline; fakes for all cloud SDKs; heaviest coverage on pure logic, error branching, retries, secret non-leakage

**Live/Cloud Verification (Makefile targets, manual/CI-gated):**
- `make test-fc-live`, `make test-verify-upload`, `make test-sts-escape`, `make test-transcribe*`, `make test-e2e-*`, `make verify-e2e-*` — run CLI commands against real OSS/FC/NLS. Their orchestration logic has offline unit tests (`test_fc_live.py`, `test_e2e.py`, `test_e2e_scenarios.py`)
- Crash-recovery tests use kill -9 scenarios and injected crash cases (`make test-crash-recovery`, `simulate-worker-crash`)

**JS Tests (node:test):**
- Pure-logic units (`classifyFcResponse`, backoff constants) plus a "node Page harness + mock wx" pattern that loads real page files (`apps/miniprogram/test/uploader.test.js` loads `pages/uploads/uploads.js`)

**E2E:** No browser/device automation framework; real-device miniprogram verification is manual per runbook.

## Common Patterns

**Error Testing:**
```python
with pytest.raises(ConfigError) as exc_info:
    load_config(_write_config(tmp_path, broken))
msg = str(exc_info.value)
assert "oss.access_key_id" in msg      # all missing fields listed at once
```

**Secret-leak assertions (do this for any code that handles credentials):**
```python
assert raw_secret not in repr(cfg)
assert raw_secret not in result.stdout
assert "ossS...CDEF" in summary        # masked form IS present
```

**Environment isolation:**
```python
def test_x(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
    ...
```

**Constants as contract:** tests pin behavioral constants exported by modules:
```python
assert RETRY_DELAYS_SECONDS == [5, 15, 45]   # style used in test_nls.py / uploader.test.js
```

**Async Testing:** Not applicable — Python code is synchronous; JS async flows are tested with `async` node tests awaiting injected `deps.wait`.

---

*Testing analysis: 2026-07-04*
