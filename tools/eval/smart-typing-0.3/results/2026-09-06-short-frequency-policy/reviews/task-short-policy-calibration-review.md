# Short-frequency policy: calibration controller review

2026-09-06. **The calibration evidence supports retaining the frozen coefficients and proceeding to the separately frozen final evaluation.** It does not approve promotion or establish holdout acceptance. No coefficient fitting or candidate-policy revision was performed. The raw all-row Original gate remains FAIL; the separate existing state-based contract annotation passes every row and explains that discrepancy without removing any row.

## Complete calibration outcomes

All 6000 calibration inputs and both ready/unavailable controller modes were joined by exact row identity against the prior controller evidence. Input dictionaries match exactly. No holdout outcome, metric or label was used for selection; the baseline JSONL was streamed and immediately filtered on split before joining or computing metrics. The current source freeze is `aa17ff21c4d28a25aac6b929962b38debbbe91650f0a957afd3cb05bedd60b00` and its complete calibration cache contains 2983 responses. The existing source/export/cache/calibration-report admission checks passed before the join.

| Language | Prior correct / spelling automatic | New correct / spelling automatic | New precision | Correct/protected false changes | Exact Undo |
| --- | --- | --- | --- | --- | --- |
| EN | 344 / 347 | 345 / 347 | 99.42% | 0 / 1000 | 2000 / 2000 |
| RU | 354 / 357 | 354 / 357 | 99.16% | 0 / 1000 | 2000 / 2000 |
| ES | 430 / 434 | 430 / 434 | 99.08% | 0 / 1000 | 2000 / 2000 |

Every language exceeds the existing 95% precision and 300 automatic spelling-change calibration thresholds, with zero aggregate or ordinary-spelling false changes on the complete 1000 negative rows per language. Model-ready errors/refusals are zero. Unavailable replay makes zero ordinary spelling automatic changes, with exact Undo on all 2000 rows per language. ES retains one canonical automatic change separately from its 434 ordinary spelling changes. These are calibration observations, not final gates.

## Changed candidates and outcomes

| Language | All rows | Short owned originals | Changed ordered requests/generations | Changed continuation sets | Changed final texts |
| --- | --- | --- | --- | --- | --- |
| EN | 2000 | 135 | 17 | 15 | 2 |
| RU | 2000 | 304 | 71 | 52 | 0 |
| ES | 2000 | 178 | 27 | 22 | 0 |

All 115 changed ordered requests/generations belong to the short owned-original subset; no long or no-owned-word generation alternatives changed. The short diagnostic uses NFC → lowercase → NFC scalar length below five, matching the source folding rule for this corpus. It is an explanatory subset, never a replacement denominator. Full ordered request comparison includes prefix, candidate IDs and continuations; set comparison separately ignores continuation order. The 89 set changes and 26 order-only changes are retained in row evidence.

Only two final text outcomes differ: `teh` previously abstained and now correctly becomes `the`; `Rofo` previously incorrectly became `Roto` and now abstains. EN automatic volume stays 347 while correct changes rise by one. RU/ES final outcomes are unchanged. On changed-generation rows, EN changes from 0 correct of 1 automatic to 1 correct of 1 automatic; RU/ES make zero automatic spelling changes. Across all short owned originals, EN changes from 1 correct of 2 automatic to 2 correct of 2 automatic; RU/ES make zero.

Target recall on all 1000 typo rows per language changes EN 952→959, RU 925→941, ES 925→936: 39 gains and five losses, total 2802→2836. On the short typo subset it changes EN 14/28→21/28, RU 80/120→96/120, ES 32/57→43/57. The five losses remain explicit:

| Typed token | Lost target | Prior candidates | New candidates | Controller outcome |
| --- | --- | --- | --- | --- |
| горп | гора | горе / гора / гори | горы / горе / гору | Abstains before and after |
| ьему | тему | тему / ему / нему | ему / нему / чему | Abstains before and after |
| сыо | сыр | сыр / сыт / со | со / сын / сто | Abstains before and after |
| Чее | Чек | Чек / Чае / Чем | Чем / Ее / Нее | Abstains before and after |
| oan | pan | pan / kan / own | tan / han / van | Abstains before and after |

Each named token appears once in calibration and is retained with before/after requests, alternatives, final text, automatic edit, model admission and evaluation. `teh` changes from `ten / eh / tea` to `the / ten / eh`, producing `Please close the ` with exact Undo. These observations do not erase the suggestion losses or establish acceptance outside this calibration split.

## Original ownership: full accounting

The raw frozen report remains exactly **1902/2000 Original retention and allPass=false per language**, with `originalAlwaysAvailablePass=false`. No frozen gate, report, coefficient or denominator was rewritten.

Applied the existing `original_applicability.classify/annotate` functions only to current calibration rows. For each language in each mode: 1902 owned-word rows, 98 no-word rows, zero invalid states, **2000/2000 state-contract passes**, zero failures. All owned words require an exact Original item and ID matching the actual owned token and composing state; this includes 125 fragment-owned rows per language rather than assuming the corpus full token is always owned. Every no-word row independently requires empty ownership/candidates, no selected candidate, no model request, no automatic edit, exact unchanged text plus the boundary, and exact backspace restoration. No corpus category or model-request exemption is used.

Thus the 98 raw failures per language are empty-ownership states whose safe no-word behavior passes the existing full-accounting contract. Both raw failure and separate contract pass remain visible. This annotation supports interpreting the Original requirement as applying to every actual owned word while preserving all 2000 rows in the safety accounting; it does not silently convert the frozen all-row gate into PASS.

## Reproducibility and scope

Wrapper and outputs are retained under `build/smart-typing-0.3/short-policy-evaluation-20260906/cal-review-01/`: `review.py`, `comparison.jsonl`, `summary.json`, `commands.json`. Exact command:

```sh
python3 build/smart-typing-0.3/short-policy-evaluation-20260906/cal-review-01/review.py
```

The first attempt stopped before producing outputs because no-word `actualRequestGeneration` is null. The wrapper was corrected to treat null generation as an empty alternatives list, then the command succeeded. No evaluation policy or frozen source was edited. All declared inputs/tools were rehashed after the join.

- Baseline row-evidence SHA: `6a19850ed122dd782ecde33aaba8087d76c77a34962fda44c055c94f717cfa75` (explicit expected pin verified).
- Existing applicability tool SHA: `25cb79bd88c0e553133fc88588c3b22394d299370d3f9e8d32ad1507e0d86db9`.
- Review wrapper SHA: `09414e73e5ddadf885343d896648d2ff37b518012d11f7fe6fe2cbcd51d8120c`.
- Summary SHA: `a6b61964383a8c127faf63dbd7a4e9f25405f3c6e1c338966a0ef2f2b7b604fb`.
- Comparison SHA: `426d5ac726297246e6799f89fe4ca6b239f47f0ac39d5b56d8e21f3d1e96f9dc`.

`summary.json.inputAndToolSha256` records exact current source freeze/export/report/evidence/cache/request and adapter/base evaluator/Unicode source/tool identities. This review did not run a model, export rows, access a device, invoke Gradle, modify the frozen adapter, or read holdout results. No policy freeze or holdout score directory existed when the review began. Physical and release gates remain separate.
