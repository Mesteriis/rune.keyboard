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

## 2026-11-23 TalkBack menu, editing and Emoji

TalkBack 17.0.0.889642762 was bound with touch exploration enabled on a
disposable API 37 ARM64 emulator. Touch events entered through the virtual
touchscreen over ADB. The passive `UiAutomation` observer kept services active
with `FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES`. It logged focus and text
changes in the synthetic QA editor and issued no accessibility actions.

- **U8 editing.** On `9aacdb65`, the focused Symbols key exposed a custom
  keyboard switch and voice action. TalkBack's Actions menu omitted the labeled
  standard long-click for Edit. A dedicated Edit action now appears in the
  menu, with the existing tap and long-press behavior preserved. Selecting it
  opened the real editing layer. Seeding a selection and double-tapping
  Copy, Line end and Paste produced exactly `beforeSELECTEDafterSELECTED` in
  the editor.
- **U9 Emoji.** Double taps opened Symbols and then Emoji. Focus events named
  Recent emoji, Smileys & Emotion, People & Body and waving hand. Activating
  People & Body set its selected state. Activating waving hand inserted `👋`,
  Delete removed the entire glyph, and Recent emoji still exposed the named
  entry. The ABC key returned to the letter layout.
- **U15 IME switching.** With the emulator voice IME enabled, TalkBack showed
  Next keyboard and Voice input in Actions. Activating Next keyboard changed
  the registered current IME from Rune to Gboard. After disabling the voice
  IME, the Rune key offered Next keyboard and its existing editing alternate,
  and omitted Voice input. The screen-reader probe did not start recording.

The patched build passed debug lint and 12 instrumentation methods on each
of API 26 and API 37. They cover eight key-view methods, public editing,
raw and password controls, and two public/private Emoji methods. The added
editing-action assertions check its label, dispatch, and rejection when the
key is disabled or offers no Edit alternate. The ordinary instrumentation ran
without TalkBack. Actual touch exploration and menu activation ran on API 37.
Sequential TalkBack navigation on the letter layout moved focus `Q → W → E → W`
with forward, forward and backward swipes. Sequential navigation within the
Emoji panel remains unverified. The clean patched checkout passed
`:app:privacyGateRelease`.

This checks an ordinary synthetic editor and its on-screen keyboard. The
audio output, physical Fold displays and their TalkBack flows remain open.

## Editing selection and sequential Emoji traversal with TalkBack

The API 37 ARM64 emulator ran candidate `687361c8` with TalkBack
17.0.0.889642762. The observer kept TalkBack active. All actions used
virtual touchscreen gestures sent through ADB.

For U8, the run typed `abcd` and opened **Edit** through the focused
Symbols key's TalkBack Actions menu. **Selection off** reported a
checkable, unchecked control. Activating it made **Selection on**
checked. **Move left** produced numeric selection endpoints 4 and 3.
**Cut** changed the editor to `abc`; **Paste** restored `abcd` at the
same caret. The receiver reported zero text-before, text-after,
selected-text, extracted-text, surrounding-text and snapshot calls
through this flow.

For U9, a forward swipe from **grinning face** moved through the eight
distinct cells in the first row, then moved to **slightly smiling face**
at the start of the second row. Eight backward swipes retraced the
same bounds and accessibility labels. Double-tapping the first cell
inserted the complete glyph. After disconnecting the observer, an
independent hierarchy dump read the exact editor value `abcd😀`.

The APK SHA-256 was
`6b31bee517d2a99427a417e1fd22894abb01876e759d387dd643add23b0bf28d`.
The event trace SHA-256 was
`4bdc0c939b34784aaeda7c7b6a4758d4310d119a7185b4d115d1d4aa6dbdd7af`.
The isolated guest, clipboard, observer and temporary records were
removed. Physical Fold acceptance and the remaining U9 device budgets
remain open.
