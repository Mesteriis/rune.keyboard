# U9 — pinned emoji catalog and offline generator (partial)

The review's emoji panel now has a durable data foundation: Emoji 15.1 and CLDR
44.1, with eight complete original source members preserved in a deterministic
4,269,918-byte ZIP_STORED archive. CLDR release 44.1.0 resolves to commit
e0981e5ad4dae80cf95729035e4c326a850ce429; immutable commit URLs were checked against
the captured release bytes. Per-member sizes/hashes, fixed URLs and archive
identity are tracked. No source depends on ignored build output or a live fetch.

The generated catalog contains 1,898 fully-qualified sequences in nine source
categories. It preserves Unicode/CLDR order, ZWJ, flags/tag sequences and variation
selectors. 1,875 skin-tone entries and non-fully-qualified/component rows are
excluded; tone selection is a later stage. Each entry has EN/RU/ES CLDR tts names,
with exact lookup or removal of U+FE0F only and no cross-language fallback.
Small category captions are authored by Rune, explicitly distinguished from
upstream item names. Unicode License V3 and Emoji copyright are packaged and
listed in THIRD_PARTY_NOTICES.md.

The TSV is 142,268 bytes against a 320,000-byte limit. A manifest binds it, its
license, generator, categories and original sources. Generation is offline and
validates everything before writing known files atomically per file. Explicit
source restoration downloads only pinned HTTPS objects, refuses changed bytes,
and reproduces the full archive identity; an existing archive is verified without
network access. The CLI never updates source pins.

Gradle preBuild now depends on emojiCatalogCheck; the standard check task includes
emojiCatalogTests. Neither a build nor keyboard startup fetches this data.

Validation:

- Fifteen source/generator tests pass without skips, covering exact source-archive
  reconstruction, deterministic offline output, three-language coverage, sequence
  preservation, absent RU refusal, source/member mutation, unexpected members,
  duplicate JSON/rows, version/category drift, invalid labels, size budget and
  refusal without modifying existing outputs. A clean relocated copy reproduces
  the assets without any build/ directory.
- An initial expected RU label was wrong in the test: pinned CLDR uses
  «широко улыбается». The test was corrected against the original source;
  generator/data bytes were not changed. Its failed 15-test/one-failure log is
  retained. The initial shell appended cat, so its unittest child exit was not
  retained; it is explicitly not a pass. Subsequent wrappers preserve exit codes.
- A fresh restore from pinned network sources reproduces the checked-in archive
  SHA byte for byte. Adding one byte to the packaged TSV makes preBuild fail
  specifically at emojiCatalogCheck. The byte is restored in finally and its
  exact original SHA is verified before positive builds.
- All 1,230 JVM tests, source tests through Gradle, IME/scoring boundary, release
  privacy, debug lint and debug/test APK builds pass. Debug/release APK entries
  match all three generated files exactly. Their total compressed payload is
  52,061 bytes in debug and 45,365 in release; these are payload sizes, not claims
  about total APK delta or native-library size.
- No typing/runtime Kotlin code, scoring asset or source in the ordinary replay
  changed. Its prior 88-source/18-asset/driver identities are verified for reuse;
  no new replay or quality qualification is claimed. Existing EN precision/volume
  limitations and ES holdout aggregate false change remain.

U9 is not implemented end to end. Remaining work: framework GridView/adapter,
entry/options/policies, lazy Paint.hasGlyph cache, RAM recents, context/revision
boundary handling, insertion/deletion and accessibility instrumentation, first-open/
startup budgets, old API 26 font and Fold dimensions. There was no device run or
phone update in this data-only slice. The adjacent JSON binds exact sources,
archive/assets, tests, negative gate, restore and packaged bytes.
