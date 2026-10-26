# Training a separate following-context revision model

Following the [feature foundation](2026-10-27-right-context-foundation.md), a
separate experimental ranker now uses the original 146 lexical/context features,
16 completed-right-context features, and one indicator of the already applied
word: 163 features total. The applied-word indicator is necessary to represent
retention of different previous outcomes under otherwise identical weak context.
It is an observed/counterfactual input, never derived from the expected target.
This model does not replace any installed model and is not connected to Android
resource loading, source qualification, ownership or editing.

## Real candidate retrieval, without target insertion

`right_context_training_groups.py` constructs queries from preceding text and
original input only. Query identity is independent of the expected answer,
applied word and following context. The source-bound current Kotlin controller
ran 472 distinct queries for the expanded authored corpus's 3,472 rows. Only
complete retrieved pools containing the applied/expected/contrast forms were
accepted. No missing form was inserted. Correct-original retention examples may
use an explicitly marked complete manual pool; that evidence cannot authorize an
automatic correction.

The selector accepted 3,378 groups / 49,218 candidate rows across 24 authored
lemma families. It excluded 94 rows for incomplete pools: 56 strong-context
unknown originals, 24 weak-context unknown originals and 14 correct originals.
All 2,720 accepted unknown-original contrast pairs match their production edit
metadata exactly, including symmetric and asymmetric cost pairs. These are
counterfactual applied-form training contrasts, not claims that the installed
controller previously selected both competing words. Actual source-admission
facts are recorded separately and are not overridden by training labels.

## Initial failure and training coverage correction

The first model used the original 1,968-row authored corpus (1,914 accepted
groups). Despite strong training scores, it still selected `виновен` in the
previously disclosed Tatoeba regression 1873299 (soweli_Elepanto, CC BY 2.0 FR).
The following-word extractor correctly reported a number conflict for that form
and support for `виновны`. Model split inspection showed no use of the following
copula evidence: its training continuations always included an immediately
following pronoun, and it relied on that redundant subject evidence instead.

The explicit `--copula-coverage` mode adds four sets of authored continuations:
standalone finite copulas, past copulas, a following adverb, and intervening
`не только` before the subject. Both competing forms still have correct-original
retention controls, and weak-context retention examples remain intact. The
previous corpus and failed model are retained. The disclosed failure word and
all independently collected natural-context families remain excluded from
training. No independent calibration/holdout model scores informed this change.

The second model keeps 128 depth-five trees, learning rate 0.05,
PairLogitPairwise, seed 25102026 and two CPU threads. Its exported 22,036-byte
binary SHA256 is `fd27f9224620e1866cbace6510d4de7c1034bccc36d480750887bc6e0f70def4`.
It ranks the target first in 1,897/1,904 strong-context training groups,
658/658 correct-original groups and 816/816 insufficient-evidence groups.
These are training diagnostics, not independent quality or source admission.
The float-leaf scalar decoder agrees with CatBoost to a maximum absolute
1.7008611810642726e-08 across the checked first 32 complete training groups.

In the real seven-entry retrieved pool for the disclosed regression, changing
only the supplied following context makes the new model select `виновны` for
the natural completed suffix. Withheld context, unfinished `будут`, and singular
`будет` retain the installed previous choice `виновен`. The existing independent
joint-source check admits the selected words. No editor operation was performed
by the experimental model; this disclosed case is regression-only.

## Independent natural corpus frozen before scoring

The initial Tatoeba sampling attempt did not meet its declared size/diversity
requirements. Its exclusion reader first stopped on a pretty-printed JSON
fixture; a tested reader now handles JSONL, a single JSON object, arrays and
`cases` containers. After that format repair, the unchanged sampling requirement
still failed: only 83 calibration / 14 holdout contexts across 14/9 families
remained. No threshold or quality requirement was relaxed.

Seven already downloaded, hash-verified Wikipedia 20231101 Russian shards
(0012–0017 and 0020) supplied additional natural contexts. The collector excludes
the 24 training families, prior authored/disclosed families and 9,941 bound
previous article IDs. Before any new-model scoring, 1,204 distinct source
articles yielded 831 unique contexts after a global cap of 30 per family.
The original sampling requirement was met without adjustment:

| Partition | Natural contexts/articles | Unseen families | Rows | Correct/protected controls |
| --- | ---: | ---: | ---: | ---: |
| Calibration | 400 | 129 | 1,600 | 1,200 |
| Holdout | 400 | 157 | 1,600 | 1,200 |

Families, source article IDs and normalized context hashes are disjoint between
parts. Each source context supplies one unknown shared corruption, the correct
source form, the already-correct competing form, and a protected form. Selection
uses dictionary-only number evidence and fixed corruption geometry; neither
model predictions nor a forced candidate choose examples. Public context text
and attribution/article links remain in ignored local corpus files, under the
Wikipedia CC BY-SA 3.0/GFDL terms. Synthetic corruptions in natural public text
are not real human typing or independent-author evidence.

The raw corpus was initially bound to the first model. A separate receipt binds
the second model before independent evaluation and verifies that corpus bytes
and training-family exclusions are unchanged. Both 1,600-row parts have completed
baseline retrieval through the actual installed-stage controller; the experimental
right-context model has not been called on either partition. No candidate query
includes the future/right context or target spelling.

## Verification and next gates

All 29 focused Python tests passed. They cover label-blind query identity,
retrieval-only selection, denied/protected/incomplete evidence, pool bounds,
retention labels, original-corruption costs, dictionary paradigm consensus,
complete feature shape/finite values, source-exclusion formats, and the added
copula coverage. `git diff --check` passed. Android sources/assets did not change
in this training milestone, so no Android rebuild or phone command was issued.
The prior installed Fold build remains unchanged.

[The aggregate evidence receipt](2026-10-27-right-context-training-evidence.json)
binds the artifacts. Ignored roots retain both model attempts, training logs and
vectors, preparation failures, source-availability reports and raw baseline
observations. The new model remains unqualified. Next are calibration and a
frozen revision policy, untouched holdout scoring, then Kotlin scorer parity,
source admission and bounded multiword ownership with exact Undo before any
installation. The existing requirements remain at least 95% precision,
100 new correct revisions, zero wrong changes/control changes/prior-correct
losses; independent editor/device acceptance is also required.
