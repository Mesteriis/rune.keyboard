# Direct supervised conversation ranking

> Historical experiment report from 2026-10-26. Measurements and separation
> claims below belong to its original inputs and implementation. Current source
> and exclusion checks are recorded in [the fixture audit](2026-10-28-q2-disclosure-tools.md);
> they do not establish fresh qualification or complete Q6 lineage.

The owner requested direct conversational training, natural competing-form examples, regression checks for the earlier 35 ranking losses, and a newly reserved evaluation. All work was local. No phone commands, APK installation, packaged model replacement or production threshold change was performed.

## Data separation and training

The source is the previously hash-pinned official Russian Tatoeba CC0 export. The existing normalized sentence-level train/calibration/holdout assignments remain unchanged. Newly selected sentences exclude every previously disclosed sentence ID and left-context/target combination, including the 35 old regressions. Calibration/holdout target families are also disjoint; training families may overlap because this tests new contexts, not unseen-word generalization.

The first preparation was rejected by the new `conversation_split_checks.py` guard: different sentences contained the same prediction contexts across splits. The corrected preparation removed all 199 cross-split context keys before model fitting. Short preceding words such as `я`/`мы` count as context tokens, without becoming candidate target words. The rejected preparation and its output were preserved and were never used to fit a model.

Frozen new corpus:

| Partition | Sentences | Target families | Rows |
| --- | ---: | ---: | ---: |
| Train | 3,758 | 1,708 | 22,527 |
| Calibration | 801 | 483 | 3,204 |
| Primary holdout | 793 | 478 | 3,172 |

Current Kotlin generation receives typed words and prefixes, never expected labels. A deterministic, predeclared mix selects 5,488 non-overlapping historical public training groups, 6,000 conversational typo groups and 1,000 correct-original retention groups. The last group uses actual manual-neighbour pools to teach preserving the original; it grants no automatic source certificate or runtime admission. There are 58 selected groups with multiple requested rival forms (`стол/стал/стул`, `будет/будут/будки`). Natural rival target words occur in 216 new training rows.

The single candidate retains the preceding 108-feature unified architecture, 128 trees, depth 5, learning rate .05, seed 25102026, and frozen character/count models. It trains on 12,488 groups / 136,425 candidate rows. No model or threshold was fitted on the 35 disclosed regressions. Model SHA-256: `1040c487f945f15d1898088f6d7337f83350da20a9c1629dbfd1129330aef22c`.

## Primary reserved evaluation

Raw joint-pool first-choice results:

- 1,202/1,449 → **1,323/1,449** correct: 162 wrong→right and 41 right→wrong. These are ranking changes, not 41 committed incorrect replacements.
- Missing-letter subset: 505/695 → **592/695**, with 116 gains and 29 losses.

Calibration found a frozen offline candidate-proposal point with 104 additional correct / zero wrong, zero prior-correct losses and zero control changes. Its score threshold is -0.024182453469533897 and margin threshold 0.1593899277759272. The primary independent check produced **77 correct / zero wrong** additional proposals, with zero prior-correct losses/control changes. It failed the predeclared minimum of 100 additional correct; the original failed volume result remains recorded.

These proposals are Python word-level arbitration after existing Kotlin candidate/admission evidence, not actual new-model editor commits. They do not establish Kotlin codec, editor-prefix/Undo, deadline or physical-device qualification.

## Previously disclosed regression checks

The 35 old raw ranking losses were frozen in `fixtures/context_ranker_regressions_20261026.jsonl` as regression-only data and excluded from training/new qualification. The new model recovers the expected first candidate in **20/35**; 15 remain raw ranking losses. At its frozen offline admission point, these 35 produce zero incorrect new proposals and zero losses of actual existing correct outputs. They are not added to independent accuracy counts.

In the separate disclosed 120-row context/control challenge, `стол` is first in all six contexts, `позвонить` remains first in six, and `будет` is first in five rather than the prior unified model's three. The remaining `скоро будкт` ranks `будут` 0.7213 versus `будет` 0.7206; its tiny margin is rejected by the frozen admission threshold. `поговорим` still does not become first; `куа` remains stopped by original-word protection before joint scoring. The 90 controls remain unchanged in the existing-product replay; experimental runtime behavior is not claimed.

## Separate fixed-size follow-on audit

After observing the under-volume primary result, a **new** final-audit plan was frozen before its data selection/scoring. The already frozen model and thresholds were unchanged. The 77 primary successes were explicitly not combined with its results.

This audit uses the official [Russian Tatoeba detailed export](https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_detailed.tsv.bz2), whose general CC BY 2.0 FR license and fields are described by the [official download documentation](https://tatoeba.org/en/downloads). It is evaluation-only: no sentence from it was used for training or copied into an APK. Source bytes/hash, contributor and sentence references are preserved privately. All normalized original CC0 sentences, disclosed/training sentences and prediction contexts were excluded. The audit contains 4,000 new prediction contexts, 2,089 target families, at most four contexts per family, and 16,000 rows (two corruptions, correct and protected controls). Related public sentence templates/authors can still span collections; this is not natural chat or author-independent accuracy.

An initially slow preparation was intentionally stopped before data freeze or any model score. Bounded context selection and duplicate-context removal then generated the fixed-size audit; the frozen size, weights, thresholds and pass criteria did not change. No data was selected by model outcomes.

The vectorized scorer first reproduced the primary 77/0 proposals and 1,202→1,323 raw ranking totals exactly, then evaluated the new audit once:

- Raw top-1: 6,208/7,314 → **6,657/7,314**, with 644 gains and 195 losses.
- Offline additional proposals: **466 correct / 5 wrong**, across 362 correctly improved family keys.
- Proposal precision: **98.9384%**, below the predeclared 99% requirement.
- Zero prior actual-correct losses, zero correct-control changes, positive net correctness (+466).

**Promotion refused.** The separate audit failed precision; it is not rescued by adding the earlier 77 successes or rounding 98.94% to 99%. Weights and thresholds were not retuned after this audit.

## Five observed errors

All intended targets were already retrieved; each incorrect proposal and its intended target share the same morphology lemma ID. This is a form/context problem, not a reason to increase the search budget:

| Typed | Wrong proposal | Intended word |
| --- | --- | --- |
| фотографие | фотографией | фотографию |
| злищься | злишься | злиться |
| научищься | научишься | научиться |
| заплатищь | заплатишь | заплатить |
| виновн | виновен | виновны |

Three errors confuse infinitive and finite verb forms; the others confuse case or number. Some endings also depend on words that have not yet been typed at the boundary. The five sentence/context references are frozen as regression-only metadata in `fixtures/conversation_supervised_false_proposals_20261026.json`; raw sentence context remains in the ignored source archive. They are not new training labels.

The next justified modeling direction is grammatical-form/context evidence built from fresh training rows, followed by a newly reserved evaluation. Selecting a special-case margin from these five already revealed failures would invalidate that evaluation.

## Validation and artifacts

- Python helper regression suites: 24 tests passed, including four new split/leakage tests and iterator-input coverage.
- Model/training-selection/source/corpus/policy hashes and disjointness guards: verified.
- Paired ranking calculations reproduce the frozen primary totals; the follow-on vectorization independently reproduces the primary scorer's decisions before use.
- Existing-product replay completion and exact Backspace evidence are baseline behavior only, not a new-model Undo claim.
- `git diff --check`: passed. No Android build/native acceptance of this new model is claimed. Its 108-feature artifact is not connected to the application's existing 95-feature decoder.

All run scripts, source manifests, label-free observer inputs, complete observations, rejected preparations, frozen model/policy, per-case proposals and regression reports are retained under ignored `build/conversation-supervised-20261026/`. Existing model assets remain unchanged.
