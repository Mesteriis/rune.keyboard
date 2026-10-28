# Q4 — explicit numeric debug export and Fold integration

Source commit: `9875aee`. The debug log manager now links to a private quality
export screen. Its Save action captures ready numeric state and opens the real
Android document picker. The suggested `rune-quality.txt` contains the existing
`RUNE_QUALITY_3` header and 81 decimal counters, bounded to 2,048 bytes. No input,
word hashes, candidates, editor identifiers or timestamps enter this payload.
Collection may be off while the user explicitly exports retained numeric history.

The repository issues a word-free snapshot permission; reset immediately revokes
old permissions, including while a document picker is open. Storage loading,
resetting or failure prevents capture, and another store cannot authorize it.
The debug UI owns URIs, output streams and its worker. Payload validation and
lifecycle/reset checks precede sink opening and writing. Closing the screen
cancels queued work; errors close streams and report failure without retries.
Cancellation cannot retract bytes already handed to a provider. Empty/partial
files can remain after failure, and local reset cannot delete exported copies.

Only the debug manifest declares the activity, private and without filters.
The existing packaging gate now also checks the export activity and worker,
including nested classes and aliases, in manifests, pre-R8 inventory and mapped
final DEX. Production numeric dashboards retain their existing behavior. No
ranking, admission, model asset, native runtime or 250 ms window changed.

## Actual checks

- **1,343 JVM tests**, zero failures/errors/skips; 44 quality tests. Regression
  coverage includes ready/foreign/reset/failed snapshot permissions, stopping
  collection without erasing history, bounded numeric output, duplicate/closed
  export, provider failures, invalid payload, reset/close during provider open
  and executor rejection.
- **12 packaging fixture tests**, including release/profile negative cases for
  pre-R8 and mapped DEX leakage, manifest components and aliases, and debug
  private/filter-free registration. Debug lint and profile privacy/R8 gates pass.
- **Five actual API 26 methods**, zero failures/skips, on one exact final APK pair.
  Existing real correction/Undo/Original, dashboard reset, actual AtomicFile v3
  storage and EN/RU resource tests pass. The new real SAF test cancels a picker,
  verifies unchanged counters, saves through the system Downloads provider,
  decodes the actual file and compares it exactly with the captured snapshot,
  recreates the screen and removes only its synthetic document. No owner profile
  was imported into this disposable emulator; it was stopped and its AVD deleted.
- The earlier **15,288-row** non-timing replay is reused explicitly: all 90
  selected core sources, 69 assets and prior observation hashes were rechecked
  unchanged. This slice does not claim another freshly executed replay or native
  inference/timing qualification.
- Clean committed-source **`:app:privacyGateRelease :app:apkFootprint`** passes.
  The unsigned release APK is **180,101,101 bytes**. This is a local clean-checkout
  result, not independent F-Droid build-server acceptance.

Failed raw attempts remain private evidence. An initial Gradle invocation named
an unavailable profile footprint task. SAF fixture repairs addressed API 26
UiObject2 Save delivery, a guessed alternate provider URI without its grant, and
an unsupported shell builtin in UiAutomation. The final fixture uses platform
input at live system-button bounds and reads the actual synthetic public file;
it still requires real success, exact decoded bytes and cleanup. Production
export code did not change during these fixture repairs. No failed attempt was
counted as a pass.

## Owner Fold

Both coordinating chats explicitly released an exclusive window. The exact
emulator-tested debug APK and tests were installed through ADB with the existing
certificate, no uninstall or data clear, and a private pre-update backup. The
installed main APK was read back and its complete SHA-256 verified. Every
packaged asset and native library matches the previous owner installation.

All **four physical tests / 15 matching cases** pass, without skips, covering two
paces, exact Undo, extra empty-field Backspaces, preserved following words and
rapid short-word correction. Four private journals were retrieved. Keyboard
preferences match both the pre-install and pre-test state; secure IME settings,
inspected protected stores and the existing optional model store are unchanged.
Both chats were told the window was released; no phone commands remain queued.
Synthetic physical fixtures temporarily disable numeric collection and restore
preferences; they do not reset owner statistics. Numeric recorder/export checks
ran on the owned emulator.

The implementation, release checks and owner installation are verified. **Q4
remains open for two actual weeks of ordinary owner use and its acceptance
report.** Installation and synthetic tests do not establish that observation
period or source correctness. Sources with fewer than 100 applications still
show insufficient data; the observed Undo fraction never labels correctness.

Machine-readable artifact/check bindings:
[debug export evidence](2026-10-28-q4-debug-export-evidence.json).
The owner’s 13 pre-existing tracked edits and 98 original untracked paths were
preserved. No push or public release was performed.
