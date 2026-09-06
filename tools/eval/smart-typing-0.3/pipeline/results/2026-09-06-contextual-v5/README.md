# Contextual punctuation v5 — 2026-09-06

The current production seven-candidate rule was evaluated on a new source-observation
pool. Corpus, extraction implementation, backend and policy were bound in a root
protocol receipt **before any real v5 scores**. All 600 calibration rows preceded
configuration freeze; the 600 holdout rows followed that freeze. No thresholds
were fitted or changed, failed rows retried, or post-score exclusions introduced.

| Holdout | EN | RU | ES |
| --- | ---: | ---: | ---: |
| Rows | 200 | 200 | 200 |
| Suggestions | 38 (19%) | 37 (18.5%) | 27 (13.5%) |
| Abstentions | 162 | 163 | 173 |
| Source-boundary matches, all rows | 87 (43.5%) | 86 (43%) | 76 (38%) |
| Suggested boundary agrees with source | 37/38 | 36/37 | 26/27 |
| Insertions at observed spaces | 0/50 | 0/50 | 0/50 |
| Production-excluded rows | 28 | 32 | 23 |
| Runtime errors / missing responses | 0 / 0 | 0 / 0 | 0 / 0 |

`report/report.json` contains every required numerator, denominator and Wilson95%
row-descriptive interval, by language and observed boundary. Excluded rows remain
in all corpus denominators. Calibration scored500 requests plus100 exclusions;
holdout scored517 plus83 exclusions. All1017 eligible responses are preserved.
`row-decisions.jsonl.gz` records all1200 decisions, including exclusions,
abstentions and the three holdout suggested disagreements, joined by ID to the
exact public source rows and attribution. No automatic punctuation was evaluated.

Observed Wikipedia boundaries are **not unique semantic correctness labels**.
Agreement among emitted suggestions is not semantic precision or an automatic-
replacement qualification. Balanced space/comma/colon/period quotas do not model
chat prevalence; question/exclamation/semicolon lack source strata. Source-space
abstention counts as agreement. Related articles and unknown base-model pretraining
may overlap. This corpus does not qualify spelling. `qualityGateEstablished` and
`semanticCorrectnessEvaluated` remain false.

Exact identities:

- Current corpus: run-c/run-d manifest
  `dbce48cfc68d36a52a1f7c60d96d612dc568012d409dd1015e5685c386461660`.
- Pre-score protocol file: `3213bb0f091652064bcce0ddfc299286610401237c4cb80f8f8647331cfe32e5`.
- Backend-only config file: `ab54898317549304d67ffa4381ca7c02992e5e10fe316ac535be098653bdb195`.
- Frozen calibration config identity:
  `57fcb49a576de30d6447a48906f81986f25a9a0e527d09a5b091ed64fc47b037`.
- Exact396704416-byte Rune GGUF:
  `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
- Release host runner:
  `bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553`.
- Current Kotlin/Python policy parity:79/79; receipt
  `713dae9657f42bdc001b7cc3760cad35b98676acfa87194004699f6cdaa6d178`.

The backend-only config does not modify or reuse the historical spelling threshold
config. Its full provenance remains bound by the pre-score protocol; score receipts
also bind exact runner/model/protocol. All old source-loader, consumer-downgrade and
numeric-receipt failures and red/green logs remain included. Current adapter tests
pass35/35, corpus tests20/20. Historical run-a/run-b manifests and parity receipts
are retained; current strict loaders reject their old implementation identities.
There is no compatibility exception.

`archive.json` records original build locations, decoded/compressed digests and
sizes. Original receipt paths are intentionally unchanged. Recreate their recorded
build-relative layout to rerun strict validation. Rebuildable JARs are omitted
with hashes; weights and source parquet shards are not bundled. Generator sources,
pinned source/exclusion locks, license/attribution details and reproduction commands
are in `qualification-v5-contextual/`. The Python3.11.14/pyarrow and JDK17 toolchain
identities and exact compile/run commands are retained in the receipts.
