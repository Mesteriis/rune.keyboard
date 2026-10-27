# Offline emoji catalog

This is the data foundation for the review's U9 panel, with a Kotlin reader and
lazy palette state connected to a framework GridView. The optional letters-row
key is an Appearance preference, off by default; Symbols always retains its entry
in allowed editors. Full performance/device acceptance remains outstanding.

The palette contains 1,898 fully-qualified Emoji 15.1 sequences in nine Unicode
source groups, retaining source/CLDR order. Skin-tone variants (1,875 entries) and
non-fully-qualified/component rows are excluded. Tone selection is a later UI
stage. Item accessibility names come from CLDR 44.1 tts in EN/RU/ES, with no
cross-language fallback. Lookup uses the exact glyph key or removes U+FE0F only.
Category captions are authored by Rune, explicitly separated from CLDR item names.

The checked-in source archive is deterministic ZIP_STORED with fixed timestamps,
permissions and member order. All eight raw members have individual size/SHA pins.
CLDR release tag 44.1.0 was resolved to commit
`e0981e5ad4dae80cf95729035e4c326a850ce429`; the immutable commit URLs were checked
against captured release bytes. Emoji data uses its versioned Unicode URL.
The source archive and manifest survive deletion of build/; generation is offline.
No user data, model training data, images or downloaded runtime are involved.

```sh
python3 tools/emoji/generate_catalog.py
python3 tools/emoji/generate_catalog.py --check
python3 -m unittest discover -s tools/emoji -p 'test_*.py' -v
```

`--check` writes nothing. Other generation validates every input before publishing
known output files atomically per file. It rejects missing locale names, changed
source/member identities, invalid glyphs, duplicate rows/JSON keys, category drift
and control characters. The catalog has a 320,000-byte budget (currently 142,268).
The Gradle `:app:emojiCatalogCheck` runs before preBuild for every variant;
`:app:emojiCatalogTests` joins the standard check task.
This adds no network operation to a build or to keyboard startup.

`ime/emoji/EmojiCatalog.kt` reads this schema with strict UTF-8 and a bounded
320,000-byte input, preserving complete glyph strings and all three names. It
closes the supplied stream on success and failure. Duplicate/unknown groups,
duplicate sequences, missing names, control characters and malformed rows refuse
the whole catalog. A single delimiter/control scan reuses six field-offset pairs;
whole-file line lists, per-row split lists and repeated blank scans are avoided.
ISO controls and Unicode whitespace are covered independently in JVM regression
tests, and every parsed field is compared with the original packaged TSV.
Every row is validated before returning the catalog. Entry objects and their three
localized name strings are created on the first access to that category, once,
with synchronized publication; reading category counts does not materialize them.
The shared decoded TSV and category offsets remain reachable while a category is
unopened. This changes allocation timing, with no measured PSS claim. A successful
recent-commit lookup still scans categories in source order and can materialize
preceding groups; category-switch/commit latency remains to be profiled.
Build-time source/hash verification remains the provenance
gate; the reader is not a substitute for it.

`EmojiPalette` provides view-owned lazy catalog state for the future GridView.
Font checks use the panel's Paint.hasGlyph, limited to the selected category and cached including
unsupported results. Recent committed entries are deduplicated, capped at 32 and
kept only in that palette instance's RAM. The service records a recent only after
an accepted editor commit. Incognito hides and does not add recents. Native font
support is verified on the pinned API 26 emulator (1,545 accepted and 353 hidden
entries), across all nine categories and three languages. The 50 ms preview
opening budget failed its first sample on a clean AVD; opening/startup/PSS and
physical Fold acceptance remain open. See the u9-emoji-api26 acceptance receipt.

The parser follow-up adds constant Rune#emojiConstruct, Rune#emojiCatalogRead,
Rune#emojiTabs and Rune#emojiGlyphFilter trace labels without user content.
Profiling identifies catalog load/parse as the largest measured phase. The
optimized parser's three-clean-AVD preview series still has one late first open;
the 50 ms gate remains failed. See the u9-emoji-parser acceptance receipt for
all samples, scope and unchanged ordinary replay identities.
The deferred-name follow-up retains full upfront validation. Its three-clean-AVD
series has all 12 handlers below 50 ms, but four draw-start observations above it;
there is no demonstrated opening-speed improvement or passed performance gate.
See the u9-emoji-deferred receipt for all samples and scheduler-profile limits.

To restore a missing archive from its exact pins, or verify a restored copy:

```sh
python3 tools/emoji/fetch_sources.py
python3 tools/emoji/fetch_sources.py --output /tmp/rune-emoji-sources.zip
```

Existing archives are verified without network access. Missing ones fetch only
the fixed HTTPS sources, check every member, reproduce the complete archive SHA,
and then write. A mismatch refuses publication; pins are never updated by a fetch.

Packaged files in app/src/main/assets/emoji:

- catalog-v1.tsv: UTF-8, LF; header `# rune-emoji-catalog-v1`; six columns per row.
  G rows contain group ID, icon, EN/RU/ES captions; E rows contain group ID, glyph,
  EN/RU/ES item names. Tabs/newlines in names are forbidden. Glyph bytes, including
  ZWJ, flag/tag sequences and variation selectors, are preserved.
- catalog-manifest.json: versions, counts, derivation/source/generator/category
  hashes and hashes of the catalog and license. No timestamps or local paths.
- LICENSE.txt: upstream Unicode License V3 and the Emoji data copyright notice.

Sources: [Emoji 15.1](https://www.unicode.org/Public/emoji/15.1/emoji-test.txt),
[CLDR release](https://github.com/unicode-org/cldr-json/tree/44.1.0),
[pinned source manifest](source-manifest.json).
