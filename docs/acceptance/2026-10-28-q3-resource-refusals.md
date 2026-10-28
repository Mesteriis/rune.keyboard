# Q3 — remaining Android resource refusals and acceptance audit

This closes Q3's remaining Android adapter audit, following the preceding
schema9-integration and Fold-update receipts. Q3's local review acceptance is
verified; the complete review and other A/U/Q cards remain open.

`AndroidTypingPersonalization` now separates unavailable dictionary/model handles
from qualification/snapshot/pool failures. The shared joint readiness helper
preserves qualification-first short-circuit order. Contextual, infinitive and
noun-case entry points retain their original model-first order; rescue and word
context retain their own qualification-first gates. Missing model/dictionary
handles report `RESOURCE_UNAVAILABLE` without admitting any extra candidate.

The compact path distinguishes unavailable morphology from unavailable rare-word
evidence. For a public-augmented target it separately reports missing morphology,
missing rare-word evidence, and a dictionary-unknown target (`TARGET_UNKNOWN`).
Both original/target lookups still occur before their existing respective vetoes;
no lookup or qualification grant was added. Admission VERSION remains 1, and no
reason ordinal, schema, asset, native library, score, weight or threshold changes.

## Direct Android before/after evidence

One identical test APK observes 101 fixed resource/qualification/pool combinations
against the preceding `92eb542` main APK and the current main APK on the verified
owned API 26 emulator. It records actual `allowed` and `refusal` values before
asserting the complete table. The old APK fails exactly 35 reason expectations;
the new APK passes all of them. Both admit exactly 15 rows and refuse 86, with
zero allowed-boolean changes. Ready/restored paths, unsupported language/length,
unevaluated/incomplete/missing pools, missing common and source-specific models,
missing dictionary flags, rare/morphology loss and unknown augmented targets are
covered, including combined failures that establish gate order.

The test waits for real packaged loaders, temporarily removes/replaces private
handles through test-only reflection, and restores them in finally. It has no
production injection hook. Hardware and explicit owned-emulator guards run
before any store mutation. The four actual personal-admission methods pass
without skips; the existing protected-word/personal-veto real-store cases remain.

All 1,301 JVM tests pass (zero failures/errors/skips), along with debug lint,
profile privacy/R8 packaging and 67 diagnostics Python tests. Six actual API 26
diagnostics UI scenarios also pass, without skips, on the exact current main/test
APK pair: consent, rotation, deletion, correction/Undo, excluded sensitive fields
and fresh layer/language segments retain their assertions.

## Complete Q3 check against the review

The adjacent evidence binds current regression sources for every requested area:
personal/protected/resource vetoes, distinct unknown target/rival analysis, local
empty search, rejected LIMIT/INVALID/STALE snapshots, unchanged joint ambiguous
winner exception, selected mechanical refusal metadata only at boundary actions,
coarse bounded numeric editor class/variation, schema 9 allowlist/negative
fixtures, append-only numeric reasons and analyzer support. The former
self-comparison test now asserts independently specified permitted/refused
outcomes. Terminal editor metadata retains its originating session through a
sensitive-editor transition. Metadata-only events do not evaluate text callbacks.

The preceding complete 12,012 + 1,676 + 1,600 core replay remains bound to the
current 90 selected core sources and 69 assets: all current hashes and stored
complete observation hashes were rechecked. No new core replay execution is
claimed in this slice. That host excludes this Android adapter, so the new
101-row Android before/after table supplies the adapter-specific evidence.
The preceding replay preserves candidates/scores/commands/text/Undo/admission,
allowing only explicit reason renames, with actual stress boundary
NOT_QUALIFIED reduced from 393 to 23. Missing admission callbacks remain null;
they are not counted as successful admission or a quality score.

All 69 assets and four native libraries also match byte-for-byte inside the old
and new debug APKs. Synthetic fixture and diagnostic specificity results are not
fresh natural-data qualification or evidence of increased correction accuracy.
Physical installation of this adapter follow-up is recorded separately after
execution; independent release/distribution acceptance is outside Q3.
