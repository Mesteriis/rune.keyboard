# Capped target-signature balancing: rare targets improve, quality still fails

The target-frequency experiment improves rare full-adjective and noun training
cases without changing the examples or total strong group-weight mass. Natural
diagnostic proposals improve modestly, but remain below requirements. No model
is selected or registered; Android assets and Fold are unchanged.

## Declared weighting rule

`right_context_signature_weights.py` adds a separate offline policy; the frozen
symmetric-weight module is unchanged. Each strong row's target is looked up in
the pinned dictionary. All possible POS values form its sorted signature, so
mixed readings stay separate rather than being assigned a preferred contextual
role. No contextual parse, model score or natural evaluation label selects a
training weight.

For signature count `n` and largest count `m`, the multiplier is
`min(8, sqrt(m/n))`. Its weighted mean over strong groups normalizes every
factor before multiplying the symmetric base weight three. Thus total strong
group weight remains 41,157 before float32 export. Every unresolved and
correct-original control keeps weight one. All groups and all signature classes
remain; none are removed or resampled. Invalid/non-training labels, missing
dictionary evidence and unseen signatures fail explicitly.

The fitted normalization is 1.716936512701234. Pure-ADJS group weight becomes
1.7473, pure-ADJF 6.9641 and pure-NOUN 11.6481. Mixed signatures have weights up
to 13.9784; the cap eight applies to the **unnormalized multiplier**, not the
final group weight. Each of the three strong intents retains total weight
13,719 before export (13,718.999844 after float32 rounding). This conserves
group-weight mass, not a claim that every group has equal pair count/loss mass.

## Controlled fit and numerical verification

All 36,272 groups / 503,679 vectors, targets, pools, feature values, frozen base,
raw baselines, 242/96 profile, source-v5, qualification rules, counts/assets and
hyperparameters are identical to v13. Only 13,719 strong group weights change.
The supervised family set stays at 42. The plan and dictionary/weight receipt
are frozen before fitting; the model is frozen before natural scoring.

Training uses the same 128 depth-six trees, .05 learning rate, seed 25102026 and
pairwise loss. Composite manifest SHA256:
`8fdbd315a7db9238ef4feb2cf98b58db835beb23ea136c5f7400f9639f5e3365`.
The old weights and their source bindings remain intact.

Actual scalar, batch and independent legacy composition agree exactly on 569
real training vectors and 512 probes around 128 distinct split borders. Head
export error versus CatBoost is below 3.66e-8; combined error including baseline
quantization is below 2.58e-7. These checks establish numerical consistency,
not a deployment-quality score.

## Rare training results and regressions

| Strong training slice | v13 | v14 |
| --- | ---: | ---: |
| Full adjective after ordinary finite: raw acquisition | 0/47 | 35/47 |
| Same frame: repair wrong applied state | 38/47 | 45/47 |
| Same frame: retain correct applied state | 47/47 | 47/47 |
| Instrumental noun: raw acquisition | 0/12 | 2/12 |
| Instrumental noun: repair wrong applied state | 0/12 | 2/12 |
| Instrumental noun: retain correct applied state | 4/12 | 12/12 |
| Oblique-complement predicate targets | 1,134/1,134 | 1,134/1,134 |

The full-adjective frame rises 85/141→127/141 and instrumental-noun targets
4/36→16/36. This demonstrates useful learning beyond a blanket applied-word
lock, while most raw noun acquisition/repair cases still fail.

Overall strong target fit falls 13,523/13,719→13,439/13,719 as the objective
redistributes weight. Unresolved retention falls 14,560/14,781→14,285/14,781 and
correct-original score-level controls 7,750/7,772→7,738/7,772. Even new oblique
correct-original training controls fall 288/288→282/288. Runtime source
protection is separate from these score-level regressions; they remain visible.

## Same natural first-action diagnostic

The unchanged 7,905 disclosed calibration records, 739 scored pools and 1,752
actual continuation events are compared. Accepted paths match recorded traces
exactly across all five recorded models in the comparison.

| Model | Correct proposals | Wrong proposals | Prior-correct losses | Control changes |
| --- | ---: | ---: | ---: | ---: |
| v11 | 101 | 7 | 0 | 0 |
| v12 | 120 | 9 | 0 | 0 |
| v13 | 132 | 11 | 0 | 0 |
| v14 | 136 | 10 | 0 | 0 |

These are first positive-margin source-certified diagnostic proposals, not
selected-policy precision, independent test accuracy or device edits. V14 gains
seven old correct paths and loses three versus v13. Correct matched-copula
proposals change 54→52, direct-subject 43→50 and agreement-role 35→34. All four
previously correct disclosed outputs remain unchanged.

Raw proposal precision is 136/146 (93.15%), below the user's 95% floor. The
unchanged 33-point threshold search fails minimum-100/zero-new-wrong requirements.
Full natural cohort volume remains insufficient; no holdout is scored.

## Remaining evidence needs

The frequency hypothesis has supported some rare-target learning, but weight
changes do not add missing evidence. Remaining disclosed errors include
short-participle/adjective competition, modality/infinitive agreement, noun
versus predicate intent and full/short or gender/number choices. Some choices
are made at the first copula before later context could distinguish roles.
No pure PRTS targets exist in the present strong corpus, and source-v5 only
certifies pure ADJS targets. Those coverage/admission limits need explicit
paired authoring, features and source tests rather than another unchanged fit
or a blacklist of disclosed failure words. Preserve genuine role repairs and
first-action timing in that work.

All 190 default `test_right_context*.py` tests pass, including five new policy
tests. Weight-mass/input/baseline identity, training/export, actual-forest numeric
parity, first-action scoring, trace/path comparison and intent/score/error audits
complete successfully. Quality, corpus-volume and the stated training-control
checks do not pass. No JVM, lint, APK, installation or device acceptance is
claimed for this host-only slice.

Artifacts under `build/right-context-signature-residual-v14-20261027/` and
`build/right-context-v14-source5-traced-20261027/` are bound by the evidence
receipt. Runtime dictionary parity, following-input ownership/cancellation/Undo,
multi-role/participial correction and independent qualification remain part of
the wider objective.
