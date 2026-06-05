## Why

`make verify-prep` currently fails in its A and B blocks even when the MVP runtime path is otherwise usable: the A block asks the Worker OSS reader credential to perform bucket-level inspection it does not need at runtime, while the B block calls STS through a misconfigured SDK path and hides the real exception. This blocks MVP acceptance with misleading diagnostics and blurs the boundary between runtime least-privilege checks and manual cloud-resource shape checks.

## What Changes

- Change the A block from bucket-level `GetBucketInfo` / `GetBucketAcl` inspection to runtime capability verification using the configured `soniscope-local-reader` credential.
- Have the A block verify the actual Worker OSS contract: `ListObjects` on the configured bucket/prefix, `HeadObject` for `sample/sample-20s.wav`, and `GetObject` access to the same sample object.
- Keep bucket name, endpoint, and region validation grounded in `config.yaml`, manifest/runbook expectations, and OSS errors; do not require `GetBucketAcl` from the Worker runtime credential.
- Move ACL private / bucket resource-shape confirmation out of the Worker runtime check and document it as a manual runbook or separate audit-credential concern.
- Fix the B block STS AssumeRole implementation so it uses the correct STS endpoint/region semantics and reports sanitized, actionable errors instead of returning a generic failure.
- Preserve secret-safety: do not print AK secrets, security tokens, wx secrets, or full sensitive values.

## Capabilities

### New Capabilities

- `worker-prep-verification`: Defines the expected behavior of `make verify-prep` for Worker runtime OSS readiness and STS diagnostic checks.

### Modified Capabilities

## Impact

- Affected code: `apps/worker/src/soniscope_worker/verify_prep.py`.
- Affected tests: worker tests covering verify-prep A/B behavior and secret-safe failure output.
- Affected docs: `docs/runbook/mvp-acceptance-checklist.md` and any runbook wording that currently implies the Worker runtime credential must verify bucket ACL.
- No production FC API, miniprogram API, config schema, cloud resource names, or long-term credential storage locations should change.
