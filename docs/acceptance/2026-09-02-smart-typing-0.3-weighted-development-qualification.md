# Smart Typing 0.3 — weighted development retrieval evidence, 2026-09-02

**Historical host correctness: PASS, 775/775 request contracts. Bounded complete retrieval remains insufficient:72/716 development retrieval requests.** This acceptance record preserves an independently reviewed existing run; promotion did not rerun production retrieval or a device benchmark.

The source-independent full oracle covers the fixed 720 development inputs plus 55 explicit public controls. Four development inputs are valid words in another routed dictionary and correctly prohibit replacement. Full neighborhoods, weighted costs, ranks, routing, case preservation, display dedup and fallback quota are checked; original plus at most seven alternatives remain bounded. There is no holdout/calibration/model evaluation.

| Active language | Development retrieval | Complete | State exhausted | Verification exhausted | Oracle top-seven identities retained | Source word returned |
|---|---:|---:|---:|---:|---:|---:|
| EN |239|23|205|11|867/1145|197/239|
| ES |237|31|192|14|1171/1348|209/237|
| RU |240|18|205|17|977/1426|157/240|
| Total |716|72|602|42|3015/3919|563/716|

All 644 incomplete results keep the strict AutoReplace veto, including 354 that happen to equal the full oracle's top-seven. Complete results equal the entire independent routed terminal set and final weighted selection. Partial results are independently selected from verified source-oracle subsets; neither partial recall nor coincidental equality proves unseen candidates irrelevant. The reader/generator caps remain 8,192 inspected states and 64 terminal verifications shared across routes, with unit radius 1 below five codepoints and 2 otherwise, maximum 32 codepoints.

The 55 additional controls cover 19 valid-word outcomes, 15 protected tokens, 1 pre-cancelled request and 20 retrieval requests (10 complete, 7 state exhausted, 3 verification exhausted). These are declared functional fixtures, not a population sample or correction-accuracy labels. The independent oracle retains 22,034 pre-dedup candidates, filling 440 missing route/query neighborhoods with a separately compiled full-list C++ oracle before the historical production execution.

Package: [weighted qualification](../../tools/lexicon/smart-typing-0.3/weighted-qualification/README.md). It contains 41 byte-preserved historical text artifacts, all 43 original artifact identities, original independent review and source/provenance records. The two compiled historical binaries are omitted; active commands rebuild explicitly from pinned source/toolchain and use fresh ignored output directories. Historical source scripts are archived for audit; portable commands do not depend on the old ignored qualification directory.

Immutable identities:

- Historical 43-artifact manifest: `45c2c6c91e69ccb78c042318d481c04b1a16589f0d41ae3f06057fc325648170`.
- Inputs: `9ad04de931daa908650b4cdbea842675ee6e1dbe9f6ca6e18bf38a3dc3203abd`.
- Full weighted expected data: `5111ae7db9c2dc75a877e8b70f9796a385ca93c5847eab0ed1c388a1a5a911a5`.
- Actual numeric request/trace results: `fa021ac23db67ee46f8349d369377adcafc1605f42d456824bbbcf628a1b8ff5`.

This evidence does not establish API26/API37 or physical Fold behavior, latency, CPU/energy/battery budgets, service/editor integration, correction quality, confidence calibration or release completion. A future exact top-seven contract/algorithm requires separate proof and review; the current exhaustive reader's COMPLETE meaning is unchanged. No exhausted result becomes eligible for automatic replacement through this promotion.
