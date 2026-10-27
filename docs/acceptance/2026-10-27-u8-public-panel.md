# U8 — public editing panel (partial acceptance)

Rune now exposes EDITING through the single Edit alternate on a long press of
?123. Its ordinary tap still opens Symbols. The panel provides horizontal arrows,
Home/End, a checked selection toggle and native Select all / Copy / Cut / Paste.
Vertical arrows are rendered only for multiline editors. Raw TYPE_NULL editors
hide context-menu commands; password editors have no entry. EN/RU/ES key labels
and accessibility names are provided. Arrows repeat every 75 ms after the platform
long-press threshold and stop on gesture cancellation; Delete retains its own
existing acceleration schedule.

Service entry and editor-resolved commands finish/disown the current Rune span,
invalidate candidates and arm the external-word boundary guard before dispatch.
Navigation, Cut and Paste await actual editor selection; dispatch acknowledgement
is not completion feedback. Until Rune inserts its own whitespace, adjacent text
stays literal with no composing ownership or correction context. Returning to
letters preserves either this guard or an already established Rune boundary.

A RAM-only continuity helper retains the protective flag across a framework
restart with matching package/fieldId. It never carries text, composing ownership
or learned context. Fresh starts and changed metadata clear it; a disabled
controller cannot acknowledge a boundary. These IDs are not universal logical
editor identity, and service recreation does not transfer this flag. Selection
mode itself resets on restart, text entry, language change and panel exit.

Privacy/setup copies now explain that the keyboard does not read clipboard
contents: the editor performs native context-menu operations. No clipboard store,
IME clipboard read or text-read fallback was introduced. The preview routes the
new commands to its own editor connection; its interactive acceptance is pending.

Verified locally:

- All 1,226 JVM tests pass, no failures/errors/skips; reducer, layout, restart flag
  and restored controller-boundary regressions are included. IME/scoring boundary,
  release privacy, debug lint and debug/test APK builds pass.
- Twelve distinct Android 36 arm64 scenarios pass in bounded groups: four public
  panel cases plus the eight executor/prototype/guard controls. Public tests use
  actual Rune key actions and the remote :qa_editor connection. They prove native
  Shift selection and Cut, following caret insertion, explicit test-process Paste,
  framework input restart, literal adjacent suffix and correction recovery after
  Rune Space, native checkable state, popup touch release, repeated arrow cancel,
  Home/End and single-line/raw/password presentation. Six payload-read counters
  remain zero. Native accessibility nodes are not a manual TalkBack check.
- The first Cut test failed because debug numeric status remained at the pre-cut
  length/selection although the actual field was already abc. A bounded second
  probe recorded that stale state. The fixture now posts its existing numeric
  publisher on context-menu dispatch without inventing an IME selection callback.
  Final coverage additionally types z and verifies abcz, proving the actual caret.
  Both failures are retained in the adjacent evidence, not counted as passes.
- A fresh current-source 12,000-row ordinary replay exactly matches archived
  baseline observations after excluding only hostStageNanos/fullTokenGenerationNanos.
  All 88 baseline source hashes were verified against commit 9c62573, not claimed
  as a pre-edit worktree check. All 18 current runtime asset hashes are unchanged.
  Projection hashing uses canonical JSON lines; both hashes match. Metrics match,
  with zero new aggregate false changes. Existing EN precision/volume failures
  and the ES holdout's one aggregate false change remain. The ordinary harness
  does not exercise panel entry; its separate native/JVM coverage is above.
- The isolated task emulator was stopped and deleted. No physical Fold actions,
  installation, owner clipboard acquisition or downloaded-model scoring occurred.

U8 remains open for actual multiline navigation, preview, fresh editor transitions,
WebView/Compose, Fold and manual TalkBack acceptance. This receipt closes only the
public EditText panel slice, not the U8 card or the complete review. Exact sources,
APK/result/log hashes, failed probes, replay bindings and cleanup are in the
adjacent JSON.
