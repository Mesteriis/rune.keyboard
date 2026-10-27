# Applied-role residual fit and evidence for lemma changes

The prepared 221-field model has now been fitted and checked. Its training
diagnostics improve, but disclosed natural calibration does not improve enough
to select it. A separate grammar-evidence guard prevents one unsupported lemma
change on both old and new experimental models. Neither model/source combination
is qualified or activated; application assets and Fold are unchanged.

## Explicit 221/75 numeric profile

`AppliedResidualRanker` combines the unchanged experimental v6 178-field base
with a 75-field head over fields 146..220. `AppliedResidualForest` is a separate
bounded RET2 reader, leaving the frozen 202/56 implementation and its historical
source hashes unchanged. Both readers retain per-file size 20..65,536, tree count
1..128, depth 1..6, exact dimensions, finite/bounded scale/bias/borders/leaves,
index, truncation and trailing-byte checks. New weights cannot be interpreted by
the old profile. No numeric profile is registered with the Android keyboard.

Both raw forests are summed before the existing `.8*tanh(sum/4)` transform.
The new scalar/batch profile agrees exactly with independent legacy tree math on
510 actual training vectors and 428 probes around 107 distinct split borders.
Actual CatBoost head-export error is below 4.28e-8 and combined prediction error,
including pool baseline quantization, is below 2.70e-7. Exported scalar/batch/raw
reference composition is exact. These are numeric checks, not quality evidence.

## Frozen training and diagnostics

The fit consumes the corrected prepared 32,024 groups / 445,321 actual candidate
rows, including 1,512 authored full/short-adjective role examples across all 24
existing adjective families. Total supervised families remain 38. Groups,
labels, native candidate pools and saved weight-three revision policy are not
changed during fitting. No disclosed natural sentence/target is added to
supervision. The model is frozen before diagnostic scoring.

Training uses the same 128 depth-six trees, learning rate .05, seed 25102026 and
PairLogitPairwise loss. The old forest supplies per-candidate raw baselines; only
the 75-field structural head learns. The two binaries total 78,888 bytes and are
bound by the composite manifest SHA256
`7c80ce024fbed668ba45ae0333388845693534fb422b9841d93159b2f849e5d1`.

Training top choices fit 11,599/11,667 strong targets, 13,516/13,521 unresolved
retention labels and all 6,836 correct-original controls. The last check recovers
the v9 model's score-level correct-original regression. Competing noun frames
fit 240/240; full-adjective attributive frames fit 136/141 and modifier frames
131/141; both short-predicate question frames fit 141/141. These counts are
training-only and do not prove natural role preservation.

## Fixed-data model comparison

The same 7,905 disclosed calibration records, source-v4 and 1,752 scored prefixes
give these first unthresholded source-certified proposals:

| Group | Previous v9 correct / wrong | New v10 correct / wrong |
| --- | ---: | ---: |
| Matched copula | 52 / 1 | 48 / 1 |
| Direct subject | 43 / 1 | 50 / 0 |
| Agreement-role negative | 46 / 9 | 42 / 9 |
| Hard other-part negative | 0 / 8 | 0 / 9 |

The new fit has 140 correct / 19 wrong proposals versus 141 / 19 previously.
Its positive-margin raw pipeline loses four already correct Rune outputs,
versus three previously, while correct-input control changes stay zero. Besides
the three old noun/full-adjective/lemma failures, it introduces
`интимные → интимны` after a completed ordinary finite verb. It is therefore not
selected merely because authored training fits improved.

These proposal counts are not accepted-policy precision, independent accuracy or
on-device changes. Both declared 33-point-grid threshold fits fail the unchanged
minimum-100/zero-wrong requirements. Full cohort availability also still fails.
No holdout is scored and no deployment candidate is frozen.

## Grammar-neutral semantic changes require another source

`AgreementDeltaSource` (source-v5) first delegates every source-v4 check. After
full-pool ranking and source validation, it refuses a narrow unsupported case:
an already applied pure short adjective is replaced with a disjoint adjective
lemma having exactly the same number/gender reading set. Number/gender evidence
cannot distinguish those meanings, so the current agreement source cannot grant
a semantic-change certificate. It does not substitute the next eligible
candidate or hide a rival from model comparison.

This is not a general semantic-correction policy or a blanket previous-word lock.
Raw acquisition, same-family inflection, cross-role transitions and cross-lemma
proposals with different agreement remain available under the existing checks.
A shared possible lemma in an ambiguous surface is preserved. Existing original,
ownership, retrieval, comparison, cost/kind, morphology and initial guards retain
priority. Genuine semantic repair with equivalent agreement still needs a
separately qualified source with lexical evidence beyond this profile; the full
sentence-correction objective is not reduced to agreement-only corrections.

With model/input held fixed, source-v5 changes no score, candidate order, margin
or pre-scoring decision. It adds seven refusals on v9 and eight on v10. For each
model, the only changed accepted path is `виноваты → виновны`; that wrong change
is removed and no correct accepted path is lost. Positive-margin diagnostics are:

| Model/source | Correct | Wrong | Prior-correct losses | Correct-input changes |
| --- | ---: | ---: | ---: | ---: |
| v9 / source-v5 | 141 | 18 | 2 | 0 |
| v10 / source-v5 | 140 | 18 | 3 | 0 |

Both quality fits still fail. The older weights with the new guard are a better
diagnostic baseline than the new fit; none is activated.

## What the error/data audit establishes

New features are not simply ignored: same-lemma evidence occurs in 126,697
training candidate rows and has 37 head splits; different-lemma evidence occurs
in 21,836 rows and has 11 splits. Last-modifier and last-pronoun evidence also
have active splits. The audit checks 564 authored opposite-intent contrast pairs;
none has identical head inputs for both contrast candidates. It does not prove
an unavoidable information collision in those authored examples.

The actual coverage gaps are more specific. No training candidate row has an
immediately preceding finite verb outside the fixed copula list, despite an
existing feature for that observation. No training group has a **pure noun**
already applied with an adjacent left copula, including instrumental nouns.
The broader noun-reading flag has 1,287 such candidate rows, but those include
mixed analyses and do not establish pure-noun coverage.

Disclosed failures expose these missing combinations: a full adjective after
`начались`, an instrumental noun after `Был`, and an adjective coordinated with
earlier full adjectives through conjunction/negation. The current applied-role
features inspect only the immediately adjacent left token; the earlier full
adjectives are not directly represented there. A token such as `основном` also
has an adjective reading even when its surrounding phrase has another role.
Dictionary POS alone cannot establish that contextual role.

Next work is authored finite-verb/copular controls, pure-noun instrumental and
genitive-complement contrasts with actual retrieval, and bounded left-sequence
evidence for adjective coordination. Ordinary finite verbs must not become a
blanket predicate veto: copular-like and other valid predicate constructions
need positive controls too. Full/short and noun/predicate repair ability must
remain represented. Repeating epochs or dropping those hard cases is not the
chosen fix. The disclosed natural failures stay diagnostic, not new supervised
examples or independent qualification.

## Checks and operating state

All 162 `test_right_context*.py` tests pass. Two new-profile batch tests and five
old-profile batch tests pass in the existing training runtime. Training, actual
forest numeric parity, three scorer processes, accepted trace/path comparison,
fixed-model guard comparison and exposure audits pass their execution/integrity
checks. Quality and corpus gates fail as stated.

Source-v5 and both readers remain host experiments. Type/role features and lemma
sets still need Kotlin parity and runtime dictionary support. Later editor
ownership, cancellation and Undo are not certified by the initial host snapshot.
No Android/JVM code changed; JVM tests, lint, APK build, installation and device
acceptance were not rerun. Installed asset hashes remain unchanged.

The [evidence receipt](2026-10-27-right-context-applied-role-fit-evidence.json)
binds the numerical profile, source guard, tests, fitted forests, rejected quality
results and exact model/source/data audits.
