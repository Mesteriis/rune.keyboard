# Protected words, application profiles and confirmed typo learning

Base `8d638a4`, existing isolated branch `codex/morphology-style`. User approved ideas
2, 3, 5 and 6 and explicitly required individual controls and a way to disable everything.

## Implemented behavior

- Protected words: language-scoped NFC/case-folded keys, up to 1,024 words of 48 code points.
  Exact current candidate ID on long press, no automatic tap after consumed long press; separate
  add/remove/reset screen. Automatic word replacements are vetoed independently of personal
  learning. Unreadable protection data blocks automatic word replacement while enabled.
- App profiles: at most 64 observed editor packages, collected only with profiles enabled in an
  eligible editor; no installed-app enumeration. Manual assignment from settings. Default inherits
  main settings. Conversation allows spelling suggestions and disables mechanical/contextual/
  double-space punctuation and finished-phrase review. Formal suppresses private phrase
  continuations and abbreviation suggestions. Profiles never enable globally disabled features
  or learning/collection consent. Missing assignments during load/failure use a restricted fallback.
- Confirmed examples: explicit candidate choices, keep-original, undo/veto and supported dictionary-
  validated manual retypes only. Ordinary typing and non-undo do not label data. Up to 512 deduped
  records; raw words saved only when collection is enabled, never conversation context. Fixed
  hash partition by language + expected word keeps all variants of a target word in one split.
  Holdout never trains, repeated pairs do not accumulate evidence, conflicting labels retract learning.
- Typo patterns: finite single-edit classes (insertion, deletion, substitution, transposition,
  repetition); minimum three different training target words per language/category; bounded bonus
  only reorders the existing dictionary suggestions. Automatic qualification remains unchanged.
- Learning lab: frozen-snapshot evaluation on shipped local lexicons; baseline vs pattern-ranked
  top suggestion, identity preservation, missing candidates and explicit denominators. Separate
  unchanged local-policy match count. Does not evaluate model/touch/exact-pair personalization or
  claim full automatic-edit accuracy. Empty/small samples do not establish improvement.

Four independent settings default off and reject malformed/future-schema enablement. The additional
**disable-all** action clears all 13 optional feature flags in one preference transaction, preserving
saved lists, profile assignments and learning data. Existing primary autocorrection/punctuation
settings remain separately controllable. Disabled app profiles resolve to global settings.

Data uses bounded atomic asynchronous `no_backup` files. Writers verify committed contents before
publishing success; failed reset/recovery cannot resume learning. Learning's 512 KiB file limit covers
its maximum accepted modified-UTF shape (372,744 bytes), tested through serialization and reload.
Protection's separate 512 KiB codec bound is tested with maximum Unicode words and app bindings.

## Diagnostics

Schema 5 preserves schema-4 feature bits and adds `protectedWords`, `appProfiles`, `collectExamples`,
`typoPatterns`; fixed integer `typingProfile` is 0/default, 1/conversation, 2/formal. No package names or
training words are added to metadata. `features` reflects main settings; `effectiveFeatures` reflects
profile restrictions, editor/language/visibility, qualification and resource readiness. Every event,
including fallback editor outcomes, retains flags/profile. Analyzer validates schema-specific exact
vocabularies and profile values, while retaining schema 1–4 compatibility. Existing diagnostic
opt-in/text consent and release no-op recorder boundaries remain enforced.

## Validation

JDK 17, pinned repository toolchain; Android API 37 emulator only.

- `:app:testDebugUnitTest`: 933 tests, zero failures/errors/skips.
- Diagnostic analyzer/boundary/packaging Python suite: 56 tests, PASS.
- Android filtered integration: 21 tests, zero failures/errors/skips; covers ten individual controls,
  disable-all preservation, protected automatic veto/storage, profile manager, actual IME profile
  behavior, shipped-lexicon holdout evaluation, learning screen recreation, candidate long press and
  existing candidate touch/accessibility paths.
- `:app:lintDebug`, `:app:assembleDebug`, `:app:imeIntelligenceBoundary`,
  `:app:forbiddenRuntimeDependencies`, `:app:privacyGateRelease`: PASS.
- Debug/release diagnostic pre-R8 and mapped-DEX packaging checks: PASS.
- `git diff --check`: PASS.
- Learning task review and final integration review completed; findings fixed with regressions.
  Final profile verification includes global double-space enabled, Conversation suppressing it,
  and disabling all extras restoring the existing global behavior.

Raw logs, reviews and verification JSON/APK are retained in ignored `build/typing-controls/`.
Initial integration rejected wildcard production imports; imports were made explicit without
weakening the source boundary. Review found and fixed a maximum Unicode persistence budget,
reset readiness/UI lifecycle and independent double-space profile interaction.

## Limits

No private Telegram archive was reread or uploaded. No automatic corpus labels or neural fine-tuning
were introduced. Manual retypes require an available validating dictionary; ambiguous/multiple edits
abstain. Benchmark scope is local suggestions on collected normalized examples, not new measured
accuracy on the user's unseen conversations or latency/battery on their phone. No physical device
was modified. The installable deliverable is a debug APK; release remains unsigned without its key.
