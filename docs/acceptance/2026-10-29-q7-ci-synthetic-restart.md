# Q7 synthetic profile process-restart CI checks

Four previously skipped methods now have an ordered host-side CI route: write
and reload the synthetic case-rejection profile, then confirm/remove a word and
verify the removal after restart. The route first requires exactly one connected
emulator with the explicit CI-owned AVD name, emulator hardware and QEMU flag.
It installs the already-built debug and instrumentation APKs once with `-r`,
uses explicit-target ADB instrumentation for each method, and force-stops only
the verified emulator's Rune package between each pair. Every raw transcript
must contain the expected method's start and successful completion, a one-test
success summary and no skip or failure; Android's final `-1` alone is not enough.
A failed first phase prevents its dependent reload. Logs and the receipt are
included in CI artifacts. The workflow names its disposable AVD explicitly.

The first attempted implementation used separate Gradle connected tests. Both
write phases passed and both reload phases failed because the expected proof
files were absent; the target package was no longer installed after the Gradle
calls. That failed run is retained under `build/q7-synthetic-restart-evidence-20261029/`.
The corrected implementation installs once and uses direct instrumentation so
application state survives between phases. One accidental invocation of the old
script was interrupted before completing and is not counted as a result.

On separate task-created API 26 and API 37 ARM64 emulators, all four corrected
phases passed without skips, including two actual force-stops and PID-change
assertions per API. The two receipts are byte-identical with SHA-256
`e0eb05f5760e9fc9a3635bd3e0c3009ea3b641897a0b5054474c50f4c132f59d`.
Raw logs are under `build/q7-synthetic-restart-evidence-20261029/`. The debug
APK SHA-256 was `05d528e5559816b7af2196cb8c49d6a8a6f2e3f5e0516b02df2424172c0664e9`;
the test APK SHA-256 was
`affc8a4327ca76d9f25dcca8657247145df19baa01943327bdcb074e0cb42d24`.
Those APKs were Gradle-built in a temporary clean source worktree at `53a18ca8`
with the exact pinned llama.cpp revision; the CI driver itself was copied into
that worktree. An initial build without the submodule failed; a shallow-reference
clone attempt also failed, then a local clone of the pinned revision succeeded.
Both emulators, isolated ADB server and temporary worktree were removed. No
physical device was used.

Three focused driver tests and ten existing suite-routing tests pass. The full
hosted workflow and x86_64 CI execution have not yet run. This does not resolve
the independent full-suite failures or close Q7.
