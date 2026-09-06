# Smart Typing 0.3 candidate-04 prepared-candidate holdout

Result: **PASS** for prepared-candidate suitability. Production qualification remains closed.

The exact 396,704,416-byte GGUF v3/qwen3/Q4_K_M candidate with SHA-256
`bff8899af525c30bf1a0939f49c073fbac6cf3fed490018a088d2e831cfcdc71` completed all 6,600
calibration rows from the frozen v3 corpus. The evaluator froze config
`b7e07c54e76e961efd9e33e28c6b9be066167b1dace4e2e815b2fc472682ed69` before the first
holdout request. It then completed all 6,600 holdout rows without changing the model, corpus,
runner or thresholds. The report exited 0 and all 13,200 response IDs are present exactly once.

| Language | Frozen margin/confidence | AutoReplace | Precision | False change | Gate |
| --- | --- | ---: | --- | --- | --- |
| RU | 4.0 / 0.95 | 484 | 484/484 = 100.00%, Wilson 95% [99.21, 100.00]% | 0/1,000 = 0.00%, [0.00, 0.38]% | PASS |
| EN | 2.0 / 0.90 | 868 | 867/868 = 99.88%, [99.35, 99.98]% | 1/1,000 = 0.10%, [0.02, 0.56]% | PASS |
| ES | 4.0 / 0.95 | 635 | 635/635 = 100.00%, [99.40, 100.00]% | 0/1,000 = 0.00%, [0.00, 0.38]% | PASS |

Original is present in every prepared set. Prepared candidate recall is 1,000/1,000 by
construction in each language, so it is not evidence for the production generator. Explicit
zero-divergent-span refusals remain abstentions in all denominators: RU 94, EN 39 and ES 36 on
holdout. Unambiguous punctuation top-1 is RU 56.00%, EN 56.67% and ES 59.33%; punctuation remains
suggestion-only.

This PASS permits candidate-04 to enter the independently bound production-candidate calibration
and holdout pipeline. It does not qualify automatic correction, on-device availability, latency,
energy use, Fold behavior, model publication or Rune 0.3.0. Those gates remain separate.

Evidence is under
`tools/eval/smart-typing-0.3/results/2026-09-04-candidate-04-prepared-holdout/`.
