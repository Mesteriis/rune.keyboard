# Frozen experimental base plus structural residual ranking

The new v9 experiment keeps the exact v6 **experimental** 178-field forest and
learns a separate 56-field structural adjustment. This is not the installed
146-field production scorer. No application model, source loader or APK changes
in this slice, and the fitted composite remains unqualified.

## Composition and numeric contract

The head receives fields 146..201 of the existing 202-field vector: 16 frozen
following-context fields, applied-word identity, 15 case/gender fields and 24
continuation fields. It cannot directly inspect the first 146 lexical/frequency
fields or any expected label. The old forest still supplies those ranking
effects through its raw score. Inference adds the two raw scores and applies
`.8 * tanh(sum / 4)` once. It does not add independently bounded scores.

`right_context_residual_ranker` provides a NumPy-free scalar implementation and
strict RET2 decoding for the explicit 178/56 profiles. It retains the existing
per-file 65,536-byte, 128-tree, depth-six, finite/bounded-weight, feature-index,
truncation and trailing-byte checks. Invalid input vectors fail explicitly.
Finite large doubles convert to float32 infinity for split comparison, matching
the existing runtime semantics; NaN/infinite input doubles are rejected.
Models and structural slices do not alias mutable caller data. A zero head
exactly preserves the base score; that invariant does not imply a fitted head
preserves every base decision.

`residual_tree_batch` uses NumPy in the existing training runtime to avoid a
slow scalar loop over 428,865 candidate rows. Inputs compare in float32, leaves
accumulate in original tree order at float64 precision, and scale/bias apply
after accumulation. Tests include all six leaf bits, multiple trees, an
independent legacy scorer and cancellation-sensitive accumulation order.

On the actual exported forests, 494 real training candidate vectors and 404
boundary probes around 101 distinct splits match the independent old
`rank_refinement.tree_score` exactly for raw sum, bounded score and batched sum.
Those arbitrary numeric probes do not establish linguistic quality.

## Fitting and artifact identity

Training retains the exact v8 30,512 groups / 428,865 candidates, labels,
counterfactual applied states, 38 supervised families and saved group weights.
The 3,701 strong wrong-applied revision groups still have weight three; other
groups have weight one. No natural calibration/holdout sentence is added to
supervision, and no hyperparameter/threshold is changed to produce these results.

The old forest's raw scores initialize CatBoost's per-candidate baseline. Only
the new structural head is fitted: 128 depth-six trees, learning rate .05,
seed 25102026, PairLogitPairwise. CatBoost stores pool baselines at float32;
the maximum offset difference from the preserved base sum is
2.3838947527110577e-7. Inference keeps the original base sum rather than rounding
it for training convenience. Actual CatBoost prediction checks confirm baseline
addition exactly, head export error below 3.16e-8 and combined export/baseline
error below 2.68e-7. Scalar and batched exported composition agree exactly.

The two exported binaries are separately validated and total 78,888 bytes.
`composite.json` binds the exact two filenames, hashes, layouts and composition;
its hash identifies the composite, rather than pretending it is one RET2 file.
Plans and model receipts are frozen before disclosed calibration scoring.
The Kotlin loader does not register the new head/profile or composite.

## Training diagnostics and retained weakness

The head fits 11,020/11,103 strong targets (v8: 10,480), 12,952/12,957 unresolved
retention labels and 6,127/6,452 correct-original labels. That last figure is a
regression: v8 and the frozen base fit all 6,452 correct-original labels.
The head lacks direct original-validity/lexical inputs, so its score-level
failure must not be confused with a production protection guarantee. Source-v3
continues to require independent original protection before scoring; this is
checked separately in the full diagnostic pipeline.

Examples of training-only scenario fits include 1,191/1,197 nominal closure,
397/399 gendered past copula, 398/399 plural copula and 204/240 competing noun
frames. Training improvement is not independent quality or activation approval.

## Same-source calibration comparison

All three models use the same source-v3, 7,905 disclosed calibration rows,
743 scored pools and 1,756 completed-prefix decisions. Trace validation binds
each accepted step to its actual score, margin and prefix. Expected labels
appear only in diagnostics after scoring. No independent holdout is read.

| Group | Frozen v6 correct / wrong | v8 correct / wrong | v9 correct / wrong |
| --- | ---: | ---: | ---: |
| Matched copula | 52 / 0 | 40 / 0 | 52 / 1 |
| Direct subject | 120 / 0 | 53 / 1 | 43 / 1 |
| Agreement-role negative | 4 / 42 | 46 / 13 | 46 / 9 |
| Hard other-part negative | 0 / 10 | 0 / 22 | 0 / 9 |

These are first **unthresholded source-certified proposals**, not accepted
policy precision or device edits. V9 recovers 21 of the 22 copula paths lost by
v8 in the earlier source-v2 comparison. Against the same-source v6 baseline it
still loses six correct copula paths and gains six others; the unchanged total
52 does not prove behavior preservation. Compared with v8, wrong paths fall
36 → 20, but 22 are removed and six different wrong paths are introduced.
Compared with v6, 36 wrong paths disappear and four different ones appear.
Direct-subject acquisition still loses substantial useful behavior.

The separately calculated positive-margin raw pipeline has zero correct-input
control changes but four losses of already correct Rune output. Their exact
previous → proposed pairs are `инициативе → инициативна`,
`представителем → представителен`, `агрессивная → агрессивна`, and
`виноваты → виновны`. The first two cross noun/predicate roles, the third
changes attributive adjective role, and the last changes adjective lemma.
One cue is a capital single-letter initial followed by a dot, which source-v3
can mistake for a completed nominal/clause. Those disclosed natural rows are
diagnostics, not new supervised training or independent qualification.

The v8 positive-margin metric excludes its two zero-margin steps and therefore
counts 138 correct proposals, rather than 139 in the unthresholded table. V9
and v6 have no zero-margin steps. Correct-input protection and preservation of
an already correct automatic correction are distinct checks; the former does
not excuse the four latter losses.

All diagnostic threshold fits still fail minimum-100/zero-wrong requirements.
The full corpus-volume gate remains failed as well. No policy is selected or
enabled. The next fixes must address initial/abbreviation evidence, changes of
an already applied word's role/lemma, and missed nominal acquisitions. Removing
these checks, keeping only the successful subset or blindly repeating fitting
would not establish the requested sentence-correction behavior.

## Checks

- `python3 -m unittest discover -s tools/typing_experiments -p 'test_right_context*.py'`:
  136 tests pass, including seven new scalar/composition tests.
- `build/typing-ranker-v2-venv/bin/python -m unittest discover -s tools/typing_experiments -p 'test_residual_tree_batch.py'`:
  five tests pass in the existing NumPy training runtime.
- Actual-forest numeric reference parity, CatBoost baseline/composition checks,
  both diagnostic scorer processes and trace/path comparisons pass.
- Installed asset hashes remain unchanged. Model quality/corpus gates fail;
  Android/JVM code, APK build, install and device acceptance are unchanged/unrun.

The [evidence receipt](2026-10-27-right-context-residual-ranking-evidence.json)
binds sources, tests, training plans, both forests, full vectors/weights,
reference parity, native-pool diagnostic traces and rejected qualification.
