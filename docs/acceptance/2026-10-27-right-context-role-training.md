# Case-role and singular-gender training, experimental model v4

Following the [rejected v3 qualification](2026-10-27-right-context-acquisition.md),
this milestone adds 15 soft case-role/gender features and authored contrasts.
It does not replace production features/assets, change admission, install an APK,
or qualify a model for automatic editing.

The new 178-feature layout retains the frozen 163-feature revision vector
unchanged and appends role evidence. A nominative analysis remains visible along
with non-nominative readings, number ambiguity, other parts of speech and the
noun/pronoun distinction. Candidate gender is explicit. A future singular copula
alone contributes no gender. The nearest past finite verb in at most eight
preceding words within 128 characters supplies soft gender evidence; commas may
be traversed, while sentence and identifier boundaries stop traversal. This is
not a syntactic parser or an admission certificate.

Authored training uses the same 24 families as v3, with dictionary-verified
masculine/feminine/neuter/plural forms. It includes completed pronouns, gendered
past copulas, preceding subjects and past verbs, direct nouns and ambiguous
complements. A future singular copula without gender evidence and ambiguous
following nouns without a subject teach retention of the applied word. Correct
originals always retain themselves. No disclosed natural failure sentence or
family was added to training. Two neuter contrasts lack a shared dictionary-unknown
one-edit corruption and are explicitly skipped rather than fabricated.

The 8,688 authored rows yield 802 distinct label-blind candidate queries. The
current source-bound Kotlin harness replayed them; the selector kept 8,286 groups
and 118,635 candidate rows, excluding 402 incomplete pools. Expected targets
never insert a candidate. The unchanged training configuration is 128 depth-five
PairLogitPairwise trees, learning rate 0.05, seed 25102026, two threads.
The experimental model SHA256 is
`3e4769ed8ccd60814b485e5b2b08d6794665669693d733308a70146c03e4b3f9`.

| Training group | Target ranked first / groups |
| --- | ---: |
| Unknown original, strong authored evidence | 3,747 / 3,771 |
| Correct original | 1,323 / 1,323 |
| Insufficient/ambiguous evidence | 3,192 / 3,192 |

These are training diagnostics. Scalar exported-tree scores match CatBoost
within 5.38e-8 absolute difference over the sampled groups.

## Disclosed regression and failed coverage gate

The old 7,410-row holdout is now disclosed regression material, not a new
independent test. The v4 model ranks feminine `невредима` above masculine
`невредим` from the observed preceding clause before completed `будешь`.
The four previously wrong plural `аналогичны` revisions no longer produce a
source-certified change; the existing incorrect `аналогично` is retained.
That is preservation of the old output, not a successful correction.
The malformed `Остра` corpus row remains in the disclosed records unchanged.

Old-model score/margin thresholds are not calibrated for this new model. With
those borrowed thresholds, the disclosed matched cohort admits one new correct
change and the side cohort none. These counts cannot establish effectiveness.
Before thresholds, the first source-certified proposals include 211 correct / 4
wrong words in the matched cohort and 142 correct / 152 wrong in side cohorts.
These are unthresholded diagnostics, not proposed production behavior.

Reusing only the previously disclosed calibration parts for fitting still fails
the declared 100-new-correct gate with zero new errors/control/correct losses.
A separate volume diagnostic with a minimum of one finds at most 62 new correct
changes on the declared 33-point grid (57 matched, five side) with zero added
errors. **The 62-change diagnostic is not an accepted policy or a reduced
qualification requirement.** Independent v4 holdout scoring was not performed.

The remaining training gap is competition with other parts of speech. Existing
training contrasts primarily compare short-adjective forms. Dictionary checks
confirm shared unknown corruptions for authored noun contrasts including
`важен/вагон`, `верен/ветер`, `силён/салон`, `слаб/штаб`, `щедр/кедр`,
`зол/зал` and `зол/пол`. These have not yet been added to training. Negative
other-part examples and valid counterpart corrections must be trained together;
coverage must not be recovered by simply admitting the existing false positives.

## Source surface integrity and next corpus

`source_surface_refusal` requires the actual source token to be plain lowercase
Cyrillic and exactly match the normalized token used for a natural target label.
A capitalized proper-name homograph cannot silently become an adjective through
lowercasing. Capitalized/otherwise changed tokens require a separately reviewed
cohort; this filter does not establish their linguistic role or broad coverage.
The previous failed corpus and its recorded error counts are preserved.

A finite new side-corpus collection was started from the seven hash-locked
existing public shards, with a new fixed seed, the surface guard, and exclusions
for all previously disclosed target families/articles plus the 24 training
families. It preserves the previous minimum cohort sizes and within-group caps.
No model scores affect selection. The running collector is not evidence of a
finished or sufficient new corpus. If a later model adds training families, its
corpus binding must verify those additional exclusions before qualification.

## Checks

73 focused Python tests pass, including layout retention/nonfinite rejection,
case alternatives, unfinished cues, future-copula gender uncertainty, preceding
past evidence and identifier/sentence boundaries, authored retention labels and
source-surface integrity. The candidate replay completed all 802 queries. Model
export parity passed. `git diff --check` passed. The first training invocation
failed because a build helper named `select.py` shadowed Python's standard
library; the helper was renamed before retry, with unchanged groups/labels and
a relocation receipt. The retry completed successfully. No Android app build,
Kotlin parity for the new 15 features, device test or install is claimed.

The [evidence receipt](2026-10-27-right-context-role-training-evidence.json) binds
sources, corpus, queries, groups, frozen model, disclosed diagnostics and checks.
Ignored artifacts are in `build/right-context-training-v4-20261027/`,
`build/right-context-v4-disclosed-regression-20261027/`,
`build/right-context-v4-calibration-20261027/` and
`build/right-context-fresh-side-v4-20261027/`.
