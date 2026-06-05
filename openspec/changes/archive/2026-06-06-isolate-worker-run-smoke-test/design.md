## Context

The Worker CLI `run` command is a long-running production command. It loads `config.yaml`, initializes runtime directories, builds an OSS client, and enters the poll loop. The existing smoke test for command registration calls `runner.invoke(app, ["run"])` without isolating `SONISCOPE_HOME`, so the test result depends on whether the developer machine has a valid real Worker configuration.

## Goals / Non-Goals

**Goals:**
- Make the `run` command smoke test deterministic on machines with or without real Worker configuration.
- Verify that the command is registered without allowing the real poll loop to start.
- Keep the change limited to test code.

**Non-Goals:**
- Do not change production CLI behavior.
- Do not add a test-only flag to the `run` command.
- Do not mock the whole Worker polling stack in this skeleton smoke test; deeper poll loop behavior is already covered by dedicated tests.
- Do not alter Worker config resolution rules.

## Decisions

- Use pytest's `tmp_path` fixture and Typer `CliRunner.invoke(..., env=...)` to set `SONISCOPE_HOME` to an empty temporary directory for `test_run_command_exists`.
  - Rationale: this tests the existing config-loading failure path while preventing access to real `$SONISCOPE_HOME/config.yaml` or `~/SoniScope/config.yaml`.
  - Alternative considered: unset `SONISCOPE_HOME`. This is insufficient because the fallback `~/SoniScope/config.yaml` may still exist.
  - Alternative considered: mock `run_poll_loop`. That would prove the poll loop call path, but it is broader than needed for a command-registration smoke test and can hide config-loading behavior.

- Assert that the command exits non-zero and does not print the removed placeholder text.
  - Rationale: the original intent was to verify registration, not successful Worker startup.
  - Alternative considered: assert exact `Config file not found` output. This is useful but can make the smoke test more brittle than necessary if wording changes.

## Risks / Trade-offs

- Test still invokes the actual CLI command up to config loading. -> This is intentional and bounded by the temporary empty runtime home.
- The assertion may not detect every future command-path regression. -> Dedicated CLI and poller tests continue to cover deeper behavior.
- Passing an explicit env only to one test may miss future tests with the same issue. -> The spec requires future CLI tests that depend on runtime files to control their environment.
