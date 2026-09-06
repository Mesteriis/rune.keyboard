# Smart Typing 0.3 candidate-04 production calibration

Result: **FAIL before product holdout**. Production qualification remains closed.

Candidate-04 passed the prepared-candidate v3 holdout, but the actual production generator and
combined ranker could not produce the required minimum 300 safe replacements per language on v3
calibration. The exact model SHA-256 is
`bff8899af525c30bf1a0939f49c073fbac6cf3fed490018a088d2e831cfcdc71`.

| Candidate set | Language | Candidate recall | Combined replacements | Correct | False changes |
| --- | --- | ---: | ---: | ---: | ---: |
| Original + 3 | EN | 602/1,000 | 36 | 36 | 0/1,000 |
| Original + 3 | RU | 725/1,000 | 65 | 65 | 0/1,000 |
| Original + 3 | ES | 683/1,000 | 69 | 69 | 0/1,000 |
| Original + 1 | EN | 419/1,000 | 11 | 11 | 0/1,000 |
| Original + 1 | RU | 518/1,000 | 10 | 10 | 0/1,000 |
| Original + 1 | ES | 476/1,000 | 4 | 4 | 0/1,000 |

Both variants completed all 3,027 model requests. Width four retained 24 explicit zero-span
fallbacks; width two retained 55. The deterministic policies replaced 27/30/36 rows at width four
and 0/2/0 at width two. Safe observed precision therefore comes from severe abstention and cannot
satisfy the release volume gate.

The frozen production holdout was not exported, scored or inspected. Thresholds will not be fitted
against it. Candidate-04 is not eligible for publication, Fold activation or production AutoReplace.
A later attempt needs a changed model trained against production hard negatives and a new independent
calibration/holdout corpus.

Evidence is under
`tools/eval/smart-typing-0.3/pipeline/results/2026-09-04-candidate-04-v3-product-calibration-fail/`.
