# Smart Typing 0.3 — composing foundation, 2026-09-02

This report covers the independent PR4 local slice, not completion of 0.3.
Original baseline: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`.
Slice base: `f06d815e07f6457a03e6c978a64250349995bc3d` (completed PR1 evidence).
Branch: `feature/smart-typing-03-pr04-foundation`. The commit containing this
report is the PR4 implementation revision; post-commit JVM results are recorded
in the task output. Version remains 0.2.0; no push or remote PR was performed.

## Delivered behavior

- Separate `TypingSessionController` owns composing and bounded RAM context.
  The reducer retains visual/Shift/language/layer/Enter responsibilities, and
  all editor writes still pass through `EditorCommandExecutor`.
- A letter starts composition; Space finishes the word and creates a visible
  pending boundary. The next letter updates that span without duplicating it.
  Composing is capped at 256 UTF-16 units; an oversized word continues through
  acknowledged plain commits until its boundary.
- Context contains only Rune-entered text, at most 2048 UTF-16 units and 1024
  code points, trimmed at ICU grapheme boundaries. Own grapheme deletion uses
  this buffer without reading editor text. Context is cleared at invalidation,
  selection changes, view/input completion, and editor restart.
- Numeric expected selection acknowledgements are bounded and retired in
  order, including coalesced callbacks. Unexpected span loss disables Smart
  Typing for that editor session. Reentrant session changes abort the remaining
  effects of an in-flight action; lost text buffers are never replayed.
- Cursor mode emits an explicit start action, before any movement. Enter,
  language/layer changes and lifecycle finish the owned span. Unknown plain
  cursor changes suspend composition until a selection callback arrives.
- NPL/password/raw inputs bypass composition. Caps and double-space now require
  `InputPolicy.NORMAL`; sensitive delete does not read surrounding text.
- Existing double-space Undo is preserved through a temporary exact numeric
  acknowledgement bridge. Its migration to one typing-owned transaction is
  deliberately the next PR5 slice, not claimed here.
- `Rune#composeUpdate` is a constant, content-free trace section.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| JVM | PASS | Fresh rerun: 272 tests (266 app + 6 runtime), zero failures/errors/skips; 41 new session/context tests, 5 executor tests and 4 privacy regressions |
| Lint/build/privacy/dependency/native | PASS | Full prescribed command plus Android test APK assembly; final invocation 292 tasks, 21 executed, 271 up-to-date |
| API 36 app instrumentation | PASS | All 43 then-existing tests passed in 422.479 s; added stationary Space hold test passed separately in 9.510 s (44 unique tests total) |
| API 26 new feature | BLOCKED | No run yet; official ARM64 image installation in progress at slice close |
| API 37 new feature | BLOCKED | No run yet; official ARM64 16 KiB image installation in progress at slice close |
| New remote CI | BLOCKED | Push/remote PR not authorized; baseline CI does not qualify this revision |
| Physical Fold / battery / latency | BLOCKED | No attached physical device or measurements in this slice |
| Prepared-candidate model quality | FAIL | Unchanged PR1 frozen result; see the PR1 report |
| Immutable model publication / release 0.3 | BLOCKED | Remaining product slices, quality, device and publication gates are open |

The 12 new Binder tests observe the actual `:qa_editor` InputConnection, not
controller internals. They cover composing and pending boundaries, grapheme
delete, external selection/rewrite, dropped/rejected spans with callbacks,
language change, restartInput, view detach, double-space Undo, stationary Space
hold, and NPL counters for seven read APIs plus composing operations. The
sensitive test includes successful plain commits as a positive counter control.

The first run had one failing fixture assertion: `EditText.setText` allowed a
new composing call after the rewrite. That run alone did not establish whether
the session restarted. The corrected fixture mutates the existing Editable,
explicitly removes spans and sends selection; the test now requires the same
InputConnection before verifying session disablement. The full 43-test run
passed with this stricter same-session assertion.

Independent code review found premature Undo invalidation by the legacy
double-space callback. The numeric +1 acknowledgement fix and six regressions
were reviewed again and approved, then verified through the real Binder test.

Local execution logs (ignored developer artifacts) are under
`build/smart-typing-0.3/`: `pr04-jvm.log`, `pr04-gates.log`,
`pr04-all-api36.log`, and `pr04-cursor-start-api36.log`.

## Reproduction and compatibility limits

Run the repository's JDK 17 / Android SDK environment:

```sh
./gradlew testDebugUnitTest --rerun-tasks
./gradlew lint assembleDebug assembleRelease assembleProfile \
  privacyGateRelease privacyGateProfile imeIntelligenceBoundary \
  forbiddenRuntimeDependencies :runtime-llama:nativeSymbolGate \
  assembleDebugAndroidTest
./gradlew :app:connectedDebugAndroidTest
```

No extra editor reads are used to diagnose composing support. A remote Binder
call may hide the editor's boolean result. Missing-span callbacks are handled;
an editor silently discarding spans without callbacks has no universal Smart
Typing guarantee. A false/ambiguous effect is not retried with the same text.
The Android ICU implementation and device timings are not inferred from JVM
fixtures. Host/AVD performance is not physical Fold energy qualification.

PR2/3/5/6/7/8/9/10 remain required. Isolated tokenizer and strip prototypes in
ignored build directories are not counted as implemented product slices.
