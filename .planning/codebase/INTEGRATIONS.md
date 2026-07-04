# External Integrations

**Analysis Date:** 2026-07-04

## APIs & External Services

**Alibaba Cloud OSS (object storage — audio backup):**
- Bucket `soniscope-audio`, region `cn-beijing`, ACL private, endpoint `oss-cn-beijing.aliyuncs.com` (registered in `docs/runbook/cloud-setup.md`)
- Mini Program uploads audio directly to OSS via `wx.uploadFile` using the PostObject V4 form protocol with OSS4-HMAC-SHA256 policy signing implemented in pure JS: `apps/miniprogram/utils/oss_sign.js` + `apps/miniprogram/utils/hmac.js`, upload URL `https://soniscope-audio.oss-cn-beijing.aliyuncs.com` (`apps/miniprogram/config.js`)
- Worker downloads/lists objects with read-only credentials: `apps/worker/src/soniscope_worker/poller.py` (`OssSource` protocol, `RealOssSource`), admin ops in `apps/worker/src/soniscope_worker/oss_admin.py`
- Object key scheme: `recordings/<YYYY-MM-DD>/<fragment_id>.wav` (`apps/fc/shared/fc_shared/sts.py` `object_key_for`)
- SDK/Client: `alibabacloud-oss-v2` (Python, lazy import); raw signed forms in JS
- Auth: Worker uses `oss.access_key_id`/`oss.access_key_secret` from `config.yaml` (RAM sub-account `soniscope-local-reader`, read-only); FC verify-upload uses `ALIYUN_AK_ID`/`ALIYUN_AK_SECRET` (sub-account `soniscope-fc`, HeadObject-only policy); Mini Program uses per-file STS credentials

**Alibaba Cloud Function Compute FC 3.0 (serverless backend):**
- Two top-level Web functions, region `cn-beijing`, account ID `1633875501759333` (`apps/worker/src/soniscope_worker/fc_deploy.py`):
  - `issue-credential` → `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run` (subdomain intentionally missing an "r" — real Alibaba-assigned URL, do NOT "fix" the spelling)
  - `verify-upload` → `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run`
- Custom runtime entrypoint `python3 app.py` (`apps/fc/shared/app.py`, WSGI); handlers in `apps/fc/issue_credential/handler.py` and `apps/fc/verify_upload/handler.py`; shared lib `apps/fc/shared/fc_shared/`
- HTTP trigger auth: anonymous; application-level auth via WeChat openid allowlist (`OPENID_ALLOWLIST` env var, `apps/fc/shared/fc_shared/auth.py`)
- Deployed/rolled back/log-tailed from the Worker CLI via `alibabacloud-fc20230330` SDK: `make deploy-fc / rollback-fc / fc-logs` (`fc_deploy.py`; deploy updates code package only, never env vars/triggers)

**Alibaba Cloud STS (temporary upload credentials):**
- `issue-credential` calls STS AssumeRole on role `acs:ram::1633875501759333:role/soniscope-uploader-role` (`apps/fc/shared/fc_shared/sts.py`)
- Security invariants: policy Resource is exactly ONE object key (no wildcards), duration ≤ 900 s, action `oss:PutObject` only; long-term AK never appears in responses or logs
- SDK: `alibabacloud-sts20150401` + `alibabacloud-tea-openapi` (lazy import, `StsIssuer` protocol)
- Auth: FC env vars `RAM_ROLE_ARN`, `ALIYUN_AK_ID`, `ALIYUN_AK_SECRET`
- Escape testing: `apps/worker/src/soniscope_worker/sts_escape.py` (`make test-sts-escape` proves cross-key writes get AccessDenied)

**Alibaba Cloud NLS (speech-to-text / ASR):**
- Primary path (`upload_mode: oss-url`): filetrans async recording-file transcription — POP API `SubmitTask` / `GetTaskResult` against `filetrans.<region>.aliyuncs.com` via `aliyunsdkcore` (`apps/worker/src/soniscope_worker/nls.py` `RealNlsBackend`); Worker presigns a 1-hour OSS GET URL for the original object, re-signs and resubmits if polling exceeds 50 min; poll interval 5 s, total timeout 2 h
- Fallback path (`upload_mode: direct`): FlashRecognizer binary upload — POST WAV bytes to `https://nls-gateway-<region>.aliyuncs.com/stream/v1/FlashRecognizer` with `X-NLS-Token` header; token minted via `CreateToken` at `nls-meta.cn-shanghai.aliyuncs.com`
- Retry policy: network/5xx exponential backoff 5s→15s→45s, max 3 retries; 4xx fails immediately (`is_retryable_status` in `nls.py`)
- Cost logging: structured JSON per call at 2.5 CNY/hour (`estimate_cost_yuan`, `nls.py`)
- Auth: `transcriber.appkey`, `transcriber.access_key_id`, `transcriber.access_key_secret` in `config.yaml` (RAM sub-account `soniscope-asr`)
- Manual probe script: `scripts/test_asr.py`

**WeChat Open Platform:**
- Mini Program client (appid `wx3f973c7297728b0c`, `apps/miniprogram/project.config.json`)
- FC functions exchange `wx.login` codes for openids via `GET https://api.weixin.qq.com/sns/jscode2session` (`apps/fc/shared/fc_shared/wechat.py`); any failure maps to `401 INVALID_CODE`, never leaking code/secret/session_key
- Legal domain whitelist (WeChat console "服务器域名"): request domains = both FC URLs; uploadFile domain = OSS upload URL (`apps/miniprogram/config.js`)
- Auth: FC env vars `WX_APPID`, `WX_APP_SECRET`

## Data Storage

**Databases:**
- None. No relational/NoSQL database anywhere in the system.

**File Storage:**
- Alibaba Cloud OSS `soniscope-audio` — durable audio backup (retention red line R-07: Worker never calls DeleteObject; verified by `make verify-oss-retention`, `apps/worker/src/soniscope_worker/ops.py`)
- Local filesystem under `$SONISCOPE_HOME` (`apps/worker/src/soniscope_worker/paths.py`): `inbox/` (downloads, `.part` files), `inbox/failed/` (transcode-failure archive), `fragments/<date>/<fragment_id>/` (final artifacts: `audio.wav`, `manifest.json`, `transcript.json`, `.txt`, `.done`), `tmp/` (transcription workspace). All must share one filesystem for atomic rename.
- Test audio fixtures live in OSS (not git), fetched by `scripts/fetch_test_fixtures.py` against `tests/audio/fixtures.manifest.json`

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- WeChat login (jscode2session) → openid → static allowlist check (`OPENID_ALLOWLIST` FC env var, parsed in `apps/fc/shared/fc_shared/env.py`, enforced in `apps/fc/shared/fc_shared/auth.py`)
- Upload authorization: per-file STS credential issuance (see STS above); Mini Program never holds long-term keys
- Worker auth: long-term RAM sub-account AKs in `$SONISCOPE_HOME/config.yaml` (chmod 600, Pydantic `MaskedSecret` masking in all logs/repr)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry or similar)

**Logs:**
- FC runtime logs go to Alibaba Cloud SLS (project/logstore configured on each function); fetched locally via `make fc-logs FUNCTION=<name>` (`fc_deploy.py`, last 1 hour lookback)
- FC request audit logging with sensitive-field redaction: `apps/fc/shared/fc_shared/audit.py`
- Worker: stdout structured logs incl. per-ASR-call JSON cost log (`nls.py` `build_cost_log`)
- Mini Program: masked logger `apps/miniprogram/utils/logger.js`

## CI/CD & Deployment

**Hosting:**
- FC 3.0 (`cn-beijing`) for the two backend functions; WeChat platform for the Mini Program; Worker runs on the user's local machine (`make worker-run`)

**CI Pipeline:**
- None detected (no `.github/` or other CI config). Quality gates run locally: `make typecheck` (mypy strict), `make lint` (ruff + miniprogram lint), `make test` (pytest + node --test)

**Deployment:**
- `make deploy-fc [FUNCTION=<name>]` — zips function code + vendored `fc_shared` + pip-installed `requirements.txt` deps, backs up current package (env var NAMES only, never values), deploys via `alibabacloud-fc20230330`; `make rollback-fc FUNCTION=<name>` restores latest backup (`apps/worker/src/soniscope_worker/fc_deploy.py`)
- Deploy credentials from env: `ALIYUN_DEPLOY_AK_ID` / `ALIYUN_DEPLOY_AK_SECRET`
- Mini Program deployed through WeChat DevTools (manual)

## Environment Configuration

**Required env vars:**
- Worker host: `SONISCOPE_HOME` (env var or repo-root `.env`)
- FC shared: `OSS_BUCKET`, `OSS_REGION`, `OSS_ENDPOINT`, `WX_APPID`, `WX_APP_SECRET`, `OPENID_ALLOWLIST`
- FC issue-credential: `RAM_ROLE_ARN`, `ALIYUN_AK_ID`, `ALIYUN_AK_SECRET`; optional `MAX_UPLOAD_BYTES` (default 50 MB)
- FC verify-upload: `ALIYUN_AK_ID`, `ALIYUN_AK_SECRET`
- Deploy tooling: `ALIYUN_DEPLOY_AK_ID`, `ALIYUN_DEPLOY_AK_SECRET`

**Secrets location:**
- 1Password (per `docs/runbook/cloud-setup.md`): RAM AKs for `soniscope-fc`, `soniscope-local-reader`, `soniscope-asr`
- Worker secrets in `$SONISCOPE_HOME/config.yaml` (outside repo, chmod 600 enforced by `make check-config`)
- FC secrets as function env vars in the FC console; backups record variable names only
- Repo-wide red line: no AK secret ever printed in logs/reports (`mask_secret` in `config.py`, `_SECRET_ENV_NAMES`/`_AK_PATTERN` scrubbing in `fc_deploy.py`, `is_sensitive` in `fc_shared/audit.py`)

## Webhooks & Callbacks

**Incoming:**
- FC HTTP endpoints called by the Mini Program (not third-party webhooks):
  - `POST https://issue-cedential-ottfirocds.cn-beijing.fcapp.run` — auth (code→openid) + STS single-key credential issuance
  - `POST https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run` — OSS HeadObject upload confirmation (size/etag/sha256 match), `apps/fc/shared/fc_shared/head.py`

**Outgoing:**
- None (Worker pulls via OSS polling; NLS filetrans results are polled, not callback-delivered — no `callback_url` used)

---

*Integration audit: 2026-07-04*
