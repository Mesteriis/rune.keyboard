# Rune Text candidate prepared-candidate suitability

Row gate: **PASS**. Production qualification: **not established**.

Lexical families and templates repeat. Wilson 95% intervals below are row-level descriptive intervals, not independent-sample guarantees.

| Split | Language | Auto | Precision (correct/auto) | False change (changed/negative) | Correct-only false change | Typo coverage | Families with auto | Rejected/missing |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: |
| calibration | ru | 506 | 100.00% (506/506); [99.25, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 50.60% (506/1000); [47.50, 53.69]% | 506 | 86 |
| calibration | en | 840 | 100.00% (840/840); [99.54, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 84.00% (840/1000); [81.60, 86.14]% | 840 | 35 |
| calibration | es | 626 | 100.00% (626/626); [99.39, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 62.60% (626/1000); [59.56, 65.55]% | 626 | 34 |
| holdout | ru | 484 | 100.00% (484/484); [99.21, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 48.40% (484/1000); [45.31, 51.50]% | 484 | 94 |
| holdout | en | 868 | 99.88% (867/868); [99.35, 99.98]% | 0.10% (1/1000); [0.02, 0.56]% | 0.14% (1/700); [0.03, 0.80]% | 86.70% (867/1000); [84.45, 88.66]% | 868 | 39 |
| holdout | es | 635 | 100.00% (635/635); [99.40, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 63.50% (635/1000); [60.47, 66.43]% | 635 | 36 |

## Abstention and prepared candidate containment

Abstention counts every spelling row without an automatic replacement, including policy-protected and rejected/missing-score rows. Prepared oracle candidate recall counts typo rows whose independently recorded expected spelling is present in the prepared set. Expected candidates are injected by construction; 100% does not evaluate production candidate generation or model ranking.

| Split | Language | Abstention (no auto/all spelling) | Prepared oracle candidate recall (contained/all typos) |
| --- | --- | --- | --- |
| calibration | ru | 74.70% (1494/2000); [72.75, 76.56]% | 100.00% (1000/1000); [99.62, 100.00]% |
| calibration | en | 58.00% (1160/2000); [55.82, 60.15]% | 100.00% (1000/1000); [99.62, 100.00]% |
| calibration | es | 68.70% (1374/2000); [66.63, 70.69]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | ru | 75.80% (1516/2000); [73.87, 77.63]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | en | 56.60% (1132/2000); [54.42, 58.76]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | es | 68.25% (1365/2000); [66.18, 70.25]% | 100.00% (1000/1000); [99.62, 100.00]% |

## Suggestion and raw ranking

| Split | Language | Typo top-1 | Unambiguous punctuation top-1 | Ambiguous punctuation excluded | Typo families | Templates |
| --- | --- | --- | --- | ---: | ---: | ---: |
| calibration | ru | 93.10% (931/1000); [91.36, 94.51]% | 48.67% (73/150); [40.80, 56.60]% | 50 | 1000 | 2200 |
| calibration | en | 95.90% (959/1000); [94.49, 96.96]% | 54.67% (82/150); [46.68, 62.42]% | 50 | 1000 | 2200 |
| calibration | es | 96.30% (963/1000); [94.94, 97.30]% | 64.00% (96/150); [56.06, 71.24]% | 50 | 1000 | 2200 |
| holdout | ru | 93.30% (933/1000); [91.58, 94.69]% | 56.00% (84/150); [48.00, 63.70]% | 50 | 1000 | 2200 |
| holdout | en | 96.50% (965/1000); [95.17, 97.47]% | 56.67% (85/150); [48.67, 64.33]% | 50 | 1000 | 2200 |
| holdout | es | 96.30% (963/1000); [94.94, 97.30]% | 59.33% (89/150); [51.33, 66.87]% | 50 | 1000 | 2200 |

## Evidence

Frozen calibration: `b7e07c54e76e961efd9e33e28c6b9be066167b1dace4e2e815b2fc472682ed69`

```json
{
  "corpusSha256": "c12064a03e4dc604461ca8ffbacfa190a1560ea6dca68585140813659909aafb",
  "modelSha256": "bff8899af525c30bf1a0939f49c073fbac6cf3fed490018a088d2e831cfcdc71",
  "protocol": "rune-score-jsonl-v1",
  "runnerSha256": "f2f8e9e21a028871da4b9ced6ce0492eb692f742c4de765467a2d44a18535973"
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

- ru: none among automatic replacements
- en: en-holdout-v3-correct-0282
- es: none among automatic replacements
