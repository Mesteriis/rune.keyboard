# Contextual suggestion quality — 2026-09-03

Baseline `825305f`. The host harness compiles and executes the exact production
`ContextualPunctuationEngine` with its real language enum. All 1,200 authored
punctuation rows produce the same bounded seven variants and stable IDs used by
the APK: space, comma, colon, semicolon, period, question mark and exclamation
mark. Sentence alternatives retain the production first-code-point casing.

The exact Rune Text GGUF and scorer completed 600/600 calibration responses.
Before any holdout request, config
`38eb7d5a93130c1fbdbaae050244a237501a4bd79c25cfb85892123b3dab9d11`
froze the already implemented rule: select the best non-Original average log
probability only when it is strictly greater than Original, with lower ID as the
stable tie break. No threshold search was performed. The config binds the engine
and quality source hashes, export receipt, model identity and calibration score
digest. The separate holdout then completed 600/600 responses without errors.

| Language | Calibration correct / clear | Holdout correct / suggested clear | Holdout clear coverage | Non-space suggestion on ambiguous |
| --- | ---: | ---: | ---: | ---: |
| EN | 100/100 | 100/100 | 100/100 | 97/100 |
| RU | 91/100 | 58/98 | 58/100 | 96/100 |
| ES | 73/100 | 49/100 | 49/100 | 100/100 |

The holdout result does not support a release-quality claim for RU or ES and
shows that the base model rarely abstains in underdetermined contexts. EN clear
clauses rank correctly in this authored set, but its 97% ambiguous non-space
rate prevents a broad contextual-quality claim. This result is therefore
recorded as **not accepted for final release qualification**. It must not be
repaired by fitting a new margin on these holdout rows.

Contextual punctuation remains suggestion-only: automatic replacements are
exactly zero, and an explicit user tap is required. The result does not weaken
the spelling qualification gate and does not authorize a version bump or model
publication. A replacement/fine-tuned model needs a newly frozen calibration
and unseen holdout.

Python contract suite: **27/27 PASS**. The score caches contain public fixture
IDs and numeric results only. Host timing is not a Fold latency or energy
measurement. No push, model publication or version change was performed.

Evidence: `tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-contextual-quality/`.
