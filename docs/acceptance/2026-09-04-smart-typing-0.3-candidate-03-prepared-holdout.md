# Smart Typing 0.3 candidate-03 prepared-candidate holdout

Result: **FAIL**. Production qualification remains closed.

The exact 396,704,416-byte GGUF v3/qwen3/Q4_K_M candidate with SHA-256
`7a61cd75e672533beba48480f972688baf281f3d0867e11ca63aee5a17228f65`
was scored by runner `f2f8e9e…` over all 13,200 rows. The cache contains one
identity header and 13,200 unique responses. Calibration completed first and
froze config `149bda1bcba74360a387b0408f7959ec2c45e8bc1acf0983ff95308d6350c554`
before the first holdout request. Report generation returned the expected exit
code 2. No threshold was changed after holdout inspection.

| Language | AutoReplace | Precision | False change | Typo coverage | Gate |
| --- | ---: | --- | --- | --- | --- |
| EN | 928 | 925/928 = 99.68%, Wilson 95% [99.05, 99.89]% | 3/1,000 = 0.30%, [0.10, 0.88]% | 925/1,000 = 92.50% | PASS |
| RU | 923 | 915/923 = 99.13%, [98.30, 99.56]% | 8/1,000 = 0.80%, [0.41, 1.57]% | 915/1,000 = 91.50% | **FAIL** |
| ES | 906 | 899/906 = 99.23%, [98.41, 99.63]% | 7/1,000 = 0.70%, [0.34, 1.44]% | 899/1,000 = 89.90% | **FAIL** |

Original is present in every prepared set. Prepared oracle candidate recall is
1,000/1,000 by construction in each language and is not production generator
evidence. Holdout punctuation top-1 over 150 unambiguous rows is EN 58.00%, RU
53.33% and ES 62.67%; punctuation remains suggestion-only. Runtime/zero-span
rejections abstain and remain in denominators: EN 33, RU 80, ES 38.

The result stops model-dependent work for this candidate. Product candidate
scoring, combined product calibration, contextual scoring, automatic promotion,
Fold model qualification and publication were not run. `SpellingQualification.CURRENT`
stays closed and the installed debug APK remains version 0.2.0 without this GGUF.
A later attempt requires a changed model and a new calibration/holdout corpus;
this revealed holdout cannot be used to tune thresholds.

Evidence is under
`tools/eval/smart-typing-0.3/results/2026-09-04-candidate-03-prepared-holdout/`.
Its emitted Markdown has a legacy hard-coded `Rune Text 0.1` heading; the JSON,
cache header, frozen config and provenance all bind the exact candidate digest
above. The raw evaluator SHA matches the frozen corpus manifest.
