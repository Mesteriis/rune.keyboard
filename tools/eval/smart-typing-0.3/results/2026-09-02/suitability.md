# Rune Text 0.1 prepared-candidate suitability

Row gate: **FAIL**. Production qualification: **not established**.

Lexical families and templates repeat. Wilson 95% intervals below are row-level descriptive intervals, not independent-sample guarantees.

| Split | Language | Auto | Precision (correct/auto) | False change (changed/negative) | Correct-only false change | Typo coverage | Families with auto | Rejected/missing |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: |
| calibration | ru | 201 | 99.50% (200/201); [97.24, 99.91]% | 0.10% (1/1000); [0.02, 0.56]% | 0.14% (1/700); [0.03, 0.80]% | 20.00% (200/1000); [17.64, 22.59]% | 51 | 44 |
| calibration | en | 1 | 100.00% (1/1); [20.65, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 0.10% (1/1000); [0.02, 0.56]% | 1 | 42 |
| calibration | es | 301 | 99.00% (298/301); [97.11, 99.66]% | 0.10% (1/1000); [0.02, 0.56]% | 0.14% (1/700); [0.03, 0.80]% | 29.80% (298/1000); [27.05, 32.71]% | 66 | 42 |
| holdout | ru | 172 | 94.19% (162/172); [89.63, 96.81]% | 0.50% (5/1000); [0.21, 1.17]% | 0.71% (5/700); [0.31, 1.66]% | 16.20% (162/1000); [14.05, 18.61]% | 44 | 36 |
| holdout | en | 7 | 100.00% (7/7); [64.57, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 0.70% (7/1000); [0.34, 1.44]% | 4 | 33 |
| holdout | es | 243 | 98.35% (239/243); [95.84, 99.36]% | 0.30% (3/1000); [0.10, 0.88]% | 0.43% (3/700); [0.15, 1.25]% | 23.90% (239/1000); [21.36, 26.64]% | 57 | 33 |

## Abstention and prepared candidate containment

Abstention counts every spelling row without an automatic replacement, including policy-protected and rejected/missing-score rows. Prepared oracle candidate recall counts typo rows whose independently recorded expected spelling is present in the prepared set. Expected candidates are injected by construction; 100% does not evaluate production candidate generation or model ranking.

| Split | Language | Abstention (no auto/all spelling) | Prepared oracle candidate recall (contained/all typos) |
| --- | --- | --- | --- |
| calibration | ru | 89.95% (1799/2000); [88.55, 91.19]% | 100.00% (1000/1000); [99.62, 100.00]% |
| calibration | en | 99.95% (1999/2000); [99.72, 99.99]% | 100.00% (1000/1000); [99.62, 100.00]% |
| calibration | es | 84.95% (1699/2000); [83.32, 86.45]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | ru | 91.40% (1828/2000); [90.09, 92.55]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | en | 99.65% (1993/2000); [99.28, 99.83]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | es | 87.85% (1757/2000); [86.35, 89.21]% | 100.00% (1000/1000); [99.62, 100.00]% |

## Suggestion and raw ranking

| Split | Language | Typo top-1 | Unambiguous punctuation top-1 | Ambiguous punctuation excluded | Typo families | Templates |
| --- | --- | --- | --- | ---: | ---: | ---: |
| calibration | ru | 77.00% (770/1000); [74.29, 79.50]% | 100.00% (100/100); [96.30, 100.00]% | 100 | 100 | 65 |
| calibration | en | 59.10% (591/1000); [56.02, 62.11]% | 100.00% (100/100); [96.30, 100.00]% | 100 | 101 | 65 |
| calibration | es | 87.30% (873/1000); [85.09, 89.22]% | 74.00% (74/100); [64.63, 81.60]% | 100 | 100 | 65 |
| holdout | ru | 78.10% (781/1000); [75.43, 80.55]% | 59.00% (59/100); [49.20, 68.13]% | 100 | 100 | 62 |
| holdout | en | 57.20% (572/1000); [54.11, 60.23]% | 100.00% (100/100); [96.30, 100.00]% | 100 | 100 | 62 |
| holdout | es | 84.70% (847/1000); [82.34, 86.80]% | 50.00% (50/100); [40.38, 59.62]% | 100 | 100 | 62 |

## Evidence

Frozen calibration: `cc5cf738022b02cf6843f10677e7a2f2d0634abd42427756a23ad2a90bd5928c`

```json
{
  "corpusSha256": "2b3874adabbb60370360087f208d6e9cf2ef308e4955af57114ef2a687c7fd96",
  "modelSha256": "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4",
  "protocol": "rune-score-jsonl-v1",
  "runnerSha256": "f28ddb5658561bc41b1fd84188c0ed11c77d5f5ec8f415b411824c72b69c9cc4"
}
```

## Limits

- Rows share lexical families and authored context templates; Wilson intervals describe row counts and are not independent-sample confidence guarantees.
- Synthetic typo and protected-token distributions do not represent real typing. Prepared candidates do not test production candidate generation.
- noAuto is an authored policy annotation. Production protection detection is not implemented or evaluated.
- Punctuation ambiguity is authored; ambiguous rows have no single correct suggestion and are excluded from suggestion accuracy.
- Runtime errors and zero-token scores abstain and remain in metric denominators.
- Abstention uses all spelling rows, including protected, error and missing-score rows. Prepared oracle candidate recall uses all typo rows; expected spellings are injected by construction, so 100% is not production candidate-generator evidence.

False positives (sample IDs only):

- ru: ru-holdout-correct-01-2-1, ru-holdout-correct-04-3-1, ru-holdout-correct-04-3-5, ru-holdout-correct-13-0-1, ru-holdout-correct-13-0-4, ru-holdout-typo-01-2-2, ru-holdout-typo-04-0-9, ru-holdout-typo-04-3-6, ru-holdout-typo-13-0-2, ru-holdout-typo-13-0-6
- en: none among automatic replacements
- es: es-holdout-correct-03-1-6, es-holdout-correct-08-2-6, es-holdout-correct-11-0-6, es-holdout-typo-03-1-9
