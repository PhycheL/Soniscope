## Context

`make verify-prep` is the MVP preparation gate for the real Worker host and cloud resources. Its current A block uses the configured Worker OSS reader credential to call bucket-level APIs (`GetBucketInfo`, `GetBucketAcl`) even though the Worker runtime only needs object listing, object metadata, and object download. The US-001 runbook grants `soniscope-local-reader` only object-read/list capabilities, so A block can fail with `AccessDenied` while the Worker runtime path is still correctly provisioned.

The B block currently uses `aliyun-python-sdk-sts` with an OSS endpoint string passed as `AcsClient`'s `region_id` argument, then catches every exception and returns `None`. That makes a real failure indistinguishable across wrong endpoint/region, bad deploy AK, missing trust policy, or RAM permission issues.

## Goals / Non-Goals

**Goals:**

- Make A block verify the actual Worker OSS runtime contract with `soniscope-local-reader`: list objects, read sample object metadata, and read the sample object body.
- Keep bucket ACL/private verification outside the Worker runtime credential path; document it as a manual runbook or separate audit-credential check.
- Make B block call STS with correct endpoint/region semantics and produce sanitized, actionable error details.
- Add focused tests so future changes do not reintroduce bucket-level runtime checks or swallowed STS exceptions.

**Non-Goals:**

- Do not broaden `soniscope-local-reader` permissions just to satisfy `verify-prep`.
- Do not change FC runtime STS policy, miniprogram upload flow, OSS key format, or Worker config schema.
- Do not print full AK secrets, STS security tokens, wx secrets, or other sensitive values.
- Do not require users to return to cloud consoles for US-002+ implementation work; only the existing US-001/manual audit remains manual.

## Decisions

1. **A block will validate runtime OSS access, not bucket shape.**
   - It will build the OSS v2 client from `config.yaml` `oss.*`.
   - It will check configured values before cloud calls: bucket must be `soniscope-audio`, endpoint must be `oss-cn-beijing.aliyuncs.com`, and derived/expected region must be `cn-beijing`.
   - It will call `ListObjects` with a bounded prefix such as `sample/` or `recordings/` and `max_keys=1`.
   - It will call `HeadObject` for `sample/sample-20s.wav` and verify a nonzero content length.
   - It will call `GetObject` or `GetObjectToFile` for `sample/sample-20s.wav` in a bounded manner sufficient to prove read access without writing permanent files.
   - Alternative considered: add `oss:GetBucketInfo` and `oss:GetBucketAcl` to `soniscope-local-reader`. This is simpler but expands the long-lived Worker credential beyond runtime needs.

2. **ACL private checks remain resource-shape checks.**
   - The acceptance checklist can continue to include an operator-confirmed line for bucket ACL private.
   - If future automation is required, it should use a separate audit/deploy credential or a clearly named optional check, not the Worker runtime reader.
   - Alternative considered: remove ACL private from acceptance entirely. That weakens the US-001 resource-shape gate and is unnecessary.

3. **B block will stop swallowing STS errors.**
   - Replace `None` return with a typed result or exception path that preserves sanitized error code, HTTP status, request id when available, and high-level failure category.
   - Use correct STS semantics: either `AcsClient(ak, secret, "cn-beijing")` with the STS SDK or the existing FC shared HMAC-SHA1 `sts.aliyuncs.com` pattern.
   - Keep the deploy/FC AK source as environment variables already documented for deployment, but report clearly when none are present.
   - Alternative considered: call the live `issue-credential` FC endpoint instead of local STS. That validates deployed FC but does not isolate local US-001 STS/RAM preparation and needs a live `wx.login` code.

4. **STS positive and negative checks stay bounded.**
   - The positive check must prove PutObject succeeds only for the exact issued object key.
   - Negative checks must continue to verify PutObject to a different key, ListObjects, and GetObject are denied.
   - The expiry check may validate returned expiration is no more than 900 seconds by default; any real wait-for-expiry behavior should remain optional because it costs 15+ minutes.

## Risks / Trade-offs

- [Risk] A block no longer automatically proves bucket ACL is private. → Mitigation: keep ACL private in manual runbook/audit wording and make the A block label clear that it is a Worker runtime access check.
- [Risk] `sample/sample-20s.wav` missing in OSS will fail A block even if recordings access works. → Mitigation: that sample object is already a US-001 fixture dependency and is also required by fixture/NLS verification, so failure is actionable.
- [Risk] B block may still fail because the real RAM trust policy or deploy AK is wrong. → Mitigation: sanitized error details must identify the failure class so the user can distinguish code bugs from cloud configuration issues.
- [Risk] Using existing FC shared STS helper may require adapting imports outside the FC package layout. → Mitigation: prefer a small shared helper only if it keeps dependencies clean; otherwise use the STS SDK with correct `region_id` and robust error handling.
