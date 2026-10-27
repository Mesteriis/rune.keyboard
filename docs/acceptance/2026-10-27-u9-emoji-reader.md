# U9 — catalog reader and lazy palette state (partial)

The packaged catalog now has a Kotlin reader, preserving all 1,898 full sequences,
nine groups and EN/RU/ES names. It bounds input to 320,000 bytes, requires strict
UTF-8/schema/rows, rejects duplicate groups/sequences, unknown groups, missing
names and control characters, and closes its input on success or failure.
Provenance is still checked by the existing build-time pinned-source gate.

EmojiPalette owns lazy state intended for one keyboard view: constructing it and
reading empty recents does not load data or query a font. Opening a category
checks only its entries and caches supported and unsupported results. Committed
recents are deduplicated, capped at 32, returned as snapshots and isolated between
instances. They have no disk or process-global storage. Actual Paint.hasGlyph and
the editor's successful-commit callback must be supplied by the future panel.

Validation (all commands offline, exact commands/exit codes and source/log hashes
in the adjacent evidence JSON):

- Targeted EmojiCatalogTest: nine tests, zero failures/errors/skips. Covers the
  actual packaged catalog, exact ZWJ/flag/variation/keycap/tag strings, malformed
  data and UTF-8, bounded input/stream closing, lazy loading, cached negative font
  results and bounded/deduplicated/instance-local recents.
- Full app JVM suite: 1,239 tests, zero failures/errors/skips.
- Fifteen emoji generator/source tests pass through emojiCatalogTests.
- imeIntelligenceBoundary, privacyGateRelease, lintDebug, assembleDebug and
  assembleDebugAndroidTest pass; the combined Gradle process exits zero.
- No existing typing/controller/model source or scoring asset changed. Ordinary
  replay was not rerun; these new classes have no production caller yet.

U9 remains open: GridView/adapter, real font filtering, entry/settings/policies,
editor context/revision isolation, successful-commit wiring, native insertion and
deletion, accessibility and startup/opening measurements, API 26 and Fold checks.
This slice does not change the visible keyboard. No device test or phone update
was performed. The preceding phone probe failed with TRANSPORT_FAILURE; that is
not evidence of phone runtime behavior.
