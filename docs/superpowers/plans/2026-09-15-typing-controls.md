# Typing control and learning

User approves ideas 2,3,5,6: explicit protected words, per-app profiles, confirmed-error evaluation
set, transferable typo-pattern learning. Preserve independent toggles and diagnostic states.
Base 8d638a4 in existing clean isolated codex/morphology-style worktree.

## Global constraints
No private archive reads, uploads or installed-app enumeration. No changes to the physical phone.
All new settings default off and fail closed. Data is bounded, app-private no_backup, with reset.
Only acknowledged explicit actions on Rune-owned text provide feedback; ordinary typing, implicit
non-undo, stale callbacks and sensitive/no-learning fields do not provide training labels.
Pattern learning only reorders the existing finite dictionary candidate set; never authorizes auto edits.
Protected words veto automatic word replacements; proposals remain manually selectable.
Profiles restrict globally enabled features; never enable global learning/collection consent.
No editor text readback. Logs contain fixed feature booleans and a fixed numeric profile identifier,
never app package identifiers or training text as metadata. Existing opt-in diagnostic text boundary stays.
Existing model qualification/ownership/undo, privacy gates and source/packaging inventories remain enforced.

## Task 1: Confirmed example evaluation and typo patterns (worker)
Own only new smarttyping/learning package, settings/LearningLabActivity.kt, dedicated layout and
learning_strings.xml EN/RU resources, and tests for these. Parent owns service, settings/preferences,
manifest, TypingPersonalization adapter, controller, diagnostics and all existing shared files.
Implement one bounded learning repository with atomic asynchronous no-backup storage, reset/status,
numeric pattern state, deduplicated examples and explicit source labels. Store singleton get(context).
Public bridge: configure(collectExamples:Boolean, learnPatterns:Boolean, eligible:Boolean);
accepted(original:String,replacement:String,language:KeyboardLanguage), confirmed(word,language),
rejected(original,replacement,language), manualRetype(original,replacement,language);
preference(original,candidate,language):Double; isReady; reset(callback:Boolean).
Feedback entrypoints recheck configured eligibility/readiness. accepted/confirmed are explicit picks;
rejected is an explicit veto (never learn replacement as correct); manualRetype must be conservatively
validated, can require dictionary validation supplied via callback constructor/get API negotiated parent.
Limit 512 unique examples, 48-codepoint single words, bounded file size and saturating numeric counts.
Retain confirmed identity examples for false-change evaluation. Fixed hash partition by language and
normalized expected word assigns 1/5 to holdout; all variants of one expected word remain in one split.
Holdout never trains patterns even if raw collection is off. Repetition must not count as new evidence.
Pattern model learns insertion/deletion/substitution/transposition/repetition from unambiguous bounded
alignments; finite categories, language-scoped counts, minimum evidence threshold and bounded bonus.
It must generalize across words, have deterministic ties, avoid automatic changes and poisoning from
contradictory labels. Unknown/ambiguous alignments abstain. No additional dependency.
LearningLabActivity exposes counts/split/status, run local evaluation, results and reset. Evaluation runs
on worker against a frozen snapshot, uses existing actual local candidate generator/policy as baseline
and same finite set with learned ranking, and reports supported metrics + denominators, including
identity preservation and missing candidates. No heldout training or accuracy claim on tiny/empty data.
Use repo-local lexicon loading pattern; inspect source. Provide testable pure evaluator; actual Android
runner connects shipped lexicons, cancellation/lifecycle safe. Explain metric scope (local suggestions,
not model/end-to-end auto accuracy). If separate reset for raw examples vs patterns useful, allow it.
Tests: explicit-only collection, toggles/exclusion, split/dedup/no leakage, malformed/bounds codec,
pattern evidence/generalization/abstention, deterministic benchmark and empty/missing coverage.
Ask parent before running Gradle (one shared process). No commits or subagents. Self-review and write
report build/typing-controls/learning-report.md with APIs, files, exact tests/results and limits.

## Task 2: Protected words and profiles (parent)
Bounded normalized language-scoped protected dictionary, add/remove/reset manager, long press
current Original/Correction with exact live candidate ID and explicit acknowledged durable save.
Enabled but unreadable protection data vetoes automatic correction rather than silently ignoring it.
Per-app profile bindings use only editor package seen when enabled (bounded recent list), manual
assignment in manager. Default inherits; Conversation restricts to suggestions and disables phrase/
contextual/mechanical punctuation; Formal suppresses personal continuation/abbreviation proposals.
Both presets preserve consent flags and global OFF. App/setting changes invalidate ownership before
new policy or feedback can apply. No raw package names in diagnostic events.
Tests: normalization, isolation, corrupt store, profiles no enablement escalation, live long-press
stale/held click behavior and service profile selection at start/settings change.

## Task 3: Integration and evidence (parent)
Add four independent toggles, navigation, resources, fail-closed settings tests. Connect worker feedback
only to acknowledged hooks and correct-word validation. Apply bonus only in visible candidate ranking.
Add protected/profile/learning readiness to effective flags, schema5 append-only fixed flags and numeric
profile ID. Analyzer accepts old schemas and validates exact new inventory. Keep metadata gate negative
fixtures and mapped release inventory strict. Review each component then whole slice, fix regressions.
Run JVM, diagnostics Python, lint, debug APK, boundary/release privacy and relevant emulator tests.
Document defaults, supported behavior, holdout/benchmark limits, reset, log semantics. Commit and deliver APK.

User steering: add one atomic disable-all action for all 13 optional personalization/tools flags, preserve stored data and profile bindings. Individual toggles remain.
