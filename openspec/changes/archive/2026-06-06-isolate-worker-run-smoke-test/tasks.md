## 1. Test Isolation

- [x] 1.1 Update `apps/worker/tests/test_skeleton.py::test_run_command_exists` to accept `tmp_path` and invoke the Typer app with `env={"SONISCOPE_HOME": str(tmp_path)}`.
- [x] 1.2 Keep the existing registration assertions, including non-zero exit and absence of the old `not yet implemented` placeholder text.
- [x] 1.3 Add an assertion that the command exits through the config-loading failure path, without requiring exact full error text.

## 2. Verification

- [x] 2.1 Run the focused test with a real runtime config environment present, e.g. `uv run --directory apps/worker --extra dev pytest -v tests/test_skeleton.py::test_run_command_exists`.
- [x] 2.2 Run `make test` and confirm the full suite completes without hanging.
- [x] 2.3 Confirm no production Worker CLI code changed.
