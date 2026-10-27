# U8 — multiline navigation, embedded preview and fresh editor transitions

This follows the public panel at 4ddb4a8. A debug-only multiline :qa_editor mode
now exposes three fixed monospace lines and real multiline EditorInfo. The public
panel test types two lines through Rune, moves vertically at a fixed column,
uses Home/End, extends selection across the newline and releases selection before
ordinary movement. All six InputConnection payload-read counters remain zero.
A separate public test restarts the input connection while selection mode is on:
the mode resets and the text remains unchanged. A fresh Activity/editor with the
same package/resource ID does not inherit the previous external-word guard;
qualified teh → the correction works normally in its empty field.

The first actual embedded-preview test reproduced a defect in the preceding
implementation: a manually created InputConnection did not extend the sample's
selection when the preview arrow was activated. PreviewEditor now dispatches the
existing paired navigation protocol directly to its own EditText. Shift events
can update native meta state without being consumed, so their delivery does not
suppress the paired arrow; release still runs through the shared protocol's
finally block. Native context-menu IDs are passed directly to the same sample
view's onTextContextMenuItem. No external editor connection, clipboard read,
IME switch, text ownership adoption or product learning is involved.

The fixed native test operates actual preview key views in SetupActivity. It
checks Shift selection, Cut, explicit test-process Paste, Home/End, Select all and
Copy. The sample remains configured with showSoftInputOnFocus=false. The test
process alone observes/clears the public clipboard sentinel. This preview check
has no remote InputConnection counters; the separate :qa_editor case supplies
that zero-read evidence.

Validation:

- 1,226 JVM tests pass without failures/errors/skips. Boundary, release privacy,
  debug lint and debug/test APK builds pass.
- Ten final Android 36 arm64 scenarios pass: all six public editing-panel cases,
  the new preview case and three existing preview/theme/Unicode/inset regressions.
  The initial two-case run had one passing multiline case and one failing preview
  case; both then passed after the fix. The first ten-case group passed nine
  cases but its new restart case stopped in a legacy helper that waits for Delete,
  which is absent in EDITING. That test now observes the panel itself; its targeted
  rerun passed. Failed evidence is retained separately. The final whole group
  binds the current test APK after this helper correction.
- The ordinary 12,000-row replay is reused by verified identity, not rerun or
  presented as fresh evidence: all 88 compiled source hashes, 18 runtime assets
  and the driver match the public-panel receipt. PreviewEditor and debug/native
  fixture additions are outside that harness. Existing EN precision/volume
  limitations and the ES holdout's one aggregate false change remain.
- The task-owned emulator was stopped and deleted. There were no Fold actions or
  installation, and native accessibility assertions do not prove manual TalkBack.

U8 remains open for WebView/Compose, Fold and manual TalkBack. Framework metadata
is still not universal logical editor identity; the RAM protective flag has no
service-recreation handoff. The fresh transition evidence above is one new
Activity/editor with matching metadata, not every app/editor lifecycle. Adjacent
JSON binds the exact sources, APKs, logs, failed/final runs and replay reuse basis.
