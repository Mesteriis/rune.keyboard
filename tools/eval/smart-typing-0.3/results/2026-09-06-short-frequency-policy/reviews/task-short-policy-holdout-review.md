# Short-frequency policy: frozen holdout controller review

2026-09-06. **The frozen variant passes the agreed numerical point gates on this revealed holdout split, with two newly unsafe English automatic changes that must remain explicit.** The separate existing Original ownership annotation passes every row; the frozen raw all-row Original FAIL and allPass=false remain unchanged. This review performs no tuning and approves no adoption. This corpus was previously revealed; these observations support revealed-data product acceptance, not unseen qualification.

## Complete results

| Language | Prior correct / automatic spelling | Frozen variant | Point precision | Correct/protected false changes | Model errors |
| --- | --- | --- | --- | --- | --- |
| EN | 293 / 304 | 294 / 306 | 96.0784% | 0 / 1000 | 2 |
| RU | 341 / 358 | 341 / 358 | 95.2514% | 1 / 1000 | 10 |
| ES | 396 / 408 | 396 / 408 | 97.0588% | 0 / 1000 | 3 |

Every language meets the existing ≥95% point precision, ≥300 ordinary spelling automatic changes, and ≤0.5% correct/protected false-change limits. The Russian false change is already present in baseline and unchanged. EN automatic volume rises by two and correct count by one, so overall EN precision declines from 96.3816% to 96.0784%. Passing the aggregate threshold does not negate individual regressions.

Each language retains the full 2000 rows, including all errors and abstentions. Current model requests are EN1015/RU994/ES964: 2973 responses, 15 model errors and zero delivery refusals. RU exchanges one scoring error for another across changed short requests (`Силв` newly errors, `порь` now receives numeric scores); ES `farp` newly returns a scoring error. These rows remain abstentions and final text does not change. Native errors were not retried, dropped or filled from old scores.

Ready and unavailable modes both have exact Undo on all 2000 rows per language. Model-unavailable replay makes zero ordinary spelling automatic changes. All source/export/freeze/cache checks passed before this read-only join; holdout report artifact hashes were independently checked.

## Changed subset and all newly unsafe automatic outcomes

| Language | Short owned-original rows | Changed ordered requests/generations | Changed continuation sets | Changed final texts | New correct auto / new unsafe auto / new abstention | Target gains / losses |
| --- | --- | --- | --- | --- | --- | --- |
| EN | 150 | 30 | 27 | 4 | 1 / 2 / 1 | 4 / 3 |
| RU | 291 | 63 | 42 | 0 | 0 / 0 / 0 | 14 / 5 |
| ES | 205 | 32 | 30 | 0 | 0 / 0 / 0 | 9 / 4 |

All 125 changed ordered requests/generations are short. There are 99 candidate continuation-set changes and 26 order-only changes; no long or no-owned-word generation alternatives change. Short length is the NFC → lowercase → NFC scalar length of the actual owned token, below five. Ordered request comparison includes prefix, candidate IDs and continuations. These subsets explain behavior and do not replace full gate denominators.

All four final text changes are English:

| Row / public token | Before | After | Evaluation |
| --- | --- | --- | --- |
| `en-holdout-typo-05-2-1`: `ipe` | `A plumber replaced the ipe ` | `A plumber replaced the ice ` | **New wrong automatic correction**: authored target is `pipe` |
| `en-holdout-typo-05-2-7`: `pioe` | `A plumber replaced the pioe ` | `A plumber replaced the pipe ` | New correct automatic correction |
| `en-holdout-typo-07-2-4`: `ipk` | `The artist mixed the ipk ` | `The artist mixed the ink ` | **New unsafe automatic correction**: target text is `ink`, but this ambiguous row explicitly requires `noAuto=true` |
| `en-holdout-typo-07-2-8`: `inb` | `The artist mixed the in ` | `The artist mixed the inb ` | New abstention removes an earlier wrong automatic correction |

The two bold rows are the complete set of newly unsafe automatic spelling outcomes. Both were prior abstentions. The `ipk` result is not a textual target mismatch; it violates the authored abstention requirement and is therefore counted as incorrect by the existing evaluator. These are typo-cohort failures, so zero EN correct/protected false changes does not hide or contradict them: they enter precision as incorrect automatic changes.

The changed-generation EN subset moves from 1 correct /5 automatic to 2/7; the broader short EN subset moves from 6/11 to 7/13. RU/ES changed and short subsets make zero ordinary spelling automatic changes. This is mixed evidence for the short policy even though the full language point gates pass.

Overall typo-target recall changes EN925→926, RU917→926, ES892→897, each out of 1000: 27 gains and 12 losses, net +15. Short typo recall changes EN23/40→24/40, RU74/118→83/118, ES33/67→38/67. Lost targets are retained individually in comparison evidence:

- EN: `onk` loses `ink`; `Inl` loses `Ink`; `dlay` loses `clay`.
- RU: `мыка` and `иука` lose `мука`; `бинь` loses `бинт`; `мачк` loses `маяк`; `порь` loses `порт`.
- ES: `mada` loses `masa`; `dera` and `ceta` lose `cera`; `garo` loses `faro`.

The five named calibration losses and `teh` do not occur in this holdout split; their earlier calibration outcomes are not spliced into these totals.

## Original ownership and unchanged raw FAIL

The frozen holdout report continues to show **1901/2000 raw Original retention per language**, `originalAlwaysAvailablePass=false`, and `allPass=false`. No frozen report or threshold was edited.

Applied the existing `original_applicability.classify/annotate` to current holdout evidence only. Each language in both modes has 1901 owned-word rows plus 99 no-word rows, zero invalid states, zero failures, and **2000/2000 complete state-contract passes**. Owned rows require the exact Original text/ID and composing ownership. No-word rows require empty ownership/candidates, no selection, no request, no automatic edit, unchanged input plus the boundary, and exact backspace restoration. All 2000 rows remain accounted for, without category or request-based exclusions. The annotation explains the raw gate mismatch rather than overwriting its FAIL.

## Source-bound artifacts and execution

Read-only wrapper and outputs: `build/smart-typing-0.3/short-policy-evaluation-20260906/hold-review-01/{review.py,comparison.jsonl,summary.json,commands.json}`. Exact command:

```sh
python3 build/smart-typing-0.3/short-policy-evaluation-20260906/hold-review-01/review.py
```

Command succeeded on the first run. The complete original evidence file was verified against expected SHA `6a19850ed122dd782ecde33aaba8087d76c77a34962fda44c055c94f717cfa75`. Baseline lines are filtered to holdout immediately before labels, joins or metrics. All 12000 selected mode-row identities and complete language/cohort partitions were verified; every old/current input dictionary matches exactly.

Current source freeze remains `aa17ff21c4d28a25aac6b929962b38debbbe91650f0a957afd3cb05bedd60b00`. `summary.json.inputAndToolSha256` binds exact current freeze/export/policy-freeze/report/evidence/cache/request bytes, old evidence bytes, and wrapper/adapter/base/applicability/Unicode tools. All identities were rechecked after the join.

- Review wrapper SHA: `dc50cbcfb3fb943faa8eea4e44b617e3d395b54db8347c4b5c9c0ddaa71ea717`.
- Summary SHA: `f5c9493cd336a1adc31d6e767b1a727d3c62a08db8d302dfcd7a36a2f10e6f4e`.
- Comparison SHA: `1aee65e233ea65a49d3afe8afef36c10bc2ed31d49123ecab830f4618f8075f7`.
- Existing applicability SHA: `25cb79bd88c0e553133fc88588c3b22394d299370d3f9e8d32ad1507e0d86db9`.

No model execution, source change, device work, Gradle invocation, old-result mutation or coefficient selection was performed. Adoption review must retain the two new unsafe changes, twelve target losses, descriptive nature of this already-revealed corpus, and separate physical/release gates.
