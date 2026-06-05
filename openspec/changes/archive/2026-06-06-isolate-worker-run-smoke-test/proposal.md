## Why

`make test` can hang on developer machines that have a real `$SONISCOPE_HOME/config.yaml` or `~/SoniScope/config.yaml`, because `tests/test_skeleton.py::test_run_command_exists` invokes the real `run` command and may enter the Worker polling loop. The smoke test should prove the command is registered without inheriting machine-specific runtime configuration.

## What Changes

- Isolate the `run` command smoke test from the developer's real Worker runtime environment.
- Ensure the test uses a temporary `SONISCOPE_HOME` that intentionally has no `config.yaml`, so the command exits during config loading instead of starting the poll loop.
- Keep the production `soniscope-worker run` command behavior unchanged.
- Add or preserve test assertions that confirm the command is registered and does not print the old placeholder text.

## Capabilities

### New Capabilities
- `worker-test-environment-isolation`: Worker tests that invoke CLI commands SHALL control runtime environment variables when command behavior depends on `$SONISCOPE_HOME` or real runtime files.

### Modified Capabilities

## Impact

- Affected test code: `apps/worker/tests/test_skeleton.py`.
- No runtime API, data model, cloud resource, Makefile target, or production behavior changes.
- Verification: `make test` should complete on machines with and without a real Worker `config.yaml`.
