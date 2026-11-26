# Q7 API 37 navigation fixture failure and targeted retry

The ongoing full Gradle-connected API 37 general suite reported a failure in
`ImeInsetsInstrumentedTest.bottomRowStaysAboveNavigationAndClickableAfterReopenAndRotation`:
`Fixture must have a navigation exclusion`. Its locally created AVD has
`hw.mainKeys=yes` and was launched without the workflow's
`-prop qemu.hw.mainkeys=0`; inspection found no visible navigation-bar inset on
that emulator. This differs from the committed CI configuration.

The same test, debug APK and test APK were run separately on a new task-owned
API 37 ARM64 emulator launched with the CI property. Although `getprop
qemu.hw.mainkeys` returned empty and the first setup guard stopped before test
execution, `dumpsys window` confirmed a visible navigation-bar inset. The
corrected guarded invocation passed one test with no skips. Its log SHA-256 is
`9bb0d1ecdbe0b371b7f7016e8ec82016fbd0ce7b1792d760e64509bc610b5066`
(`build/q7-nav-retry-api37-20261029.log`); the retry AVD was deleted.

The fixture difference and targeted pass support the missing-navigation
explanation but do not turn the original full run into a pass or establish that
all other failures share that cause. The original suite is still running on its
own isolated ADB server; hosted CI and Q7 remain open. No physical device was
used.
