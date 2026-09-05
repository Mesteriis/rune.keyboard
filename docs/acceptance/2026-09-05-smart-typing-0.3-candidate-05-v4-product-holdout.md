# Candidate-05 v4 product spelling holdout — 2026-09-05

Candidate-05 GGUF SHA-256 `26b6e8db369b2f9e9fa8759c8682532f5bd6f84900499aa74e1733ad5bc1f7bd`
was evaluated with the production Kotlin candidate generator, three alternatives and the
user-selected 95% point-precision profile. Calibration scored all 3,110 required requests before
the holdout export. Its frozen combined config SHA-256 is
`410ce5ad2ebaf94add1dd53ceba45f3e46dc40f43a693ed516b5fb8e4944f1ab`.

Calibration produced EN 124/129 = 96.12%, RU 241/253 = 95.26%, and ES 130/136 = 95.59%.
False changes were 2, 5, and 1 per 1,000 correct/protected rows. No language reached the required
300 replacements, so calibration did not qualify automatic replacement. The frozen configuration
was still applied once to the untouched holdout to measure generalization; no threshold was fitted
or changed after holdout export.

| Language | Auto | Correct | Precision, Wilson 95% | False change, Wilson 95% | Candidate recall | Gate |
| --- | ---: | ---: | --- | --- | --- | --- |
| EN | 127 | 117 | 92.13% [86.11, 95.67]% | 3/1,000 [0.10, 0.88]% | 577/1,000 | FAIL |
| RU | 234 | 224 | 95.73% [92.31, 97.66]% | 1/1,000 [0.02, 0.56]% | 683/1,000 | FAIL |
| ES | 141 | 133 | 94.33% [89.20, 97.10]% | 1/1,000 [0.02, 0.56]% | 677/1,000 | FAIL |

All 3,081 required holdout score responses were recorded. Nineteen bounded scorer errors used the
deterministic fallback. Original was available in every set. The result is **FAIL**: every language
misses the 300-replacement gate and EN/ES also miss 95% point precision. Candidate-05 remains
ineligible for publication or runtime activation.

The final report SHA-256 is
`78f04202709fabba36411e9c94fd389df26d7f8bced15846a8d62c1244749097`; the evidence remains under
ignored `build/smart-typing-0.3/model-v02/` because it includes large numeric caches.
