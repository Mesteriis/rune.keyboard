# Android CI: reject severely truncated general suites

The boundary-suite verifier previously accepted a successful general-suite JUnit
report with only one executed test. The published API 26 and API 37 jobs each
reported more than 300 general cases before fixture exclusions were split, and the
current API 26 runner lists 351 cases with the four special classes excluded.
The general suite now requires at least 300 reported and 250 non-skipped cases in
fresh, valid JUnit results, in addition to the existing exit-code and failure
checks. The special suite thresholds are unchanged.

These floors are intentionally conservative: they catch gross filtering or
missing-result errors but cannot establish the complete expected case identity
set, prove a hosted run, or substitute for individual case results. The six
local Python unit tests pass, including rejection of one reported case, 299
reported cases, and 300 cases with only 249 executed; the test also checks that
other suite results remain independently verified. Output is retained in
`build/review-hosted-editor/suite-floor-unit.log`.

## General suite discovery and report identity

Before running the general suite, the owned-emulator runner now asks
AndroidJUnitRunner to enumerate the cases in the current debug test APK.
Discovery is log-only and uses the same instrumentation arguments as the
Gradle run. CI retains the runner output and the sorted class/method list.
The actual general scope must produce one fresh JUnit report with exactly
those identities. A discovery failure fails the general scope while the
independent scopes still run. The existing execution floors, required passing
cases, and known-skip inventory remain part of the gate.

The debug APKs were built in a clean temporary checkout. On local ARM64
API 26 and API 37 emulators, direct log-only discovery and Gradle log-only
JUnit output agreed on all 398 identities on each API. The API sets share
396 cases, with two SDK-specific cases on each side. Two mutations of the actual API 37
listing XML deleted or renamed one non-required case. Both remained within
the previous counts and required-case checks. The new identity comparison
rejected both. A real API 26 Gradle run of all eight KeyFlickView cases also
matched the discovered subset, with zero failures or skips. All 53 Android
CI helper tests passed.

Log-only mode verifies dispatch and reporting identities. The execution
results below apply to the local API 26 boundary run.

## API 26 connected boundary run

A clean checkout of `40e4559512270a3b865a52484c557ba360d4a295` built the
ordinary, instrumentation, Compose QA and native-runtime APKs locally.
The owned ARM64 API 26 AVD then ran every scope from
`android_boundary_suites.py --api 26` through Gradle. The
[runner receipt](2026-11-23-q7-api26-connected-boundary.json) records exit
code zero and a fresh verified JUnit report for all eleven scopes.

| Scope | Passed | Skipped |
| --- | ---: | ---: |
| General | 339 | 59 |
| Personal | 4 | 0 |
| Case rejection | 2 | 0 |
| Confirmed words | 3 | 0 |
| Compose editor | 4 | 0 |
| Emoji memory | 1 | 0 |
| Export navigation | 1 | 0 |
| Export picker | 1 | 0 |
| Qualification lifecycle | 1 | 0 |
| Qualification safety | 1 | 0 |
| Native runtime | 6 | 0 |

A second read of the raw reports confirmed all counts and the exact match
between the 398 discovered and reported general identities. The 59 skipped
identities equal the inventory at that commit. The general XML SHA-256 is
`c69c5193925612604fbf89cbeca99e9cf5aebfbc1799127de6104b6616c61eb8`.
The receipt SHA-256 is
`94522a1e47f1eecbfce178c0d571e148219a5974e3ef453f61fa4dfaa5f90c35`.
The API 37 boundary run, hosted x86_64 execution and physical Fold coverage
require their own evidence.

### API 26 restart, process death and voice routes

After restoring the ordinary APKs, the same checkout and API 26 emulator
ran three additional workflow entry points.

| Runner | Verified result |
| --- | --- |
| `android_synthetic_restart_suites.py` | Four cases passed: write and reload for case rejection and confirmed words. |
| `android_editing_process_death.py` | Both left and right editing cases showed the required process interruption and passed recovery in the independent Compose editor. |
| `android_voice_fixture_suites.py` | Five cases passed: unavailable voice, enabled voice, gesture switching, stale voice and the API 26 system picker. |

The first invocation used output directories outside the checkout. All
three runners refused them before executing tests. The workflow's
checkout-local `build/` paths allowed the rerun to complete with exit zero.
The original receipts and raw reports for the boundary and additional
routes are in the local `build/ci-q7-api26-40e45595/reports.tar.gz` archive.
The separate night-learning workload needs a fresh AVD and remains
outside this run.

## API 37 interruption after a blocked input window

The 16 KiB ARM64 API 37 run at `40e45595` was stopped deliberately after
330 of the 398 discovered cases. At that point there were 47 skips and
nine failures. Four earlier failures were in scoring and model readiness,
and one was the [point-key flick](2026-10-29-q7-api37-flick-retry.md).

The last four failures were in the mechanical punctuation class. Three
captured editor snapshots showed an active input connection, zero compose
or commit commands and text length zero. Android `InputDispatcher`
logged rejected touches during these tests. Its window snapshot placed
the System UI starting window for `ImeQaActivity` above Rune's IME for the
entire screen. This explains the absent editor input in those snapshots.
The scoring and flick failures need their own reproductions.

The interrupted run did not finish the general report or invoke the
separate boundary scopes. Its log and failure captures were retained for
follow-up.

The debug QA editor now inherits the setup theme with the Android starting
preview disabled. On the same AVD, the patched APK built successfully and
12 consecutive clear-task launches reported success with no QA splash
input window. The emulator's untrusted-touch policy was equal before and
after the run.

In a six-case direct repeat, five cases passed, including the decimal and
hostname path, comma popup, command dot, and the earlier point-flick
failure. The cached-mechanical-toggle case failed in setup while waiting
for the IME window, before its first tap. The full API 37 run and that
setup failure remain open.

The cached-toggle method passed in isolation on the same AVD. Both
scoring and model-readiness classes then passed all 17 tests twice,
once on the normal QA APK and once with a temporary numeric probe.
The probe logged seven rejected scoring requests. All were explicit
memory-pressure controls, with the duty owner reporting suspension.
None of the four earlier failures recurred, so these runs leave their
original cause open. The diagnostic build was replaced with the normal
QA APK before the old AVD was deleted.

The interrupted run, captured overlays, and targeted results were
verified in a local archive at
`build/ci-q7-api37-interrupted/reports.tar.gz`. The clean full repeat
uses the same Android code plus the debug QA theme on a new 16 KiB AVD.

## API 37 general repeat with the debug preview disabled

The 16 KiB ARM64 repeat used `40e45595` with the two debug Android files
from `e3e9df48`. JUnit reported all 398 discovered case identities exactly
once, with 339 passes, 58 known skips and one failure. The Android boundary
report verifier accepted the identities and allowed skips. All nine cases
that failed in the interrupted run passed, including all four punctuation
cases, the point-key flick and the scoring and model-readiness cases.

The only failure was
`ConfirmedWordsInstrumentedTest.fullConfirmationReportsLimitOnceAndListCanBeFiltered`.
The fixture should skip in the general route. The inherited editor setup
timed out in `waitForKeyboard` before the fixture could check its opt-in.
Gradle returned exit code 1. Verification of the startup patch, completion
of the remaining scopes and hosted CI have separate results.

The JUnit file has SHA-256
`9a63ae2c9bbbc05e7d6a0eeb13a139f9585353bbb41c188a2ba9d0234c91cdb7`.
The report, runner discovery and punctuation and flick excerpts are retained
in `build/ci-q7-api37-repeat-general/reports.tar.gz`.

The other nine boundary scopes passed with 23 instrumented tests and zero
skips. The separate synthetic restart, editing process-death, voice and
Chrome commands also exited successfully. Chrome verified both textarea
profiles and produced a numeric verdict for each.

## API 37 debug editor startup fix

The QA activity now requests the keyboard through the window insets
controller on API 30 and above. Earlier Android versions use the posted
input-method request. Both debug and debug instrumentation APKs built and
their recorded hashes were verified before installation on the same AVD.

Without the synthetic profile opt-in, the confirmed-words case reached its
expected skip and the cached mechanical-toggle case passed. With opt-in,
both ran to completion in each of three repeats. The verifier checked each
case's instrumentation status and refused a skip in any opt-in repeat.
The full run with the startup fix and hosted acceptance are still open.

### API 37 connected scopes with the startup fix

The local 16 KiB ARM64 run used `40e45595` with the pinned debug theme and
startup overlays. General discovery and JUnit agreed on all 398 identities.
JUnit reported **339 passed, 59 known skips and zero failures**. The
confirmed-words case that timed out in the preceding general run reported
its expected skip.

Eight additional scopes passed in the first invocation. All four Compose
cases stopped in setup because the independent editor APK had been omitted
after wiping the AVD. The hosted workflow explicitly installs that fixture.
On the same AVD, installing and verifying the package followed by a separate
Gradle repeat passed all four Compose cases with zero skips.

The [API 37 receipt](2026-11-24-q7-api37-connected-boundary.json) binds the
source overlays, the discovery output, both runner receipts and ten JUnit
reports. Across the two invocations the ten scopes report 362 passed and 59
known skips. Raw reports and the original failed Compose setup are retained
locally in `build/ci-q7-api37-repeat-general/startup-fixed-boundaries.tar.gz`.
A single complete invocation on this source, the fresh night-learning
route and hosted x86_64 acceptance remain open.
