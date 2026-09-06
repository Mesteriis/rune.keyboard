# Contextual v5 real-run chain review — 2026-09-06

Verdict: **PASS — no material gap found in the reviewed fixed-protocol artifact chain before archive/commit**. The source corpus, exact production export, both complete score caches, calibration freeze, backend identity and final report are mutually consistent. This is an independent read-only admission and saved-response recomputation; it is not a rerun of model scoring or a semantic quality qualification.

Reviewed directory: `build/smart-typing-0.3/contextual-v5-20260906/`. No production/tooling/corpus source or historical receipt was changed. No build, device, model invocation, threshold fitting or commit occurred. Only this report was written.

## Admission and source/backend binding

I ran the current `contextual_quality.load_export` using the recorded Python 3.11.14 interpreter with `PYTHONDONTWRITEBYTECODE=1` and the recorded pyarrow site-packages path. This executed complete `corpus_contract.load_corpus` admission, including source/exclusion/toolchain identities and selector replay, then verified corpus-row digest, exact Kotlin input bytes and parsed actual output against all 1,200 stored rows. It passed. Every exported row retained v5 observed-boundary semantics and had either zero or seven variants; no legacy ambiguity/expected-candidate fields appeared.

The consumer source remains `ab02e8457abe3cfdf711f67b52b13be33fde7f7693270bf4dc4203f5ba49c713`; the strict loader remains `100bafb1fa324aa4be500c38bd49f7c54c2ca211ca0149be5bd6f30d52e1371e`. Protocol/source/exclusion/recipe hashes, corpus files and manifest (`dbce48cfc68d36a52a1f7c60d96d612dc568012d409dd1015e5685c386461660`) all match the frozen links. Actual export source and binary/input/output hashes pass the current consumer's checks. The current 79-case Kotlin/Python policy verification was admitted through `load_frozen`; no compiler was rerun.

I verified protocol and backend canonical self-digests, the protocol's exact backend-config file hash, freeze-script hash, every protocol source/corpus file hash and every backend evidence-file hash. Actual runner and model bytes were hashed read-only and match the backend config; model size is 396,704,416 bytes. Both score splits use exactly `rune-score-jsonl-v1`, runner `bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553`, model `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`. No compatibility substitution for historical runner `f2f8…` is used. Backend scope remains contextual-only, contains no thresholds, and explicitly denies a new quality qualification from historical spelling compatibility.

The backend config's complete provenance is independently bound by `protocol.json`, addressing the helper's narrower execution-identity propagation noted in the adapter review. The protocol and pipeline artifacts agree on the same policy/consumer/loader/corpus/backend identities; their agreement was explicitly checked rather than assumed from directory placement.

## Ordered freeze and score chain

Protocol file SHA-256 is `3213bb0f091652064bcce0ddfc299286610401237c4cb80f8f8647331cfe32e5`; its internal `freezeSha256` is `b4867e194a1c360a3348c6a62c3c63aa795fbe21f15deac65428534dc9e7c586`. The retained freeze script requires a fresh protocol directory and absence of any `scores.jsonl` beneath this v5 run directory before writing the protocol. It binds the reviewed backend, source and corpus before scoring.

The receipts and retained logs follow protocol freeze → exact export → complete calibration → config freeze → complete holdout → report. Artifact modification times corroborate that local order: protocol 10:02:19 UTC; export 10:02:55; calibration receipt 10:03:55 and complete 10:06:04; frozen config 10:07:12; holdout receipt 10:08:57 and complete 10:11:05; report 10:13:10. These are local execution evidence, not externally attested timestamps or proof about unknown prior model exposure.

`load_scores` validates every cached response against the exact split request IDs and ordered continuation payloads, header request digest, protocol/backend identity, run-input/completion equality and score-file digest. I checked calibration has no frozen-config link, and the frozen config hashes exactly its calibration complete receipt and score file. Config internal digest is `57fcb49a576de30d6447a48906f81986f25a9a0e527d09a5b091ed64fc47b037` (distinct from its file SHA in the table below). Holdout run-input/completion reference that exact config digest and export receipt. Final provenance references the same config, verification, export and holdout scores, and its report-file digest matches.

Every policy object remains the unchanged total-log-probability rule: winner advantage strictly `>0.5` over Original and `>=4.0` over the strongest other punctuation, ascending-ID ties, token counts 1–255. No threshold search or post-holdout change is declared or present in the linked source. Frozen calibration metrics and the entire final holdout language/stratum metric structures were recomputed from saved responses with the current admitted evaluator and compare exactly to the stored values, including Wilson intervals.

## Complete denominators and observed results

| Split | Corpus rows | Submitted / saved responses | Retained production exclusions | Runtime errors | Missing responses | Policy-invalid token-count rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibration | 600 | 500 / 500 | 100 | 0 | 0 | 0 |
| Holdout | 600 | 517 / 517 | 83 | 0 | 0 | 0 |

Every language/split has 200 rows and every observed-boundary stratum has 50. Excluded rows receive no request/score, abstain, and remain in all applicable denominators. No error or missing row was removed; both caches contain none, and all scored rows have policy-admissible token counts. All seven candidate-decision counts are exposed. Automatic replacements are zero throughout.

| Split / language | Source-boundary matches / 200 | Suggestions / 200 | Abstentions / 200 | Retained exclusions / 200 | Insertions / observed spaces |
| --- | ---: | ---: | ---: | ---: | ---: |
| Calibration EN | 84 / 200 | 35 / 200 | 165 / 200 | 35 / 200 | 0 / 50 |
| Calibration RU | 89 / 200 | 42 / 200 | 158 / 200 | 42 / 200 | 0 / 50 |
| Calibration ES | 80 / 200 | 33 / 200 | 167 / 200 | 23 / 200 | 0 / 50 |
| Holdout EN | 87 / 200 | 38 / 200 | 162 / 200 | 28 / 200 | 0 / 50 |
| Holdout RU | 86 / 200 | 37 / 200 | 163 / 200 | 32 / 200 | 0 / 50 |
| Holdout ES | 76 / 200 | 27 / 200 | 173 / 200 | 23 / 200 | 0 / 50 |

Holdout source-boundary agreement values and stored Wilson 95% row-descriptive intervals are EN `0.435 [0.36815725502699076, 0.504292637402054]`, RU `0.43 [0.36334322333434416, 0.4992951223584731]`, ES `0.38 [0.31559005848673627, 0.44893281984380773]`. Each 0/50 insertion rate retains the interval `[6.938893903907228e-18, 0.07134759913335872]`; the tiny lower endpoint is the existing floating-point Wilson result, not a changed count or rounding rule. Zero observed insertions is not a population-zero claim.

Each language's 50 Original decisions at source spaces contributes 50 source agreements, including excluded source-space rows. Remaining suggestions disagree with the source on one row per language; these outcomes remain in the decision counts. They are not converted into a semantic error/precision claim. Semicolon, question and exclamation decision counts are zero in this run but remain exposed despite having no source strata.

Config/report/provenance retain `metricSemantics: observed-source-boundary-diagnostic`, `qualityGateEstablished:false`, `semanticCorrectnessEvaluated:false`, zero automatic replacements, and no thresholds fitted on holdout. The corpus's balanced source strata, unknown pretraining overlap and related-article dependence still limit interpretation. No spelling, automatic punctuation, real-editor, latency or device qualification follows from this result.

## Archive handoff and exact file identities

Archive the protocol and backend config together with their retained script, current parity receipt/artifacts, corpus/export provenance, both full response caches and receipts, frozen config, report/provenance and execution logs. Preserve the original receipts and build-relative locations; archive mapping/reproduction instructions should explain how to restore those paths for strict read-only admission, rather than rewriting identities in historical JSON. This is preservation of the reviewed chain, not additional scoring work.

All paths below are relative to the reviewed v5 run directory. SHA-256 file hashes:

| File | SHA-256 |
| --- | --- |
| `protocol-freeze/protocol.json` | `3213bb0f091652064bcce0ddfc299286610401237c4cb80f8f8647331cfe32e5` |
| `protocol-freeze/backend-config.json` | `ab54898317549304d67ffa4381ca7c02992e5e10fe316ac535be098653bdb195` |
| `production-export/provenance.json` | `0e151de5f3c280fbedca0c2d00c32eddf5e07305b65410c4368d46b5008e7bb3` |
| `production-export/rows.jsonl` | `62d353dd80c4541290bd4a21308053a973761ec7928580fa1ee364469c074d65` |
| `calibration/run-input.json` | `ca20b46956892eb2e421175333c9834e6ca441f3de48c7aadc6c5fd3e52a5b40` |
| `calibration/complete.json` | `793da2a25f019386551582182a8d307b5577a769e54a1b56442e0968fe7dc7f7` |
| `calibration/scores.jsonl` | `7820440ccaf1ec9be1f7e07253454119d891eea1bfbfd6b5aaff986e3d63c554` |
| `frozen-config/config.json` | `8a7b3692b5a186dcd834e92c12ab1803dc2b6ff179b650357b1fa715d4999ed4` |
| `holdout/run-input.json` | `a5c294636b7024fb796a77ed7a16d1f4b8ffa81c115767e91cbdb4b6276b8e81` |
| `holdout/complete.json` | `953e16fd77e18474a0427ff00fecb94dead83557e00c0d066f95590b3384ca6e` |
| `holdout/scores.jsonl` | `63ae6e1eea4be0657f0b29100157c9ed1e1ed7c6cfc94dc9721b9ca422294bad` |
| `report/provenance.json` | `0b28f953b299f22d60866da4b48cd6d3673aa5996ea21111703d72c0789d0c04` |
| `report/report.json` | `bfafd4404454b4579d7e5ded15695a9d0bdce2a6ef1526335c1886e6518d383c` |
| `adapter-policy-parity-downgrade-fix/verification.json` | `713dae9657f42bdc001b7cc3760cad35b98676acfa87194004699f6cdaa6d178` |

The listed file bytes were rechecked unchanged at report creation. Historical policy/variant receipts and previous revealed spelling results were neither relabeled nor replaced.
