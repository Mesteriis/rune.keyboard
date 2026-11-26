# Q7: detect unexpected general-suite skips

The Android general-suite report gate required case counts and selected passed
identities, but a different skipped test could still fit under the count floor.
It now rejects every skipped identity outside the sorted versioned inventory
`tools/ci/android-general-skips.json`. An expected identity may pass instead;
the list does not require it to remain skipped. Malformed or duplicate inventory
entries fail validation. The list is an explicit exception inventory, not an
assertion that skipped tests passed or that their separate routes all ran.

The retained API 26 and API 37 general reports have identical sets of 48
skips; a third older API 26 report contains the same skip identities but lacks
some of the current required cases and is correctly refused by the existing
required-case gate. The 48 include physical-Fold, installed-model, voice,
special fixtures, Chrome, Compose, process-restart and measurement cases.
Some are exercised by separate scopes; others require device, model, fixture or
manual evidence. The inventory was derived from identities only, without
copying log payloads. It does not make those scenarios passing.

Comparing the inventory to the current configured Compose, confirmation,
case-rejection, restart, process-death and voice method identities accounts
for 20 of the 48 skipped identities across the API 26/37 plans. This is a
static routing count, not execution evidence: the voice picker and switching
methods are API-specific. The remaining 28 are not covered by those routes;
they include physical-Fold, model, Chrome, memory and learning fixtures.

Both retained API 26 and API 37 reports contain 369 cases and 48 skips and
pass the updated report parser. Changing an otherwise passing, non-required
case to skipped makes each report fail with `TEST_REPORT_UNEXPECTED_SKIP`.
The host runner suite passed 22 tests, including the new allowed/unexpected skip
and malformed-inventory checks; all 22 also passed from a staged source archive
without `build/`. The old third report was deliberately checked
and failed the prior `TEST_REPORT_REQUIRED_CASES` requirement. No new Android
emulator, physical Fold or hosted CI run is claimed. Temporary mutant reports
and the source archive were removed.

## Native runtime required cases

The separate native-runtime gate previously accepted any single passing test
in the runtime package. It now requires all six core
`LlamaRuntimeInstrumentedTest` methods to pass, covering library load, invalid
inputs, and cancellation/unload/close behavior. Other runtime tests can still
be reported, and this requirement does not assert that real-model or benchmark
tests ran. Removing or skipping any required case makes the report fail.

All 23 host runner tests passed, including the six missing-case and six
skipped-case mutations. They also passed in a temporary source archive without
`build/`. The retained API 26 and API 37 reports each contain all six required
passing cases and pass the revised parser. These are existing reports, not new
emulator runs; hosted execution and the remaining skipped scopes are still open.

## Emoji memory route and general opening checks

The current general-suite exception inventory contains 59 identities. The
memory observer still requires an explicit opt-in, so the ordinary general
suite can report it skipped. The existing owned-emulator boundary runner now
executes it separately as `emoji-memory` on API 26 and API 37. Its fresh JUnit
report must contain the exact observer as a passing case. Empty, substituted,
and skipped reports fail the route. This also puts the observer's report under
the existing boundary-suite artifact collection.

The general report now requires both opening checks by test identity, the
fresh palette draw-start probe and the real-IME PixelCopy evidence probe.
Retained API 26 and API 37 general reports contain both as passing cases.
These checks establish measurement validity. SurfaceFlinger timing and the
50 ms acceptance target have their own
[U9 evidence](2026-11-23-u9-surfaceflinger.md).

All 45 host checks across the six Android runner and artifact-collection
suites passed. This includes wrong-observer and skipped-observer probes.

The exact new runner command and report gate passed locally on separate
disposable ARM64 API 26 and API 37 emulators. Each connected Gradle run took
35 seconds and produced one fresh passing case with zero errors, failures
or skips. The local invocation selected only the new route, using the
cached pinned Gradle distribution. Hosted x86_64 execution and a fresh
full general-suite run remain open.

## Night-learning fixture evidence

The two night-job fixture cases and the Learning Lab progress case now have
[a current-source local repeat](2026-10-27-u13-night-learning.md#current-source-repeat-on-api-26-and-api-37)
on both matrix APIs. Each still requires the explicit night-learning fixture.
The local evidence covers test execution, with the hosted route still open.

The emulator-smoke matrix now runs the night-learning fixture on a second,
fresh AVD at each API level. It runs after the ordinary scopes, reuses the
already built default-package APKs, and uploads its logs and receipt with
the matrix artifacts. The route requires an empty emulator, the expected
API and user, and the actual local night window before APK installation.
The primary CI AVD retains its own clock, power settings and application
data. The dedicated route covers the two fixture cases and Learning Lab
progress, and also repeats the JobScheduler constraint check.

The workflow chooses a regional timezone that places the emulator at
02:00 or 03:00 local. The first API 37 attempt with an `Etc/GMT` offset
booted in UTC. The night-window check rejected it before installation.
The regional-zone retry booted in the expected window and passed. Both
local ARM64 APIs produced four passing cases and a successful route receipt.
All 50 host suite checks and actionlint v1.7.12 passed. Hosted execution
on x86_64 and natural overnight dispatch remain open.

## Current route coverage for the 59 known skip identities

At `b19e2386`, comparing the exact class/method pairs in the skip inventory
with the current emulator workflow and its runner arguments accounted for 27
distinct identities across both API jobs. The workflows route 24 identities
on API 26 and 26 on API 37. Two API 37 Chrome cases and the two
API-specific next-keyboard paths account for the differences.

| Separate route | API 26 | API 37 |
| --- | ---: | ---: |
| Case rejection and confirmed words | 5 | 5 |
| Independent Compose editor | 4 | 4 |
| Emoji memory | 1 | 1 |
| Synthetic process restart | 4 | 4 |
| Editing process death | 2 | 2 |
| Night learning and Learning Lab progress | 3 | 3 |
| Voice and next keyboard | 5 | 5 |
| Chrome textarea with numeric DOM verification | — | 2 |

Each count describes a scheduled identity. The editing process-death
preparation method is expected to stop when its process is killed. That
route requires both the deliberate interruption and verified recovery.
The counts do not establish whether the current hosted jobs have run.

Of the 32 identities outside those routes, 29 require a physical Fold
scenario and three require a real installed model fixture. The physical
cases cover 18 autocorrection tests, five punctuation boundaries, three Undo
tests, one unfold scenario, Chrome's address bar and Termux. The installed
model cases separately cover bounded scoring, private Binder service scoring
and typing with exact Undo. Existing physical or real-model evidence must
be assessed against the version and display or editor conditions it used.
