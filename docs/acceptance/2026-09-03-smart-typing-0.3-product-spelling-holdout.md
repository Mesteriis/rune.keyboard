# Product spelling holdout — 2026-09-03

Baseline `7ab2f45`. This is the first end-to-end spelling holdout over the actual
production candidate generator, frozen three-alternative policy and exact Rune
Text GGUF. It does not reuse prepared candidate panels and performs no fitting,
threshold search or label-driven generation on holdout.

The export verifies the immutable combined and deterministic config hashes,
their calibration generator receipt, all 17 production generator source hashes,
the nine frozen lexicon/rank assets and the corpus manifest. It then runs the
production Kotlin generator on exactly 6,000 holdout spelling rows. Original is
present in every set. Candidate recall is EN 925/1000, RU 917/1000 and ES
892/1000.

The exact scorer `f2f8e9e…35973b` and GGUF `7a97111c…dd9c4` returned all
2,940 required responses; 3,060 original-only sets correctly made no model
request. Fourteen zero-divergent-span sets returned the explicit
`SCORING_FAILED` contract result and used the frozen deterministic fallback.
The score cache SHA-256 is
`689545ffd51c3daae20d90ece3f451dee9321c4d70b8425b87c56624a5b862a6`.

## Frozen holdout result

| Language | Pipeline | Auto | Correct | Precision, Wilson 95% | False change, Wilson 95% | Candidate recall |
| --- | --- | ---: | ---: | --- | --- | --- |
| EN | deterministic | 254 | 249 | 98.03% [95.48, 99.16] | 0.10% [0.02, 0.56] | 92.50% |
| EN | model-assisted | 304 | 293 | 96.38% [93.64, 97.97] | 0.00% [0.00, 0.38] | 92.50% |
| RU | deterministic | 335 | 313 | 93.43% [90.26, 95.62] | 0.10% [0.02, 0.56] | 91.70% |
| RU | model-assisted | 359 | 342 | 95.26% [92.55, 97.02] | 0.10% [0.02, 0.56] | 91.70% |
| ES | deterministic | 265 | 262 | 98.87% [96.73, 99.61] | 0.00% [0.00, 0.38] | 89.20% |
| ES | model-assisted | 408 | 396 | 97.06% [94.93, 98.31] | 0.00% [0.00, 0.38] | 89.20% |

The model-assisted volume gate reaches at least 300 replacements in every
language and the false-change gate passes. Precision is below the required 99%
in every language. Overall result: **FAIL**. The final evaluator writes the full
report and exits with status 2. `SpellingQualification.CURRENT` remains closed;
no setting or Ready model state can enable automatic replacement.

The failed result must not be repaired by retuning these thresholds against the
observed holdout. Model/data development is a separate milestone and its next
qualification requires newly frozen calibration plus a new unseen holdout split.
The current model may continue to order manual suggestions while its bounded
service duty controls remain in force.

Python contract suite: **24/24 PASS**. The initial verifier rejection, zero-score
split bug and fail-report exit-code bug are retained with the corrected final
artifacts. Host scoring is not a device latency or energy measurement. Contextual
punctuation quality, real automatic Binder flow, complete physical Fold matrix,
energy/performance, remote CI, immutable model publication and version 0.3.0
remain open. No push, publication or version change was performed.

Evidence: `tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-product-holdout/`.
