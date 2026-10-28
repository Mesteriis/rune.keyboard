# Missing-letter and context-ranking experiments

> Historical experiment report from 2026-10-26. Measurements and separation
> claims below belong to its original inputs and implementation. Current source
> and exclusion checks are recorded in [the fixture audit](2026-10-28-q2-disclosure-tools.md);
> they do not establish fresh qualification or complete Q6 lineage.

The owner requested investigation of the remaining ranking faults, additional contexts/valid-word controls, and a new reserved evaluation before enabling automatic replacements. This window was local-only; no Fold commands, APK installations or packaged-model changes were made.

## Why the existing ordering fails

Python decomposition of the frozen joint tree and character-context model agrees with Kotlin's observed combined scores within `1e-5` on all compared candidates in four disclosed cases. For `сттл` after `поставь стакан на`, the tree prefers `стол` (0.689) over `стал` (0.470), but the character-context contributions are approximately -0.007 and +0.364. The additive result reverses the order. For `поггорим`, the tree itself has a near tie (`прогоним` 0.533, `поговорим` 0.531), and the character model further favours `прогоним`.

`будкт` is a different problem: `будет` is already the combined winner, but nearly tied with `будки`. For `позвоеить`, `позвонить` is also already first, with a stronger competitor `позволить`. Changing ordering alone does not establish that either ambiguity is safe to commit. `куа` is stopped by original-word protection before joint ranking; changing model scores does not override that guard.

## Data and experimental variants

Both variants use the same historical public training observations: 5,492 complete groups and 56,966 candidate rows. Training targets are not taken from the new evaluation sets. Candidate weights use the existing fixed 128-tree/depth-5/seed setup; no hyperparameters are selected on the reserved evaluations.

The new pure-Python `word_context_features.py` supplies six bounded features for each public count table: log pair/document counts, ratios against stored word/prefix count mass, gain over the typed-original pair, and availability. These are ratios over a truncated table, not normalized full-language probabilities. Whole-word suffix matching preserves punctuation and identifier boundaries. Four new unit tests cover these semantics and malformed count records.

The Wikipedia table is the existing bounded 500,000-pair artifact. Its complete contents were checked against the hash-pinned full count source before use. A second table uses only the training split of the official Russian Tatoeba CC0 export. The official [download documentation](https://tatoeba.org/en/downloads) identifies its CC0 subset and fields; the [Russian CC0 archive](https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_CC0.tsv.bz2) is pinned by compressed/decompressed hashes and response headers in the ignored source lock. Exact normalized duplicate sentences were removed and assigned before model fitting: 18,497 train, 2,335 reserved calibration, 2,245 reserved holdout. Related templates/authors can occur across splits, so this is not an author-independent or natural-chat benchmark. Only training sentences contribute counts.

1. **Additional whole-word features, existing additive character score.** The tree has 107 features; the frozen character score is still added afterward. A new Wikipedia shard-0020 corpus was frozen before training/scoring: 3,563 calibration rows (600 family keys), 5,906 holdout rows (1,000 keys). Previously exposed article IDs, target lemma/family keys and prefix tails were excluded. Calibration and holdout have disjoint target families and article IDs. Unsupervised public pretraining can still contain these words.
2. **Unified learned score.** The tree has 108 features, including the frozen character-context score as an input; there is no fixed character bonus after the tree. It was evaluated on a separately frozen selection from the previously reserved Tatoeba sentence splits: 2,184 calibration rows / 546 sentences / 378 families, and 2,260 holdout rows / 565 sentences / 369 families. Calibration and holdout target families and sentence IDs are disjoint. Those families may occur in the historical ranker training: this evaluates new sentence contexts, not unseen-word generalization. The first experiment's already-revealed Wikipedia evaluation was not used to qualify the second variant.

Current-source Kotlin replay receives only row identity, split, language, prefix and typed input. Targets remain outside the observer. Existing production output and complete joint-pool/admission exports were collected separately. Experimental Python model/policy identities were frozen before their respective holdout model scores. Offline proposal scoring is not a Kotlin/controller/Undo qualification of either new model; the application decoder still expects its existing 95-feature models.

## Reserved ranking results

Counts below describe **raw first choices in complete eligible joint pools**, including the original, not automatic replacements and not visible manual-strip ordering. Ineligible/incomplete groups are not silently included as ranking successes.

| Variant / separate reserved data | Eligible pools | Existing correct top-1 | Experimental correct top-1 | Wrong→right | Right→wrong |
| --- | ---: | ---: | ---: | ---: | ---: |
| Added word features / Wikipedia | 3,466 | 3,040 | 3,055 | 50 | 35 |
| Unified score / Tatoeba | 1,024 | 875 | 908 | 68 | 35 |

The raw ranking eligibility filter also excludes `inputChangedByTyping` rows; these excluded cases are not reclassified as successes. Across all missing-letter intentions in the reserved sets, current retrieval showed:

| Observed state | Wikipedia (1,910 rows) | Tatoeba (567 rows) |
| --- | ---: | ---: |
| Complete joint pool already contains intended target | 1,674 | 478 |
| Dictionary-valid original | 110 | 39 |
| Joint pool reports original-word protection (`VALID_WORD`) | 121 | 49 |
| Joint verified-terminal budget exhausted | 5 | 1 |

No complete pool in these missing-letter cohorts lacked its intended target. Ranking and original-word ambiguity therefore dominate these observed cohorts; they do not justify a broad search-budget increase or removal of valid-word protection. Synthetic deletion can itself produce a legitimate word.

For missing-letter rows specifically, the first variant improves 1,291/1,606 → 1,318/1,606 (48 gains, 21 losses); the unified variant improves 363/478 → 388/478 (49 gains, 24 losses). Net improvement does not erase those regressions.

## Authored conversation/control challenge

A separate 120-row disclosed discovery challenge was frozen before experimental scores: six prefix contexts for each of `куа`, `будкт`, `позвоеить`, `сттл`, `поггорим`; each has an intended typo and three valid-word/name/rival controls. It contains 30 intentions and 90 controls. Future words are not passed to a scorer at the word boundary.

The first variant does not change the intended raw winners: `стол` remains behind `стал` in all six contexts, and `поговорим` remains behind `прогоним`. The unified model puts `стол` first in all six, but loses `будет` in three contexts where it was previously first. `позвонить` stays first in six of six; `поговорим` does not improve. `куа` has no eligible joint pool. All 90 controls are unchanged in the **existing product** replay; this is not claimed as a deployed experimental-model control result.

## Automatic promotion refused

Before either holdout was scored, calibration required at least 100 additional correct candidate proposals at ≥99.5% precision, positive net correctness, zero correct-control changes and zero prior-correct losses. A prospective independent check would require at least 100 at ≥99%. Both variants failed the calibration volume gate. Their enabled-source thresholds were therefore frozen to disabled sentinels; zero changes at those disabled thresholds are not evidence of perfect precision.

For diagnostic transparency, each calibration also froze its best smaller-volume point before holdout scoring. Evaluating exactly those predeclared points without selecting a new threshold gives:

| Variant | Calibration proposals: correct/wrong | Reserved proposals: correct/wrong | Reserved prior-correct losses |
| --- | ---: | ---: | ---: |
| Added word features | 21 / 0 | 38 / 1 | 0 |
| Unified score | 56 / 0 | 43 / 0 | 0 |

These are offline candidate proposals after existing source/admission checks, not committed editor edits. Neither the required volume nor product-runtime qualification is established. Neither experimental model is promoted, copied into assets or installed on Fold. No original-word protection, score/margin threshold or production search budget was weakened.

## Checks and retained evidence

- Pure-Python regression suites: 20 tests passed (four new feature tests plus existing slice/stress checks).
- Frozen corpus hashes and calibration/holdout family/article separation: verified.
- Both experimental model/feature/source hashes and unchanged packaged model hashes: verified.
- Paired rank analysis using Kotlin's frozen character contribution reproduces both reserved top-1 totals.
- All current-product replay records completed with exact Backspace restoration; these baseline checks do not validate a hypothetical new-model editor write.
- `git diff --check`: passed. No Android build/device result is claimed for this local-only experiment.

Source locks, corpus manifests, label-free inputs, all observer output, model/policy freezes, paired regressions, authored cases and run scripts are retained under ignored `build/context-feature-ranker-20261026/`. The first corpus preparation rejected a legacy non-string `word` field and the first training attempt rejected an incorrectly selected count receipt; both were repaired before training/scoring, with their original failures retained. No failed promotion is relabelled as a pass.

The measured next direction is richer conversational hard-negative training with a newly reserved evaluation: learn when character evidence should be trusted without losing forms such as `будет`, and obtain enough independently checked additions before automatic use. The already-revealed evaluations above remain regression data for any subsequent selection.
