# Following-context evidence for predicate agreement

The remaining disclosed `виновн` → `виновны` regression needs information that
is absent at the first word boundary. In the previously downloaded public
Tatoeba sentence 1873299 (soweli_Elepanto, CC BY 2.0 FR), the relevant continuation
is `будут`. The installed general/infinitive/noun scorers receive only preceding
text. The existing previous-word refinement request also submits its old prefix
and isolated alternatives, without the following composition. Its ticket lasts
one second and owns only the previous word plus one following composition.
Extending that deadline alone would not provide right-context evidence.

This milestone adds a separate, experimental 16-feature schema in Python and
Kotlin. It is not appended to the installed 146-feature model, loaded by Android
resources, or consulted by the controller. No automatic decision or editor edit
is authorized by these features, and no new APK was installed in this milestone.

## Input contract

The caller supplies the exact already-typed suffix after the candidate, including
its separating space. Only completed following words contribute. A token at the
caret remains unfinished even if it happens to be a dictionary word: ` он` must
not be treated as a completed subject while the user may still type `она`.
A visible space/tab or clause-ending punctuation completes a token. Punctuation
and newlines stop traversal; identifiers, hyphenated continuations and foreign
letters cannot be shortened into a grammatical cue. The extractor considers at
most the first 128 input characters and eight complete Russian words, normalizes
NFC and case, and never scans into later clauses or accepts a truncated token.

Dictionary-only analyses provide short-adjective/short-participle number and
gender, a following finite copula from the existing Russian forms of `быть`, and
an immediate nominative noun/pronoun (optionally immediately after that copula).
The feature vector preserves number/gender ambiguity. A supported alternative
reading prevents a false conflict; future copulas supply no invented gender.
Candidate normalization processes the complete bounded candidate rather than
silently cutting an identifier suffix. These are soft evidence features, not a
rule that forces agreement or a general syntactic parser.

## Training contrasts and feature audit

The deterministic generator froze 1,968 authored training-only rows across 24
dictionary-validated lemma families. The disclosed failure forms and previous
predicate contrast forms are excluded from this training corpus. Each unknown
shared one-edit input is paired with both possible already-applied forms and
opposing completed right contexts. The schema records `original`, `applied`,
`expectedApplied`, both contexts, and the candidate forms separately.

- 840 unknown-original rows have explicit number evidence: 420 would require
  changing the applied form and 420 retain an already correct applied form.
- 288 correctly spelled originals always retain the applied word, including
  144 cases where the grammatical cue conflicts with that spelling.
- 840 insufficient-evidence rows retain the applied word. These include
  unfinished tokens, identifiers, punctuation barriers and a non-immediate subject.

The dictionary-backed feature audit matches the intended number evidence in all
840 strong rows and produces no copula/subject cue in the 840 weak rows. These
are checks of authored labels and feature extraction, not candidate retrieval,
model accuracy, automatic precision or independent qualification. No model was
trained or threshold tuned in this milestone. Future qualification must exclude
all authored training families and templates.

## Cross-language and regression checks

The frozen authored fixture contains 1,870 candidate/context pairs, including
boundary, normalization, ambiguity and missing-word cases. All 16 Python feature
values match Kotlin exactly in both the small fixture dictionary and the complete
current production grammar asset. This is 59,840 numeric comparisons, with zero
difference. The production grammar asset is sufficient for this feature fixture;
it was not regenerated or replaced. The disclosed singular/plural regression also
has a direct production-dictionary check; its words appear only as regression
inputs, not training examples.

The fixture grammar data derives from OpenCorpora (CC BY-SA 3.0), with source,
license, dictionary package identities and hashes recorded in its provenance.
It contains no owner text or new downloaded sentence text.

`./gradlew --max-workers=2 :app:testDebugUnitTest :app:lintDebug` passed
1,128 JVM tests with zero failures/errors/skips and debug lint passed. The focused
Python suite passed all 14 tests. `python3 tools/verify-scoring-boundaries.py`
and `git diff --check` passed.

The final checks and artifact hashes are recorded in
[the evidence receipt](2026-10-27-right-context-foundation-evidence.json).
Ignored logs, the full training corpus and audit are under
`build/right-context-evidence-20261027/`.

## Remaining production work

Next, independently qualify a scorer using these features and actual retrieved
candidate pools. Integration needs a separately qualified bounded ownership
record that survives the next completed word, retaining original input, previous
applied form, immutable request identity and complete suffix. It must invalidate
on external selection/session changes, explicit correction/Undo and ownership
loss, and must recheck source protection and qualification at the editor boundary.
Exact Undo must restore the original input while preserving subsequently typed
words. Neither delayed scoring nor silent acceptance may become training labels.
The existing one-second refinement mechanism and its qualified behavior are
unchanged by this experimental feature work.
