## ADDED Requirements

### Requirement: Verify Worker OSS Runtime Access
The `make verify-prep` A block SHALL verify the OSS access capabilities required by the Worker runtime using the configured `oss.access_key_id` and `oss.access_key_secret`, without requiring bucket-level `GetBucketInfo` or `GetBucketAcl` permissions from the Worker reader credential.

#### Scenario: Runtime OSS access succeeds
- **WHEN** `$SONISCOPE_HOME/config.yaml` contains `oss.bucket=soniscope-audio`, `oss.endpoint=oss-cn-beijing.aliyuncs.com`, and valid `soniscope-local-reader` credentials
- **THEN** the A block SHALL pass after successfully performing a bounded `ListObjects` check and `HeadObject`/`GetObject` checks for `sample/sample-20s.wav`

#### Scenario: Worker reader lacks bucket-level inspection permissions
- **WHEN** `soniscope-local-reader` has only the runtime permissions `oss:ListObjects`, `oss:HeadObject`, and `oss:GetObject`
- **THEN** the A block SHALL NOT call `GetBucketInfo` or `GetBucketAcl`

#### Scenario: Configured OSS endpoint or bucket is wrong
- **WHEN** `config.yaml` contains an unexpected OSS bucket, endpoint, or region-derived value
- **THEN** the A block SHALL fail with a message identifying the mismatched configured value and the expected `soniscope-audio` / `oss-cn-beijing.aliyuncs.com` / `cn-beijing` values

#### Scenario: Sample object is unavailable
- **WHEN** `sample/sample-20s.wav` cannot be found or read through the configured Worker reader credential
- **THEN** the A block SHALL fail with a fix hint pointing to the US-001 fixture/sample-object preparation path, not to bucket ACL changes

### Requirement: Keep Bucket ACL Audit Separate
The `make verify-prep` A block SHALL treat bucket ACL/private confirmation as a resource-shape audit outside the Worker runtime credential check.

#### Scenario: Acceptance checklist references ACL private
- **WHEN** the MVP acceptance checklist mentions OSS Bucket ACL private
- **THEN** the checklist SHALL identify it as manual runbook confirmation or a separate audit-credential check, not as a permission required by `soniscope-local-reader`

#### Scenario: A block output describes its scope
- **WHEN** `make verify-prep` prints the A block heading or check labels
- **THEN** the output SHALL make clear that the block verifies Worker OSS runtime access rather than bucket ACL inspection

### Requirement: Diagnose STS AssumeRole Failures
The `make verify-prep` B block SHALL call STS AssumeRole with correct STS endpoint/region semantics and preserve sanitized diagnostic details when the call fails.

#### Scenario: STS AssumeRole succeeds
- **WHEN** `ALIYUN_DEPLOY_AK_ID` and `ALIYUN_DEPLOY_AK_SECRET` identify a principal allowed to assume `acs:ram::1633875501759333:role/soniscope-uploader-role`
- **THEN** the B block SHALL obtain temporary credentials scoped to one exact object key and continue to its positive and negative OSS checks

#### Scenario: STS SDK call is configured
- **WHEN** the B block constructs an STS client
- **THEN** it SHALL use a valid region id such as `cn-beijing` or an explicit STS endpoint flow, and SHALL NOT pass the OSS endpoint `oss-cn-beijing.aliyuncs.com` as the STS SDK region id

#### Scenario: AssumeRole is denied by RAM
- **WHEN** STS returns an authorization, trust-policy, role ARN, or access-key error
- **THEN** the B block SHALL fail with sanitized detail including the high-level error code/category and fix hints for deploy AK, role ARN, trust policy, and AssumeRole permission

#### Scenario: STS diagnostic output is secret-safe
- **WHEN** the B block reports any success or failure
- **THEN** it MUST NOT print full AccessKey secrets, STS security tokens, wx secrets, or other sensitive values

### Requirement: Verify STS Single-Key Policy Boundaries
The `make verify-prep` B block SHALL verify that issued STS credentials allow PutObject only to the exact intended object key and deny unrelated object access.

#### Scenario: PutObject to exact key succeeds
- **WHEN** B block obtains STS credentials for its test object key
- **THEN** PutObject to that exact key SHALL succeed

#### Scenario: PutObject to another key is denied
- **WHEN** B block uses the same STS credentials to PutObject to a different key
- **THEN** OSS SHALL return AccessDenied or an equivalent authorization failure and the B block SHALL pass that negative check

#### Scenario: ListObjects is denied
- **WHEN** B block uses the same STS credentials to ListObjects
- **THEN** OSS SHALL return AccessDenied or an equivalent authorization failure and the B block SHALL pass that negative check

#### Scenario: GetObject is denied
- **WHEN** B block uses the same STS credentials to GetObject the uploaded test object
- **THEN** OSS SHALL return AccessDenied or an equivalent authorization failure and the B block SHALL pass that negative check

#### Scenario: STS duration is bounded
- **WHEN** B block obtains STS credentials
- **THEN** it SHALL verify the returned expiration is no more than 900 seconds from issuance, or otherwise fail with a fix hint for `DurationSeconds`
