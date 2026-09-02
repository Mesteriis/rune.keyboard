# Independent settings consumer/UI review

Verdict: **CHANGES REQUESTED for one P2 in a new Android test expectation.** No material defect found in the scoped production consumer/UI changes. Source approval does not establish runtime geometry safety; API26/API37 gates remain required after the test correction.

Reviewed patch SHA-256 `bf92fda0c35d70513696392cbdf68d79ee7a9696c1aaa11e11df6b9666384681` against the approved design and implementation brief. All eleven before/overlay identities matched `source-identities.json`; the patch exactly reconstructs those changes, and existing root source bytes matched `before/` at review time.

## P2 — preserve the established single-space double-space Undo expectation

Location: `overlay/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/SmartTypingSettingsInstrumentedTest.kt:158`, in `spellingAndStripChangesPreserveMechanicalUndoAndIndependentDoubleSpace`.

After `hello. ` the test deletes once and expects `hello  ` with two spaces. Current double-space Undo restores the first pending single space. `MechanicalPunctuationPlanner.kt:29–35` deliberately supplies the previous composing suffix as the Undo value; existing `SmartTypingComposingInstrumentedTest.kt:206–214` checks `a. ` → Delete → `a ` and continued `a b`. Thus the new test would reject the established correct behavior and block the proposed device gate.

This was first identified by the parent and independently confirmed against the actual planner/controller seam and existing Binder regression. Change only the new expected value to `hello ` (one trailing space). Keep the independence, transformed output and readback assertions. Do not change production Undo to satisfy this mistaken two-space expectation. No additional algorithm or persistence change is needed.

## Production spec and quality assessment

`CandidateOwnerState` separates base eligibility, spelling policy and strip presentation. `canRequestSpelling` is the conjunction required for the current manual-only consumer. OFF + visible strip projects only the current composing Original with a selected ID belonging to that filtered list; hidden strip admits no spelling request. Suggestions and High confidence share manual dictionary behavior and grant no automatic edit authority. Base editor/view/layer/selection protection continues to override every mode/strip combination.

Selection resolves the requested ID against the current filtered view before preserving the controller allowlist for the actual tap. Correction cannot bypass OFF or hidden policy. OFF Original uses the non-restoring `selectOriginal` path; if a caller omitted invalidation after an earlier manual replacement, rejection without mutation is intentional and safe. The actual service does invalidate on mode/strip changes, so its displayed current Original is usable and cannot restore discarded pre-correction spelling.

Service changes are limited to cached owner fields and candidate invalidation on actual mode/strip differences. Invalidation cancels pending worker/load demand, advances candidate epochs and clears reply/selection metadata without an editor command or mechanical Undo reset. Mechanical/double-space changes retain their separate existing Undo invalidation. Contextual mode neither enables spelling nor requests model work. The existing visual/language/candidate-only renderer classification is preserved, including simultaneous visual updates; repeated equivalent decoded settings do not acquire a key rebuild path.

Requests still originate only after accepted explicit composing edits. Reply delivery rechecks live work eligibility and ownership. Settings writes, view projection, Ready changes and Activity reopening do not submit a word, recreate a worker or bind a model. No new editor readback, model observer, on-key settings read, schema, dependency or weighted-prototype coupling was introduced.

The four new controls use existing framework helpers and preference writers; double-space appears once in Smart Typing and preview remains in Typing. Optional summaries preserve the selected label. Both EN/RU resources accurately explain the manual-only High confidence behavior, saved-but-unavailable contextual Suggestions and independent mechanical punctuation. Stored future intent is retained. Existing explicit Local intelligence navigation is unchanged and is not invoked by a setting or readiness event.

## Tests and evidence limits

Read the saved red control: 26 tests ran with five failures in missing policy gating/publication/selection/admission behavior. Read the final host log: **26/26 PASS**, including eight added methods. The new tests use actual controlled route/reader/worker execution, cancellation latches, queued delivery, editor-command counters and controller state. They cover the six mode×strip rows, blocked and late replies, stale IDs, enable/Ready/render without work, next-edit admission, OFF Original after manual correction, policy-filtered taps, preserved mechanical Undo and base ownership gates.

Saved source/resource checks all end in `EXIT 0`: coordinator/JVM compile, host tests, AAPT2 compile/link, generated R.java compile, proposed service/UI/affected instrumentation source compile and isolated patch dry-run. These records support compilation and focused JVM behavior only. The reviewer did not rerun them.

The new Android source tests exercise actual settings rows/dialogs, persisted independent values, effective summaries, live OFF/enable behavior and a Correction held through disabling. The latter retains its original physical release coordinates and asserts no compose/commit or field change. `CandidateCell.bind` immediately cancels a changed/removed item; final coordinator ID/policy checks also reject a stale callback.

The key tests retain the original DOWN coordinates for UP, exercise strip on→off, off→on and repeated toggles, assert no early character, exactly one expected released character, and compare actual keyboard/key object identities before and after the final queue drain. CANCEL and private-editor transitions have separate assertions against resurfacing old content. The extracted test-only inspector preserves the existing API29 public/older reflection branches, main-thread inspection and test-thread exception propagation; identity failures do not format `View.toString`. The shared fixture writes all five schema-3 fields and explicitly enables Suggestions/strip for existing live tests. Full raw preference restoration and failure-artifact opt-out remain intact; six readback counters are checked without claiming zero NORMAL caps lookup.

Immediate VISIBLE/GONE strip geometry remains unchanged. The authored UP/CANCEL tests must actually pass on the target runtimes before claiming safety; object identity or source compilation alone cannot prove coordinate stability. The twelve affected Android scenarios (six settings, three existing live, three existing mechanical) are still unrun in the supplied evidence. Any observed geometry failure should retain its diagnostic evidence and receive the smallest separately reviewed correction, without weakening these assertions.

Scope of this review: source/evidence inspection and read-only identity/diff arithmetic. No tests, Gradle, devices, model/corpus work or production edits were performed; only this review file was written. Physical Fold, automatic-correction quality, resource/battery behavior and production release remain separate gates.
