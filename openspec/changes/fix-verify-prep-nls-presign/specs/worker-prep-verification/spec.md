## ADDED Requirements

### Requirement: Verify-prep NLS check uses supported OSS v2 presigning
The Worker preparation verification command SHALL generate the OSS file link for the E block using an Alibaba Cloud OSS v2 SDK supported presign flow for GET object requests.

#### Scenario: E block generates a signed OSS file link
- **WHEN** `verify-prep` runs the E block with valid OSS and NLS configuration
- **THEN** the system SHALL create a signed GET URL for `sample/sample-20s.wav` using `Client.presign` with a `GetObjectRequest`

#### Scenario: Unsupported SDK method is not used
- **WHEN** the E block prepares the NLS `SubmitTask` request
- **THEN** the system MUST NOT call `generate_presigned_url` on the OSS v2 client

### Requirement: Verify-prep NLS check submits presigned URL to NLS
The Worker preparation verification command SHALL pass the generated OSS signed URL as the `file_link` field in the NLS `SubmitTask` payload.

#### Scenario: NLS submit payload contains signed URL
- **WHEN** OSS presigning succeeds during the E block
- **THEN** the NLS `SubmitTask` body SHALL include `file_link` set to the generated signed URL

#### Scenario: Existing E block output behavior is preserved
- **WHEN** the E block succeeds, fails, or encounters an exception after this change
- **THEN** the system SHALL continue reporting the result through the existing `CheckResult` / `BlockResult` output structure with actionable fix hints for failures
