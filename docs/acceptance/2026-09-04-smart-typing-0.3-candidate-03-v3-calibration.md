# Smart Typing 0.3 candidate-03 qualification-v3 calibration

Result: **FAIL before holdout**. Production qualification remains closed.

The exact 396,704,416-byte GGUF v3/qwen3/Q4_K_M candidate with SHA-256
`7a61cd75e672533beba48480f972688baf281f3d0867e11ca63aee5a17228f65` completed all 6,600
calibration rows from the frozen v3 corpus. The evaluator froze config
`d416855d391eaf1825f1270941320d392350252a1dcff5c2d42fbf0b358ea078` using only calibration and
the precommitted Wilson-95 rule.

| Language | Frozen margin/confidence | AutoReplace | Precision | False change | Calibration decision |
| --- | --- | ---: | --- | --- | --- |
| RU | 2.0 / 0.90 | 795 | 795/795, Wilson 95% [99.52, 100.00]% | 0/1,000, [0.00, 0.38]% | eligible |
| EN | 1e9 / 1.00 | 0 | undefined | 0/1,000, [0.00, 0.38]% | **no safe bucket** |
| ES | 2.0 / 0.95 | 756 | 756/756, [99.49, 100.00]% | 0/1,000, [0.00, 0.38]% | eligible |

EN full abstention makes the required minimum 300 holdout AutoReplace impossible. The v3 holdout
therefore received zero model requests and remains untouched for a changed candidate. The emitted
report returned exit code 2 and records 2,200 missing holdout rows per language. Product spelling,
contextual scoring, automatic promotion, Fold candidate installation and publication were not run.
The active Fold model remains the baseline digest `7a9711…d9c4`.

Evidence is under
`tools/eval/smart-typing-0.3/results/2026-09-04-candidate-03-v3-calibration-fail/`.
