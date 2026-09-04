# Rune Text candidate prepared-candidate suitability

Row gate: **FAIL**. Production qualification: **not established**.

Lexical families and templates repeat. Wilson 95% intervals below are row-level descriptive intervals, not independent-sample guarantees.

| Split | Language | Auto | Precision (correct/auto) | False change (changed/negative) | Correct-only false change | Typo coverage | Families with auto | Rejected/missing |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: |
| calibration | ru | 795 | 100.00% (795/795); [99.52, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 79.50% (795/1000); [76.89, 81.89]% | 795 | 86 |
| calibration | en | 0 | undefined (0/0) | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 0.00% (0/1000); [0.00, 0.38]% | 0 | 35 |
| calibration | es | 756 | 100.00% (756/756); [99.49, 100.00]% | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 75.60% (756/1000); [72.84, 78.16]% | 756 | 34 |
| holdout | ru | 0 | undefined (0/0) | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 0.00% (0/1000); [0.00, 0.38]% | 0 | 2200 |
| holdout | en | 0 | undefined (0/0) | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 0.00% (0/1000); [0.00, 0.38]% | 0 | 2200 |
| holdout | es | 0 | undefined (0/0) | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/700); [0.00, 0.55]% | 0.00% (0/1000); [0.00, 0.38]% | 0 | 2200 |

## Abstention and prepared candidate containment

Abstention counts every spelling row without an automatic replacement, including policy-protected and rejected/missing-score rows. Prepared oracle candidate recall counts typo rows whose independently recorded expected spelling is present in the prepared set. Expected candidates are injected by construction; 100% does not evaluate production candidate generation or model ranking.

| Split | Language | Abstention (no auto/all spelling) | Prepared oracle candidate recall (contained/all typos) |
| --- | --- | --- | --- |
| calibration | ru | 60.25% (1205/2000); [58.09, 62.37]% | 100.00% (1000/1000); [99.62, 100.00]% |
| calibration | en | 100.00% (2000/2000); [99.81, 100.00]% | 100.00% (1000/1000); [99.62, 100.00]% |
| calibration | es | 62.20% (1244/2000); [60.05, 64.30]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | ru | 100.00% (2000/2000); [99.81, 100.00]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | en | 100.00% (2000/2000); [99.81, 100.00]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | es | 100.00% (2000/2000); [99.81, 100.00]% | 100.00% (1000/1000); [99.62, 100.00]% |

## Suggestion and raw ranking

| Split | Language | Typo top-1 | Unambiguous punctuation top-1 | Ambiguous punctuation excluded | Typo families | Templates |
| --- | --- | --- | --- | ---: | ---: | ---: |
| calibration | ru | 93.60% (936/1000); [91.91, 94.96]% | 56.00% (84/150); [48.00, 63.70]% | 50 | 1000 | 2200 |
| calibration | en | 96.20% (962/1000); [94.83, 97.22]% | 54.00% (81/150); [46.02, 61.78]% | 50 | 1000 | 2200 |
| calibration | es | 96.30% (963/1000); [94.94, 97.30]% | 58.67% (88/150); [50.67, 66.23]% | 50 | 1000 | 2200 |
| holdout | ru | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/150); [0.00, 2.50]% | 50 | 1000 | 2200 |
| holdout | en | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/150); [0.00, 2.50]% | 50 | 1000 | 2200 |
| holdout | es | 0.00% (0/1000); [0.00, 0.38]% | 0.00% (0/150); [0.00, 2.50]% | 50 | 1000 | 2200 |

## Evidence

Frozen calibration: `d416855d391eaf1825f1270941320d392350252a1dcff5c2d42fbf0b358ea078`

```json
{
  "corpusSha256": "c12064a03e4dc604461ca8ffbacfa190a1560ea6dca68585140813659909aafb",
  "modelSha256": "7a61cd75e672533beba48480f972688baf281f3d0867e11ca63aee5a17228f65",
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
- en: none among automatic replacements
- es: none among automatic replacements
