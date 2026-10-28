# Q3 — schema 9 and boundary replay integration

This integrates the preceding admission, personal-veto, candidate-rejection and
mechanical-refusal slices. Q3 remains open for the Android adapter's remaining
combined resource-readiness refusals; the complete review remains open.

Schema 9 appends one integer `editorType` to the fixed shared DTO. The producer
retains only `TYPE_MASK_CLASS | TYPE_MASK_VARIATION`; flags, package names,
IME options and action labels are excluded. Serialization admits 0–4095 and
maps invalid DTO values to zero. Zero also represents an unknown originating
editor: a reply from another session is never assigned the new editor's type.
Admitted terminal editor outcomes retain the originating immutable event's type,
including a reentrant switch to a sensitive editor. Excluded editors remain
excluded. The analyzer accepts historical schemas and requires a bounded integer
for schema 9; it does not invent a missing type for old captures.

The fixed-field source allowlist and its negative fixtures include the new Int.
Reason ordinals remain append-only and admission VERSION remains 1. No weights,
thresholds, native code, assets or model/store formats change.

## Actual boundary explanations

Initial stress observation found 393 `BOUNDARY=NOT_QUALIFIED` events in both
versions: renaming admission callbacks alone did not explain the real boundary.
The controller now preserves the result of the primary local evaluation it was
already performing. Only a generic non-model ranking refusal may use that
observed local reason; specific joint refusals and model decisions retain their
own explanations. The successful decision is exactly the existing evaluation's
`decision`, with no additional admission call or grant. Unit cases cover empty
and incomplete local search, model precedence and a specific joint refusal.

Final paired results, from actual controller `BOUNDARY` events:

| Corpus | Rows | Old NOT_QUALIFIED | New NOT_QUALIFIED | Automatic branches, old/new |
| --- | ---: | ---: | ---: | ---: |
| Historical regression | 12,012 | 1,760 | 40 | 5,983 / 5,983 |
| Local stress | 1,676 | 393 | 23 | 887 / 887 |
| Historical calibration | 1,600 | 288 | 0 | 99 / 99 |

Stress generic refusals decrease from 23.45% to 1.37% of rows. This is diagnostic
specificity, not increased correction accuracy. Rows without an admission callback
remain null and are not credited as successful explanations or corrections.
Every paired row has an actual boundary event; that is observation coverage,
not an accuracy criterion.

All 15,288 paired rows match in every existing non-timing field except explicitly
allowlisted reason renames, including candidates, scores, allowed booleans,
commands, final text and Undo. The new boundary observer's fields also match
except reason names. Complete-empty-search renames have a checked complete/empty
pool prerequisite. The current observations additionally match the preceding
step's frozen candidate observations exactly after removing only the two existing
host timings and the newly added boundary observation field.

The baseline production source is `3c3abe6`, with the identical optional,
metadata-only observer used on the candidate. The adjacent zero-context patch
reproduces that observer with `git apply --unidiff-zero`; application and exact
source equality were checked, then the disposable baseline was restored clean.
Its host was compiled earlier in this validation cycle and bound before reuse.
The final candidate was freshly compiled after the namespace repair below.
All 69 asset identities match before/after and across versions. Inputs, complete
Kotlin source selections, toolchain/compiler/JVM/stub, JARs and observations are
bound in the adjacent evidence. The optional observer never invokes text callbacks.
No native GGUF inference or renewed unseen-data qualification is claimed.

## Build and device diagnostics

All 1,301 JVM tests pass without failures/errors/skips, as do debug lint, 32
analyzer tests, 25 boundary/privacy fixtures and 37 contextual compiler tests.
The actual current contextual host compiles and passes all 22 synthetic cases.
The profile APK passes privacy/diagnostics packaging through R8.

That packaging gate initially rejected the pure mechanical mapper in the shared
`diagnostics` package, which permits only its fixed observer contract. The mapper
and its tests moved to the punctuation domain; the strict gate was retained.
One interrupted candidate replay is retained as a failed/interrupted attempt,
not counted as final parity; the complete final candidate was rebuilt afterward.

On the final main APK, six real API 26 diagnostics UI scenarios pass, with no
skips, including consent controls, rotation, deletion, actual correction/Undo,
sensitive/private field exclusion and fresh segments across layer/language
changes. The last scenario also passes two separate targeted repetitions.
A preceding run missed its final recorded Russian key although the later failure
snapshot showed all 23 characters in the editor. The test previously exported
after gesture completion without checking editor acknowledgement. It now waits
for exact numeric lengths before fencing the recorder worker and saves phase
snapshots before assertions. Exact `p`/`й` checks and context-isolation assertions
are preserved. The three successful strengthened runs retain both final keys;
no production retry or text normalization was introduced to make them pass.
The original failure and all phase records remain private evidence.

The main debug APK and test APK selected for Fold are byte-bound to that successful
UI run. Installation, physical results and owner-state restoration are recorded
separately after execution. This receipt does not substitute for those checks.

## Remaining Q3 audit

`AndroidTypingPersonalization` still combines some model/dictionary readiness
checks with qualification failures. The compact path also combines morphology
and rare-word availability under one morphology refusal. These paths require
separate exact refusal identities and direct unavailable-resource regressions
before Q3 can be marked complete. The current core replay does not compile that
Android store adapter and is not claimed to validate those remaining paths.
