# Q7 spelling-popup fixture: API 37 and release boundary

On a disposable API 37 ARM64 emulator with software navigation, the five
`EditorBoundaryInstrumentedTest` cases passed. The API-26-specific spelling
popup test was explicitly requested separately and AndroidJUnitRunner reported
`OK (0 tests)` on API 37, consistent with its `SdkSuppress` scope; this is a
filtered test, not an executed pass. The two logs are retained under ignored
`build/q7-popup-api37-20261103/` with SHA-256
`17c2a9bd4b95bfbc8653423554563685ce7f325fdd0de26349ae4e3d9ebcb1c3` and
`0b11f0d02d2fbbc250a3919c88e3946d434564383f36108bad3c8d9253ed2ca6`.
The test AVD was deleted; no physical phone was used.

The first `:app:privacyGateRelease` attempt in the normal checkout failed at
`RELEASE_SUBMODULE_NOT_READY`; the main checkout's submodule is present but not
registered as initialized. In a separate clean local clone of `01c178c1` with
the exact pinned llama.cpp submodule initialized from the local copy, the same
Gradle gate passed (89 tasks executed, 69 restored from cache). Release typing
packaging and lint passed. The resulting unsigned APK's manifest does not name
`ImeQaActivity`, and its DEX does not contain the test fixture intent string.
The successful build log SHA-256 is
`1a0cf27db43131458ae87abfb8f77e5d7d7adb178e858de05df597e97e3421ea`;
raw logs, clone and manifest are retained under ignored `build/q7-popup-*` paths.
The clean clone remained free of tracked changes. This local release boundary
check does not establish a distribution release or hosted CI success.
