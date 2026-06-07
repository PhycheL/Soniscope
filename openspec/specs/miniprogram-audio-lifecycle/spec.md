# miniprogram-audio-lifecycle Specification

## Purpose
TBD - created by archiving change fix-miniprogram-audio-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: Unified Cross-Platform Mini Program Audio Lifecycle
The mini program MUST use one shared implementation for draft audition behavior across iOS and Android, with any platform-specific logic limited to small guarded audio lifecycle or error-classification helpers.

#### Scenario: Shared implementation is used on supported mobile platforms
- **WHEN** the mini program runs on iOS or Android
- **THEN** recording, draft preview, save/upload, and verify flows use the same page and business state machine

#### Scenario: Platform-specific logic remains localized
- **WHEN** platform-specific handling is required for audio permission or lifecycle behavior
- **THEN** the implementation confines it to audio cleanup or expected-error classification helpers without duplicating pages or upload flows

### Requirement: Audition Event Handlers Do Not Accumulate
The draft audition implementation MUST prevent repeated taps on the audition button from accumulating multiple active `InnerAudioContext` `onEnded` or `onError` handlers for the same page instance.

#### Scenario: Repeated audition taps use a single active callback set
- **WHEN** the user taps audition multiple times for the same draft
- **THEN** the page has at most one active audio context callback set that can update audition state or log playback errors

#### Scenario: New audition starts from a clean audio context
- **WHEN** the user starts audition after a previous audition was stopped, paused, failed, or ended
- **THEN** stale audio context state is cleared before playback starts

### Requirement: iOS Audition Playback Is Audible In Normal Preview
The draft audition implementation MUST configure mini program audio playback so an iOS real-device draft preview is not silently muted by the device mute switch when playback has otherwise reached `onPlay`.

#### Scenario: Audition disables iOS mute-switch obedience
- **WHEN** the user taps audition for a recorded draft on an iOS real device
- **THEN** the mini program configures inner audio playback with `obeyMuteSwitch: false` before starting playback

### Requirement: Draft Exit Releases Audition Resources
The mini program MUST stop and release audition audio resources when the user exits draft preview through re-record, delete, save-and-upload completion, page hide, or page unload.

#### Scenario: Re-record releases audition resources
- **WHEN** the user taps re-record from draft preview after auditioning
- **THEN** audition playback is stopped, the audio context is released, and audition state is reset before the new recording starts

#### Scenario: Delete releases audition resources
- **WHEN** the user confirms draft deletion after auditioning
- **THEN** audition playback is stopped, the audio context is released, and no audio callback remains tied to the deleted draft

#### Scenario: Save and upload releases audition resources
- **WHEN** a draft is saved into the upload queue successfully
- **THEN** audition playback is stopped, the audio context is released, and draft preview exits without leaving an active audio callback

#### Scenario: Backgrounding releases audition resources
- **WHEN** the page receives `onHide` while an audition context exists
- **THEN** audition playback is stopped or released through the shared cleanup helper, and expected background audio permission errors are not surfaced as user-visible failures

#### Scenario: Unload releases audition resources
- **WHEN** the page receives `onUnload`
- **THEN** the audio context is destroyed or otherwise released and the page no longer holds an active audio context reference

### Requirement: Real-Device Acceptance Covers Audition Lifecycle
The MVP acceptance checklist MUST include a real-device smoke test for both iOS and Android covering audition, pause, re-record, delete, save-and-upload, and background transitions.

#### Scenario: iOS real-device smoke test covers background transition
- **WHEN** the tester runs the iOS smoke test sequence after recording a draft
- **THEN** audition, pause, re-record/delete/save paths complete without `operateAudio` error-level console noise after the mini program enters background

#### Scenario: Android real-device smoke test covers the same behavior
- **WHEN** the tester runs the Android smoke test sequence after recording a draft
- **THEN** the same shared implementation completes the sequence without console errors or divergent upload state behavior

