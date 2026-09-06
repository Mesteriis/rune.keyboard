# Historical prepared decisions under the user-selected point95 target

**FAIL in RU, EN and ES.** This separate comparison keeps every September 2
decision, threshold and denominator unchanged. It does not recalibrate, call the
model, or rewrite the original 99% report. The complete stored metrics, including
Wilson95% row-descriptive intervals, are copied into `comparison.json`.

| Language | Correct / automatic | Point precision | False changes / negatives | Coverage / spelling rows | Gate failure |
| --- | ---: | ---: | ---: | ---: | --- |
| RU | 162 / 172 | 94.1860465% | 5 / 1000 | 172 / 2000 | Precision and volume |
| EN | 7 / 7 | 100% | 0 / 1000 | 7 / 2000 | Volume |
| ES | 239 / 243 | 98.3539094% | 3 / 1000 | 243 / 2000 | Volume |

The comparison requires at least300 actual spelling replacements, at least95%
point precision and at most0.5% false change. Integer cross-products decide the
gates; Wilson intervals are reported, not used as additional acceptance floors.
Zero-divergent-span abstentions (RU36, EN33, ES33) remain in the denominators;
runtime errors and missing responses are zero. There are13200 historical responses.
Prepared panels inject expected alternatives and do not measure production
candidate generation, combined ranking or editor behavior.

Exact model SHA256: `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
Historical runner: `f28ddb5658561bc41b1fd84188c0ed11c77d5f5ec8f415b411824c72b69c9cc4`.
The frozen config remains `cc5cf738022b02cf6843f10677e7a2f2d0634abd42427756a23ad2a90bd5928c`:
RU margin2/confidence0.95, EN8/0.99, ES4/0.95. Confidence here is the selector's
softmax feature, not an empirical probability that a correction is right.

Reproduce with `python3 tools/eval/smart-typing-0.3/results/2026-09-06-prepared-fixed-point95/compare.py`.
The script verifies exact historical report/config/cache hashes and has no model
or calibration entry point. The original archive remains byte-identical.

This explains the retained standalone prepared-selector failure under the later
95% request. The separately authorized combined product pipeline must satisfy its
own current-source gates. Neither that authorization nor this comparison creates
a prepared PASS or evidence of unseen generalization.
