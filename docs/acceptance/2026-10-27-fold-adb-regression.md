# Fold regression through ADB

The owner explicitly selected ADB for phone operations. AURA and the Android MCP
chat acknowledged an exclusive Rune window and were both notified when it ended.
No Android MCP phone command was used in this run.

The physical Samsung SM-F966B (API 37) received the existing debug 0.4.2/code 8
APK with `adb install -r`. Its certificate matched the previously installed app;
the installed APK bytes matched the candidate. App data was backed up privately
before replacement. No uninstall, data clear or permission grant was performed.

Four existing physical-only instrumentation tests passed, with zero failures or
skips and 15 reported public cases:

- `freshReviewedCorrectionsAtTwoPacesWithExactUndo`: eight cases at 50/100 ms.
  `я уже ддмой ` becomes `я уже домой ` and `сейчас всее ` becomes `сейчас все `;
  already-correct words remain unchanged. Backspace restores the original typo.
- `extraBackspacesInEmptyFieldKeepTheWholeNextWord`: two cases, with and without
  erasing a preceding owned word. Extra Backspaces preserve the whole next
  `зочу`; Space corrects it to `хочу ` and Backspace restores `зочу`.
- `correctionPreviewAndUndoPreserveNextWord`: visible Undo restores `ссын до`
  after beginning the next word; a separate `зочу` correction also undoes exactly.
- `rapidShortWordCorrectionAtThreePacesKeepsFollowingWords`: `ссын идет домой `
  becomes `сын идет домой ` at 50/100/150 ms pauses.

These are actual touch events against Rune's QA editor and remote
InputConnection. Each case asserts zero for all six editor-payload read counters.
Synthetic personal feedback was temporarily disabled. All keyboard preference
entries and three secure IME settings were restored. The inspected known personal
store paths had the same contents before and after; one persisted file existed.
Four diagnostic journal snapshots were retrieved into ignored private storage.
Diagnostic consent was unchanged. No phone command remains active or queued.

The adjacent JSON binds the installed artifacts, test sources and results. Raw
backups, settings, logs, device connection details and journals remain private in
the ignored build directory. The candidate remains installed on Fold.

This is a debug regression slice using existing public phrases. It establishes
neither fresh quality qualification nor release/downloaded-model acceptance.
U1 still needs its other physical source paths; U8/U9 display, lifecycle,
accessibility and performance checks and the remaining original review criteria
stay open. No new autocorrection defect was observed in this slice, so no ranking
or admission policy was changed.
