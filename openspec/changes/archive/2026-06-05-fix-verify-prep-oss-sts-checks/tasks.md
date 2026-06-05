## 1. A Block OSS Runtime Verification

- [x] 1.1 Update `apps/worker/src/soniscope_worker/verify_prep.py` A block labels/docstring from bucket ACL inspection to Worker OSS runtime access verification.
- [x] 1.2 Replace `GetBucketInfo` / `GetBucketAcl` calls with configured-value checks for bucket `soniscope-audio`, endpoint `oss-cn-beijing.aliyuncs.com`, and region `cn-beijing`.
- [x] 1.3 Add bounded OSS runtime checks using `soniscope-local-reader`: `ListObjects` with a small prefix/max-keys, `HeadObject` for `sample/sample-20s.wav`, and `GetObject` access for the same sample object.
- [x] 1.4 Ensure A block failure hints distinguish wrong config/endpoint, missing sample fixture object, and insufficient runtime read permissions without recommending bucket ACL permission changes.

## 2. B Block STS Diagnostics

- [x] 2.1 Fix `_get_sts_credentials` to use correct STS region/endpoint semantics instead of passing `oss-cn-beijing.aliyuncs.com` as `AcsClient` region id.
- [x] 2.2 Replace the generic `except Exception: return None` path with sanitized diagnostic detail that preserves error category/code/status/request id when available.
- [x] 2.3 Update B block failure output and fix hints for missing deploy AK, bad deploy AK, wrong role ARN, trust policy denial, and missing AssumeRole permission.
- [x] 2.4 Keep positive PutObject and negative PutObject/ListObjects/GetObject checks intact, and verify STS expiration is no more than 900 seconds.

## 3. Tests

- [x] 3.1 Add unit tests for A block proving it uses `ListObjects`, `HeadObject`, and `GetObject` but does not call `GetBucketInfo` or `GetBucketAcl`.
- [x] 3.2 Add unit tests for A block config mismatch and missing sample object failure messages.
- [x] 3.3 Add unit tests for B block STS client construction or REST call shape so the OSS endpoint cannot be used as the STS region id.
- [x] 3.4 Add unit tests for B block sanitized failure output, including no full AK secret or STS token leakage.

## 4. Documentation And Verification

- [x] 4.1 Update `docs/runbook/mvp-acceptance-checklist.md` to state that A block verifies Worker OSS runtime access, while ACL private remains manual runbook or separate audit confirmation.
- [x] 4.2 Check whether `docs/PRD_v1.md`, `docs/tech-spec.md`, or `scripts/ralph/prd.json` need wording updates so they no longer imply the Worker reader credential must perform bucket ACL inspection.
- [x] 4.3 Run focused verify-prep tests under the worker test suite.
- [x] 4.4 Run `make verify-prep` in the real credentialed environment, or document which remaining failures are true cloud configuration issues rather than script defects.
