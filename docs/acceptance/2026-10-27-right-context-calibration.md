# Following-context calibration refusal and acquisition training

The [separate following-context model](2026-10-27-right-context-training.md)
was evaluated on the frozen 1,600-row calibration part (400 corrupted words and
1,200 correct/protected controls). It **did not qualify**. No policy was frozen,
no right-context model scored the holdout, and no application asset, Android
source, device setting or installed APK changed in this milestone.

## Admission and coverage findings

`RightContextRevisionScope` explicitly separates the original input, an actually
admitted previous replacement, completed right context, the exhaustive retrieved
pool, dictionary analyses, positive packed lemma identities and independent
proposal-source admission. Unknown/missing/ambiguous certificates retain the
previous output. It cannot acquire a correction when the previous engine kept
the original, revive an unadmitted replacement, or edit correctly spelled or
protected originals. Every analysis of the old/proposed short adjective must
agree on lemma and number; the proposal must resolve a completed right number
conflict without introducing another number or gender conflict. This is offline
experimental scope, not an editor-ownership certificate.

The initial scope checked number agreement but omitted explicit gender conflict.
It left two source-admitted proposals: one correct and one wrong. The wrong
proposal was masculine `несопоставим` before neuter `было`, where the source form
was `несопоставимо`. Scope version 2 now rejects a proposal that conflicts with
an available copula/subject gender cue. The model is unchanged; it does not
resurrect a lower-ranked candidate after refusal. The initial scope snapshot is
retained and verified against the original scoring-plan digest.

The repeated calibration with scope version 2 yields:

| Observation | Count |
| --- | ---: |
| All rows / controls | 1,600 / 1,200 |
| Exact, admitted previous target-word replacements | 66 |
| Pools reaching new-model comparison | 18 |
| Candidate/original scores calculated | 251 |
| Proposal-source admission refusals | 16 |
| Explicit gender-conflict refusal | 1 |
| Eligible correct / wrong proposals | 1 / 0 |

The other refusals are 1,415 without an admitted previous replacement, 119 with
changed input/prefix, 29 with a previous word outside the unambiguous short
predicate scope, and 19 without a completed right number conflict. The declared
minimum of 100 new correct revisions is not met. A high percentage over a single
proposal would not qualify this component. The existing 95% requirement,
zero-wrong/control-loss requirements and minimum volume were not relaxed.

The underlying 400 typo rows make the coverage problem explicit: the existing
controller leaves 278 originals unchanged. Such errors need a separately
qualified acquisition path, not merely reconsideration of old replacements.
Early counts of non-null `autoEdit` are insufficient: a retained edit can belong
to another span. The revision evaluator additionally checks the exact original,
applied span, committed start and correction-generation identity.

## Exact source refusal evidence

The replay observer now exports `jointSourceRefusals` alongside its existing
admission booleans. Both fields come from one invocation of the same pure
`jointAdmissionEvidence`; there is no duplicate decision path, source override
or ranking-state mutation. Allowed decisions have a null refusal; denied
ones have an explicit existing enum (or `NOT_QUALIFIED` for missing detail).

A fresh source-bound Kotlin harness replayed all 1,600 calibration rows. Every
pre-existing field matched the previous observations exactly, excluding only
the two existing host-duration fields. This includes model scores, admission,
candidates, editor commands, final text and Undo. All 5,514 candidate decisions
have consistent booleans/reasons: 366 allowed, 5,148 refused. The 16 rejected new
proposals are all `WINNER_AMBIGUOUS`.

Inspection shows all 16 proposed winners are dictionary-known and have a positive
packed lemma and one dictionary lemma/short-adjective reading. Each complete
pool also contains a plausibly close unknown/ambiguous rival, which the existing
guard refuses before treating complete model comparison as resolving that rival.
This explains the refusal without claiming the candidate itself is ambiguous.
The guard remains unchanged. Resolving that class requires its own measured
contextual source admission; this diagnostic is not authorization to ignore it.

## Input fidelity audit

The observer also exposes 119 pre-boundary input differences. The new audit
categorizes them without rewriting any row: 87 case-only changes, 8 changes to
whitespace runs, and 24 changes affecting token boundaries. All 119 retain the
same non-whitespace characters when ignoring case, but token merges/splits and
spacing around punctuation remain distinct from exact ownership evidence.
All are still refused by this evaluator. No normalization was used to readmit
them or improve calibration numbers. The baseline restores the exact observed
pre-boundary text after Backspace in all 1,600 rows.

## Explicit raw-original training state

`right_context_contrast_corpus.py --copula-coverage --original-acquisition`
adds the dictionary-unknown original as another explicitly authored applied
state. With strong completed context, its label is the intended retrieved form;
with insufficient evidence, its label is the unchanged original. Correct-word
retention controls remain unchanged. Query identity still contains only preceding
text and original input; labels/following context never enter candidate retrieval.
This is authored counterfactual training, not silent learning from applied edits.

The expanded corpus has 4,872 rows over the same 24 training families. A fresh
current-harness replay ran 472 distinct queries; the strict selector kept
4,738 groups / 71,398 candidate rows and excluded 134 incomplete-pool rows.
All accepted corruption edit costs still match production metadata.
The frozen third model keeps 163 features and the same 128 depth-five trees,
learning rate 0.05, seed and objective. Its 22,036-byte binary SHA256 is
`170205268883a58d9a7968391b9ccf7aa753b838d3176287c4a73a63ae8af808`.

| Training category | Target ranked first / groups |
| --- | ---: |
| Unknown original, existing applied form | 1,897 / 1,904 |
| Unknown original, raw original still applied | 945 / 952 |
| Correct original | 658 / 658 |
| Weak context, existing applied form | 816 / 816 |
| Weak context, raw original still applied | 408 / 408 |

These are training diagnostics only. The new model has no qualified acquisition
source, has not been evaluated on calibration/holdout, and is not loaded on Fold.
A separate model-binding receipt preserves the unchanged natural corpus and its
training-family exclusions; the holdout remains unscored by every experimental
right-context model.

## Checks and remaining work

All 42 focused Python tests passed, covering source/certificate defaults,
complete pools, lemma identity, explicit gender conflicts, raw-original training
and input audits that do not disguise first-letter loss or word merges.
The current Kotlin observer compiled successfully; its 1,600-row semantic
noninterference audit passed. `git diff --check` passed. No Android application
build or phone check was run because production application code/assets did not
change. No installation or production-quality claim is made from these results.

[The evidence receipt](2026-10-27-right-context-calibration-evidence.json) binds
both calibration outcomes, observer/rival audits and the new training model.
Ignored artifacts are in `build/right-context-qualification[-v2]-20261027/`,
`build/right-context-source-diagnostics-20261027/` and
`build/right-context-training-v3-20261027/`.

Next: qualify contextual acquisition/source admission while retaining original
protection; use exact Rune-owned input context rather than silently normalized
corpus prefixes; freeze a policy before holdout scoring. Kotlin scorer parity,
actual multiword ownership, exact Undo and device acceptance still precede any
application activation.
