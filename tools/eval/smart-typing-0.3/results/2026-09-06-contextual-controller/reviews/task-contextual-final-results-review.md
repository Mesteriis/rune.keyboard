# Final contextual attribution results — evidence review

**Verdict: PASS for receipt consistency and the stated observed-source attribution result.** The completed supplement and replay form a coherent 1,200-row result under the previously reviewed host, source, cache, policy, and supplemental-admission contracts. No unresolved row, harness failure, transport error, forbidden edit, automatic contextual edit, or tap refusal remains. This is an evidence audit; the earlier code and protocol reviews remain authoritative.

Reviewed read-only:

- `supplement-prepare-01`, `supplement-freeze-01`, and `supplement-replay-01` under `build/smart-typing-0.3/contextual-controller-attribution-20260906/`.
- `root-verify.log`, SHA-256 `73bb56fe3b025abe3f60f8b1e05f11503bbebcbe87f0e2b68984ac4897007373`, which records: `Verified full contextual attribution bindings and all row denominators; no inference.` Root reported the verify process exited zero.

No source, Gradle, device, native scorer, model, network, replay, or verifier command was run for this review. Checks were read-only shell inspection except for this report.

## Supplement execution chain

The frozen supplement retains internal freeze SHA-256 `0f067e87fdf1982102f797e6c86b39a858f75bd73b09009d6e7e549ca434d21c` and ordered request digest `cfef3f5f2e84612b0b75b26d63d747d5cadde4bef7e90c58108d7d9a74bc09cc`. It binds the reviewed total-log-probability policy, token range 1–255, fixed model SHA-256 `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`, and runner SHA-256 `bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553`.

Calibration contains exactly 18 requests and 18 responses. Its execution receipt records `attempts=1`, `exitCode=0`, no error IDs, and no unrepresentable IDs. Holdout contains exactly 28 requests and 28 responses with the same one-attempt, zero-exit, zero-error, and zero-unrepresentable result. Request and response IDs match in exact order for both splits; all 46 responses contain seven scores ordered by candidate IDs `[0,1,2,3,4,5,6]`, with controller-representable token counts.

The holdout run-input and completion bind calibration completion SHA-256 `8cab1f2444c67069c95fab652ba2846f69d25f2dfaa45f586cfd71a36a855cd4`, which equals the actual calibration `complete.json` hash. This preserves calibration-before-holdout ordering without fitting. The holdout completion SHA-256 is `63f50f6e2606814c07127bdb7287803016dc03f40ceeac3d3d71d3225764733e`.

## Full replay consistency

The replay contains 1,200 `actual.jsonl` records, 1,200 response bindings, and 1,200 row-evidence records with 1,200 unique IDs. Its binding partition is exact and exhaustive:

| Binding | Rows |
|---|---:|
| Original v5 exact cache | 863 |
| Supplemental exact response | 46 |
| No contextual request | 291 |
| **Total** | **1,200** |

The row provenance partition independently matches those counts: 863 `original-v5-cache`, 46 `supplement`, and 291 without response provenance. The final `unscored-requests.jsonl` is empty. Report and row evidence agree on zero unresolved rows, zero unscored payloads, zero unrepresentable replies, zero harness errors, zero forbidden edits, and zero automatic contextual edits. `attributionComplete` is true.

There are 179 actual punctuation offers, 179 tap attempts, and 179 successful taps, with zero refusals. The full-denominator observed-source agreement is 471/1,200 (39.25%), suggestion coverage is 179/1,200 (14.92%), and suggested-source agreement is 171/179 (95.53%). These are descriptive source-boundary measures. In particular, the full-denominator agreement includes rows whose Original/space outcome matches the observed source boundary; it is not a suggestion-precision measure.

The requested holdout figures are internally exact when labeled **suggested-source agreement**:

| Holdout language | Suggested-source matches | Offers | Rate |
|---|---:|---:|---:|
| English | 31 | 31 | 100% |
| Russian | 33 | 34 | 97.06% |
| Spanish | 19 | 20 | 95% |

Their corresponding full 200-row source-boundary agreements are 81/200 English, 83/200 Russian, and 69/200 Spanish. Keeping these two denominators separate prevents the high agreement among offered suggestions from being mistaken for all-row semantic accuracy.

The replay provenance binds the prepared completion and all generated replay ledgers. Its SHA-256 is `be908acf98a2c733a4330e1851475c32b0b08b993c3a75642ab2c335595596cc`, and the final marker binds that exact value with `attributionComplete=true`. Key final identities:

| Artifact | SHA-256 |
|---|---|
| `supplement-prepare-01/prepare-complete.json` | `abac0b8285a449174b2749f4a2c1ddc7ed0875dc1ddb3edbce8a877c962fb2b0` |
| `supplement-freeze-01/freeze.json` | `e60e059d5afe6bce51aa7005139f3597791214971fe1efff00549f7586778b9c` |
| `supplement-replay-01/provenance.json` | `be908acf98a2c733a4330e1851475c32b0b08b993c3a75642ab2c335595596cc` |
| `supplement-replay-01/complete.json` | `65bb57bc265293362c8867e73008885cf32470f8d70dd20e5127196709e49950` |
| `supplement-replay-01/report.json` | `f9e41d00a7cc2949744b449b5cf5bb7f802da8a0187e1fdd0ffde27504b8852b` |
| `supplement-replay-01/row-evidence.jsonl` | `c3e1c4e5b56739dafded6d8b1b87c231c61ba33233b5e992ee54bc3ec6e2298c` |

## Claim boundary

This result attributes the revealed v5 corpus through the reviewed current packaged generator/controller route using exact old and supplemental numeric evidence. It reports agreement with the corpus's observed source boundary. The report correctly records `qualityGateEstablished=false`, `semanticCorrectnessEvaluated=false`, `unseenGeneralization=false`, `physicalAvailabilityMeasured=false`, `realInputConnection=false`, and `thresholdsFittedOnHoldout=false`.

Accordingly, the result does not establish semantic punctuation precision, behavior on unseen text, real model-service availability, asynchronous worker timing, Android `InputConnection` behavior, physical-device performance, latency, or energy quality. The 46 supplemental rows were scored only to complete the already revealed exact request universe; they were not used to change thresholds or policy.
