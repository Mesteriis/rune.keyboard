# Initial evidence and applied-word role learning inputs

Source-v4 removes an experimental letter-name cue that caused a correct Rune
replacement to be overwritten before `Н.`. New soft applied-word features and
authored role contrasts prepare the next learning stage. Model weights and the
installed application remain unchanged; the new 221-field layout is not fitted,
registered or installed.

## Initial guard and fixed-model result

`SurfaceAwareContinuationSource` delegates to frozen source-v3 before applying
the surface guard. A completed single-letter first right word cannot establish
a nominal subject through a letter-name dictionary reading. A true nominative
pronoun such as `я` retains its reading; longer names and acronyms are not
blanket-blocked. Original protection, ownership, complete retrieval, comparison,
candidate metadata and morphology checks keep their existing priority.

This is a guard on the first nominal cue, not a complete abbreviation/name
parser. It does not traverse a surname after an initial's dot or reinterpret
the frozen feature extractor's sentence boundaries. That limitation remains
part of future continuation work.

The exact v9 composite was replayed on the same 7,905 disclosed calibration rows
with source-v4. Four formerly scored prefixes are now refused as
`SINGLE_LETTER_NOMINAL_UNPROVEN`; every remaining one of 1,752 scored decisions
matches its source-v3 trace exactly, including winner, scores and margins.
Only one accepted path changes: `инициативе → инициативна` before `Н.` is
prevented. The other three removed prefixes had no accepted change already.

First positive-margin diagnostic correct actions remain 141, wrong actions fall
20 → 19, correct-input controls remain unchanged, and losses of already correct
Rune output fall four → three. The noun/predicate, full/short adjective and
different-adjective-lemma failures remain; this initial guard does not solve
them. Diagnostic threshold fitting and full corpus-volume qualification still
fail. No independent holdout is scored and no policy is selected.

## Soft role/lemma features, without a revision prohibition

`AppliedWordFeatures` appends 19 fields after the frozen 202, producing 221:
original dictionary availability and identity, applied-word identity/knownness,
applied noun/full-adjective/adverb/predicate/other readings, adjective-lemma
ambiguity, same/different adjective-lemma relationships, candidate noun/full
adjective readings, and immediate left modifier/pronoun/case evidence.

Known-word status is queried independently from the pinned dictionary, not
inferred from an expected label. Multiple POS/lemma/case readings remain visible.
Missing case evidence cannot establish a universal conflict. Immediate modifier
evidence is not borrowed across punctuation, identifiers or an unfinished word.
Normalization and word/vector bounds are explicit; old fields and caller data
are not mutated.

These features do not refuse role or lemma changes. A wrongly applied noun/full
adjective must remain repairable, and a same-lemma relationship alone does not
prove that a full/short-adjective transition preserves the intended role. The
features supply distinctions that the previous 56-field head could not see.
Fitted behavior and legitimate cross-lemma repair still require evaluation.

## Authored contrasts and a preparation defect

The new full/short-adjective contrasts use the existing 24 adjective training
families and dictionary-only feminine forms. Attributive frames with `это` and
`вот эта`, and authored predicate questions with `насколько` and `почему`, have
explicit target intent. They are not universal syntactic admission rules.
Both already applied forms and the raw typo are represented. The data includes
retention of a correct full adjective and repairs in both full/short directions;
unresolved clauses and correct-original controls retain their previous word.
Retrieval queries never depend on those labels or the future suffix.

The first preparation produced 936 new rows and skipped nine families. Inspection
showed an input-selection defect: lexical ordering could choose the superlative
`наиполезнейшая` before the positive `полезная`, leaving no shared one-edit typo.
The generator now excludes superlative/secondary-comparative readings and orders
remaining forms by length then spelling. A regression test reproduces that exact
dictionary-paradigm ambiguity without using a natural failure word.

The initial preparation, its logs and its exact pre-fix generator snapshot remain
in `build/right-context-applied-v10-20261027/`; it is not used for the final
vectors. The corrected preparation is in
`build/right-context-applied-v10-v2-20261027/` and retains all 24 families with
no skipped full/short pair. No natural calibration sentences or their failure
targets are added to supervision; supervised families remain the previous 38.

## Actual pools and prepared vectors

The corrected corpus contains 33,428 rows, including 1,512 new role rows. All
1,581 distinct queries run through the unchanged, hash-bound native controller.
The existing complete-pool selector retains 32,024 groups / 445,321 candidate
rows. Its 1,404 incomplete-pool exclusions are all in the old portion; every new
role row is supported by a complete actual pool containing both contrast forms.
Missing expected forms are never injected.

The saved float32 matrix has 221 fields. All 30,512 old selected groups reuse
identical candidate metadata and targets. An independent saved-file audit checks
the first 428,865 rows: all first-202 fields, labels, group IDs and weights match
v9 exactly. The 1,512 fresh groups have newly computed first-202 features and the
same appended role schema. The whole corpus has zero contradictory target labels
for identical actual inputs; repeated authored inputs are reported as repeats,
not independent qualification volume.

The preparation keeps the prior weight policy: weight three for a strong target
that repairs an already applied non-original form, weight one otherwise. It
contains no fitted model. A future structural head would have 75 fields; the
current scalar composite still accepts only its old 202/56 layout. Explicit
numeric profile support, fitting and parity checks remain necessary before using
the new vectors. No frozen old feature/model semantics are silently replaced.

## Checks and remaining acceptance

All 154 `test_right_context*.py` tests pass, including five surface-source tests,
eight applied-feature tests and five role-corpus tests. Native replay, complete
pool selection, vectorization, saved-input identity and the fixed-model surface
comparison pass. The same v9 model/asset hashes are checked unchanged.

The actual three remaining prior-correct losses, missed nominal acquisitions,
initial-aware continuation, legitimate role/lemma repairs and the quality/corpus
gates remain open. No Android/JVM source changes were made; JVM tests, lint, APK
build, installation and real-device acceptance were not rerun. The keyboard on
Fold has not received these experimental changes.

The [evidence receipt](2026-10-27-right-context-initials-and-applied-roles-evidence.json)
binds code, tests, the historical preparation snapshot, corrected native pools,
vectors, input audits and the failed qualification result.
