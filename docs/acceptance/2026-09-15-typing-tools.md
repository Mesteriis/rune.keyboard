# Six optional typing tools

Base: `c6543e2`, branch `codex/morphology-style`. User approved all six tools and
required independent settings plus diagnostic enabled/disabled state.

## Delivered behavior

1. Local quality dashboard: bounded numeric counts for acknowledged automatic edits,
   explicit correction/original/tool choices and actual undo, plus six response-time buckets.
   Atomic worker persistence in `no_backup`; explicit reset and storage status.
2. Shadow comparison: current qualified automatic decision versus the first visible spelling
   alternative after enabled personalization. No experimental text mutation. Only exact explicit
   choices, immediate undo or backed completed retypes label a comparison. Same-revision model
   refresh replaces the pending aggregate contribution without double counting; stale ownership
   clears pending text. Disabled shadow mode skips ranking/guard work for comparison.
3. Russian split/join proposals: bounded dictionary queries and explicit exceptions; ambiguity,
   unknown dictionary state and protected boundaries abstain.
4. User abbreviations: language-scoped normalized keys, bounded validated expansions, manual
   candidate insertion. Separate add/edit/delete/reset screen; atomic no-backup storage.
5. Finished-phrase review: bounded Russian pronoun/verb agreement and supported comma rules
   after terminal punctuation. Manual proposals only, no general grammar or style rewrite.
6. Visible word-autocorrection undo: exact owned edit, eight-second limit, invalidated by further
   changes; existing Backspace undo remains available independently.

All six settings default off, persist independently, and fail closed on malformed/future settings.
Manual tools need the candidate strip, an eligible editor and the current Rune-owned suffix.
No surrounding-editor readback is added. Sensitive/no-learning fields, stale IDs and failed
transactions remain excluded. Disabling retains saved data; reset deletes it.

## Diagnostic contract

Schema 4 adds fixed Boolean dictionaries `features` (configured) and `effectiveFeatures`
(current availability) to each recorded event, including ordinary/fallback editor outcomes.
Fourteen fixed names cover existing spelling/punctuation/personalization and all six new toggles.
Effective flags are a subset of configured flags and account for editor/layer/selection,
visibility, supported language, resource readiness, runtime qualification and model readiness.
Candidate confidence and exact ownership still decide individual proposals/replacements.

A CONFIGURATION event records changes; session events carry the same flags. Existing diagnostic
opt-in/text consent and debug-only recording remain. Final variants retain only the exact
content-free shared contract, fixed flag vocabulary and no-op providers. Source and pre-R8/mapped
DEX inventories were extended by exact names/mapping, with negative fixtures; no wildcard bypass.
The analyzer remains compatible with schemas 1–3 and reports `featureConfigurations` for schema 4.

## Validation

JDK 17, pinned repository toolchain, Android API 37 emulator (`emulator-5580`).

- `:app:testDebugUnitTest`: **904 tests**, zero failures/errors/skips.
- Diagnostic analyzer/boundary/packaging Python suite: **55 tests**, PASS.
- `:app:connectedDebugAndroidTest`, filtered to `TypingToolsInstrumentedTest` and
  `CandidateStripInstrumentedTest`: **15 tests**, zero failures/errors/skips. Real settings
  clicks/recreation, durable abbreviation save/display/reset, dashboard counts/reset storage,
  candidate/undo labels and click IDs, hidden-strip stale-action exclusion and existing touch/
  accessibility candidate behaviors.
- `:app:lintDebug`, `:app:assembleDebug`, `:app:assembleDebugAndroidTest`: PASS.
- `:app:imeIntelligenceBoundary`, `:app:forbiddenRuntimeDependencies`,
  `:app:privacyGateRelease`, debug/release diagnostics packaging: PASS.
- `git diff --check`: PASS.
- Independent review findings fixed with regressions; final scoped re-review clean.

Initial validation exposed an old schema assertion and exact diagnostic inventories needing
explicit schema-4 additions. A coordinator feedback regression found during review was fixed
and tested through the production request path. Final checks above passed after those fixes.
Logs, review reports, test evidence and installable debug APK are in ignored `build/typing-tools/`.

## Limits

No accuracy, battery or real-device latency improvement is claimed from synthetic tests.
No new neural fine-tuning, private chat import or network transfer was performed in this slice.
The connected physical phone was not modified; installation/tests used only the named emulator.
Release remains unsigned without the release key; the delivered installable artifact is debug.
