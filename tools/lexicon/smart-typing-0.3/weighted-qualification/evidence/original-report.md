# Weighted candidate development qualification report

**Correctness contracts PASS: 775/775 requests, zero violations. Retrieval feasibility remains limited: 72/716 development retrieval requests complete under unchanged caps.** No production edits, pruning changes, cap relaxation or policy tuning were made. These are actual host results from the integrated generator/packed reader, not device or holdout evidence.

## Actual development720 results

Every original query remains in the frozen corpus. Four queries are exact valid words in another routed dictionary and correctly return VALID_WORD with an AutoReplace veto. The remaining 716 exercise retrieval:

| Active/source language | Fixed requests | Other-route valid words | Complete retrieval | State exhausted | Verification exhausted | Full oracle top-7 identities retained | Source word returned |
|---|---:|---:|---:|---:|---:|---:|---:|
| EN | 240 | 1 | 23 / 239 | 205 | 11 | 867 / 1145 | 197 / 239 |
| ES | 240 | 3 | 31 / 237 | 192 | 14 | 1171 / 1348 | 209 / 237 |
| RU | 240 | 0 | 18 / 240 | 205 | 17 | 977 / 1426 | 157 / 240 |
| Total | 720 | 4 | 72 / 716 | 602 | 42 | 3015 / 3919 | 563 / 716 |

Complete coverage is about 10.1% of retrieval requests. Micro top-7 identity retention is about 76.9%; source-word return is about 78.6%. These are retrieval diagnostics on fixed development fixtures, not correction accuracy, user intent or AutoReplace quality. A complete source neighborhood can have fewer than seven alternatives, which explains the top-7 denominator. The source word was independently in the actual routed neighborhood for every one of the 716 retrieval requests.

All 644 incomplete requests retain the strict veto. Of them, **354 happen to return the same full weighted top-7** (EN108, ES137, RU109); they remain incomplete and are not counted as successful exhaustive search or automatic-replacement eligibility. No algorithm bug was found by the full/partial/routing/case assertions. The dominant unresolved issue is bounded exhaustive-neighborhood feasibility, not a license to reinterpret exhausted results as complete.

## Explicit additional controls

55 inputs were declared and locked before production execution: 19 valid-word protections, 15 protected tokens, 1 pre-cancelled request, and 20 retrieval requests (10 complete, 7 state exhausted, 3 verification exhausted). Across valid-word controls there are 15 primary exact hits and 4 fallback exact hits. Both layouts for shared EN/ES valid words and Latin under RU layout are represented. Retrieval controls include active-language ambiguity, fallback quota/dedup, title preservation, accented Spanish/ñ, ё and decomposed NFC, repeated characters and transposition, short radius, and exactly 32 codepoints. Protected controls include mixed scripts/script marks, technical paths/identifiers, all caps/mixed case, digits, hyphens, unsupported script, empty/malformed input and 33 codepoints. Inputs/expected derivations are public fixtures, not numeric result payloads.

Every alternative's display/folded display, raw terminal identity, language/fallback/prior, source frequency rank, unit radius, weighted quarter cost, repetition fields, length difference and case pattern matched the independent expected record. Fallback suggestions never exceed two, duplicates are removed by folded display, and original text is retained (or null for cancellation). Exact membership and traversal share the same inspected-state budget. Traces account for all inspected states and verified terminals; complete scans contain exactly the independent full routed terminal set. Incomplete outputs equal independent selection from their verified subset and are contained in the full oracle set.

## Oracle independence and frozen identities

The 720 original queries/categories/source metadata were copied unchanged from the validated full benchmark fixture. There is no holdout/calibration access. The explicit 55 controls are fixed public examples. Input lock was written before any production retrieval:

- `fixtures/inputs.json`: `9ad04de931daa908650b4cdbea842675ee6e1dbe9f6ca6e18bf38a3dc3203abd`.
- Exact frozen pipeline manifest: `ec26c80edd28f2b42008a844c8b0ce83c11759386ccc9de591cb038a7a4f3c48`.
- Full benchmark fixture manifest: `39c5b0836e67678d1711f33936ab08cd0c970e679e861b31185411dc3ac8d534`.

Own-language full unit neighborhoods reuse the independently checked benchmark oracle. Only missing actual-route neighborhoods were scanned: EN187, RU2, ES251, total440. A fresh local binary was compiled from the unchanged independent full-list C++ oracle source (`a9a689eb7b11f9c03a92ae2dd8f086e645ec2fbc23fd02f3d673cbb2b865f6f0`). Whole canonical wordlists and frequency inputs were hashed against frozen identities; membership/terminal ordinals and frequencies are obtained from those inputs, never from the production reader.

The independent weighted/reference implementation enumerates every prior matching transposition endpoint in prefix DP, with separate source-derived routing/protection/case and global grouping/quota selection. It does not call production distance, ranker, router, case helpers or the packed reader. Its finite Dijkstra comparison covers 39 strings × 39 strings × 2 profiles, checking reachable distances up to ten quarter units and exclusion above that bound; separate sentinels cover unrestricted CA→ABC, transposition, accents and adjacent substitution.

Expected data was finished **before** production execution:

- `fixtures/expected.json`: `5111ae7db9c2dc75a877e8b70f9796a385ca93c5847eab0ed1c388a1a5a911a5`.
- Full independent candidate records: **22,034**, including routed duplicates before case/dedup/quota selection.
- `fixtures/candidates.tsv`: `ea404738c03b541316fac2b6b3e771b28c4551d896b71b627ba5dfe56dccc6fa`.
- Per-language query/neighborhood digests and oracle binary/source hashes: `oracle/provenance.json` and `oracle/scan-plan.json`.

## Actual execution/checks

Exact commands are in README. The following evidence is retained:

| Check | Actual result | Evidence |
|---|---|---|
| Input selection/lock before production | 720 + 55 frozen | `fixtures/input-lock.json` |
| Missing-route independent full scans and weighted expected generation | 440 pairs, 22,034 full candidates | `reports/oracle-build.log`, `oracle/provenance.json` |
| Independent reference contracts | 4 tests PASS | `reports/reference-tests.log` |
| Kotlin 2.2.10 compile against integrated production sources | PASS, 13 production sources plus observation harness | `reports/compile.log`, `reports/compiled-sources.json`, `reports/compiled-artifact.json` |
| Real packed handle validation + generator execution | All 3 language assets validated; 775 requests finished | `reports/actual.tsv`, `reports/run-identity.json` |
| Full and partial output/feature/routing/budget comparison | 775 PASS, 0 violations | `reports/comparison.log`, `reports/summary.json`, `reports/per-query.tsv` |
| Negative comparison controls | 4 tests PASS | `reports/comparison-negative-tests.log` |

Negative controls prove rejection of a false COMPLETE claim hiding unvisited terminals, an incomplete output without veto, a wrong weighted feature, and incorrect routed exact membership. They mutate copies of numeric records and never rerun the production generator. The same production generator instance handled all 775 requests sequentially; the tracing adapter only observes numeric deltas and visitor outcomes. Pinned source hashes were identical before/after execution. Loader validation uses actual `FrozenPackedLexicons` and the approved trie/length/rank bytes, including full structure/canonical-hash reconstruction. The Android APK loader itself is outside this host run.

After the single production run, the reproduction scripts gained explicit assertions for the already-frozen development TSV/JSONL source hashes and the locally copied inherited TSV hashes. The same actual files were rechecked against the locks; no input, expected candidate, reference algorithm, compiled source or production result was regenerated. Python syntax and all compiled-source identities were checked again. These final provenance assertions are reproduction hardening, not an additional production run.

Only the isolated C++ oracle and Kotlin host toolchains ran. No Gradle, ADB, device measurement, model, source expansion, native lexicon performance benchmark or production root edit was performed by this task. Parent functional Gradle work could overlap; incidental host duration is deliberately not reported as performance evidence. No overall Smart Typing quality or release completion is claimed. Independent review remains required for this qualification package.
