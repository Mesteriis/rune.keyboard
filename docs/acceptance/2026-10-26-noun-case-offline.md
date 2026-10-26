# Noun-case revision: offline qualification

The [noun-case experimental weights](2026-10-26-noun-case-training.md) passed a
separately frozen calibration and focused holdout, followed by a new broad
regression sample and natural instrumental counterexamples. This qualifies an
offline component, not the Android implementation or deployment.
[The evidence receipt](2026-10-26-noun-case-offline-evidence.json) binds the results.
Application sources, packaged weights and the installed APK were not changed.

## Scope and actual reference

Only an unknown spelling's existing singular instrumental noun replacement may
be reconsidered as an unambiguous singular accusative of the same unique lemma.
The existing grammatical verb-object cue must support the proposal. Both words
must be in the actual complete candidate pool; the proposed candidate must pass
the exact joint-source admission guard. Known/protected originals, missing
certificates, no previous replacement, ambiguous analyses and wrong lemmas are
refused. Every refusal retains the installed result. This does not acquire a new
correction when the previous engine kept the original.

`noun_case_revision_scope.py` implements this offline scope, with separate tests
for actual previous-pool membership, original dictionary protection, mixed
case/POS/number/lemma analyses, missing evidence and refused admission. It does
not authorize an edit. Its version is 1; SHA256 is
`7b66e507c0b361c4a26c46ee9e38ea7f0784ca54de8f09d0e261db2c7fc76a60`.

The reference is the actual current controller in
`infinitive-revision-production` mode, including the qualified infinitive stage.
The new 146-feature model is scored afterwards in Python over genuine retrieved
pools. Expected spellings never enter the Kotlin observer or candidate search.
Experimental noun corrections have **not** yet run through controller editing,
its deadlines or Undo machinery. Undo assertions here apply to reference/pool
controller runs, not to this new stage.

## Frozen policy and independent results

The original 1,000-context-per-part corpus remained unchanged. Its calibration
and holdout contain different lemma families and exclude authored training
families/templates, disclosed failure families and earlier sentence/context
material. Each part has 4,000 inputs, including 3,000 controls.

Calibration selected score `0.6485549857424353` and margin
`0.05342739426456289` at the existing 97.5% criterion and minimum 100 incremental
correct changes. Policy SHA256, frozen before holdout scoring, is
`ed6589ff9a16a7c7375258def2b1c9fc214afc1ca9a20a57e4c6d9448a244d1d`.
No threshold, model or scope was changed after calibration.

| Partition | Inputs | Additional correct | Additional wrong | Previous-correct losses | Changed controls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Calibration | 4,000 | 120 | 0 | 0 | 0 / 3,000 |
| Focused holdout | 4,000 | 171 | 0 | 0 | 0 / 3,000 |
| Fresh broad regression | 12,000 | 0 | 0 | 0 | 0 / 6,000 |
| Natural instrumental regression | 68 | 0 | 0 | 0 | 0 / 51 |

Focused holdout changes span 24 families, with at most 37 changes in one family.
Actual reference correctness there is 3,035/4,000 and the projected result is
3,206/4,000. These numbers describe this synthetic cohort, not arbitrary typing.
All 291 selected calibration/holdout pairs have matching nonzero lemma IDs in the
frozen Android `ru.morph` asset. Character-component reconstruction matched 32
scalar checks in each scoring partition within the declared 1e-6 bound.

The broad sample has 3,000 new contexts across 1,657 packed lemma families,
with at most four contexts per family, two synthetic corruptions and two
controls each. There are zero eligible noun revisions in that sample, so it
establishes regression retention, not additional broad-distribution precision.
The recorded precision is null when no changes occur.

The additional instrumental sample searches natural instrumental nouns after
exactly the same verb-object cue. Only 17 distinct contexts in five families
were available after exclusions; all were used with 51 controls. Eleven typo
inputs already have a correct reference replacement and are preserved. Six
remain uncorrected because there is no existing replacement. Exact source
admission refuses the potential changes. This small sample is additional
regression evidence, not a general precision estimate.

Fourteen authored valency probes also preserve every previously correct result.
The disclosed photo example changes to `фотографию` in the offline projection,
while `она довольна фотографие` retains `фотографией`. Cases such as `ручко`,
`машинко`, `книго`, `сило`, `отмычко` and `кисточко` expose remaining source
admission/no-acquisition limits. Their raw new scores are not authority to bypass
those guards. These probes are regression examples, not independent evaluation.

## Exact admission evidence and validation history

The original observer exported `jointAdmission` only for `joint-export`, using
the refinement guard. The first scorer stopped with `KeyError: jointAdmission`
when asking for that field on a production observation, after partial numerical
computation but before selecting a policy. That attempt remains retained.

The observer now exports `jointSourceAdmission` from a pure
`jointAdmissionEvidence` function shared with its actual joint controller path.
It does not change stored observer decision/candidate state while exporting.
After recompilation, all 4,000 reference editor results, pool orders, joint model
scores and exact Undo checks match the first run. There were no Boolean admission
differences between the two guard projections on these calibration inputs;
the certificates remain semantically distinct. Model, scope, data and criteria
were unchanged when the corrected computation ran.

The first broad preparer mistakenly compared packed numeric family IDs with
canonical dictionary lemma names. Its unscored corpus was retained and superseded.
The corrected preparer consistently uses packed ID strings, asserts disjointness
from authored/disclosed families, and retained the original seed, volume and
quality gates. No model evaluation used the first broad corpus. A holdout launcher
also stopped on a misspelled guard key before dispatch; it was corrected to
`calibrationPassed` before any holdout command started.

## Checks and next boundary

All 36 focused Python tests passed:

```sh
PYTHONPATH=tools/typing_experiments python3 -m unittest \
  test_noun_case_revision_scope test_noun_case_focus_forms \
  test_noun_case_contrast_corpus test_grammar_revision_scope \
  test_grammar_revision_calibration test_grammar_context_features \
  test_contextual_policy_calibration
```

The updated Kotlin observer compiled. Primary reference/pool runs completed
40,164 observations with exact pre-boundary restoration: 16,000 focused,
24,000 broad, 136 natural instrumental, and 28 authored probe observations.
Repeated initial calibration observations are not counted as new independent data.
`git diff --check` passed. No Android build or phone command was required for
this offline slice; application sources and packaged assets are unchanged.

Artifacts remain ignored under `build/noun-case-qualification-v2-20261026/`,
`build/noun-case-broad-v2-20261026/` and
`build/noun-case-instrumental-20261026/`. Kotlin scorer/scope parity, integrated
controller qualification, protected-original/independent-admission tests, Android
build/lint and physical Fold acceptance remain required before enabling the new
weights. Right-context-dependent `виновн` remains unresolved.
