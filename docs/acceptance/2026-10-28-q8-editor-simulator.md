# Q8: independent editor profiles and late composition cleanup

An independent `EditorSimulator` now owns its own document, caret and composing
span and runs the real `EditorCommandExecutor` through an `InputConnection`
proxy. It does not change the existing `CorrectionBoundaryTest.Fixture`.
Callbacks are queued until a controller command returns; batch results coalesce.
External prefix insertion shifts the editor's own span before its acknowledgement.
Payload-read attempts are forbidden and explicitly checked after every test.

The profile contracts were recorded before the first execution:

| Profile | Availability and safety outcome |
| --- | --- |
| Normal control | Correction and exact snapshot Undo; external prefix intact. |
| No callback on stationary cursor | Session stays active; next word corrects and Undo remains exact. |
| Selection before composition | Conservative session disable, intact word and no revived Undo. |
| Prefix insertion before region acknowledgement | External prefix intact, session disabled, Undo absent, later literal input preserved. |
| Silent span loss | Documented duplicate-composition degradation, session disabled, Undo absent; not a compatibility pass. |

## Reproduction and fix

Against the original controller, five tests ran and one failed. With a two-phase
selection/composition callback, the editor contained the word but first reported
no composing span. Rune revoked ownership and disabled the session. The later
span report was ignored, leaving the span live, so a subsequent plain Space
replaced the word. The expected `outside teh ` became `outside `.

The controller now remembers that lost owned composition for the same session.
Its first later reported span receives one non-text `FinishComposingText`, even
while Smart Typing remains disabled. This never restores composition ownership,
text replacement authority, candidates or Undo. The marker clears before cleanup
and on disable/end/start lifecycle transitions. A new password session cannot
receive the obsolete cleanup. Refusal and exceptions are attempted once; an
editor that refuses cleanup is not guaranteed to remove its span.

All nine simulator tests pass, including both refused/throwing cleanup and
session replacement. Silent unreported span removal remains an explicit
unsupported degradation. These are synthetic protocol profiles; actual callback
traces from qa_editor/WebView and third-party editors remain required.

## Integration evidence

- All 1,352 JVM tests pass with zero failures/errors/skips; the scoring boundary
  also passes. The complete existing boundary fixture is unchanged.
- The actual two-profile CI replay command passes all 14,160 rows. Both fresh
  JVM projections agree for each profile and match the existing separate
  baselines; no baseline was updated and no model was called. Runtime sources
  and all 69 assets remain bound by the existing driver.
- Debug/test APK compilation and debug lint pass. The separate numeric-export
  navigation repair restores the pre-existing architectural boundary failure,
  with an API26 native UI check. That check is not a native callback-profile test.
- Initial combined integration failures are retained: the pre-existing numeric
  export dependency closure, then the expected strict dirty-source refusal for
  the release build. A fresh tracked-clean checkout of committed source e2c49c4
  then passed `imeIntelligenceBoundary`, `privacyGateRelease` and
  `privacyGateProfile` offline, including actual debug/release/profile packaging.
  Git was clean before and after; signing material was not copied. All three
  APK hashes are recorded. No exemption was added to either guard.
- The task-owned API26 emulator was stopped and deleted. Fold was not used.

The [machine receipt](2026-10-28-q8-editor-simulator-evidence.json) binds the
original failure, recoverable initial fixture bytes, final tests, replay
comparisons, sources and cleanup. Q8 remains in progress for trace calibration,
qa_editor profiles/debug reasons and APP-001…005 continuation measurements on
Fold. This does not establish universal editor compatibility or full review
completion.

## External-selection diagnostics follow-up (2026-11-09)

An unexpected selection callback that actually disables the active Smart
Typing session now produces the content-free `SESSION /
EXTERNAL_SELECTION_DISABLED` diagnostic. Admission is obtained before the
external change invalidates the recording segment, and the one-shot outcome is
emitted only after the controller has disabled that same session. Consent
changes revoke it. An ordinary external cursor move that leaves the session
enabled emits no disabled outcome; incognito cannot admit the event. The
debug recorder's output contains no editor text or selection offsets.

The initial architecture boundary check rejected the newly added shared
observer method. The exact allowed interface and its mutation fixture were
updated; the boundary then passed for debug, release and profile. The full
debug JVM suite passed 1,401 tests, with no failures, errors or skips; debug
lint and 33 analyzer tests passed. Both current-product double-run replay
sets matched their existing projections: 2,160 multilingual and 12,000
historical rows, zero differing rows. Temporary replay output was removed.
These are local checks; no Android instrumentation, Fold or hosted CI was run
for this change, and the Q8 app matrix remains open.

## Real-IME diagnostic follow-up

A separate synthetic diagnostic fixture runs the same two-phase callback in
an ordinary editor with metadata recording enabled. On temporary ARM64 API 26
and API 37 emulators, the real IME produced exactly one content-free
`EXTERNAL_SELECTION_DISABLED` event. The test then ran the two-phase callback
in a `NO_PERSONALIZED_LEARNING` field and confirmed the metadata snapshot did
not change; both cases also check that no editor payload-read methods were
called. The final version passed once on each API after an earlier version
without the private-field assertion also passed once on each API. Debug and
instrumentation APK builds passed. Each temporary emulator and its synthetic
diagnostics were removed. This is owned-fixture evidence, not a Fold or
third-party editor matrix run; hosted CI remains unverified.

The general Android-suite receipt gate now requires this diagnostic test by
exact class and method identity. A missing or skipped required case is rejected
by the existing report verifier; a regression test also asserts that this
particular identity remains required. The verifier tests pass locally. The
separate full general run must still complete before it can validate the gate
against its actual report.

## General API 26 attempt and targeted reruns

An isolated API 26 general-suite attempt at the new gate was stopped by its
30-minute time limit before producing a complete JUnit report. Its last
preserved log snapshot reported 280 of 367 cases, 37 skips and two failures.
`backspaceRepeatStopsWhenImeViewDetaches` observed one more character remaining
than predicted from dispatched Delete actions; `canonicalCaseAutoReplacesOnBoundaryAndBackspaceRestoresOriginal`
failed to reach the Russian layout. The incomplete run is not a pass and does
not prove whether the mandatory diagnostic test ran. Its partial raw log is
retained under `build/ci-editing-investigation/q8-general-api26-timeout.log`.

Each of those two tests passed once in a subsequent clean isolated API 26
emulator using the same APKs. The targeted passes do not erase the failures or
establish their causes, nor do they replace a complete general-suite report.
Both temporary emulators and their synthetic data were removed. Physical Fold
and hosted CI remain unverified.

Further isolated API 26 checks ran the two failing methods five times each on
one clean emulator: all ten invocations passed. The Backspace method then
passed ten additional invocations on a fresh one-core API 26 emulator. Raw
synthetic instrumentation output is retained in
`build/ci-editing-investigation/q8-api26-repeated-cases.log` and
`build/ci-editing-investigation/q8-api26-one-core-repeat.log`. These bounded
repeats show no reproduction in those conditions; they do not establish the
cause of the two original failures or a passing general suite. In particular,
the original Backspace assertion compares dispatched actions with the final
editor text; dispatch by itself does not prove every edit was accepted during
the detach transition. No assertion or production behavior was changed.

An opt-in debug-editor probe now records only lengths and the last edit time at
activity pause/stop, plus a test-side key-detachment timestamp while the listener
is installed. The test reads its synthetic editor text through the test driver;
this is not proof of zero IME payload reads. An initial proposed assertion that
the editor could not change after `onPause` failed five times on API 26 and five
times on API 37: `onPause` is earlier than the complete transition and is not an
IME-detach acknowledgement. That assertion was removed before further tests.

With the bounded ordering probe, three runs per API and a final run per API
observed edits between pause and stop, with the stopped length equal to the final
length. The key-detachment listener observed no detach while installed; it was
removed after the helper returned, so later detach is not excluded. Before
revising the assertion, the original Backspace case and external-selection
diagnostic case each passed once on API 26 and API 37. Raw synthetic logs, including the failed
pause assertion, are retained in `build/ci-editing-investigation/q8-detach-length-verification.log`,
`q8-detach-order-probe.log`, `q8-detach-order-final.log`, and
`q8-detach-order-final-v2.log`. The v2 sequence reproduced the original
one-command mismatch on API 26 after the probe, while API 37 passed. These
results do not identify the editor-connection outcome for the missing command
or prove a full general-suite pass. No production IME or autocorrection
behavior changed.

The Backspace test now distinguishes dispatched Delete actions from edits
actually applied by the editor during the transition. It requires at least
three applied deletions, an unchanged remaining prefix, no more applied
deletions than observed dispatches, and stable text after the wait. This allows
a dispatch to be dropped as the input connection changes; it does not prove
why the original command was dropped or that a key was physically detached.
After the ordering probe, this revised test passed five times on each of API 26
and API 37; the cancel case and external-selection diagnostic case also passed
once per API. The raw result is `build/ci-editing-investigation/q8-detach-oracle-final.log`.
The original incomplete general-suite failure remains recorded; a complete
general suite, Russian-layout failure analysis and Fold acceptance remain open.

The language-switch test driver now records the decoded enabled language names,
visible language labels and gesture injection results when its bounded cycle
fails. It does not include editor text or raw preference values. On an isolated
API 26 emulator, a deliberate English-only configuration verified the failure
diagnostic. In a separate instrumentation invocation, the theme language-swipe
test followed by the previously failing canonical-case test both passed, in
that order. The earlier suite log did not retain these diagnostic details, so
this does not establish its cause or prove the full suite passes. The first
emulator attempt could not install an APK because the build was still running;
the retry was started after the build succeeded. Raw logs are retained locally in
`build/ci-editing-investigation/q8-language-build.log`,
`q8-language-isolated.log`, and `q8-language-isolated-retry.log`.

The general-suite report gate now also requires both previously failed methods
and the language-switch diagnostic test by exact identity. Its unit suite passed
16 tests, including refusal when each required case is absent or skipped; raw
output is retained in `build/ci-editing-investigation/q8-general-gate-unit.log`.
This tightens report validation and is not a completed Android run.

An isolated API 26 general invocation completed with Gradle exit 1: its JUnit
report records 369 tests, 48 skips and two failures. The Backspace detach case,
canonical-case language switch and disabled-language diagnostic all passed,
as did every other exact identity required by the current general report gate.
The failures were the bottom-row navigation exclusion and the theme's dark
navigation backdrop. This AVD inadvertently booted with `qemu.hw.mainkeys=1`,
so its required software-navigation fixture was absent. On a fresh isolated
API 26 AVD verified with `qemu.hw.mainkeys=0`, both failed methods passed in
separate instrumentation invocations. This supports the fixture explanation,
but does not establish a passing full general invocation or the other routed
suites. Full raw results and individual exit codes are retained locally under
`build/ci-editing-investigation/q8-general-api26-isolated` and
`q8-nav-api26-recheck`. The initial isolated-server guard attempt stopped before
the suite because its guard inherited the default ADB environment; it did not
modify the physical device. The retry inherited the isolated ADB server.

The boundary-suite CLI checks `qemu.hw.mainkeys` after identifying the owned
emulator and at each existing device guard. API 26 requires `0`; API 37 also
allows an empty property because the local 16 KiB image leaves it unexposed
even with the emulator flag. An explicit `1` is refused on either API. This
property does not itself prove actual navigation insets: the instrumented test
must still verify them. An initial strict `0` guard wrongly refused the API 37
image before tests. The updated 20-test Python suite checks both API modes;
raw output is retained locally in
`build/ci-editing-investigation/q8-navigation-preflight-api37-unit.log`.

The API 26 general suite was then rerun on an isolated ARM64 AVD after checking
`qemu.hw.mainkeys=0`. Gradle exited 0 and the fresh XML reported 369 tests,
321 executed, 48 skipped, zero failures and zero errors. All 33 identities
required by the current general report validator passed. The two navigation
methods that failed on the previous misconfigured AVD, both previously failed
Backspace/language methods, and the disabled-language diagnostic also passed
in this invocation. Raw log, exit code, AVD property and XML are retained in
`build/ci-editing-investigation/q8-general-api26-nav`. This is one local general
scope, not a pass for the separately routed fixtures, API 37, hosted CI, or
physical Fold acceptance.

The 369 per-test API 37 logcat files from that run were later compressed
individually and their decompressed SHA-256 values verified before deleting the
uncompressed copies. `q8-general-api37-nav-retry/logcat-compression.json`
records the original names, hashes and sizes. The JUnit XML and general runner
log remain directly readable; the report validator still accepts all required
identities. Archived logcat filenames now require `.gz` decompression.

The corresponding API 37 ARM64/16 KiB general suite also completed with
Gradle exit 0: its fresh XML reports 369 tests, 321 executed, 48 skipped and
zero failures or errors. All 33 identities required by the general validator
passed, as did the real navigation-inset test and the five-theme test that had
failed in the earlier API 37 general attempt. This establishes this local
invocation, not the cause of the historical theme failure or the separately
routed scopes, hosted x86_64 CI, or physical-device acceptance. The initial
attempt stopped before tests on the overly strict property check described
above. Logs, exit code and XML are retained locally under
`build/ci-editing-investigation/q8-general-api37-nav-retry`.

The separately routed scopes were subsequently run on fresh isolated ARM64
AVDs with the real Compose editor installed. API 26 passed nine scopes and
22 tests; API 37 passed eight scopes and 21 tests. Both receipts contain zero
skips, failures or errors and each scope has a fresh validated XML report.
These counts include personal admission, case rejection, confirmed words,
Compose, export navigation, qualification lifecycle/safety and native runtime;
the API 26 plan also includes the document picker. The general scope was
deliberately omitted from these invocations because the separate fresh reports
above cover it; therefore the selected-scope receipt is not a full CI receipt.
The post-run attempt to pull failure captures reported that the remote directory
did not exist; no failed scope needed a capture. Logs, command exit codes,
selected-scope receipts and XML are retained locally in
`build/ci-editing-investigation/q8-routed-api26` and `q8-routed-api37`.
Synthetic restart, process-death and voice host runners, hosted x86_64 CI and
Fold acceptance remain separate.

The three CI host runners were then executed on fresh isolated API 26 and API 37
ARM64 AVDs using the ordinary Rune debug APK, its test APK and the separate
Compose fixture. On each API the synthetic restart receipt verifies four
write/reload phases; the process-death receipt verifies intentional termination
of the identified Rune process and recovery for both left and right contexts;
the voice receipt verifies five unavailable, enabled, gesture, stale-target
and next-keyboard scopes. All six receipts pass. The post-run capture pulls
reported no remote failure-capture directory, consistent with these passing
scopes. Logs, command exit codes and receipts remain locally under
`build/ci-editing-investigation/q8-host-runners`. These are separate local runs,
not a single end-to-end hosted CI job or physical-device acceptance.
