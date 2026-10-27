# Symmetric strong-intent weights: controlled ablation

Equalizing raw acquisition, correct-state retention and wrong-state repair
increases useful diagnostic proposals, but also increases wrong proposals and
does not fix the rare noun/full-adjective training gaps. This experiment is
rejected for deployment. Installed Android assets and Fold are unchanged.

## One controlled change

`right_context_training_weights.py` defines a separate offline policy. Every
strong unknown-original training row receives weight three, regardless of its
applied state. Unfinished/unresolved rows and correct-original controls stay at
one. Non-training, non-Russian, incomplete, unknown-kind or inconsistent labels
fail explicitly. Model scores, words' parts of speech and scenarios do not
select this policy's weights. No examples, targets, pools or features change.

The prior policy used weights 1/1/3 for raw acquisition, correct-state retention
and wrong-state repair. The new policy is 3/3/3. Each strong intent has 4,573
groups, so its total weight becomes 13,719. Exactly 9,146 group weights change.
All 14,781 unresolved and 7,772 protected-original control weights remain one.
This also raises the total strong-to-control/unresolved weight ratio; the
experiment is not a claim of fixed total training-weight mass.

A controlled-ablation audit confirms byte-identical groups, vectors and frozen
base forest, plus identical profile, hyperparameters, qualification requirements,
asset/count bindings and raw baselines. Training still has 36,272 groups,
503,679 candidate vectors, 242/96 features and 42 supervised families. It uses
the same 128 depth-six trees, .05 learning rate, seed 25102026 and pairwise loss.
The old weights are preserved separately; the prepared data directory is not
modified. The new weight receipt and source hashes are frozen before fitting.

Composite model manifest SHA256:
`1e1f154031d21e1c2732dcd2aacf80c5365ab989a8b62959f569cfdab1fcb56d`.
The model is frozen before natural diagnostic scoring; no disclosed natural
failure becomes a training row or a weight-selection input.

## Actual numerical and training results

Scalar, batch and independent legacy composition agree exactly on 569 actual
training vectors and 520 probes around 130 distinct split borders. Exported
head error versus CatBoost is below 5.28e-8; combined error including baseline
quantization is below 2.77e-7. The numeric reader/profile is unchanged.

Strong training targets improve from 13,270/13,719 to 13,523/13,719. Unresolved
retention falls from 14,765/14,781 to 14,560/14,781; correct-original score-level
controls fall from 7,768/7,772 to 7,750/7,772. These training regressions must not
be hidden by the runtime source's original-word protection.

Instrumental-noun strong targets remain 4/36: raw acquisition and wrong-state
repair both stay 0/12, while correct-state retention stays 4/12. Full adjective
after ordinary finite remains 0/47 raw acquisitions and 47/47 retentions;
wrong-state repair drops 45/47→38/47. The aggregate therefore falls 92/141→85/141.
New oblique-predicate strong targets still fit 1,134/1,134.

For all 47 raw full-adjective cases, the model still retains the unknown input.
The residual target-minus-winner margin changes from -0.5375 to +0.03315, which
is insufficient to overcome the unchanged base margins (-1.603..-0.126).
This confirms a changed score contribution, not successful acquisition or an
irreducible inability to represent the distinction.

## Same natural diagnostic and source-v5

The same 7,905 disclosed calibration records, 739 scored pools and 1,752 actual
continuation events are compared. Accepted paths exactly match recorded traces
for v9, v11, v12 and v13.

| Model | Correct proposals | Wrong proposals | Prior-correct losses | Control changes |
| --- | ---: | ---: | ---: | ---: |
| v11 | 101 | 7 | 0 | 0 |
| v12 | 120 | 9 | 0 | 0 |
| v13 | 132 | 11 | 0 | 0 |

These are first source-certified positive-margin diagnostic proposals, not an
accepted threshold policy, independent quality or device actions. Relative to
v12, v13 gains 16 correct individual paths and loses four. Matched-copula correct
proposals rise 48→54, direct-subject 36→43 and agreement-role fall 36→35.
All four previously correct disclosed outputs remain unchanged.

Raw proposal precision falls 93.02%→92.31%, below the user's 95% floor. The
unchanged 33-point threshold fit fails minimum-100/zero-new-wrong requirements.
Natural cohort volume still fails, no holdout is scored, and no weights/profile
are registered with the keyboard.

## What the ablation rules out and what remains

Symmetric strong-intent weighting alone does not repair these rare target gaps.
The dictionary target-signature audit finds 11,199 pure-ADJS strong groups, only
252 pure-NOUN groups and 705 pure-ADJF groups among 13,719 strong groups. Other
groups retain mixed POS signatures; those signatures are possible dictionary
analyses, not proven contextual roles. There are no pure PRTS targets in this
training set. Increasing the global weight of all strong examples has not
balanced target-part exposure.

The next controlled experiment should address target-role/signature frequency
while preserving every existing category and reporting mixed readings honestly.
This audit does not prove a particular frequency weighting will generalize;
neither another unchanged epoch nor dropping hard cases is justified. The
existing weight module/source binding remains frozen for reproducibility.

All 185 default `test_right_context*.py` tests pass, including five new policy
tests. Weight preparation, input/baseline identity, training/export, actual-model
numeric parity, first-action scoring, trace/path comparison, intent/score
decomposition and dictionary target-frequency audits complete successfully.
Quality, corpus-volume and the stated score-level training checks do not pass.
No JVM, lint, APK, installation or device acceptance is claimed for this slice.

Artifacts are under `build/right-context-symmetric-residual-v13-20261027/` and
`build/right-context-v13-source5-traced-20261027/`, bound by the evidence receipt.
The wider runtime ownership/cancellation/Undo, dictionary parity, multi-role and
participial repair, and independent qualification work remains outstanding.
