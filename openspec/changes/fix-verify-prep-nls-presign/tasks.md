## 1. Implementation

- [ ] 1.1 Update `apps/worker/src/soniscope_worker/verify_prep.py` E block to generate the OSS signed URL with the OSS v2 supported `Client.presign(GetObjectRequest(...), expires=...)` flow or by reusing the existing production helper.
- [ ] 1.2 Ensure the generated signed URL is passed unchanged as `file_link` in the NLS `SubmitTask` payload.
- [ ] 1.3 Preserve existing E block result labels, failure handling, and fix hints except where wording must clarify presign-related failures.

## 2. Tests

- [ ] 2.1 Add a worker unit test that stubs the OSS v2 client and verifies E block presigning uses `presign` / `GetObjectRequest`, not `generate_presigned_url`.
- [ ] 2.2 Add or update a worker unit test that stubs NLS `SubmitTask` / `GetTaskResult` and verifies the submitted task body contains the generated signed URL as `file_link`.
- [ ] 2.3 Run the focused worker tests covering verify-prep/NLS presigning.

## 3. Verification

- [ ] 3.1 Run the relevant worker test suite or focused pytest command under `uv run --directory apps/worker`.
- [ ] 3.2 Run `make verify-prep` after local credentials are available and confirm E block no longer fails with `'Client' object has no attribute 'generate_presigned_url'`.
- [ ] 3.3 Document any remaining A/B/E failures as environment or credential issues if they persist after the presign bug is fixed.
