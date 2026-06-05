## Purpose

Define the expected isolation behavior for Worker tests that invoke CLI paths depending on runtime home configuration or real local Worker files.

## Requirements

### Requirement: Isolate Worker CLI Smoke Tests From Runtime Home
Worker tests that invoke CLI commands whose behavior depends on `$SONISCOPE_HOME` or `~/SoniScope` SHALL provide an explicit isolated runtime environment for the invocation.

#### Scenario: Run command smoke test on machine with real config
- **WHEN** `tests/test_skeleton.py::test_run_command_exists` runs on a machine that has a valid real Worker `config.yaml`
- **THEN** the test SHALL NOT load that real configuration or start the Worker polling loop

#### Scenario: Run command smoke test proves command registration
- **WHEN** `tests/test_skeleton.py::test_run_command_exists` invokes `soniscope-worker run`
- **THEN** the invocation SHALL use a temporary runtime home without `config.yaml`
- **AND** the test SHALL assert the command exits through the expected config-loading failure path rather than the old placeholder path

#### Scenario: Production run behavior remains unchanged
- **WHEN** a user invokes `python -m soniscope_worker run` or `make worker-run` outside the test harness
- **THEN** the command SHALL continue to resolve configuration from `$SONISCOPE_HOME/config.yaml` or `~/SoniScope/config.yaml` and run the Worker polling loop when configuration is valid
