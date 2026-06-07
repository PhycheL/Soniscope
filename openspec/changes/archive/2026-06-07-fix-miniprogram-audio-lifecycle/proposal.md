## Why

iOS real-device testing exposed `operateAudio:fail jsapi has no permission` after auditioning, pausing, re-recording/deleting a draft, and sending the mini program to the background. The current implementation lets `InnerAudioContext` callbacks outlive the draft lifecycle, so the MVP can pass cloud/data-chain checks while still failing the US-009 real-device "no console errors" interaction requirement.

## What Changes

- Use one mini program implementation for iOS and Android; do not fork pages, upload flows, or business state machines by platform.
- Tighten the draft audition lifecycle so audio playback is stopped, callbacks are not duplicated, and `InnerAudioContext` is released on every draft exit path and page background/unload path.
- Treat platform differences as small guarded branches only when a unified cleanup path is insufficient.
- Add static/unit coverage that catches repeated audition listener registration and incomplete draft-exit cleanup.
- Update the MVP acceptance checklist so iOS and Android real-device smoke checks explicitly cover audition → pause → re-record/delete/save → background lifecycle.

## Capabilities

### New Capabilities

- `miniprogram-audio-lifecycle`: Defines cross-platform mini program audio audition lifecycle behavior for draft preview, page backgrounding, and draft exit paths.

### Modified Capabilities

- None.

## Impact

- Affected code: `apps/miniprogram/pages/index/index.js`, related index page WXML/WXSS only if needed, and focused mini program static tests under `apps/worker/tests/`.
- Affected docs: `docs/runbook/mvp-acceptance-checklist.md`; PRD/tech-spec only if the behavior contract changes beyond the existing US-009/tech-spec audio API requirements.
- No changes to FC APIs, OSS object contract, Worker state machine, upload metadata, or transcriber behavior.
- No new runtime dependency and no request for background audio capability unless a future product requirement explicitly needs background playback.
