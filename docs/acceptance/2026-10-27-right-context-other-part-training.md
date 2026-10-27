# Other-part competition and reliable following-subject evidence

This milestone adds authored noun/predicate training competition and fixes a
separate source-evidence bug. It remains a host experiment. No Android application
source/asset, editor admission, device setting or installed APK changed.

## Paired competition, experimental model v5

`right_context_other_part_corpus.py` supplies shared dictionary-unknown corruptions
for seven authored contrasts: `зол/зал`, `зол/пол`, `силён/салон`, `слаб/штаб`,
`верен/ветер`, `важен/вагон`, `щедр/кедр`. With the same unknown input, a noun frame
such as `этот … будет` targets `вагон`, while `он … будет` targets `важен`.
Every completed prefix used for a strong label already contains its explicit
preceding context; later words do not supply a hidden answer. With no subject or
an unfinished suffix, labels retain the applied word. Correct originals retain
themselves. All targets must be retrieved by the actual controller.

A noun surface can itself have another dictionary reading: `пол` also has an
adjective reading. Its authored noun frame is retained with every competing lemma
recorded, rather than pretending the dictionary is unambiguous. Two-character
shared corruptions are excluded from this three-character-minimum source.

The 884 new rows augment the frozen v4 corpus, yielding 9,572 rows and 1,007
distinct label-blind controller queries. Replay completed all queries. The
selector kept 9,094 groups / 134,459 candidate rows, excluding 478 incomplete
pools. Training-family metadata now includes all competing lemmas (38 total),
not just the main adjective family. The 178-feature layout and training settings
remain unchanged: 128 depth-five trees, learning rate 0.05, seed 25102026.
The v5 experimental binary SHA256 is
`44327fbfc294b7568292702ab8b43f8d3a0c951458f5c5bc1fc89ca065e1b16b`.

| Training category | Target first / groups |
| --- | ---: |
| Strong unknown-original rows | 4,077 / 4,251 |
| Correct original | 1,531 / 1,531 |
| Insufficient/ambiguous evidence | 3,304 / 3,312 |
| New noun frames, unknown original (subset above) | 160 / 240 |
| New predicate counterpart, unknown original (subset above) | 232 / 240 |

These diagnostics show remaining underfit, including eight new weak-context
retention failures. They are not quality qualification. Exported scalar scores
match the sampled CatBoost predictions within 3.76e-8 absolute difference.

## Fresh corpus separation and calibration

The finite seven-shard collection completed over 648,354 public articles. Its
11,580 rows were frozen without model scores, excluding previously disclosed
families/articles and using the actual lowercase source-surface guard.
New noun training added families after that collection began.
`exclude_training_contexts` therefore excludes entire source contexts when any
source/rival family intersects the supervised families. It never inspects a
prediction or expected spelling to choose exclusions, and it removes controls
and typo variants together. Missing or inconsistent family metadata fails closed.

One four-row holdout context is excluded. The bound v5 corpus has 5,800 calibration
rows over 1,240 contexts and 5,776 unscored holdout rows over 1,235 contexts.
Family/article/context separation is preserved. The current controller replayed
all 5,800 calibration rows with the same source-bound observer. Initial v5
calibration with source version 1 failed the declared 100-new-correct,
zero-new-wrong/correct/control-loss gate; no candidate policy was frozen and the
experimental model did not score the holdout.

## Root cause: dictionary homographs are not subject evidence

Inspection of calibration errors showed suffixes such as ` и `, ` в ` and ` по `
being treated as following subjects. The pinned dictionary has nominal readings
for these surfaces, including letter-name homographs, as well as their ordinary
function-word readings. The existential nominative lookup incorrectly licensed
source evidence. For example, a conjunction after a plural predicate could lead
the ranker toward a masculine singular form.

Source scope version 2 now uses a separate `SubjectEvidenceLexicon` view: when
PREP, CONJ or PRCL analyses exist, nominal readings do not establish a subject.
Other analyses remain visible. The original dictionary is unchanged and still
owns known-word protection, candidate generation, lexical features and target
certificates. Ordinary noun case ambiguity (`модели`) remains visible, and
pronouns `она`/`они` and genuine finite copulas retain their evidence. A copula
followed by a function word still contributes its own finite evidence without
acquiring a fictitious subject.

This changes source admission only. Frozen v4/v5 feature definitions and binaries
are not silently reinterpreted. The source-v1 snapshot is retained and its digest
matches the initial scoring plan. Real pinned-dictionary checks confirm that
`и`, `в` and `по` lose only the nominal source cue; raw dictionary analyses are
identical before/after. The synthetic tests also cover particles and ordinary
case ambiguity without assuming every tested synthetic homograph exists in the
real dictionary.

The unchanged model was recalibrated with source version 2 and again failed the
100-gain gate. A label-based *coverage audit*, without model scores or threshold
selection, explains a data limitation: the original calibration cohort permits
at most 23 additional gold corrections under reliable source admission, versus
306 under the erroneous nominal interpretation. The old cohort's
`direct_subject_positive` name is therefore not proof of real subject evidence.
These audit counts are upper bounds, never a selector or accepted policy. Labels
and recorded failures of the frozen corpus remain unchanged.

## Remaining corpus work

A separate finite attempt to replenish the original copula cohort scanned
926,220 articles in ten existing hash-locked shards. Excluding all previously
disclosed/training families left 25 calibration and 20 holdout contexts; the
holdout also has only 19 families. It failed the unchanged 400-context/20-family
requirements and produced no qualified corpus. The available records are
preserved without lowering requirements.

A new side collection has been started with reliable subject evidence at
selection time, the source-surface guard, and the same cohort-size requirements.
It excludes the previous fresh contexts by article. Its family partition seed is
unchanged, so previously unscored holdout families cannot move into calibration.
No model scores affect selection. At this milestone it remains a running
collector, not a finished corpus or a passed gate. The objective remains improved
sentence autocorrection with useful coverage; retaining 23 easy corrections is
not the completion criterion.

## Checks and limits

85 focused Python tests pass. The training replay and fresh baseline-calibration
replay completed. Export parity passed; `git diff --check` passed. An initial
training-corpus preparation rejected the `пол` homograph; dictionary inspection
led to preserving its competing readings explicitly before training. The first
reliable-collector launcher had a duplicate keyword and failed before collection;
the corrected launcher is a separate logged retry. Neither failure is a pass.

No Android application build, new-feature Kotlin parity, multiword ownership,
Undo/device acceptance or installation is claimed. A model must pass meaningful
calibration and independent holdout gates before those runtime integration steps.
The [evidence receipt](2026-10-27-right-context-other-part-training-evidence.json)
binds corpus/model/source versions, audits and actual checks. Build artifacts
use the `right-context-…-v5-20261027` roots named in that receipt.
