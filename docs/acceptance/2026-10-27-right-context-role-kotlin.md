# Kotlin role parity, exact past evidence and depth-six experiment

This milestone ports the 15 experimental role features to Kotlin with exact
Python parity. It does not connect the 178-feature model to production scoring
or editor admission and does not install an APK.

## Exact past evidence rather than a guessed tense

The installed compact grammar format stores POS, case, number, gender, person
and two existing lexical flags. It has no tense field. The Python role extractor
uses `tense == past` to find the nearest past finite verb. Absence of person is
insufficient: dictionary imperatives such as `иди`, `идите`, `давай` and `поезжай`
also lack a person value. Treating those as past would hide older valid gender
evidence. A plural past verb must, conversely, stop traversal even though it has
no singular gender.

`past_context_assets.py` reads the pinned dictionary entries to enumerate past
query spellings, including the same е/ё aliases as DictionaryAnalyzer. It then
uses the existing dictionary-only adapter for the exact analyses of each query,
keeps only VERB/past readings and writes the unchanged packed grammar format.
No guessed analysis, corpus label or user text is an input. The supplemental
index has 127,220 records / 1,542,125 bytes, SHA256
`11ecbb8b95f428a2d39cf44462ef0e8126a3a0a57c395760ddc25817dc6a380d`.
It is stored as a test resource, with OpenCorpora attribution and a bound receipt;
no new main/application asset or existing asset format was introduced.

Kotlin `RightContextRoleFeatures` requires both general grammar lookup and an
explicit past-finite lookup. It never infers tense from person or gender. The
15 ordered outputs preserve the frozen Python v1 semantics; source admission
version 2 remains a separate concern. Preceding context uses the same
128-code-point/eight-word bounds, comma traversal and sentence/identifier stops,
including surrogate-pair windows. A wrong supplemental hash is rejected.

The fixture exporter froze 5,472 authored cases, including case alternatives,
pronouns, future/gendered copulas, candidate genders, unknown/identifier inputs,
unfinished following words, preceding past, imperatives, intervening plural past,
е/ё normalization, long windows and emoji. Every value matches exactly with both
mini dictionaries and the full production grammar plus full supplemental past
index: 164,160 numeric comparisons. Preceding-word boundaries match in every case
as well. The index and test vectors are not training or independent accuracy
qualification, and do not prove runtime ownership or device latency.

## Model v6: conditional capacity, unchanged data

The v5 training audit fitted only 160/240 explicit noun-frame targets. The next
experiment increases depth from five to six within the existing RET2 exporter
bounds, retaining 128 trees, learning rate 0.05, seed 25102026, loss, candidates,
labels and all 9,094 groups / 134,459 rows. Feature/group/vector identities are
verified against v5; no evaluation sentence was added to training.

The 39,444-byte v6 model SHA256 is
`dfdc98954e702b3787118cb88ecd3268b25b4b1f498b45777872dc4c4c977594`.
Its training diagnostics are:

| Category | Target ranked first / groups |
| --- | ---: |
| Strong unknown original | 4,205 / 4,251 |
| Correct original | 1,531 / 1,531 |
| Insufficient evidence | 3,305 / 3,312 |
| Noun frames (strong subset) | 216 / 240 |
| Predicate counterparts (strong subset) | 240 / 240 |

Exported scalar scores agree with sampled CatBoost predictions within 3.06e-8.
These are training results; seven weak-context and 46 strong rows remain wrong.
The model is frozen but not independently qualified or loaded by Android.

## Reliable corpus availability and explicit protocol scope

The reliable-subject collection completed its seven-shard scan. It meets negative
cohort availability but finds only 39 calibration and 40 holdout direct-subject
positive contexts, below the predeclared minimum 100 per part. It failed without
publishing a qualified corpus or scoring a model. The earlier copula collection
also remains failed (25/20 contexts, below 400/400).

These attempts excluded every family declared in earlier evaluation corpora,
including families never used for fitting. That tests increasingly rare lexical
novelty rather than the broader task of correcting new sentences with ordinary
known words. The failure results and their requirements are preserved.

A separately frozen new-sentence protocol now allows families observed in earlier
evaluations while excluding supervised v6 families, legacy authored training
families, families named by the bound conversation-regression fixture, and
articles identified by the prior corpus bindings.
It retains family separation between its own calibration/holdout, the fixed
partition seed, exact source-case checks, reliable subject evidence, the original
positive/negative cohort requirements and 100-new-correct/zero-added-wrong/
zero-correct-or-control-loss qualification requirements. It reports previous
family exposure separately. It will not claim entirely unseen-family accuracy.
This broadens evaluation to the actual common-word sentence task; it does not
turn an earlier failed novel-family run into a pass.

The ten-shard new-sentence collector is running under a plan frozen before any
model scoring. Its outputs still require source/context novelty audits, corpus
binding, calibration, policy freezing and a first untouched sentence-holdout
score. No successful collection or qualification is claimed in this milestone.
Kotlin source-admission parity, model wiring, private multiword ownership,
cancellation, Undo, preservation of following text and Fold acceptance remain
necessary before activation.

## Checks

All 1,132 debug JVM tests pass (120 suites, zero failures/errors/skips), including
the four new role tests. `:app:lintDebug` passes. All 85 right-context Python tests
and two past-export tests pass. `git diff --check` passes. No Android APK build,
installation, phone use or on-device quality/latency check was performed.

The [evidence receipt](2026-10-27-right-context-role-kotlin-evidence.json) binds
the feature sources, dictionary/test data, Gradle reports, v6 training and failed
availability reports. Build roots are `right-context-training-v6-20261027`,
`right-context-past-asset-20261027`, `right-context-role-parity-20261027` and
`right-context-sentence-corpus-v6-20261027`.
