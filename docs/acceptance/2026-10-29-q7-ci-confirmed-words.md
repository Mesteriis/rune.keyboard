# Q7 CI routing for confirmed-word tests

Three independent `ConfirmedWordsInstrumentedTest` methods were skipped in the
general suite because they require `runeSyntheticProfileFixture=true`. A
separate CI scope now supplies that argument and selects the capacity, write
failure/retry and settings-navigation methods explicitly. Its XML must contain
exactly those three identities with no skips or failures. The tests require an
emulator; the two process-restart methods are not included because their
ordered, host-triggered restart is a separate fixture. The general scope still
reports its skips and the remaining separately gated tests remain open.

The comma-separated method selection ran with AndroidJUnitRunner on newly
created task-owned API 26 and API 37 ARM64 emulators: three tests passed on
each, no skips. API 26 log SHA-256:
`12d04b004ba931c9b967a317790e3ffa8bd6af827c00229ed631fbe6c712254f`;
API 37 log SHA-256:
`200640bf02ef60a91d9bbc6edc5f863d5f730e2317a204183c42a2e060770fb3`.
The debug APK SHA-256 was
`2f61e8102f535107107fdd15cf1140fff1da529b4c976d742bb4f8f92b7cf4f4`;
the test APK SHA-256 was
`8b8ebe500c1eccc429708b8284dcf8538c9bc3260b170da8e3b58ec43ce0771c`.
Logs remain under `build/q7-confirmed-*`; both AVDs were deleted. No physical
device was used.

The CI routing unit suite passes ten tests, including missing method and skipped
scope rejection. The Android runs used direct instrumentation; the new Gradle
scope and hosted CI have not yet run. The concurrent API 37 Gradle suite began
before this routing change and does not cover it. Q7 remains open.

An attempted parallel Gradle verification was stopped by a device-isolation
precheck before the Gradle command: a second ADB server rediscovered the first
suite's already-running emulator as well as the new emulator. The temporary
second emulator and clean worktree were removed. This is not a passing or failed
Gradle test; the existing suite was allowed to continue on its own server. A
single-emulator Gradle check remains necessary.
