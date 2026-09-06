# Final product spelling replay final review — 2026-09-06

Spec verdict: **PASS** for the bounded tooling review. Code-quality verdict: **PASS**. Both residual P2 findings are closed, and the spot-check found no regression to the earlier closures. No actionable findings remain in this review scope.

This is acceptance of the reviewed replay tooling before its first model call. It is not an executed native-scoring result, product-quality PASS, unseen qualification, or release approval.

## Residual findings closed

1. **Controller-deliverable numeric range — CLOSED.** `tools/eval/smart-typing-0.3/pipeline/final_product_replay.py:295` now requires true-integer token counts in 1–255, matching production `NumericScore` (`app/src/main/java/io/github/mesteriis/rune/keyboard/intelligence/ipc/ScoringContract.kt:28`). The duration-bearing native envelope, exact score fields/order, finite nonpositive values and stable error vocabulary remain enforced at `final_product_replay.py:274`. The new boundary test accepts 1/255 and rejects 0/256, including zero count with zero sum (`test_final_product_replay.py:41`). Invalid success records are rejected, not converted to synthetic unavailable outcomes.

2. **Bound launched JDK runtime — CLOSED.** The exact JDK-local inventory now includes the launcher, release metadata, modules, `lib/libjli.dylib`, and `lib/server/libjvm.dylib` (`final_product_replay.py:47`). Export requires all five files (`:214`) and includes them in its ordinary bound-file verification (`:179`). Replay admission requires the exact schema/inventory/file set, checks that the launcher belongs to the bound home, rejects alternate paths, validates every current byte hash and the canonical distribution digest (`:226`). JSON map order does not affect admission. The regression covers a sorted-JSON round trip, alternate Java refusal, and mutation of the bound VM library (`test_final_product_replay.py:189`). This closes the requested JDK-local dependency gap; external OS inventory is outside this task.

## Earlier closures preserved

- Independent complete-cache and policy-chain admission remains at `final_product_replay.py:349` and `:380`, including fresh identity derivation, complete-receipt reconstruction, calibration score bytes and the preceding receipt chain. Holdout verifies the chain before model launch (`:590`); replay re-admits it and each split (`:646`).
- Full live request identity/payload validation, split-scoped execution, missing/duplicate/foreign delivery refusal, and process failure on row errors remain in the unchanged Kotlin harness (`FinalProductSpellingReplay.kt:249`, `:304`). Its SHA-256 is identical to the prior accepted harness.
- Product `allPass` still requires aggregate and ordinary negative safety while keeping ordinary precision and spelling-only volume (`final_product_replay.py:404`); final report construction uses that gate (`:709`).
- Explicit UI Original role and actual owned-fragment text remain the retention basis (`final_product_replay.py:420`). All-row denominators and actual controller/editor Backspace observations remain unchanged.

No quality override, production-source change, label-bearing model payload or parameter fitting was introduced by these fixes. Binding depends on actual source bytes, so an unrelated Git HEAD change does not itself invalidate the experiment.

## Verification and provenance

Read `task-final-product-replay-second-fix-report.md`, current scoped code and README, the final receipt, and retained RED/GREEN logs. The retained RED demonstrates that counts 0/256 were accepted before the fix. The separate round-trip RED records the JSON-map-order failure. The final retained GREEN records **13 tests passed in 3.135 seconds**, including the implementer's bounded Kotlin delivery positive/refusal test, followed by `SECOND_FIX_V2_EXPORT_REVALIDATED`. Those tests were not rerun by this reviewer.

Independently SHA-256 checked all **84 bound files** and **11 export artifacts** against the final receipt: **zero mismatches**. The fresh directory contains no calibration/holdout score, policy-freeze or replay-report outputs. Its receipt records model calls **0**, with 6,000 rows per split: calibration 2,983 requests/3,017 no requests, holdout 2,973 requests/3,027 no requests. Counts remain observations, not filters.

No implementation edits, builds, tests, Gradle, devices, model calls, commits or delegation were performed during this review. Only this report was written. Native transport with the real runner and full ready/unavailable corpus replay remain unexecuted at this handoff; their eventual evidence must retain the revealed-data and host-JVM limits already documented.

## Exact accepted identities

| File/artifact | SHA-256 |
| --- | --- |
| `pipeline/final_product_replay.py` | `88d72471eb76384ce7cd063e311b49d1394ea7588cace3381f58d3cc9beea745` |
| `pipeline/FinalProductSpellingReplay.kt` | `14401121fe12ec71948f8c61541dee201598b3b5794f3577a768f7e2d5d2f487` |
| `pipeline/test_final_product_replay.py` | `52ee32573e8e3316f0c40292a3900a0fc4665191dd002aed23f205510eadfaed` |
| `pipeline/README.md` | `1cd842c44ec2b7aa7fb2867883fae286e7bf9db2c8049700bba53255e804a55c` |
| `review-second-fix-v2/export-receipt.json` | `62748ec036e8ce8eb42f1902a49a8abd7fed00305b62913171219eff688be932` |
| `review-second-fix-v2/source-freeze.json` | `fe2bc43d6f7f180367f26348d669f53ee923b451cb1b298f6bd5a4645806d64e` |
| `review-second-fix-v2/final-product-spelling-replay.jar` | `e9a5e60d4a5fffdff308320f69b8f2c944c9e85c21a9fdfb9353a226e982b1de` |

The accepted export directory is `build/smart-typing-0.3/final-product-replay-20260906-review-second-fix-v2/`. Its JDK inventory digest is `ac16018d100cee0f9acd41a380375bb583833b15a4e6ba582f3a642f8cee5661`; runner/model hashes remain `bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553` / `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`. Preserve all superseded exports and failure evidence. The scoped review accepts this exact fresh export for the subsequent sequential execution, subject to its existing byte-drift checks.
