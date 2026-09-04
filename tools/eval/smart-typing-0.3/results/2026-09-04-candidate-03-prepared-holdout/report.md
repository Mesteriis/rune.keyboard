# Rune Text 0.1 prepared-candidate suitability

Row gate: **FAIL**. Production qualification: **not established**.

Lexical families and templates repeat. Wilson 95% intervals below are row-level descriptive intervals, not independent-sample guarantees.

| Split | Language | Auto | Precision (correct/auto) | False change (changed/negative) | Correct-only false change | Typo coverage | Families with auto | Rejected/missing |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: |
| calibration | ru | 919 | 99.46% (914/919); [98.73, 99.77]% | 0.50% (5/1000); [0.21, 1.17]% | 0.71% (5/700); [0.31, 1.66]% | 91.40% (914/1000); [89.50, 92.98]% | 919 | 90 |
| calibration | en | 939 | 99.79% (937/939); [99.23, 99.94]% | 0.20% (2/1000); [0.05, 0.73]% | 0.29% (2/700); [0.08, 1.04]% | 93.70% (937/1000); [92.02, 95.05]% | 939 | 37 |
| calibration | es | 915 | 99.78% (913/915); [99.21, 99.94]% | 0.20% (2/1000); [0.05, 0.73]% | 0.29% (2/700); [0.08, 1.04]% | 91.30% (913/1000); [89.39, 92.89]% | 915 | 34 |
| holdout | ru | 923 | 99.13% (915/923); [98.30, 99.56]% | 0.80% (8/1000); [0.41, 1.57]% | 1.14% (8/700); [0.58, 2.24]% | 91.50% (915/1000); [89.61, 93.07]% | 923 | 80 |
| holdout | en | 928 | 99.68% (925/928); [99.05, 99.89]% | 0.30% (3/1000); [0.10, 0.88]% | 0.43% (3/700); [0.15, 1.25]% | 92.50% (925/1000); [90.70, 93.97]% | 928 | 33 |
| holdout | es | 906 | 99.23% (899/906); [98.41, 99.63]% | 0.70% (7/1000); [0.34, 1.44]% | 1.00% (7/700); [0.49, 2.05]% | 89.90% (899/1000); [87.88, 91.62]% | 906 | 38 |

## Abstention and prepared candidate containment

Abstention counts every spelling row without an automatic replacement, including policy-protected and rejected/missing-score rows. Prepared oracle candidate recall counts typo rows whose independently recorded expected spelling is present in the prepared set. Expected candidates are injected by construction; 100% does not evaluate production candidate generation or model ranking.

| Split | Language | Abstention (no auto/all spelling) | Prepared oracle candidate recall (contained/all typos) |
| --- | --- | --- | --- |
| calibration | ru | 54.05% (1081/2000); [51.86, 56.22]% | 100.00% (1000/1000); [99.62, 100.00]% |
| calibration | en | 53.05% (1061/2000); [50.86, 55.23]% | 100.00% (1000/1000); [99.62, 100.00]% |
| calibration | es | 54.25% (1085/2000); [52.06, 56.42]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | ru | 53.85% (1077/2000); [51.66, 56.03]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | en | 53.60% (1072/2000); [51.41, 55.78]% | 100.00% (1000/1000); [99.62, 100.00]% |
| holdout | es | 54.70% (1094/2000); [52.51, 56.87]% | 100.00% (1000/1000); [99.62, 100.00]% |

## Suggestion and raw ranking

| Split | Language | Typo top-1 | Unambiguous punctuation top-1 | Ambiguous punctuation excluded | Typo families | Templates |
| --- | --- | --- | --- | ---: | ---: | ---: |
| calibration | ru | 93.80% (938/1000); [92.13, 95.13]% | 51.33% (77/150); [43.40, 59.20]% | 50 | 1000 | 2200 |
| calibration | en | 95.90% (959/1000); [94.49, 96.96]% | 55.33% (83/150); [47.34, 63.06]% | 50 | 1000 | 2200 |
| calibration | es | 96.80% (968/1000); [95.52, 97.72]% | 50.00% (75/150); [42.10, 57.90]% | 50 | 1000 | 2200 |
| holdout | ru | 93.70% (937/1000); [92.02, 95.05]% | 53.33% (80/150); [45.37, 61.13]% | 50 | 1000 | 2200 |
| holdout | en | 95.20% (952/1000); [93.69, 96.36]% | 58.00% (87/150); [50.00, 65.60]% | 50 | 1000 | 2200 |
| holdout | es | 95.10% (951/1000); [93.58, 96.27]% | 62.67% (94/150); [54.70, 70.00]% | 50 | 1000 | 2200 |

## Evidence

Frozen calibration: `149bda1bcba74360a387b0408f7959ec2c45e8bc1acf0983ff95308d6350c554`

```json
{
  "corpusSha256": "aa81aede5c0e90c4879003cddeca0db4f6d00e512c4f396695ac0df067f0fd13",
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

- ru: ru-holdout-v2-correct-0001, ru-holdout-v2-correct-0197, ru-holdout-v2-correct-0198, ru-holdout-v2-correct-0328, ru-holdout-v2-correct-0395, ru-holdout-v2-correct-0433, ru-holdout-v2-correct-0603, ru-holdout-v2-correct-0650
- en: en-holdout-v2-correct-0274, en-holdout-v2-correct-0292, en-holdout-v2-correct-0360
- es: es-holdout-v2-correct-0002, es-holdout-v2-correct-0207, es-holdout-v2-correct-0216, es-holdout-v2-correct-0328, es-holdout-v2-correct-0506, es-holdout-v2-correct-0670, es-holdout-v2-correct-0695
