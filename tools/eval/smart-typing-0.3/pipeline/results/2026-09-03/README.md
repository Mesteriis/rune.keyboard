# Calibration retrieval baseline — 2026-09-03

Production source baseline: `5ff78a8` (exact source/asset hashes in provenance).
Fresh execution compiled the actual Kotlin generator and validated frozen packed
assets. All 6,000 calibration spelling rows completed with bounded result records;
no model or holdout was executed. No expected word was supplied to generation.

| Calibration measure | EN | RU | ES |
| --- | ---: | ---: | ---: |
| Rows | 2000 | 2000 | 2000 |
| Unique typed inputs | 1500 | 1500 | 1499 |
| Typo rows | 1000 | 1000 | 1000 |
| Expected spelling present | 894 | 666 | 824 |
| Expected spelling present, retrieval complete | 22 | 126 | 90 |
| All rows with alternatives and no retrieval veto | 41 | 137 | 98 |
| State-budget exhausted | 935 | 791 | 762 |
| Verification-budget exhausted | 26 | 60 | 116 |

Original is retained for every row. Candidate recall includes incomplete
suggestions; it does not imply that they can be automatically applied. Completion
does not itself establish confidence or authorize a replacement. For this
calibration set, even perfect ranking cannot correct more than the complete
recalled typo count without changing retrieval or violating its veto. This
identifies retrieval as a prerequisite for the intended AutoReplace coverage.
It is not a prediction of holdout counts or permission to increase search caps.

The fixed prepared corpus repeats candidate-set-sensitivity observations that
become identical generator inputs. Row counts retain that weighting; they are
not 6,000 independent typing observations. No precision, quality-gate PASS,
model ranking, latency or battery conclusion follows from these retrieval counts.
No thresholds were selected, and the previous failed model report is unchanged.

`*.gz` are deterministic compressed copies of the exact public-corpus protocol,
original-preserving candidate JSONL and label-free generator inputs. Their
decompressed SHA-256 values match `provenance.json`. Compiler/runtime stdout
outside the protocol was empty; eight protocol regression tests passed.
`manifest.json` identifies the archived bytes. No personal input is present.

Next: improve candidate retrieval with an exact top-N proof and the existing
8192-state/64-verification bounds, retaining incomplete-result vetoes. Then
calibrate the actual deterministic/model-assisted decision pipeline and freeze
its configuration before holdout. The earlier weighted top-seven prototype is
research evidence; it is not silently substituted into this production baseline.
