# Q3 — Fold update and clean-source release checks

The diagnostics integration at `92eb542` is installed on the owner's Samsung
SM-F966B (API 37) through explicit-transport ADB. AURA and Android MCP confirmed
an exclusive window beforehand and received release messages after collection.
No Android MCP phone commands were used.

The installed debug APK is byte-identical to the successful API 26 diagnostics
UI artifact recorded in the schema9-integration receipt. Its signing certificate
matches the previously installed Rune; all packaged assets and native libraries
match the preceding installation byte-for-byte. Installation used `adb install
-r`, with private state backup and no uninstall or data clear. The installed APK
was read back and its complete digest verified. Version remains 0.4.2/code 8.

Four actual physical instrumentation methods pass, with no failures or skips:
fresh reviewed corrections at two paces, excess Backspace in an empty field,
preview/Undo with continued input, and rapid short-word correction at three
paces. All 15 scripted public cases report an exact match. These checks cover
known phrase/short-word regressions, first-letter retention and subsequent-word
preservation; they do not establish general correction accuracy.

After testing, keyboard preferences and the inspected three secure IME settings
match their saved values. The inspected personal/control/learning roots retain
their exact file contents and optional model-delivery files retain their hashes.
The device contained one file in the inspected non-diagnostics state roots;
empty or absent stores are not represented as populated fixtures. The updater
also backed up the prior diagnostics state; append-only diagnostics naturally
change during testing. Raw backups, settings, logs and four journal snapshots
remain private, outside Git.

The current analyzer accepts all four text snapshots, including retained schema
8 rows from before installation. New schema 9 rows in all eight text/metadata
streams contain bounded integer editor types (the synthetic plain-text editor
has type 1). An initial assertion incorrectly assumed every retained row would
be schema 9; inspection showed preserved historical schema 8 text. Validation
was corrected to require editor metadata only for schema 9 while retaining
historical analyzer compatibility. Snapshots overlap; their row totals are not
counts of distinct events or an accuracy measure.

A separate clean checkout at `92eb542` passes `:app:privacyGateRelease` and
`:app:apkFootprint` (exit 0). Its unsigned release APK is 180,096,157 bytes.
This is a local committed-source release/privacy/size check, not independent
F-Droid build-server evidence, source-export acceptance or a public release.
No push, tag, model weights or admission thresholds changed.

The adjacent evidence binds the actual APKs, outputs and private journal archive.
Q3 remains open for the Android adapter's combined resource-readiness refusals
and their direct unavailable-resource regressions; Q1's distribution acceptance
and the complete review also remain open.
