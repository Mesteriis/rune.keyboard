# Hosted CI: incognito transition assertions

The published API 26 workflow failed two candidate transition tests. Both failures
were reproduced on API 37 before this change: one expected no composing operation,
while the other rejected the new word's candidate. Their private fixture uses
`IME_FLAG_NO_PERSONALIZED_LEARNING`, not password input. The accepted U3 policy
explicitly permits owned composition and qualified suggestions in that mode,
while excluding personal learning, diagnostics and editor reads; password and
NO_SUGGESTIONS remain separate policies.

The two test assertions now require composition and the new original-word
candidate, while continuing to reject stale candidates from the previous editor
and require zero content-read counters. This changes tests only; it does not
alter privacy or product behavior. Existing U3 acceptance contains the separate
store/diagnostic and password controls.

On local disposable ARM64 emulators, both revised tests and a real-service
foreign-text boundary regression passed together: 3/3 on API 26 and 3/3 on
API 37. The original API 37 failures are retained in
`build/review-hosted-editor/other-api37.log`; passing runner transcripts are
`incognito-api26.log` and `incognito-api37.log` in the same directory.
`:app:assembleDebugAndroidTest --offline` passed. The test APK SHA-256 was
`b48afa85683457044b82065f9a8023609133d6f36612071f562d2a8935c1dd09` and
the app APK was
`4ec78729849a0d86bed2e9636c1717e859692e86836a6f2e98ef075ed1af82f3`.

This is targeted local verification, not a hosted CI rerun or full Q7 closure.
