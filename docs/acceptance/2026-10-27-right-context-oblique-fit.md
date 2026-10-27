# Oblique-complement supervision and measured fit

Authored positive predicate/complement examples recover some missed natural
repairs, but the new fit still fails quality requirements and damages scarce
instrumental-noun training targets. It is not selected or activated. Installed
assets and Fold remain unchanged.

## Added authored supervision

`right_context_oblique_corpus.py` derives masculine/feminine/neuter/plural short
forms for four existing supervised families: `полезный`, `нужный`, `важный` and
`верный`. Explicit left subject/copula frames support each target agreement.
The complements `аудитории`, `молодёжи` and `команде` must independently have
dictionary dative readings; their alternative readings remain visible. These
are authored training intents, not a general rule that every adjacent nominal
is a complement or every genitive reading should permit a predicate change.

Every shared unknown corruption includes raw acquisition, retaining the right
applied form and repairing the wrong inflection. Correct-original controls and
unfinished-suffix retention are included. Targets and forms come from dictionary
paradigms; no natural failure word or sentence supplies supervision.

Preparation produces 2,016 rows / 156 label-independent replay queries across
all four families, with no missing dictionary forms. Native selection retains
1,800 groups / 30,612 candidate rows: 1,134 unknown-original groups, 288
correct-original controls and 378 unfinished-suffix groups. The other 216 groups
are excluded for incomplete candidate pools. No candidate is inserted to make a
contrast available. Both forms must actually occur in complete joint pools for
unknown/unfinished groups; known controls retain the existing manual-pool route.

All four target agreement roles remain represented. The selected unknown rows
include 756 with a possible genitive reading on the following noun, 378 retaining
the correct applied form and 378 repairing its rival. They are counterfactual
training states, not observed editor actions or independent quality evidence.

## Combined data and frozen fit

The corpus combines with all previous groups to give 36,272 groups / 503,679
candidate vectors. The prior 473,067 vectors preserve all 242 feature values,
labels, group IDs and weights exactly. There are no changed old pools. Across
combined input tuples, 6,649 repeats have consistent targets and there are zero
contradictory labels. The supervised family set stays at 42.

The existing 242/96 reader/profile, source-v5, frozen v6 base, old group-weight
policy, 128 depth-six trees, learning rate .05, seed 25102026 and pairwise loss
remain unchanged. Only the added prepared supervision differs. The plan is
frozen before training and the model before disclosed natural scoring.
Composite manifest SHA256:
`727f06eb2ba9c08ab91a4d55f5527af929f3bab2b12cd68b4e5b6a4464e7424c`.
No receipt correction is required for this fit.

Actual exported scalar/batch/legacy composition agrees exactly on 569 real
training vectors and 476 probes around 119 distinct split borders. Head export
error versus CatBoost is below 4.09e-8; combined prediction error including
baseline quantization is below 2.71e-7. No runtime registration or Android change
is implied by these numerical results.

## Training reveals an unresolved tradeoff

The model ranks 13,270/13,719 unknown-original targets first and 14,765/14,781
unfinished/unresolved labels. Known-original score-level controls fall to
7,768/7,772; runtime source protection is separate from that training regression.
The new oblique targets fit 1,134/1,134, but instrumental-noun targets collapse
from 28/36 in v11 to 4/36. For those 36 noun rows, raw acquisition and repair both
drop to 0/12 and retaining the correct noun drops from 12/12 to 4/12.

The intent audit also corrects an incomplete interpretation of the earlier
ordinary-finite/full-adjective result: its 92/141 training fit is 0/47 raw
acquisitions, 45/47 wrong-state repairs and 47/47 correct-state retentions, in
both v11 and v12. All 47 raw cases retain the unknown input. A focused score
decomposition finds target-versus-winner frozen-base margins from -1.603 to
-0.126, and identical residual margins of -0.5375. The head reinforces raw
retention in this slice; this is not proof of an irreducible input collision or
an overwhelming numerical base-score bound.

The existing weight policy assigns raw acquisition and correct applied-state
retention weight one, but wrong-state repair weight three. For the instrumental
noun scenario these sums are 12/12/36; the added oblique scenario has sums
378/378/1,134. These facts motivate a controlled intent/role balancing experiment
on fixed inputs. They do not prove which weight change will generalize. Do not
drop noun, raw-acquisition, full-adjective or genuine predicate-repair categories
to improve a headline metric, and do not repeat this fit unchanged.

## Fixed natural diagnostic comparison

The same 7,905 disclosed calibration records, 739 scored pools and 1,752 actual
continuation events are evaluated under source-v5. Accepted paths agree exactly
with all recorded traces for v9, v11 and v12.

| Model | Correct proposals | Wrong proposals | Prior-correct losses | Control changes |
| --- | ---: | ---: | ---: | ---: |
| v9 | 141 | 18 | 2 | 0 |
| v11 | 101 | 7 | 0 | 0 |
| v12 | 120 | 9 | 0 | 0 |

These are first positive-margin source-certified diagnostic proposals, not a
selected deployment policy or independent precision. Versus v11, v12 gains 25
correct individual paths and loses six. Correct unthresholded agreement-role
proposals rise 20→36 and direct-subject 29→36, while matched-copula falls 52→48.
Raw proposal precision is 120/129 (93.02%), below the user's 95% floor. The
unchanged 33-point threshold search fails the declared minimum-100/zero-new-wrong
requirements, and full natural cohort volume still fails. No holdout is scored.

The four previously correct disclosed outputs remain unchanged. The two extra
wrong proposals are raw acquisitions preferring short forms where the reference
is a full adjective, consistent with the training raw-role gap. The error audit
records those disclosed failures for diagnosis only, without adding their words
or sentences to authoring. Zero observed prior-correct losses does not erase the
training noun-retention regression or establish broad safety.

## Checks and remaining work

All 180 default `test_right_context*.py` tests pass. Native replay/selection,
dictionary-role exposure, combined target-conflict audit, exact previous-input
identity, training/export, actual-forest numeric parity, first-action diagnostic
scoring, trace/path comparison and score/intent audits complete successfully.
Quality and corpus-volume gates remain failed; training controls have the four
score-level failures stated above. No JVM/lint/APK/device check or installation
is claimed for these host-only changes.

Raw evidence is under `build/right-context-oblique-v1-20261027/`,
`build/right-context-oblique-v12-inputs-20261027/`,
`build/right-context-oblique-residual-v12-20261027/` and
`build/right-context-v12-source5-traced-20261027/`, bound by the accompanying
receipt. Runtime dictionary parity, multi-role/participial source support,
following-input ownership/cancellation/Undo and independent qualification remain
part of the wider objective.
