# Q7 CI routing for personal case-rejection IME tests

The general Android CI scope does not pass `runeSyntheticProfileFixture=true`,
so both `CaseRejectionImeInstrumentedTest` methods were assumption-skipped in
the direct API 37 general run. The CI routing plan now invokes that class as a
separate scope with the synthetic fixture explicitly enabled. Its report must
contain exactly the two expected method identities, both executed without skips
or failures. A missing method, wrong class, skip, stale report, or nonzero
Gradle result cannot pass this scope. The test methods themselves require an
emulator and restore their synthetic personal-store snapshot and settings.

Nine routing unit tests pass, including missing-identity and skipped-result
negative cases. Direct AndroidJUnitRunner runs of the two methods each passed
with no skips on new task-owned API 26 and API 37 emulators. The API 26 log
SHA-256 is `5b4ba2bd58494e3b318379f72996d4e357719c155964a5c25090e238d39bbea8`;
the API 37 log SHA-256 is
`ee57567a45768af6c34e7f10b14cf6242c2d99dfb1a875aa79d3fb35dd6cd6be`.
Both used debug APK SHA-256
`2f61e8102f535107107fdd15cf1140fff1da529b4c976d742bb4f8f92b7cf4f4` and
test APK SHA-256
`8b8ebe500c1eccc429708b8284dcf8538c9bc3260b170da8e3b58ec43ce0771c`.
Logs remain under `build/q7-case-*`. Both task-owned AVDs were deleted; no
physical device was used.

The Android runs used direct ADB instrumentation, not the Gradle-connected
runner or hosted CI. Other assumption-skipped tests have distinct fixtures and
are not covered by this new scope. The actual hosted run and Q7 remain open.

## Gradle-connected API 37 follow-up

The exact new Gradle command also ran on a task-owned API 37 emulator with an
isolated ADB server limited to a nonexistent USB serial and containing only
the emulator TCP endpoint. `:app:connectedDebugAndroidTest` returned zero,
and the generated fresh XML passed `report(..., 'case-rejection')`: two tests,
zero failures, errors or skips. The local Gradle log is
`build/q7-case-gradle-api37-20261029.log`, SHA-256
`4d07c66512d5e0453e19a78c850fb51aaa7767deec0284fa79abfc3024dae55c`.
This verifies the single Gradle scope, not the full routed runner or hosted CI.
