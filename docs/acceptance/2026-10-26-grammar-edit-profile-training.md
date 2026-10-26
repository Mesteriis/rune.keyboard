# Diverse edit profiles: three disclosed verb winners recovered, full replacement rejected

The first authored contrasts used the shortest shared corruption and failed to
represent the edit-cost disadvantage of the intended infinitive. The optional
`--edit-profiles` mode in `grammar_contrast_corpus.py` now selects up to three
distinct corruption profiles per paradigm. Profiles distinguish left/right
weighted-cost differences and insertion/deletion lengths. Selection uses static
Russian keyboard geometry and dictionary-only unknownness, never model scores
or expected performance on evaluation data.

The old default remains unchanged: a new default generation was byte-identical
to the original 630-row corpus. The new mode has an explicit v2 source marker,
new row identities and cost metadata on typo rows. Correct-word controls occur
once per context, regardless of the number of corruptions.

```sh
python tools/typing_experiments/grammar_contrast_corpus.py --edit-profiles --output build/grammar-profile-new
PYTHONPATH=tools/typing_experiments python3 -m unittest test_grammar_contrast_corpus test_grammar_training_groups test_contextual_policy_calibration test_grammar_context_features
```

## Production verification and fit

The generated corpus contains 978 rows: 558 typo and 420 retention rows, on the
same 35 authored paradigms, still excluding all five disclosed failure targets.
The Kotlin production controller replay completed every row. Selection rejected
six known-original rows and 24 incomplete-pool rows, leaving **948 groups**:
540 typos and 408 retention controls. Both forms were genuinely retrieved for
every selected typo. All **540 pairs of weighted edit costs** matched the
production candidate metadata exactly, without disagreement.

The selected infinitive/finite groups cover 120 equal-cost pairs, 114 where the
infinitive is cheaper by 0.25, and 108 where it is more expensive by 0.25. The
first experiment had only the 120 equal-cost pairs. Predicate groups now cover
both asymmetries too; selected noun groups have equal costs for both forms.

The fixed broad mix of 19,802 original groups was retained, replacing the first
authored set with these 948 groups. No new group duplicates a broad group's
normalized prefix/typed/target tuple. The fit uses the same 146 features,
128 depth-five trees, seed, learning rate and pairwise objective: **20,750 groups
/ 239,460 candidate rows**. The experimental binary SHA256 is
`20409f7407fea7381d223351570b784adaed46357c5cd1643a28d285961b23cd`.

| Training slice | Installed raw target first | New raw target first |
| --- | ---: | ---: |
| Broad mix | 18,851 / 19,802 | 18,809 / 19,802 |
| Profile typo groups | 271 / 540 | 433 / 540 |
| Retention groups | 360 / 408 | 405 / 408 |

Three previously disclosed training cases now have the intended raw winner:
`злищься → злиться`, `научищься → научиться`, `заплатищь → заплатить`.
`фотографие` and `виновн` still select the earlier wrong forms. These five are
already training examples; this is not an independent result, accepted editor
behavior or a claim that the Fold version changed.

## Calibration and retained holdout

The frozen 97.5% calibration criterion and 95% final requirement were retained,
with minimum volume and zero prior/installed-correct loss or correct-word change.
Calibration reuses the previous 12,000 calibration inputs, recomputing both
146-feature scorers on the unchanged, hash-bound candidate pools and frozen
character component. It was previously used by another model and is explicitly
tuning data. The same 3,000-context final partition remains unused. Its original
sentence/context and contrast-family exclusions still cover the unchanged
paradigms and context templates; the new corruptions were not added to any
evaluation partition.

No point on the fixed 33-by-33 calibration grid passed all full-replacement
constraints. The experimental model therefore remains **unqualified**. No final
holdout replay, labels or scores were consumed, and no thresholds were relaxed.
The broad ranking losses make continued global replacement trials a poor next
step; the useful grammatical discrimination should instead be evaluated as a
separate component while retaining the installed general spelling path. Such a
component still requires its own frozen policy, source guards and independent
qualification before it can affect editor text.

## Checks and artifacts

All **29 Python tests passed**, including both edit asymmetries, unchanged v1
output, non-one-edit refusal, deterministic profile selection and unduplicated
retention controls. Numeric vectorized tree scores matched the scalar decoder
exactly on 128 sampled vectors per model (maximum error zero). The adjacent JSON
receipt binds corpus, observations, model, selection, policy and calibration
hashes. Local artifacts are ignored under `build/grammar-contrasts-profiles-20261026/`
and `build/grammar-profile-training-20261026/`.

Packaged model/policy bytes are unchanged. No phone commands or installation
were performed; Fold retains the previously qualified model.
