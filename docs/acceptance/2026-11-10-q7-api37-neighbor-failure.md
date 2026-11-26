# Q7: API 37 workflow and neighbor-recovery failure

A clean checkout at `7da49492` ran the Android workflow shell on a disposable,
isolated ARM64 API 37 (16 KiB) emulator with 4 GiB RAM, software navigation and
GPU, and disabled animation scales. Gradle ran offline with a two-worker limit;
the local wrapper attempted to stop its background Logcat process on exit. This
is not a hosted x86_64 run or a physical Fold result. The full workflow exited
1 and must not be reported as passing.

The fresh general JUnit report contains 397 cases, 59 skipped and one failure.
`NeighborRecoveryLiveInstrumentedTest.twoNeighborErrorsCorrectAndUndoKeepsTheNextWord`
expected `он не дает ни малейшего ` but observed `он не дает ни палецшего `.
The synthetic failure screenshot and hierarchy confirmed the unchanged word;
their SHA-256 values were respectively
`6358cc1d5b4f6b42b0d843109f8f284eb32720298fdb5cc9e437a56ec3a876a3` and
`27e54c6fb8ed3d703c2b8b5a6e175835c534698592181fe3652f1d6e6ea6b9a4`.
The general Gradle invocation reported failure after 48m 56s on this local host.
The CI report gate rejected the general result. Separate fresh reports passed
without skips: personal 4, case rejection 2, confirmed words 3, Compose editor
4, export navigation 1, qualification lifecycle 1, qualification safety 1 and
native runtime 6. The API 26-only picker is not an API 37 route. Four synthetic
restart phases, two editor-process death phases and five voice scopes passed;
the failure collector reported captures present.

The fixed workflow Logcat stream continued after the privacy test's `logcat -c`.
This run did not observe the earlier ADB EOF, so it is not an end-to-end test of
reconnection after an actual disconnect.

## Metadata-only isolated repeats

After the workflow ended, a temporary test-only probe was added in the isolated
checkout and its test APK rebuilt. It required explicit opt-in, an emulator,
and an empty, disabled diagnostics store. It enabled metadata only, ran the
same synthetic test, exported fixed-vocabulary metadata without typed text and
then deleted its synthetic diagnostics. Three separate instrumentation runs
reported `OK (1 test)` and Android instrumentation code `-1`. Each correction
boundary was preceded in its session by an accepted complete neighbor recovery
with 10,770 inspected states and one verified terminal. The original failing
run had not enabled this metadata, so these passing repeats cannot establish
whether its search expired, a result arrived late, or another condition caused
abstention. Reinstalling a changed test APK, enabling diagnostics and restarting
instrumentation also changed the conditions. No product code or threshold was
changed and no successful full API 37 rerun is claimed.

The full workflow's post-restoration ordinary debug APK SHA-256 was
`c4920747eac7ad58421a2ebf46ffd0f1dbd62726e19575ce473081779cc350ed`; its
ordinary test APK SHA-256 was
`a636a2683269c165f003509cfb3b7d11b51e33abcb507de30f2e5fdf1584389c`.
The later diagnostic test APK was separate. The observed intermittent refusal,
root cause and correction remain open; hosted CI and release acceptance remain
open as well.

## Bounded contention repeat

A fourth metadata-only run used the same temporary test APK and opt-in emulator
fixture while two separate host CPU workers ran for a bounded 45 seconds. Both
workers exited 0. The instrumentation completed during their lifetime and
reported `OK (1 test)` with instrumentation code `-1`; the recovery accepted
before the correction boundary was `COMPLETE`, with 10,770 inspected states and
one verified terminal. The first worker-launch attempt did not exercise load:
Python's default spawn could not import a standard-input script; its child
failures were observed and the plan changed to explicit forked workers before
the successful attempt.

This is a single artificial contention observation, not a reproduction of the
full suite's preceding state, a benchmark, or proof that wall-clock timing was
not involved in the original failure. No threshold or production code changed;
the full-run failure and its cause remain open.

## CI failure metadata fixture

The existing two-neighbor real-IME test now wraps its unchanged assertion in a
metadata-only diagnostic fixture when `runeCiFailureCapture=true`, the device
reports QEMU and ranchu/goldfish, and the diagnostics preferences and store are
empty and disabled. It exports fixed-schema metadata to `RuneRecoveryFailure`
only if that test fails, then deletes its own synthetic diagnostics. Active
metadata/text consent or a nonempty store causes the fixture to leave that store
untouched and run the original assertion without capture. Physical devices and
runs without the explicit CI flag do not enable it. Capture and cleanup errors
are attached to the original failure where applicable. This is a test-only
change; it does not change the correction policy or diagnose the historical
failure retroactively.

At `14f96563` plus this test-only patch, a fresh isolated API 37 ARM64 emulator
built the ordinary debug and test APKs. With CI capture opted in, the unchanged
real-IME scenario passed one test with no failure metadata and the synthetic
diagnostics directory was empty afterwards. In the temporary checkout only,
the expected text was then deliberately replaced with a wrong synthetic value:
the instrumentation reported one failure, and 203 emitted metadata events all
matched the fixed 26-field metadata schema, with no text fields. The store was
empty and both preferences were disabled afterwards. Repeating that deliberate
failure with a pre-existing synthetic sentinel left the sentinel intact and
emitted no fixture metadata; without the CI opt-in it also emitted no fixture
metadata and left the store empty. These are targeted local fixture checks, not
a full workflow rerun or proof of the earlier failure's cause.

The empty-store guard subsequently became fail-closed if an existing diagnostics
directory cannot be listed. At `ddc6303b` plus that one-line guard change, a
fresh API 37 test APK ran the same opted-in scenario with a synthetic sentinel
inside a directory set to mode `000`. A separate `run-as ls` check confirmed
listing exited 1. The test itself reported `OK (1 test)` and instrumentation
code `-1`, emitted no fixture failure metadata, and the sentinel was unchanged
after directory permissions were restored. A second run with the task-owned
sentinel removed passed and left the diagnostics directory empty. Both runs
used the isolated emulator; no physical device was involved.

## Controller boundary regression

A focused JVM controller test now exercises a staged synthetic neighbor result
where the baseline was accepted before Space and recovery arrived afterward. A
complete admitted result at 100 ms applies and is exactly undone; a result at
the 250 ms boundary, an exhausted search and a cancelled search leave the typed
word unchanged. The four cases passed in a clean temporary checkout with the
pinned native submodule and offline Gradle. The test uses a synthetic
personalization decision and does not exercise the real model, worker delivery
or the failure seen in the full emulator run. Production code is unchanged.

## Coordinator staging regression

A coordinator/worker test now blocks a synthetic neighbor-recovery pass after
its baseline reply is published, delivers the baseline before Space, then
releases recovery after Space. At 100 ms the admitted result corrects the word
and Backspace restores it exactly; at the 250 ms deadline the original remains.
The synthetic lexicon and personalization isolate staging and ownership; they
do not run the packed reader or the real recovery model. In a clean temporary
checkout with the pinned submodule and offline Gradle, the complete
`LocalCandidateCoordinatorTest` class passed 97 tests with no failures, errors
or skips. Production behavior was not changed and the original API 37 refusal
remains unexplained.

The coordinator regression was extended to cover both delivery orders: the
baseline arrives before Space, or it is still queued when Space is entered and
arrives afterward. In both orders the staged recovery is admitted at 100 ms and
rejected at 250 ms. The focused test passed in a clean temporary checkout with
offline Gradle and the pinned submodule. It remains a synthetic coordinator test,
not a reconstruction of the original emulator failure.

A further focused coordinator test holds the same staged synthetic recovery
across Space and the first letter of the next word. Once released at 60 ms it
corrects the previous word without losing the new letter; selecting visible
Undo restores the original previous word while preserving that letter. The
focused test passed in a clean temporary checkout with offline Gradle and the
pinned submodule. It uses synthetic recovery and admission, so it does not
explain or qualify the real-IME failure.

## Repeated current-product JVM observation

At `7dac0731`, a clean temporary checkout ran the existing current-product JVM
replay on 20 copies of the disclosed historical `holdout-adjacent2-589` input,
using the lowercase prefix from the Android test. Both replay passes completed
and their projections matched exactly. All 40 observations had neighbor
recovery `COMPLETE`, 10,770 inspected states and one verified terminal; the
boundary produced `он не дает ни малейшего ` and Backspace restored
`он не дает ни палецшего`. The measured full-token-generation range was
3.60–37.17 ms across these observations on this host; it is not a separate
measurement of recovery or an Android timing guarantee. No external model calls
were made and no independent baseline was compared. These repeated copies are
one disclosed example, not 40 independent examples or a new holdout. The
result does not reproduce or explain the failed Android run. Temporary replay
inputs, outputs and checkout were removed.

## Hosted timeout headroom

The local API 37 general Gradle invocation above took 48m 56s by itself; the
previous local API 26 general invocation took 46m 48s. The tested local API 37
emulator reported four processors. The pinned emulator action's default is two
cores, and the workflow does not override it. Local ARM64 timings are not
hosted x86_64 timings, but the prior 60-minute job limit also covered checkout,
provisioning, all separate scopes and artifact upload, leaving little margin
relative to the observed local general stage. The workflow timeout is raised to
90 minutes to allow those steps; it remains a maximum, not a claim about actual
hosted duration or a passing hosted run. The six Android CI shell unit tests
passed after this configuration change. The action's pinned input definition is
[available upstream](https://github.com/ReactiveCircus/android-emulator-runner/blob/a421e43855164a8197daf9d8d40fe71c6996bb0d/action.yml).

## Post-Space recovery diagnostics

A staged recovery reply retained after Space previously did not record its
recovery completion or search counters, even though the pre-Space path did.
The coordinator now records a matching post-Space recovery reply as a
content-free `CANDIDATES/NONE/NEIGHBOR_RECOVERY` observation before applying its
existing deadline and ownership checks. It contains bounded completion, state
and terminal counts and no text callback. It describes an observed reply, not
acceptance or successful correction; it also records replies arriving after the
deadline. No admission, timing or correction policy was changed.

At `bc4ed5af` plus the staged change, a focused coordinator regression covered
both baseline delivery orders, complete and exhausted recovery, and 100/250 ms
boundaries; it verified the emitted completion and counters, absence of a text
callback and the existing correction/abstention outcomes. In a clean temporary
checkout with the pinned submodule and offline Gradle, 231 tests across the
coordinator, boundary and mechanical-diagnostics classes passed without
failures, errors or skips. Debug and instrumentation APK assembly passed. The
full two-pass current-product CI replay passed both frozen corpora: 2,160 and
12,000 rows, zero behavioral or tolerated score differences. This is local
JVM/build evidence, not an Android runtime or hosted CI result. The currently
running API 37 repeat was started from `68364850` before this production change
and therefore cannot validate the new event. The initial failure's cause and
fresh device acceptance remain open.

### Post-space recovery diagnostic privacy regression

At `2e8cb7e3` with the accompanying test change, a clean temporary checkout ran
`TypingDiagnosticsHooksTest`, `IncognitoDiagnosticsTest`, and
`DiagnosticsRecorderTest`: 61 JVM tests passed, with no failures, errors or
skips. The new test directly exercises serialization of a post-space recovery
reply, verifies its bounded completion and numeric counters, rejects the test
input sentinel and input/context fields, and verifies that a password session
emits no diagnostic event. This is JVM evidence, not an Android or hosted CI
result, and does not establish the cause of the original failure.

### Full API 37 repeat with failure-only metadata fixture

A separate disposable ARM64 API 37 emulator ran the full local Android workflow
from clean source `6836485016fbf0f6201135622f409bbee5f27fdf`; the workflow exited
0. The general JUnit report records 397 cases, 59 skips, zero failures and zero
errors. Both `NeighborRecoveryLiveInstrumentedTest` cases passed, including the
case that failed in the earlier full run. Eight separately routed groups record
22 cases total, with zero failures, errors or skips. All four synthetic restart
phases, both independent-editor process-death cases and five voice fixture
scopes passed. No failure-only diagnostic capture was produced.

The debug APK SHA-256 was
`7befa9b2c3e0afe690b8444e1bb756ccac58f69ca1732d7f9a64825644a9d5d2`;
the instrumentation APK SHA-256 was
`d833f4d9cc57f84311d777780f6389e30285e4f724908049785798bd955ec920`.
This repeat does not determine why the earlier run failed. It predates
`2e8cb7e3`, which adds post-space recovery evidence, and does not establish
hosted CI or Fold behavior.

### Current-source real-IME follow-up

Clean source `782ce633` was built in a disposable checkout and installed on a
fresh isolated ARM64 API 37 emulator. Direct Android instrumentation of both
`NeighborRecoveryLiveInstrumentedTest` methods, with the CI failure-capture
fixture opted in, reported `OK (2 tests)` and instrumentation code `-1`. The
build and test APK SHA-256 values were respectively
`b0b6aced16c5bb172fb00cc47312f5849314dde4bcd63cbe883028af2848563a` and
`d833f4d9cc57f84311d777780f6389e30285e4f724908049785798bd955ec920`.
This verifies those real-IME scenarios on the code containing the post-space
diagnostic change. It does not establish that the delayed-reply branch executed,
reproduce the original intermittent failure, or constitute a full current-source
workflow, hosted execution or Fold evidence.

### Current-source full JVM and frozen replay

At clean source `78ce557b43a4b93c7e1370aaf2c41da10a701aff`, an offline clean
checkout ran `:app:testDebugUnitTest`: 139 JUnit suites and 1,412 tests, with
zero failures, errors or skips. The actual `tools/ci/product_replay_ci.py` gate
then completed both current-product profiles with two deterministic runs each.
All 2,160 and all 12,000 rows matched the respective frozen projections, with
zero tolerated score differences. The projection hashes were respectively
`e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea`
and `b7b49f16aed912ea4c80d811c834f059dc1ac47f6b655e9798923651ec47f512`;
host timing fields are excluded from the determinism comparison. Both commands
exited 0. The temporary checkout, test results and replay artifacts were removed.

This local JVM evidence covers the post-space diagnostic implementation; it
does not establish the cause of the earlier Android failure, a full Android
workflow at this source, physical Fold behavior, independent natural-language
quality or hosted CI.
