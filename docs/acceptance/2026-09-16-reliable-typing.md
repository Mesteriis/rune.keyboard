# Rune reliable typing: tap delivery and autocorrection refusals

## Baseline and scope

- Date: 2026-09-16 (Europe/Madrid).
- Starting branch/SHA: `main` / `f3802d53c6b26dae45a5faed8eb2210c2a0571bd` (`v0.4.1`).
- Working branch: `fix/reliable-typing`.
- `origin/main` after fetch: `f3802d53c6b26dae45a5faed8eb2210c2a0571bd`.
- Worktree before changes: clean.
- Pinned submodule: `runtime-llama/src/main/cpp/llama.cpp` at
  `36b10154383b60eb15baac2c7a40d2a5f784faa7`; initialized at that gitlink.
- The reviewed SHA is therefore the current source baseline, but says nothing about an installed
  APK. No physical device was connected during baseline discovery.
- Scope is limited to (A) the confirmed ordinary-tap loss and (B) typed autocorrection refusal
  evidence. Models, dictionaries, limits, thresholds, ranking order, learning, permissions and
  runtime dependencies remain unchanged.

## Baseline receipts

- The current `KeyFlickGesture.kt` is byte-identical to the handoff reference (SHA-256
  `86716023d4aa53f689ecff6991c1fa32d024d083b4ff1c229924eeda5248aeae`).
- Handoff `repro/run-probe.sh`: attempted, exit 2 because `kotlinc` is not installed. The pinned
  build toolchain was not changed. Raw receipt: `build/reliable-typing/baseline/pure-probe.log`.
- `./gradlew testDebugUnitTest --rerun-tasks`: PASS, exit 0. Raw receipt:
  `build/reliable-typing/baseline/testDebugUnitTest.log`.
- Static chain on the baseline: upward travel beyond `touchSlop` enters
  `KeyFlickGesture.State.CANCELLED`; `KeyboardKeyView.updateFlick()` then calls
  `cancelPendingActions()`, disarming the key before an in-bounds `ACTION_UP` can click.

## Plan recorded before behavior changes

### Commit A — ordinary tap arbitration

1. Add RED coverage in `KeyFlickGestureTest`, `KeyFlickViewInstrumentedTest` and
   `KeyFlickImeInstrumentedTest` for an upward displacement larger than touch slop whose release
   remains inside the original key.
2. Add parent-surface `RuneKeyboardView.dispatchTouchEvent` coverage in
   `PhysicalTouchInstrumentedTest` for two fingers on different keys, overlapping contacts,
   reverse release order, pointer splitting and a render deferred until both contacts end.
3. Change only `KeyFlickGesture.kt` and `KeyboardKeyView.kt`: make a rejected flick distinct from
   cancellation of the whole key; retain tap eligibility only while the contact is within the key's
   existing slop bounds. Preserve terminal cancellation for non-finite input, real exits,
   `ACTION_CANCEL`, detach/reconfiguration, long press, accessibility and the selected downward
   flick.
4. Run scoped JVM and instrumentation RED/GREEN, then the available API 26/API 37 suites. Commit
   this slice before touching autocorrection diagnostics.

### Commit B — typed autocorrection refusal evidence

1. Extend the fixed diagnostic vocabulary/schema in `TypingDiagnostics.kt` and debug-only
   `DiagnosticsEncoding.kt`; no input text, coordinates, key labels or hashes are added to metadata.
2. Add side-effect-free typed evaluations to `CandidateRanker`, `LocalCorrectionPolicy`,
   `AutoCorrectionAdmissionGuard` and the `TypingPersonalization` boundary. Existing boolean/ID
   APIs delegate to the same evaluation so thresholds, order and automatic decisions remain
   identical.
3. Emit only reasons known at the existing short-circuit point in `TypingSessionController`,
   `LocalCandidateCoordinator` and `ModelCandidateCoordinator`, including result readiness,
   deadline, revision, ownership and editor response.
4. Extend `tools/typing_diagnostics_analyzer.py` and its tests. Optional synthetic/authorized
   ground truth may distinguish target absence, incomplete/not-found retrieval, top-K exclusion and
   manual-only candidates; free typing without ground truth reports those as unknown instead of
   inferring intent.
5. Add equivalence/regression coverage in the existing correction, session, recorder and analyzer
   tests. Update `docs/DEBUG_DIAGNOSTICS.md` for schema compatibility, then run Python tests, JVM
   tests, packaging/privacy/boundary gates and the available instrumentation matrix.

## Commit order

1. Stage A: tap/flick arbitration plus Android regressions and this initial receipt.
2. Stage B: refusal diagnostics/analyzer plus equivalence tests and final receipts.

No third roadmap slice will be implemented in this branch.

## Device and settings matrix

| Target | Build/source | Geometry/profile | Configured/effective test controls | Result |
| --- | --- | --- | --- | --- |
| API 37 `google_apis_ps16k/arm64-v8a` AVD | local debug, final worktree | 1080×2340 emulator; fixed test key geometry | flick ON; autocorrection OFF; dynamic touch shadow/apply OFF; personal/touch learning OFF in the Stage A profile. Preferences were asserted after synchronous write and the live IME listener was drained. Full diagnostics tests exercised configured/effective flags and consent. | RED reproduced in View and Binder-editor; Stage A scoped GREEN 20/20; final full run: app 215 (211 passed, 4 expected skipped), runtime 6/6, 0 failed. |
| API 26 `google_apis/arm64-v8a` AVD | local debug, final worktree | 1080×2340 emulator; fixed test key geometry | same deterministic profile; runner restored the complete previous raw preference map and previous IME after every test | Stage A scoped GREEN 20/20. Final full app run: 209 passed, 4 expected skipped, one language-switch diagnostics timing failure; that exact test passed 1/1 immediately in isolation. Runtime 6/6 passed. |
| Physical Fold, outer screen, flick OFF/ON AB/BA | installed APK unknown | NOT_RUN | configured/effective values NOT_RUN | No device connected; no APK/settings/IME changes attempted. |
| Physical Fold, inner screen, flick OFF/ON AB/BA | installed APK unknown | NOT_RUN | configured/effective values NOT_RUN | No device connected; no APK/settings/IME changes attempted. |

The emulator matrix is not a physical A/B measurement and therefore supplies no real-device miss,
duplicate, adjacent-key or false-flick rate. The tests use synthetic known text only and do not
modify or erase accumulated learning outside their restored test preferences.

## Stage A result

### RED

- API 37 View dispatch test `upwardDriftInsideTheKeyStillCommitsOneOrdinaryLetter`: FAIL as
  expected; one in-bounds contact produced zero actions instead of `CommitLetter("q")`.
- API 37 real IME/Binder editor test `upwardDriftInsideKeyCommitsThroughTheRealEditor`: FAIL as
  expected; the editor remained empty after the same contact.
- Raw receipts:
  `build/reliable-typing/baseline/stage-a-red-view-api37.log` and
  `build/reliable-typing/baseline/stage-a-red-ime-api37.log`.

### Minimal fix and confirmed cause

`KeyFlickGesture` now distinguishes terminal `REJECTED` flick recognition from terminal
`CANCELLED` invalid input. `KeyboardKeyView` keeps the ordinary click armed for `REJECTED` only
while each event remains within the key's existing slop bounds. A real exit still calls
`cancelPendingActions()`. No slop, flick threshold, long-press timeout or action mapping changed.

This confirms the reviewed chain as the cause of the reproduced loss: the old upward-limit branch
used a state that the View interpreted as cancellation of the entire key, not cancellation of only
the secondary flick candidate.

### GREEN and regression evidence

- `./gradlew :app:testDebugUnitTest --tests ...KeyFlickGestureTest --rerun-tasks`: PASS.
- API 37 `KeyFlickViewInstrumentedTest` + `PhysicalTouchInstrumentedTest`: 11/11 PASS.
- API 37 `KeyFlickImeInstrumentedTest` + `RapidTypingInstrumentedTest` +
  `DynamicTouchInstrumentedTest`: 9/9 PASS.
- API 26 all five classes above: 20/20 PASS.
- `./gradlew testDebugUnitTest --rerun-tasks`: PASS after the fix.

The parent-surface regression sends two overlapping pointer IDs to different child keys through
`RuneKeyboardView.dispatchTouchEvent`. Both release orders commit exactly once in release order;
the old key views remain until the second contact ends, then the queued render is applied. Existing
tests continue to cover downward flick, flick retreat, long-press alternatives, accessibility,
second-pointer cancellation on one unsplit child, `ACTION_CANCEL`, explicit reconfiguration cancel,
dynamic-touch invalidation and rapid editor delivery. A Fold/configuration transition itself was
not physically run.

## Stage B result

### RED and decision equivalence

- New correction tests initially failed to compile because `chooseWithReason`, `evaluate` and the
  typed refusal enums did not exist. Receipt:
  `build/reliable-typing/stage-b/red/gradle-app.log`.
- New analyzer tests failed because `analyze_events` accepted no ground truth and produced no
  schema-7 refusal report. Receipt: `build/reliable-typing/stage-b/red/analyzer-real.log`.
- GREEN equivalence checks assert, over accepted and rejected fixtures, that:
  `CandidateRanker.choose == chooseWithReason.candidateId`,
  `LocalCorrectionPolicy.decide == evaluate.decision`, and
  `AutoCorrectionAdmissionGuard.allows == evaluate.allowed`.
- The independent 6,000-row ranker calibration oracle and all existing controller/editor tests
  also remain green. Threshold values, short-circuit order, candidate ordering, qualification and
  morphology veto decisions were not changed.

### Known refusal evidence

Schema 7 keeps metadata content-free and adds fixed reasons only at established decision points:

- retrieval: `SEARCH_INCOMPLETE`; target-aware `TARGET_NOT_IN_DICTIONARY`, `TARGET_NOT_FOUND`,
  `TOP_K_EXCLUDED` and `MANUAL_ONLY` exist only in analyzer output supplied with an explicit
  authorized corpus row;
- ranking/policy: `TOO_SHORT`, `ORIGINAL_VALID`, `WINNER_AMBIGUOUS`,
  `INSUFFICIENT_MARGIN`, `NOT_QUALIFIED`;
- morphology: `MORPHOLOGY_UNAVAILABLE`, `RIVAL_OTHER_LEMMA`;
- lifecycle/editor: `DEADLINE_MISSED`, `STALE_REVISION`, existing
  `OWNERSHIP_REJECTED`, and existing terminal `EDITOR_REJECTED`.

For example, equal plausible alternatives now report `WINNER_AMBIGUOUS`; a winner that fails only
the original-word margin reports `INSUFFICIENT_MARGIN`; an unavailable morphology lexicon reports
`MORPHOLOGY_UNAVAILABLE`; and a plausible Russian competitor with another observed lemma reports
`RIVAL_OTHER_LEMMA`. The analyzer reports a corpus target found only in `manualCandidates` as both
`TOP_K_EXCLUDED` and `MANUAL_ONLY`, but does not include the target string in its report. Without
ground truth it emits only reasons explicitly recorded by the app and does not infer intent from
free typing or the absence of Undo.

The optional `manualCandidates` text field exists only in the separately consented debug text
stream. Release/profile still use the exact no-op provider. No coordinates, key labels, words or
hashes were added to metadata, and no recorder, permission, network or service was added.

### Final verification receipts

- `python3 -m unittest test_typing_diagnostics_analyzer.py test_typing_diagnostics_boundary.py`:
  51/51 PASS.
- `./gradlew testDebugUnitTest --rerun-tasks`: 985/985 PASS, plus runtime module tests PASS.
- `./gradlew lint assembleDebug assembleRelease assembleProfile privacyGateRelease
  privacyGateProfile imeIntelligenceBoundary forbiddenRuntimeDependencies
  :runtime-llama:nativeSymbolGate --rerun-tasks`: PASS (242 tasks); debug/release/profile
  diagnostics packaging, 17 negative + 6 positive boundary fixtures, privacy and native symbol
  gates passed.
- API 37 full `connectedDebugAndroidTest`: PASS; app 215 tests with 4 expected skips, runtime 6
  tests, 0 failures. Receipt: `build/reliable-typing/stage-b/green/instrumentation-api37.log`.
- API 26 full `connectedDebugAndroidTest`: one failure in 214 app tests after 33.6 seconds in the
  language-switch diagnostics UI test; the exact test then passed 1/1 in 56 seconds. All other app
  tests and all 6 runtime tests passed. Receipts:
  `build/reliable-typing/stage-b/green/instrumentation-api26.log` and
  `build/reliable-typing/stage-b/green/instrumentation-api26-diagnostics-rerun.log`.

The four expected instrumentation skips on each API are physical Fold and installed-real-model
checks unavailable in these AVDs. The API 26 full-run timing failure is retained as a known flaky
limitation rather than rewritten as a clean full-suite pass.

## Known limits and next priority

- The handoff pure probe remains NOT_RUN because the machine has no `kotlinc`; stronger Android
  View and Binder-editor regressions did run.
- Physical Fold outer/inner controlled A/B is NOT_RUN. No miss, duplicate, adjacent-key or
  false-flick rate was measured, so this work does not claim that everyday misclicks are solved.
- Installed real-model instrumentation is SKIPPED, and refusal diagnostics do not establish that
  autocorrection quality is sufficient.
- Free conversation has no known intended target; target/dictionary/top-K/manual-only analysis is
  limited to an explicit synthetic or authorized test corpus.

The next priority is the controlled physical Fold A/B with identical phrases and geometry, flick
OFF/ON in balanced order, and configured/effective autocorrection, dynamic touch and learning
disabled. It supplies the missing real-device miss/duplicate/false-flick measurements before any
ranking snapshot or touch-aware retrieval proposal is considered. General ranking snapshots,
touch-aware retrieval and new learning remain proposed future work and were not implemented here.

## Commit record

- Baseline: `f3802d53c6b26dae45a5faed8eb2210c2a0571bd`.
- Stage A: `fcecaf5aeef49741fd30da4ca6603e4dd6c926d9`.
- Stage B: the commit containing this final receipt; its SHA is reported from Git after creation.
