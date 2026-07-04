# Codebase Concerns

**Analysis Date:** 2026-07-04

## Tech Debt

**FC-direct transcription decided but not implemented (largest open item):**
- Issue: The project has decided (deployment stage, 2026-07) that FC 直转 (`transcribe-audio` OSS-event-triggered FC function) is the primary transcription path (see `docs/fc-transcribe-design.md`, `docs/transcribe-approach-comparison.md` §6). Only `issue-credential` and `verify-upload` exist under `apps/fc/`; the new function directory `apps/fc/transcribe_audio/` does not exist yet.
- Files: `apps/fc/` (missing `transcribe_audio/`), `apps/worker/src/soniscope_worker/nls.py` (logic to be ported), `apps/worker/src/soniscope_worker/fc_deploy.py` (hardcoded two-function `FUNCTIONS` tuple)
- Impact: The Worker's full download→ffmpeg→NLS→local-disk pipeline (`pipeline.py`, `nls.py`, `poller.py`, ~2,700 lines plus tests) becomes a partially redundant legacy path once FC-direct ships. Until then the decided architecture and the deployed architecture diverge.
- Fix approach: Implement `apps/fc/transcribe_audio/` per `docs/fc-transcribe-design.md` §3 (idempotent HeadObject check on `transcripts/`, presign GET, NLS filetrans submit/poll, PutObject results), add it to `fc_deploy.FUNCTIONS`, grant `oss:GetObject` + `oss:PutObject` (prefix `transcripts/*`) + NLS to the `soniscope-fc` sub-account, then redefine the Worker's role (reconciliation/re-transcribe only, per design doc §3.6).

**Authoritative docs moved but deletions uncommitted and references stale:**
- Issue: `docs/PRD_v1.md`, `docs/tech-spec.md`, `docs/deployment-guide.md` are deleted in the working tree (uncommitted `D` in git status). The content now lives at `docs/v1.0.0 prd/PRD_v1.md`, `docs/v1.0.0 prd/tech-spec.md`, `docs/runbook/deployment-guide.md`, but references were not updated.
- Files: `AGENTS.md` (lines 5-6, 69, 81-82 still point to `docs/PRD_v1.md` / `docs/tech-spec.md`), `docs/fc-transcribe-design.md`, `docs/transcribe-approach-comparison.md`, `docs/multi-user-design.md`, `scripts/ralph/progress.txt`
- Impact: AGENTS.md declares `docs/tech-spec.md` the "唯一权威" (sole authority) at a path that no longer exists; AI agents and humans following the priority chain hit dead links. Uncommitted deletions risk accidental restore or confusing merges.
- Fix approach: Commit the move, then update every `docs/tech-spec.md` / `docs/PRD_v1.md` / `docs/deployment-guide.md` reference to the new paths (or add redirect stubs).

**Pure-JS SHA-256 on the recording thread:**
- Issue: `apps/miniprogram/utils/sha256.js` implements SHA-256 in pure JS. `AGENTS.md` prescribes `wasm-crypto` (or similar) to avoid main-thread jank; the file's own header acknowledges "wasm 化属后续性能优化".
- Files: `apps/miniprogram/utils/sha256.js`, callers in `apps/miniprogram/pages/index/index.js` (~line 629, computes sha256 of full audio bytes)
- Impact: Hashing multi-MB audio (up to 10-minute chunks, `CHUNK_MAX_DURATION_SECONDS=600`) on the JS main thread can freeze the UI on low-end devices.
- Fix approach: Swap in a wasm SHA-256 implementation behind the same function signature; the module is already pure (accepts ArrayBuffer/TypedArray) so node unit tests in `apps/miniprogram/test/` keep working.

**FC deploy tooling only supports code updates:**
- Issue: `fc_deploy.py` only does `update_code`; function creation, OSS event triggers, env-var configuration, and domain registration remain one-time manual runbook steps.
- Files: `apps/worker/src/soniscope_worker/fc_deploy.py` (707 lines, `FUNCTIONS` hardcoded), `docs/runbook/cloud-setup.md`
- Impact: Environment rebuild/disaster recovery depends on manual runbook fidelity; adding `transcribe-audio` requires manual console work before `make deploy-fc` can manage it.
- Fix approach: Acceptable for single-developer MVP; document precisely in the runbook, or extend `fc_deploy.py` with create-function/trigger support via `alibabacloud-fc20230330`.

**`whisper-local` transcriber is a deliberate stub:**
- Issue: `WhisperLocalTranscriber.transcribe` raises by design ("本期不部署本地 Whisper").
- Files: `apps/worker/src/soniscope_worker/transcriber.py` (line ~145)
- Impact: Selecting `transcriber.name: whisper-local` in `config.yaml` fails at runtime. Intentional per AGENTS.md red line (no faster-whisper/whisper.cpp this milestone) — do not "fix" without a scope decision.

**Vendored Aliyun FC sample repository committed:**
- Issue: `docs/example/start-fc-main/` is a full vendored copy of Alibaba's FC starter repo — 29 MB, 1,003 tracked files, unrelated runtimes (Node hooks, containers, etc.).
- Files: `docs/example/start-fc-main/`
- Impact: Repo bloat, noisy greps, misleading search hits (it contains its own handlers/configs that can be confused with project code).
- Fix approach: Delete and replace with a link + the few files actually referenced, or move to a separate reference location outside git.

**Quadruplicated agent tooling directories:**
- Issue: GSD/agent scaffolding is duplicated across `.claude/`, `.cursor/`, `.codex/`, and `.agents/` (commands, hooks, gsd-core, skills each copied per tool).
- Files: `.claude/`, `.cursor/`, `.codex/`, `.agents/`
- Impact: Four copies drift independently; skill/command fixes applied to one tree silently miss the others.
- Fix approach: Pick one canonical tree and symlink or generate the others, or document which tree is authoritative.

## Known Bugs

**None detected in application code.** No TODO/FIXME/HACK markers exist in `apps/` source (only descriptive comments about 临时文件/占位 stubs). The test suites (`apps/worker/tests/`, `apps/fc/tests/`, `apps/miniprogram/test/`) cover crash recovery, fault injection, and idempotency paths explicitly.

## Security Considerations

**Committed presigned OSS URL with STS token:**
- Risk: `scripts/test_asr.py` embeds `DEFAULT_FILE_LINK`, a signed OSS GET URL including an `OSSAccessKeyId=TMP.*` STS token and signature (line ~80). The `Expires=1780035733` timestamp (2026-05-29) has passed, so the URL is dead, but committing signed URLs normalizes leaking tokens into git history.
- Files: `scripts/test_asr.py`
- Current mitigation: Token is short-lived STS, single-object, already expired; script otherwise takes credentials only from env vars (`ALIYUN_AK_ID`/`ALIYUN_AK_SECRET`/`NLS_APP_KEY`) and masks them.
- Recommendations: Replace `DEFAULT_FILE_LINK` with a placeholder that forces `--file-link`, and add a pre-commit scan for `OSSAccessKeyId=` / `Signature=` patterns.

**Long-term credentials in FC env vars and local config.yaml:**
- Risk: `WX_APP_SECRET`, `ALIYUN_AK_ID`/`ALIYUN_AK_SECRET`, and `RAM_ROLE_ARN` live as FC function environment variables (`apps/fc/shared/fc_shared/env.py`); Worker keeps OSS/NLS keys in plaintext `$SONISCOPE_HOME/config.yaml`.
- Files: `apps/fc/shared/fc_shared/env.py`, `apps/worker/src/soniscope_worker/config.py`
- Current mitigation: Strong — `audit.is_sensitive` log scrubbing in `apps/fc/shared/fc_shared/audit.py`, `MaskedSecret` (front/back 4 chars) in Worker config, `config_permission_is_600` check, error paths never echo values (env loader reports missing variable *names* only).
- Recommendations: Consider Aliyun KMS/Secrets Manager for FC env vars post-MVP; rotate the `soniscope-fc` AK on a schedule.

**Single-user auth via openid allowlist:**
- Risk: Authorization is `OPENID_ALLOWLIST` string membership (`apps/fc/shared/fc_shared/auth.py:check_allowlist`). There is no session, rate limiting, or per-user isolation; anyone on the allowlist has full upload rights, and every request requires a fresh `wx.login` code round-trip to WeChat.
- Files: `apps/fc/shared/fc_shared/auth.py`, `apps/fc/shared/fc_shared/wechat.py`
- Current mitigation: Acceptable and explicit for the personal-use MVP; STS blast radius is tightly bounded — `single_key_policy` in `apps/fc/shared/fc_shared/sts.py` grants `oss:PutObject` on exactly one object key, ≤900 s, verified live by `make test-sts-escape` (`apps/worker/src/soniscope_worker/sts_escape.py`).
- Recommendations: Follow `docs/multi-user-design.md` when multi-user becomes real; add basic per-openid rate limiting on `issue-credential` before widening the allowlist.

**Miniprogram receives raw STS secrets (by design):**
- Risk: `credential_response` (`apps/fc/shared/fc_shared/sts.py:102`) returns `access_key_secret` and `security_token` to the client.
- Current mitigation: Inherent to the OSS direct-upload pattern; scoped to one key, PutObject-only, ≤900 s.
- Recommendations: None needed now; the alternative (PostObject policy signature, see `apps/miniprogram/utils/oss_sign.js`) is already partially in place if further tightening is desired.

## Performance Bottlenecks

**Worker processes fragments sequentially in one process:**
- Problem: The poll loop downloads, ffmpeg-transcodes, then synchronously polls NLS (5 s interval, `NLS_POLL_INTERVAL_SECONDS` in `apps/worker/src/soniscope_worker/nls.py`) per fragment before moving on.
- Files: `apps/worker/src/soniscope_worker/pipeline.py`, `apps/worker/src/soniscope_worker/poller.py`, `apps/worker/src/soniscope_worker/nls.py`
- Cause: Single-threaded design keeps the disk state machine simple (deliberate MVP choice; `locks.py` exists for the retranscribe-vs-run mutex, not parallelism).
- Improvement path: The FC-direct cutover removes this entirely (event-driven, parallel per-object FC invocations). If Worker stays on the hot path, batch NLS submissions and poll them concurrently. The ≥50-minute presign re-sign logic (`RESIGN_THRESHOLD_SECONDS`) already guards very long jobs.

**FC-direct will pay for NLS poll wait time:**
- Problem: The planned `transcribe-audio` function polls NLS inside the FC invocation (design §3.3), so FC billing includes 1–3 min of idle waiting per fragment.
- Files: `docs/fc-transcribe-design.md`
- Improvement path: Acceptable at personal volume (cost analysis in `docs/transcribe-approach-comparison.md`); NLS callback/notification integration is the escape hatch if volume grows.

**`wsgiref.simple_server` as the FC custom runtime server:**
- Problem: `apps/fc/shared/app.py` serves via `wsgiref` `ThreadingWSGIServer` — no request limits, minimal HTTP robustness.
- Files: `apps/fc/shared/app.py`
- Cause: Simplicity; FC fronts it and each instance handles low concurrency.
- Improvement path: Fine for MVP; swap to a production WSGI server only if FC concurrency per instance is raised.

## Fragile Areas

**The `issue-cedential` misspelled domain:**
- Files: `apps/miniprogram/config.js` (line 10)
- Why fragile: The real Aliyun-assigned FC subdomain is `issue-cedential-ottfirocds.cn-beijing.fcapp.run` — missing an "r". Any well-meaning "typo fix" (human or AI) breaks the miniprogram against the WeChat domain whitelist and the live function.
- Safe modification: Never edit the URL string; the inline comment (line 8) warns about this. If the function is ever recreated, update both `config.js` and the WeChat console whitelist together.
- Test coverage: `make test-fc-live` exercises the real URL.

**Duplicated fragment_id ↔ object_key contract logic:**
- Files: `apps/fc/shared/fc_shared/sts.py` (`_FRAGMENT_ID_RE`, `object_key_for`), `apps/worker/src/soniscope_worker/oss_admin.py` (`object_key_for`), `apps/miniprogram/utils/audio.js` (key preview), `apps/worker/src/soniscope_worker/poller.py` (`fragment_id_from_key` round-trip)
- Why fragile: The `recordings/<YYYY-MM-DD>/<fragment_id>.wav` contract is re-implemented in FC (Python), Worker (Python), and miniprogram (JS). A format change (e.g., new extension, deviceShortId length) must land in all three plus the planned `transcribe-audio` parser, or uploads silently become invisible to the Worker (`fragment_id_from_key` returns `None` and the object is skipped forever).
- Safe modification: Change the regex/format in `fc_shared/sts.py` and `oss_admin.py` in the same commit; run `apps/fc/tests/test_sts.py`, `apps/worker/tests/test_poller.py`, and `apps/miniprogram/test/ids.test.js`.
- Test coverage: Good per-component; no single cross-component contract test.

**FC handlers excluded from mypy strict:**
- Files: `apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`; exclusion documented in `pyproject.toml` `[tool.mypy]` comment (both files named `handler.py` → module-name collision)
- Why fragile: The two entrypoints that face the public internet get only ruff linting, not strict type checking, while everything they call (`fc_shared`) is strict.
- Safe modification: Keep handlers thin (they are — all logic lives in `fc_shared`); any new branching should be pushed into `fc_shared` where mypy strict applies.
- Test coverage: Compensated well by `apps/fc/tests/test_fc_handlers.py`, `test_issue_credential.py`, `test_verify_upload.py`, `test_custom_runtime_app.py`.

**`ENV = 'development'` hardcoded in miniprogram config:**
- Files: `apps/miniprogram/config.js` (line 29), gates `apps/miniprogram/utils/fault_injection.js` and `apps/miniprogram/pages/dev/`
- Why fragile: Production release requires manually flipping one constant. Shipping with `development` exposes the developer menu and fault-injection switches (forced FC failure, simulated offline, forced verify failure) to end users. `fault_injection.js` has a production read/write safety net, but the dev menu visibility itself depends on this constant.
- Safe modification: Flip `ENV` to `'production'` as a release checklist item; longer term, derive it from `wx.getAccountInfoSync().miniProgram.envVersion` instead of a hand-edited constant.
- Test coverage: `apps/miniprogram/test/fault_injection.test.js` covers the production-gating behavior.

**Home-grown miniprogram lint instead of ESLint:**
- Files: `apps/worker/src/soniscope_worker/miniprogram_lint.py` (invoked by `make lint`), tests in `apps/worker/tests/test_miniprogram_lint.py`
- Why fragile: A custom Python static checker for JS catches only the rules it was taught; real ESLint classes of bugs (unused vars, scoping, etc.) pass silently.
- Safe modification: When touching miniprogram JS, run `make lint` and the node test suite (`apps/worker/tests/test_miniprogram_js.py` drives `apps/miniprogram/test/*.test.js`).

## Scaling Limits

**Single machine, single user, poll-based:**
- Current capacity: One Worker on one Mac, one allowlisted openid, `poll.interval_seconds` (default per config) OSS polling; local disk (`$SONISCOPE_HOME/fragments/`) is the authoritative store with no replication.
- Limit: Worker offline = no transcription (audio safe in OSS, backlog drains on restart — by design). Mac disk loss loses all transcripts (audio recoverable from OSS via re-download + `retranscribe`). Allowlist auth caps users at "people you personally add".
- Scaling path: FC-direct transcription (`docs/fc-transcribe-design.md`) removes the always-on Mac from the hot path and puts transcripts in OSS `transcripts/`; `docs/multi-user-design.md` sketches multi-user.

**No FC rate limiting or quota per openid:**
- Current capacity: `issue-credential` will sign one STS per valid request, unbounded.
- Limit: A compromised allowlisted client could spam uploads (each still confined to one 50 MB-max object; `MAX_UPLOAD_BYTES` default in `apps/fc/shared/fc_shared/env.py`).
- Scaling path: Add per-openid request counting before widening access.

## Dependencies at Risk

**`aliyun-python-sdk-core` (legacy SDK) in `scripts/test_asr.py`:**
- Risk: The manual ASR probe script uses the deprecated-generation Aliyun SDK (`AcsClient`), while the Worker proper uses the new `alibabacloud-*` v2 SDKs. Two SDK generations to understand for one API.
- Impact: Script-only; not packaged with Worker or FC.
- Migration plan: Port the probe to the same POP call style used in `apps/worker/src/soniscope_worker/nls.py`, or retire the script now that `make test-transcribe-oss-url` covers the same ground.

**`alibabacloud-nls20180628` / NLS filetrans API (2018 vintage):**
- Risk: The whole transcription path (Worker today, FC-direct tomorrow) depends on Aliyun NLS 录音文件识别, API version 2018-08-17. Aliyun is pushing newer speech services; deprecation would strand the pipeline.
- Impact: `apps/worker/src/soniscope_worker/nls.py` (740 lines) and the planned `transcribe-audio` function.
- Migration plan: The `Transcriber` Protocol (`apps/worker/src/soniscope_worker/transcriber.py`) already isolates the engine; a replacement backend slots in behind `TranscriptResult`.

## Missing Critical Features

**`transcribe-audio` FC function (decided, unbuilt):**
- Problem: See Tech Debt above — the decided primary transcription path has no code yet.
- Blocks: Deployment-stage acceptance of the FC-direct architecture; retiring the always-on local Worker from the hot path.

**Transcript consumption/display:**
- Problem: Transcripts land as local files (`transcript.txt`/`transcript.json`) or, post-cutover, OSS `transcripts/*.md`. There is no reading UI anywhere (explicitly out of MVP scope: no 日稿展示, no LLM polish).
- Blocks: End-user value beyond raw archival; intentionally deferred.

## Test Coverage Gaps

**No automated cross-component E2E without manual WeChat codes:**
- What's not tested: The real miniprogram→FC→OSS→Worker chain requires fresh `wx.login` codes passed manually (`make test-fc-live CODE=...`, `test-e2e-security CODE=...`). CI cannot run the live path.
- Files: `apps/worker/src/soniscope_worker/fc_live.py`, `e2e.py`, `e2e_scenarios.py`, `Makefile`
- Risk: Regressions in the WeChat auth handshake or live FC config surface only during manual acceptance runs.
- Priority: Medium (self-contained stub E2E `test-e2e-*` targets cover orchestration logic well).

**FC `handler.py` files outside mypy strict:**
- What's not tested: Type-level correctness of the two WSGI entrypoints (see Fragile Areas).
- Files: `apps/fc/issue_credential/handler.py`, `apps/fc/verify_upload/handler.py`
- Risk: Low — thin handlers, strong behavioral tests in `apps/fc/tests/`.
- Priority: Low.

**Miniprogram page-level code (`pages/index/index.js`, 796 lines) tested only via extracted pure modules:**
- What's not tested: The wx-API glue (recorder callbacks, storage IO, showModal flows) in page files; node tests cover the pure `utils/` modules they delegate to.
- Files: `apps/miniprogram/pages/index/index.js`, `apps/miniprogram/pages/uploads/uploads.js`
- Risk: Wiring bugs between page and utils appear only on real devices.
- Priority: Medium — mitigated by the fault-injection dev menu (`pages/dev/`) used for on-device scenario testing.

**`scripts/` excluded from lint/typecheck:**
- What's not tested: `scripts/test_asr.py` (355 lines) and `scripts/fetch_test_fixtures.py` are outside `pyproject.toml` mypy/ruff `files`/`src` scopes ("遗留 scripts/ 由各自 story 收口" per `Makefile` lint target comment).
- Files: `scripts/test_asr.py`, `scripts/fetch_test_fixtures.py`
- Risk: Low — manual probe scripts only.
- Priority: Low.

---

*Concerns audit: 2026-07-04*
