# Noun-case revision: Kotlin scorer and scope parity

The [offline-qualified noun component](2026-10-26-noun-case-offline.md) now has
an Android-language scope and an independent numeric scorer.
[Evidence](2026-10-26-noun-case-android-core-evidence.json) binds this milestone.
This core slice does not load new production assets or enable noun corrections.

`NounCaseRevisionScope` checks every stored grammatical analysis: the old noun
must be singular instrumental and the proposal singular accusative. Both need
the same positive packed morphology lemma ID, and the bounded preceding context
must provide the existing object cue. Missing/ambiguous/mismatched morphology,
wrong case/number/part of speech and absent cues refuse the revision. An early
precondition checks the old noun and cue before a second model comparison.
This grammar classification never authorizes an editor operation.

Compact grammar projection preserves every distinct grammatical code, while its
separate ambiguity count is capped. It normalizes special case aliases. The
frozen dictionary's complete 5,532-tag registry contains no singular noun tags
with special `acc2`, so this normalization does not broaden the singular
accusative classification used here.

`ExperimentModels` keeps separate base, infinitive and noun weights. The three
scorers share the already validated immutable feature indices; no second context
or grammar table is loaded. Missing/malformed noun weights yield unavailable
scores without replacing either preceding scorer. Reloading the base invalidates
both derived models. Android resource loading and automatic admission are not
connected in this slice; noun readiness stays false in the application.

## Parity and regression evidence

Actual Kotlin methods ran against the packaged context/grammar/morphology assets:

- 97,973 candidate/original scores for **each** of the new noun model, existing
  general model and existing infinitive model match Python. Maximum absolute
  difference is 2.220446049250313e-16 for all three models.
- All 20,068 scope decisions match the portable dictionary/packed-lemma contract
  over calibration, holdout, broad and natural instrumental cohorts.
- Python dictionary-only classification allows 545 raw pairs; the packed contract
  allows 508. Its 37 extra refusals are for missing, ambiguous or different packed
  lemma evidence. All already fail the independent external certificates. All
  304 externally eligible cases remain eligible, including every selected
  calibration/holdout change; there is no loss of qualified offline cases.
- The necessary precondition accepts every fully allowed scope case.

Score parity covers every complete nonempty pool in those cohorts: 97,973
candidate/original vectors, with 12,710 no-complete-pool inputs excluded from
score calculation. Scope checking still covers all 20,068 inputs. No case was
excluded to remove a numerical or scope mismatch. The original true/false
source-admission facts are carried separately; this is not proof of a new
controller's source/ownership checks or editor timing.

Unit tests cover positive cues and datives, punctuation/preposition/noun barriers,
all-analysis case/POS/number rejection, missing/zero/negative/different lemma IDs,
unavailable/malformed model loads, exact preservation of both preceding scorer
outputs and invalidation on base reload. An initial test accidentally used the
same old/proposed word while expecting a wrong-case refusal; the correct result
was `UNCHANGED`. The test was corrected to compare different words, preserving
production refusal order. Initial failing XML/logs remain retained.

`./gradlew --max-workers=2 :app:testDebugUnitTest :app:lintDebug` passed all
1,112 JVM tests with zero failures/errors/skips; debug lint passed.
`git diff --check` passed. Artifacts are ignored under
`build/noun-case-android-core-20261026/`.

Production asset/fingerprint loading, independent source admission, controller
routing, exact new-replacement Undo and physical Fold acceptance remain pending.
No phone command or installation was performed in this core slice.
