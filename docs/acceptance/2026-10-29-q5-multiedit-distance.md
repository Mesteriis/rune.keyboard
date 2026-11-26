# Q5: higher-distance choices on disclosed multi-operation inputs

The original historical word-ranking test partition was restored byte for byte from the verified public fixture. It has 300 unchanged controls and 1,500 synthetic typo rows: 600 with one edit operation, 600 with two, and 300 with three. Two fresh current-product JVM controller/editor runs completed all 1,800 rows; their full observer projections, excluding the two declared timing fields, matched exactly. The inputs and targets were disclosed before this experiment and are not independent holdout data.

| Synthetic operations | Rows | Automatic edits | Exact synthetic target | Exact target with selected candidate distance > 1 |
| --- | ---: | ---: | ---: | ---: |
| 1 | 600 | 493 | 492 | 0 |
| 2 | 600 | 289 | 247 | 247 |
| 3 | 300 | 68 | 34 | 34 |

The selected-candidate distance is the controller observer's recorded `unitDistance`, not the number of generator operations. A blanket veto after selection would reject these 281 currently correct high-distance choices in this disclosed synthetic set. This is a tradeoff screen, not a counterfactual product replay: earlier rejection could alter ranking, and outcomes in natural typing remain unmeasured. There were 22 other high-distance automatic choices in the two-operation group and 25 in the three-operation group that did not match the synthetic target. The 300 source controls produced no automatic edit in this run; their source correctness is not independently verified. One automatic one-operation edit could not be attributed to the recorded admission candidate and is excluded from the distance breakdown.

The historical prefixes often already end with whitespace; the replay adds a separator and mechanical input handling changes the resulting text in 1,617 of 1,800 cases. The analysis checks and counts this separately and measures final replacement against the actual pre-boundary prefix, not the unchanged source prefix. All counted automatic edits passed immediate exact Undo in this host editor simulation. Neither this run nor the synthetic target labels establish physical-device behavior, a population accuracy rate or model qualification. No policy was changed.

The [analysis receipt](2026-10-29-q5-multiedit-distance.json) binds the verified archive rows, observations and replay receipt; the [projection comparison](2026-10-29-q5-multiedit-projection.json) records the two-run equality. Raw replay artifacts are under `build/q5-multiedit-replay-*`. Three focused tests cover prefix-input deviation, correct multi-edit attribution, missing attribution, corrupt identity and Undo failure. The original archive's article and target-context exclusions predate this screen; the [follow-up disclosure](2026-10-29-q6-wordrank-replay-disclosure.md) also quarantines the observed inputs, synthetic targets and outputs. Global registry coverage remains incomplete.
