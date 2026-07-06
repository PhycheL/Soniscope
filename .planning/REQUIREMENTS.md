# Requirements: SoniScope

**Defined:** 2026-07-06
**Milestone:** v1.1 上线前修复
**Core Value:** 首批真实用户前,关闭会导致静默失败、录音上传死态或误发 development 构建的 PRE-LAUNCH 风险。
**Source:** `.planning/audit/REPORT.md` PRE-LAUNCH 必做清单(`F-CODE-02`、`F-CODE-06`、`F-DOC-03`)

## v1.1 Requirements

### Worker Failure Isolation

- [ ] **WKR-01**: Worker can persist per-fragment failure history for `sha256_mismatch`, audio probe failure, and audio standardization failure.
- [ ] **WKR-02**: Worker can stop unbounded redownload/reprocess loops by skipping or quarantining a fragment after a configured failure threshold.
- [ ] **WKR-03**: Operator can identify quarantined fragments from explicit alert logs or local diagnostic state that includes `fragment_id`, failure reason, attempt count, and next action.

### Upload Queue Recovery

- [ ] **MP-01**: Miniprogram can detect stale `uploading` queue items before automatic upload driving and reset them to a recoverable state.
- [ ] **MP-02**: User can recover a stale `uploading` item from the upload list through a visible retry/recovery path, and the item is counted in backlog prompts.
- [ ] **MP-03**: Node tests cover stale `uploading` recovery and update the existing assertion that currently locks `uploading` out of backlog handling.

### Release Production Guardrail

- [ ] **DOC-01**: Release documentation requires changing `apps/miniprogram/config.js` `ENV` from `development` to `production` before uploading a release build.
- [ ] **DOC-02**: Release checklist requires real-device confirmation that the developer menu is hidden and fault injection switches are unavailable before submitting/releasing.

## Future Requirements

Deferred to later repair milestones. Tracked but not in the current roadmap.

### Audit Backlog

- **AUDIT-POST-01**: Repair remaining 37 POST-LAUNCH findings from `.planning/audit/REPORT.md` after PRE-LAUNCH is closed.
- **AUDIT-WP-01**: Implement contract/key derivation repairs and cross-language contract tests from WP-01/FUTURE-02.
- **AUDIT-WP-02**: Reduce mirrored constants/request assembly drift from WP-02.
- **AUDIT-WP-05**: Restore static gates and quality checks from WP-05.
- **AUDIT-WP-06**: Repair integration/deployment tool accuracy from WP-06.
- **AUDIT-WP-08**: Strengthen test coverage and live-check lists from WP-08.
- **AUDIT-WP-09**: Handle any remaining POST-LAUNCH package not required for first-user launch.

## Out of Scope

Explicitly excluded from this milestone.

| Feature | Reason |
|---------|--------|
| FC direct transcription target-state migration | Separate product/architecture milestone; v1.1 only removes PRE-LAUNCH launch risk. |
| Multi-user login or account model | Not part of MVP launch-risk repair. |
| Local Whisper implementation | Explicitly excluded by project scope; `whisper-local` remains a controlled stub. |
| Broad rewrite of upload/worker architecture | Current audit identified narrow repair surfaces; keep blast radius small before launch. |
| All POST-LAUNCH findings | Deferred so first launch is not blocked by non-critical debt. |

## Traceability

Which phases cover which requirements.

| Requirement | Source Finding | Phase | Status |
|-------------|----------------|-------|--------|
| WKR-01 | F-CODE-02 | Phase 6 | Pending |
| WKR-02 | F-CODE-02 | Phase 6 | Pending |
| WKR-03 | F-CODE-02 | Phase 6 | Pending |
| MP-01 | F-CODE-06 | Phase 7 | Pending |
| MP-02 | F-CODE-06 | Phase 7 | Pending |
| MP-03 | F-CODE-06 / F-TEST-06 | Phase 7 | Pending |
| DOC-01 | F-DOC-03 | Phase 8 | Pending |
| DOC-02 | F-DOC-03 | Phase 8 | Pending |

**Coverage:**

- v1.1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0
- PRE-LAUNCH findings covered: 3/3

---
*Requirements defined: 2026-07-06*
*Last updated: 2026-07-06 after v1.1 milestone start*
