# Authored prefix training and first-action continuation calibration

The continuation experiment now teaches an explicit wait state before a bare
nominal can resolve its role. It remains outside the running keyboard. No model,
source policy or dictionary was installed, and no APK was built in this slice.

## Training construction and real candidate pools

`right_context_continuation_corpus.generate` accepts only an authored train
corpus. It derives new prefixes from the previous 9,572 authored records and
preserves their existing 38 supervised families. No natural calibration or
holdout sentence is used as supervised training.

The three old immediate-nominal scenarios are replaced with explicit timelines.
For example, the completed ` он ` retains the counterfactual applied word, while
` он .` and a completed later finite copula can supply an authored target.
Additive/comma nominal links wait for closure unless an adjacent left plural
copula supplies number. Alternative roles and ordinary subject-plus-finite-verb
continuations retain the prior output instead of inventing an adverb absent from
the actual pool. An unanchored reciprocal also retains the prior output; the
authored plural-positive counterpart has a left plural copula. These templates
express specified training intent, not universal syntactic admission rules.

Every derived correct-original control retains its original at every emitted
prefix, including contexts that appear to favor another form. Other prior
authored scenarios remain unchanged. Parent records are not mutated. Duplicate
derived model inputs with contradictory expected targets are rejected.

The generated corpus has 31,916 rows and 1,201 label-blind unique native queries.
The current hash-bound native controller replays all queries. Existing selection
requires complete retrieved pools and real applied/target/contrast candidates;
it never inserts a missing target. It selects 30,512 groups / 428,865 candidate
rows and excludes 1,404 records for incomplete pools. Applied states remain
counterfactual training contrasts, not evidence of runtime ownership.

An additional whole-corpus identity audit finds 25,378 distinct actual input
tuples and 6,538 repeated authored input rows with zero contradictory targets.
Those repeats remain training weight, not independent samples or qualification
volume. They should be accounted for before drawing conclusions about corpus
balance. Correct-original controls can use the existing explicit manual
retention pool; that is not automatic source admission.

## New evaluation protocol

`right_context_continuation_calibration` is separate from frozen word-count-only
calibration. It validates each step against actual events of the exact recorded
suffix, with strictly increasing typed prefix lengths. Completed word counts may
stay equal when punctuation creates a new decision point. Invalid, synthetic,
unfinished or reordered events cannot become source-certified steps.

Only the first threshold-crossing action counts. A later correct proposal cannot
erase a first wrong action. Original/control losses and the minimum 100 new
correct changes remain enforced. The zero-new-wrong calibration requirement is
still precision 1.0; the user's 95% floor is not used to weaken the declared
zero-loss experiment requirements. Policy fitting validates the event paths
once before the threshold grid, not once per threshold pair.

## First 202-field fit (v7)

The model uses 128 depth-six trees, learning rate .05, seed 25102026 and the same
PairLogitPairwise loss as v6. The new 202-field layout retains the first 178
fields exactly. NumPy storage is preallocated rather than retaining hundreds of
thousands of Python feature tuples. The binary is 39,444 bytes, SHA256
`bf428a1c497dd897fd21b5768fd3b01e0dfef587b3cdd834fcd229d941eed6be`.

Training-only top choices match 12,951/12,957 insufficient-evidence labels,
10,480/11,103 strong labels and all 6,452 correct-original controls. This is not
an independent quality measurement. It still fails 402/1,197 authored nominal
closure targets: 400 of those failures preserve a wrong already applied word.
The problem spans masculine, feminine, neuter and plural targets, rather than
one missing gender. Raw typo acquisition and revision of an already applied
wrong form are therefore distinct learning problems.

## Available calibration diagnostic

Both the old v6 and new v7 were scored on the same continuation-event timeline,
same 7,905 disclosed calibration records, actual native candidate pools and
unchanged source-v2 certificates. This isolates the effect of the new fit from
additional punctuation decision points. The new model evaluates 8,007 prefixes
over 1,521 pools. Neither model evaluates holdout or passes the diagnostic fit.

The first unthresholded source-certified actions are:

| Group | v6 correct / wrong | v7 correct / wrong | v8 correct / wrong |
| --- | ---: | ---: | ---: |
| Matched copula | 52 / 0 | 52 / 0 | 40 / 0 |
| Direct subject | 236 / 2 | 52 / 3 | 75 / 1 |
| Agreement-role negative | 0 / 138 | 0 / 12 | 1 / 23 |
| Other-part hard negative | 0 / 25 | 0 / 25 | 0 / 29 |
| Other-part ordinary negative | 0 / 1 | 0 / 0 | 0 / 0 |

These counts are not deployable policy behavior. Fewer wrong changes accompany
a large loss of useful changes, so this is not accepted as a quality improvement
or a safe reduced production scope. No diagnostic policy satisfies the unchanged
volume/precision requirements. The source-v2 still has its old possible-subject
interpretation and can veto a plural-list repair as a singular-subject conflict;
that source issue is not resolved by the numeric training experiment.

The full data-availability gate also remains false: the available matched-copula
cohorts still do not reach 400 per part. No holdout or production qualification
is claimed by this calibration exercise.

## Revision-weight follow-up

The v8 fit keeps the exact v7 groups, vectors, layout and hyperparameters. Its
plan is frozen before fitting: group weight 3 applies only to strong authored
targets that change an already applied non-original form; all other groups,
including correct-original and unresolved-role controls, retain weight 1.
The diagnosis comes from authored training failures, not from relabeling natural
calibration failures. There are 3,701 weighted groups. Per-candidate group weights
are checked constant within every group and saved as a hash-bound array.

The frozen v8 binary is 39,444 bytes, SHA256
`231f9dd7b785c9b35f33bef42978e8828c1d915aa686b3222104ba87feec7c89`.
It fits 1,178/1,197 authored nominal-closure targets rather than 795, but the
total strong-label top choices remain 10,480/11,103: errors move into copula and
other scenarios. Unresolved retention is 12,948/12,957, and all 6,452
correct-original training controls still select their original. These training
outcomes do not establish quality or noninterference on real input.

The same 7,905 disclosed calibration records and 8,007 prefix scores give the v8
column above. The diagnostic fit fails again, with no accepted threshold policy.
Neither v7 nor v8 is selected for activation. The next investigation must separate
role/timing learning from existing copula behavior and audit candidate decisions
and source-v2 refusals; repeating epochs or adjusting one aggregate weight is
not supported as the next fix by these mixed outcomes.

## Checks and limits

All 120 `test_right_context*.py` tests pass, including seven new corpus tests and
five new continuation-calibration tests. Native replay, hash-bound pool selection
and scalar/CatBoost numeric checks are recorded separately. The first replay
wrapper attempt failed before launching the controller because its output
directory was missing; that failure log is retained, and the directory-creating
retry succeeds. No controller or application source changed in this slice.
JVM tests, lint, APK build and device acceptance were not rerun.

Kotlin parity for the new layout, explicit source/timing integration, sufficient
independent data, quality qualification and real editor/Fold acceptance remain
required. Existing installed assets are checked unchanged by both training fits.

The [evidence receipt](2026-10-27-right-context-prefix-training-evidence.json)
binds code, plans, model binaries, pool replay, raw tests and diagnostic outcomes.
