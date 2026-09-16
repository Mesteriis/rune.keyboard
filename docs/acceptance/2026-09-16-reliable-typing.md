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
| API 37 `google_apis_ps16k/arm64-v8a` AVD | local debug, Stage A worktree | 1080×2340 emulator; fixed test key geometry | flick ON; autocorrection OFF; dynamic touch shadow/apply OFF; personal/touch learning OFF. Preferences were asserted after synchronous write and the live IME listener was drained. | RED reproduced in View and Binder-editor; GREEN for 20 scoped JVM/View/IME/multi-touch/rapid/dynamic tests. |
| API 26 `google_apis/arm64-v8a` AVD | local debug, Stage A worktree | 1080×2340 emulator; fixed test key geometry | same deterministic profile; runner restored the complete previous raw preference map and previous IME after every test | GREEN: 20 scoped Android tests, 0 skipped/failed. |
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

## Final results

Stage A complete; Stage B pending.
