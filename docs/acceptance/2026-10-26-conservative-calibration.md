# Conservative calibration: no policy qualified

The contrast-trained model remained frozen at SHA256
`71454f1b6ce2f3755b17a5af4712a077525230bc4cc4d448f904972a1c40be69`.
No refit or feature change was performed. Before selecting new data or scoring,
the experiment fixed **97.5% calibration precision**, **95% final precision**,
at least 100 additional correct proposals, zero prior/installed-correct losses,
zero correct-word changes and positive net correct gain over the installed model.
This stricter calibration ratio is a chosen margin, not a confidence interval or
a guarantee about independent precision.

`tools/typing_experiments/contextual_policy_calibration.py` implements reusable
calibration/acceptance over label-isolated scored records. It validates identity,
schema, finite scores and count integrity; computes precision from integer
counts; uses a fixed deterministic 33-by-33 quantile grid; and returns `None`
when no policy satisfies every constraint. It has no automatic relaxed fallback.
Final acceptance uses the separately supplied final precision requirement.

New source selection excluded all previous sentence IDs and prediction contexts,
including both partitions of the preceding failed contrast fit. Contrast lemma
families were excluded, and new calibration/holdout families were disjoint from
each other. Both new partitions contain 3,000 contexts / 12,000 rows. The model
was already frozen; the new stage is explicitly pre-scoring, not pre-fit.

Both calibration Kotlin replays (`joint-export`, `joint-production`) completed
all 12,000 inputs. Python scored 5,574 eligible candidate groups and joined
labels afterwards. **No policy passed all calibration constraints at 97.5%.**
The result was frozen as `calibrationPassed=false` without replacement thresholds.

The run then stopped before holdout replay or label scoring. No holdout export,
production observations or score-record artifact exists for this experiment.
The reserved final partition remains unused; no independent result is claimed.
Ignored local artifacts are in `build/grammar-conservative-20261026/`; the
adjacent aggregate JSON binds model, plan, corpus, records and result hashes.

All **27 Python tests passed**, covering the new stricter criterion, exact
95%/97.5% count boundaries, volume, correct-word/prior/installed retention,
determinism, empty/no-policy behavior, malformed/nonfinite input and protection
selection:

```sh
PYTHONPATH=tools/typing_experiments python3 -m unittest test_contextual_policy_calibration test_grammar_training_groups test_grammar_contrast_corpus test_grammar_context_features
```

No application asset, threshold or installed APK changed; no phone commands were
issued. This preserves the previously accepted model on Fold.

## Next training evidence

Inspection of the actual selected training pools found equal edit costs for
both forms in **all 120 infinitive/finite contrast typo groups**. The same is
true for all 42 selected noun contrasts. The disclosed failing infinitive cases
instead favor the finite rival by keyboard edit cost (0.75 versus 1.0). Merely
adding more shortest shared deletions leaves that asymmetry poorly represented.
The next authored corruption selector should explicitly cover different edit
profiles using production verification, without word-specific exceptions.

One remaining short-adjective example also lacks a preceding subject that fixes
singular/plural number: a later subject can determine the desired form. Its
left-context-only ranking result cannot establish that a forced plural correction
is justified. Improving this class requires separately tested right-context
refinement or abstention, rather than a memorized replacement.
