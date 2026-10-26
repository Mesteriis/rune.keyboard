# Learned infinitive revision: offline qualification

The globally substituted profile ranker failed retention constraints. This
experiment retains the installed contextual result and evaluates the learned
ranker only as a separate grammatical revision component. Model bytes are still
`20409f7407fea7381d223351570b784adaed46357c5cd1643a28d285961b23cd`;
the installed general model remains `4d7bf2a9477b588046a1187c11e206bd1ca6f73180e8abf3b21c84f024a783f0`.

## Scope and incremental metrics

`grammar_revision_scope.py` requires all of the following before a candidate can
even reach score thresholds:

- The actual installed result is an existing replacement, not the editor's original.
- The original is unknown/unprotected; its protection evidence is explicit.
- The proposed word was retrieved in the complete joint pool and independently
  passes the existing source-admission decision.
- Every dictionary analysis of the previous word is finite `VERB`; every analysis
  of the proposal is `INFN`; their dictionary lemmas intersect.
- The bounded preceding context has the existing infinitive cue. Ambiguity,
  punctuation boundaries, absent dictionary evidence and other lemmas decline.

The scope itself never ranks, grants admission or edits text. Outside it, the
installed output is retained. `grammar_revision_calibration.py` counts changes
relative to that installed result, keeping the actual editor original separately
in audit records. Its required minimum is **100 newly correct revisions**;
successful corrections from older engines cannot satisfy it. Precision uses only
this component's changed proposals, with zero installed-correct losses or
correct-word changes.

An initial probe of the 5,574 eligible groups in the general calibration corpus
found no applicable revisions. That corpus could not qualify this component.

## Focused, source-disjoint evaluation

Before source selection or scoring, the plan fixed 500 contexts per partition,
at most 16 per family, 97.5% calibration precision, 95% final precision and minimum
100 incremental correct revisions. `grammar_focus_forms.py` verifies a natural
source infinitive, its same-lemma finite rival and an unknown shared corruption
whose edit costs are 1.0 and 0.75 respectively. No model response selected source
contexts or corruptions.

The source is the existing hash-pinned public Tatoeba Russian detailed dump,
licensed CC BY 2.0 FR. Sentence IDs/contributors are retained locally with source
references. All prior source IDs, prediction contexts and authored contrast
families were excluded. Calibration and holdout are also lemma-family disjoint.
An additional audit found no selected normalized sentence hash in 145,382 prior
rows carrying such hashes, and no calibration/holdout sentence-hash overlap.
This is sentence/context separation, not author independence or globally novel
vocabulary: broad training can contain the same word families in other contexts.

Each partition has **500 contexts / 2,000 inputs**, over 155 calibration and 148
holdout families. Each context supplies the fixed adjacent typo plus three
retention inputs: the correct infinitive, the correctly spelled finite form, and
a protected token. A grammatical disagreement does not authorize changing an
already correctly spelled finite original.

The unchanged 33-by-33 calibration grid selected score
`0.41741117881683354`, margin `0.004802324582884099`, then froze them before any
holdout score. Calibration produced **180 correct / 0 wrong revisions**. The
independent focused holdout produced **158 correct / 0 wrong revisions**, zero
installed-correct losses and zero control changes. This is focused synthetic
typing in natural sentence contexts, not general natural phone-typing accuracy.

## Separate broad holdout

The same frozen policy was then tested on the previously unused 3,000-context
general holdout: **12,000 inputs, including 6,000 correct/protected controls**.
Its normalized sentence hashes also had no overlap with prior excluded rows.
The component produced **one additional correct revision, zero wrong revisions**,
with zero installed-correct losses and zero global control changes. The earlier
frozen broad gate requires at least 95% precision if any revision occurs and
zero losses/control changes. Focused volume and precision are reported separately;
they are not diluted with older successful spelling corrections.

All 339 proposed pairs across focused calibration/holdout and broad holdout have
matching non-null lemma IDs in the actual packaged morphology index. This binds
the prototype's lemma relation to the existing Android resource for these cases;
it is not a claim of exhaustive dictionary equivalence.

## Checks and pending Android integration

All **41 Python tests passed**:

```sh
PYTHONPATH=tools/typing_experiments python3 -m unittest test_grammar_revision_calibration test_grammar_focus_forms test_grammar_revision_scope test_contextual_policy_calibration test_grammar_training_groups test_grammar_contrast_corpus test_grammar_context_features
```

Kotlin candidate/baseline replays completed all 4,000 focused inputs and 12,000
broad inputs. Labels stayed outside the harness. Revision projection and scores
were computed offline; the current Kotlin controller did not execute the new
revision component. No claim of its editor ownership, exact Undo, Android timing
or physical acceptance follows from this result.

The adjacent JSON binds model, scope, policy, corpus, separation and result
evidence. Ignored artifacts are under `build/grammar-revision-scope-20261026/`,
`build/grammar-focused-eval-20261026/` and `build/grammar-revision-broad-20261026/`.
Android integration, parity, full controller replay and Fold acceptance remain
pending. No application assets or installed APK changed in this offline slice.
