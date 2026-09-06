# Smart Typing 0.3 — candidate strip and Undo foundation, 2026-09-02

This is the local PR5 foundation, not a 0.3 release or autocorrection-quality
qualification. Original baseline: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`.
Slice base: `ffe8e3932449da9a7d2c2a8cf6f5554535c3e511`.
Branch: `feature/smart-typing-03-pr05-strip-undo`. Version remains 0.2.0.
No push, remote PR or model publication was performed.

## Delivered behavior

The separate migration commit `e22fdbd4fed9687baa00ee99996ff1e3194f584b`
removes double-space Undo from KeyboardState. A single typing-owned
`UndoableTextEdit` records the original/applied owned suffix and bounded
context snapshot. Double-space edits only an owned pending boundary; its
first Backspace restores that span as composition without ordinary deletion.
The next text action or ownership invalidation closes the transaction.
Unowned or ineligible double-space remains two plain spaces. The executor's
old surrounding-text conversion/revert path is removed.

`RuneKeyboardView` now has permanent candidate and keys containers. The strip
updates three permanent cells without rebuilding keys or cancelling their
touch/popup state. A changed candidate invalidates an already armed candidate
tap; pointer identity and out-of-bounds release are checked. A hidden strip
clears payload and accessibility state. An enabled empty strip retains height.
Nonempty sets contain exactly one Original; selected state and labelled
TalkBack click actions are exposed.

The current product consumer displays the original composing word. Tapping it
validates session/revision, records the user's choice for that word and does
not write to the editor. Old IDs, sensitive sessions and lost composition
cannot accept stale choices. Candidate data never appears in diagnostic
`toString()` output. `Rune#candidateRender` is a constant trace label.

Correction and punctuation item rendering is tested in isolation, but these
alternatives are not yet supplied by the product. Autocorrection/full changed
suffix Undo and later punctuation consumers still require integration and
their own Binder coverage. No Undo stack or placeholder edit subclasses were
introduced.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Migration JVM | PASS | Fresh post-commit rerun: 281/281 (275 app + 6 runtime), no failures/errors/skips |
| Migration build gates | PASS | Full prescribed command and Android test APK assembly; 292 tasks, 51 executed |
| Migration Binder | PASS | All 13 composing tests on API36, 119.440 s |
| Strip JVM | PASS | Fresh rerun: 292/292 (286 app + 6 runtime), no failures/errors/skips |
| Strip build gates | PASS | Full prescribed command and Android test APK assembly after fixture fix; 292 tasks, 21 executed |
| API36 app instrumentation | PASS with scoped rerun | Initial full 57-test run: 56 passed, one accessibility fixture failure, 492.582 s; after fixture repair all 10 strip tests passed, 6.881 s. Together 57 unique tests passed; no claim of a second full-suite run |
| API26 / API37 | BLOCKED | Separate fresh device runs not completed at this slice's evidence checkpoint |
| New remote CI | BLOCKED | Push not authorized; old baseline CI is not evidence for this revision |
| Physical Fold / latency / battery | BLOCKED | No physical measurements in this slice |
| Prepared-candidate model quality | FAIL | Frozen PR1 evidence unchanged |
| Immutable model release / version 0.3 | BLOCKED | Remaining implementation, quality, device and publication gates open |

The failed accessibility test created an unattached View hierarchy. Its
replacement attaches the same hierarchy using ActivityScenario, waits for
idle, asserts attachment and retains all selected/description/action/callback
assertions. It then passes without a production-code workaround. Independent
review approved the migration, strip integration and this scoped fixture fix.

The real Binder tests additionally verify that tapping Original produces no
editor commit/composing operation, subsequent typing refreshes it, and changing
to a sensitive editor removes the previous word. Component tests verify key
instance identity, Shift preservation, active touch/repeat cancellation and
attached alternate-popup selection across candidate updates.

Ignored logs under `build/smart-typing-0.3/`: `pr05-undo-post-commit-jvm.log`,
`pr05-undo-gates.log`, `pr05-undo-binder-api36.log`, `pr05-strip-jvm.log`,
`pr05-strip-gates.log`, `pr05-strip-all-api36.log`, and
`pr05-strip-components-api36.log`. A screenshot of the actual empty strip and
keyboard is `pr05-strip-visual-api36.png`; it is not physical Fold evidence.

## Reproduction

```sh
./gradlew testDebugUnitTest --rerun-tasks
./gradlew lint assembleDebug assembleRelease assembleProfile \
  privacyGateRelease privacyGateProfile imeIntelligenceBoundary \
  forbiddenRuntimeDependencies :runtime-llama:nativeSymbolGate \
  assembleDebugAndroidTest
./gradlew :app:connectedDebugAndroidTest
```

The required fresh JVM run is repeated after each commit. Post-commit results
are recorded with the actual commit SHA in the execution ledger/task evidence.
