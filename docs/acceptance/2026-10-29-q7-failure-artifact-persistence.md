# Q7 Android failure-artifact persistence

The CI-owned IME test fixture now makes a shell-owned copy of its failure PNG
and hierarchy XML under `/data/local/tmp` before returning from the failure
watcher. This happens only with the explicit `runeCiFailureCapture=true`
instrumentation argument. It survives target-app uninstall; the existing
app-private capture behavior remains for other runs. Class and method names are
sanitized for file names, and each shell copy is checked. The CI boundary and
synthetic-restart runners pass that argument on their verified disposable AVD.

An EXIT handler invokes the host collector even when a suite fails. The collector
checks the expected single AVD, copies captures into the already-uploaded CI
artifact directory, reports PNG/XML counts and missing pairs, and fails if a
present capture directory is empty. The handler preserves the first suite error;
it reports a collection failure and fails an otherwise successful job. Both
boundary and restart suites are attempted, with failures retained. Shell tests
exercise success and combinations of suite and capture failures.

A temporary test intentionally failed on separate task-owned API 26 and API 37
ARM64 emulators. On each, the original assertion failure remained visible; both
PNG and XML were copied, survived target-app uninstall, were pulled to the host,
and passed PNG-signature and XML-root checks. The temporary failing test was
removed, the clean test APK rebuilt, and its dex verified not to contain the
probe. The host collector was exercised against each isolated TCP ADB server
with a locally injected identity check: API 37 used the AVD property and API 26
used its verified emulator process plus QEMU/API properties. The production
`emulator-N` ownership guard is covered by unit tests, not by this TCP probe.
Both disposable AVDs and their servers were removed; Fold was not used.

The probe logs have SHA-256 values
`e1eae7a6d93df2aa0661f128008dff9376a766a8097b3d05c4ddfd4c0e3d2607`
(API 37) and `cddb27117ddc4de6b2613b11a59732e7e16b6e5bd990f927d9a022cadd7cb076`
(API 26). Both numeric capture receipts have SHA-256
`c5c8612c7497de643110825237f59abe715c41d3ff7034617a9bbcbcd744e46d`.
The first two API 37 probe attempts exposed and retained a compound-shell-command
failure; the final implementation uses separately verified commands. Twelve
boundary-runner tests, three restart-runner tests, two collector tests and one
shell-status test pass; debug test APK assembly succeeds. Full connected suites
and hosted CI have not run this change. The earlier general-suite failure and
its missing captures remain historical facts, not repaired by this future guard.
