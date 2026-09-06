# Full 134-test editor matrix — 2026-09-06

API 26: **131 PASS, three optional full-model assumptions, no failures**, 676.963 s.
API 37: **130 PASS, three assumptions, one editor-focus failure**, 654.377 s.
The API 37 failure occurs in `standardAndCustomEditorActionsReachTheRemoteEditor`
before action dispatch: the target did not produce a visible IME. The original
log and synthetic QA screenshot/hierarchy are preserved. This run is not PASS.

Both runs cover the new raw TYPE_NULL and 75-character rapid-input scenarios,
command-dot preservation and the bounded normal/disabled/password preview test.
Every new scenario passed on both APIs. The double-space fixtures explicitly set
their required gesture preference; the earlier default-dependent failure remains
in the separate preview-policy-full archive.

Each input receipt records source HEAD plus the exact working patch, source
hashes and installed APK bytes. New untracked test sources are included. Both
emulators ran the same app APK `a1bff1aa8c4d006667c21fcee633a686108e217ebe97373b78a537a8c4b1e028`
and test APK `a603b9a25811ccbd139194e1866ad557e71b15bff5c39b6e5265fdbc6f5b6e35`.
Only instrumentation status bundles with class and test names count as results.
Numeric diagnostic status bundles are excluded. No full model was installed;
these runs do not qualify physical Fold performance or the pending live fake
model/editor integration matrix.
