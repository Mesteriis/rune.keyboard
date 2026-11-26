# Q7 API 37 connected suites with software navigation

The local Gradle-connected run on an isolated API 37 ARM64 AVD with the CI
software-navigation option finished with overall status **FAIL**. The general
suite reported 353 tests: 304 passed, 48 skipped, one failed and zero errors.
Its failure is the theme-test initial input described in
[q7-api37-theme-retry](2026-10-29-q7-api37-theme-retry.md). Four individual
retries and an ordered two-test retry passed, without establishing the cause.

All seven separately routed scopes had fresh verified reports with zero skips,
failures or errors: personal admission 4 tests, case rejection 2, confirmed words
3, export navigation 1, qualification lifecycle 1, qualification safety 1,
and native runtime 6. The complete runner receipt SHA-256 is
`11a746c5340381a08a6d42bdd915709bfb75c9a9b01cea55da965f4c6d65e875`;
logs and XML remain under ignored
`build/q7-connected-api37-ci-nav-isolated-20261029/`.

This run used a separate ADB server and task-owned emulator. That AVD and server
were stopped and deleted after completion; the physical device was not used.
It began before later CI device-guard edits and does not validate those edits or
hosted x86_64 CI. The general suite is not a pass, and Q7 remains open.

Cleanup limitation: the general failure rule writes a screenshot and window
hierarchy to the emulator's external app files. They were not pulled before the
AVD was deleted and are no longer available from that run. The JUnit report and
filtered TestRunner stack were retained, but they cannot substitute for those
visual artifacts. This omission limits diagnosis of the lost initial input.
