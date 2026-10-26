# Grammar contrast fit: rejected for promotion

The fixed experiment combined all **19,802 frozen original training groups**
with **612 eligible authored contrast groups** (204 typo and 408 retention
groups). It trained the same 146-feature, 128-tree, depth-five ranker with the
same learning rate, seed and pairwise objective. No group oversampling, word
exceptions, feature changes or application threshold changes were introduced.
The result is **not qualified or installed**.

## Training selection

`tools/typing_experiments/grammar_training_groups.py` joins labels only after
complete production retrieval. It checks row identity, explicit original-word
protection evidence, complete candidate pools, both contrasting forms and an
actually retrieved target. Missing labels never silently become an original-word
target. Correct-word retention may use a complete manual pool and always targets
the original. Six `копие` typo rows were excluded because the production lexicon
marks the source valid; 12 retention rows lacked a complete pool.

The initial preparation assertion incorrectly expected only the six exclusions
and stopped **before fitting**. Inspection also caught an overly broad use of
`prohibitsAutoReplace`: that property covers exhausted baseline retrieval as well
as source protection. The contextual production policy permits its separately
complete joint pool after baseline exhaustion. Selection now mirrors that source
contract (`isValidWord` / `protectedReason` plus a complete joint pool); no product
guard was changed. Regression tests cover this distinction.

All frozen base IDs and their order were reconstructed from hash-bound original
corpora/observations, including the already authorized promoted conversational
audit. Their historical missing-target-as-original labels were retained for this
ablation; the new selector does not introduce that fallback for new groups.
Frozen total: **20,414 groups / 234,984 candidate rows**.

On training groups only, raw target selection changed as follows:

| Slice | Installed ranker | Experimental ranker |
| --- | ---: | ---: |
| Broad original mix | 18,851 / 19,802 | 18,820 / 19,802 |
| Contrast typos | 103 / 204 | 165 / 204 |
| Contrast retention | 360 / 408 | 406 / 408 |

Of the five previously disclosed training cases, only `заплатищь → заплатить`
became the raw winner; the other four remained wrong. This is training fit, not
independent evidence or an accepted editor action.

## Fresh evaluation and frozen policy

New public conversational source selection excluded prior sentences and target
contexts, including the preceding grammar evaluation and authored contrasts.
The packaged morphology index resolved 32 contrast lemma families for explicit
exclusion. Calibration and holdout were also disjoint by family: each has **3,000
contexts / 12,000 input rows**, with 1,451 and 1,422 families respectively.
Source licensing remains Tatoeba CC BY 2.0 FR; source references/attribution stay
in ignored local artifacts. No owner messages were used.

Source selection ran while fitting was already underway, before any evaluation
scores. An inherited manifest stage incorrectly said "before model fit"; its
wording was corrected before scoring, retaining the original manifest and
unchanged row hashes. It is not evidence of pre-fit evaluation reservation.

Calibration selected once from a fixed 33-by-33 score/margin quantile grid,
requiring at least 100 additional correct proposals, precision at least 95%,
no baseline/installed-correct loss, no control changes and positive net correct
gain over the installed model. It selected score `-0.027978906309855247` and
margin `0.010098681744052086`, then froze them before holdout scoring.

| Selected-policy result | Calibration | Independent holdout |
| --- | ---: | ---: |
| Additional correct / wrong vs joint baseline | 681 / 35 | 609 / 37 |
| Precision | 95.1117% | **94.2724%** |
| Installed-correct losses | 0 | 0 |
| Installed-correct gains | 99 | 73 |
| Correct-word control changes | 0 | 0 |

The holdout **fails the required 95% precision**, despite positive net gain.
The fixed *installed* thresholds were separately disclosed as an untuned
diagnostic: 548 correct / 18 wrong (96.8198%), but one installed-correct loss,
so that option fails too. No threshold was selected from holdout results.
Raw holdout ranking was nearly unchanged: 5,305 versus 5,306 correct first
candidates out of 5,526 eligible groups.

## Verification and next constraint

All four 12,000-row Kotlin replay processes completed successfully. Labels did
not enter the harness. Numeric vectorized tree scoring matched the scalar
decoder exactly on 128 sampled vectors for each of the two 146-feature models
(maximum absolute error zero); frozen character-component parity was checked
separately in both evaluation partitions. **18 Python tests passed**:

```sh
PYTHONPATH=tools/typing_experiments python3 -m unittest test_grammar_training_groups test_grammar_contrast_corpus test_grammar_context_features
```

The experimental model SHA256 is
`71454f1b6ce2f3755b17a5af4712a077525230bc4cc4d448f904972a1c40be69`.
Detailed ignored artifacts are under `build/grammar-contrast-training-20261026/`;
the adjacent aggregate JSON binds selection, model, evaluation and policy hashes.
Packaged model/policy hashes are unchanged. No phone commands or installation
were performed in this experiment, and this result does not supersede Fold
acceptance of the installed model.

The calibration optimum was only just above 95%, and did not generalize above
the required ratio. A subsequent experiment should reserve fresh qualification
data and use a more conservative calibration criterion fixed before scoring;
this revealed holdout must be treated as diagnostic/regression material. The
current result does not justify another epoch with these same evaluation labels.
