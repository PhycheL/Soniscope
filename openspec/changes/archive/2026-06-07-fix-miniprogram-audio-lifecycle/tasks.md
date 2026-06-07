## 1. Test Coverage

- [x] 1.1 Add focused tests for `pages/index/index.js` that fail if `onAudition()` registers `onEnded` or `onError` on every tap instead of using a single managed callback set.
- [x] 1.2 Add tests that require re-record, confirmed delete, save-and-upload completion, `onHide`, and `onUnload` to call the shared audition release helper.
- [x] 1.3 Add tests that confirm no iOS/Android page split or duplicated upload flow is introduced for the fix.
- [x] 1.4 Add a regression test requiring iOS draft preview playback to configure `obeyMuteSwitch: false`.

## 2. Mini Program Audio Lifecycle

- [x] 2.1 Refactor `apps/miniprogram/pages/index/index.js` to manage audition through explicit helpers for creating, stopping, releasing, and resetting audition state.
- [x] 2.2 Ensure each audition start clears stale context state before playback and creates at most one active callback set for the page instance.
- [x] 2.3 Route re-record, confirmed delete, successful save-and-upload exit, `onHide`, and `onUnload` through the shared release helper.
- [x] 2.4 Classify expected background `operateAudio` permission failures after release/background as non-user-visible noise, without masking real foreground playback failures.
- [x] 2.5 Keep the implementation shared across iOS and Android; add only localized platform guards if a unified cleanup path cannot safely handle a platform-specific behavior.
- [x] 2.6 Configure inner audio playback so iOS real-device audition is audible even when the device mute switch is enabled.

## 3. Acceptance Documentation

- [x] 3.1 Update `docs/runbook/mvp-acceptance-checklist.md` with an iOS smoke test: record draft, audition, pause, re-record, delete, save-and-upload, background/foreground, and confirm no `operateAudio` error-level console noise.
- [x] 3.2 Add the matching Android smoke test to the checklist and require any unavailable device result to be marked explicitly as not run.
- [x] 3.3 Add a short note explaining that Part 1 data-chain AC can pass independently from the US-009 real-device audition lifecycle AC.

## 4. Verification

- [x] 4.1 Run `make miniprogram-lint`.
- [x] 4.2 Run the focused pytest coverage for the modified mini program tests.
- [x] 4.3 Run `make test` or document why the full suite was not run.
- [ ] 4.4 Manually verify on iOS real device; record device/WeChat/base library versions and result in the checklist.
- [ ] 4.5 Manually verify on Android real device when available; record device/WeChat/base library versions and result in the checklist.
