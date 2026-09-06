# Bounded equal-key frontier scheduling probe

2026-09-06, production source `6f7c35eda1ee11a9f0a510eadadd0fbf2912356c`. This is a model-free calibration diagnostic, not a product change or automatic qualification. Immutable final review is unchanged.

The single build-only variant changes the final FIFO tie in `PackedTopSeven.frontierLess` to prefer greater depth, then original allocation ID, only after the existing weighted-lower-bound, route-prior and language keys all tie. It preserves the covering frontier, certificate checks, terminal and candidate comparators, all buffers and cancellation code. No query-specific exceptions or extra candidate sources were introduced.

## Measured outcome

| Named input | Production copy | Deeper equal-key variant |
| --- | --- | --- |
| автокрекция | STATES_EXHAUSTED; 8192 states, 0 terminals, no alternatives | STATES_EXHAUSTED; 8192 states, 1 terminal, автокоррекция returned |
| correcion | STATES_EXHAUSTED; 8192 states, 6 terminals; correction / correcto / correctos | STATES_EXHAUSTED; 8192 states, 7 terminals; correction / coercion / correcto; corrección still missing |
| teh | COMPLETE; 1639 states, 21 terminals; ten / eh / tea | Exact same output and counts; the still missing |

The Russian retrieval gain justified the authorized wider calibration run. All 6000 calibration rows were measured with both copies. The input loader filters `split == calibration` before inspecting outcomes; the generator receives only row index, language and typed token. No holdout evaluation or holdout outcomes were read.

| Metric | Production copy | Variant |
| --- | ---: | ---: |
| COMPLETE | 1714 | 1714 |
| STATES_EXHAUSTED | 1136 | 1136 |
| VERIFIED_EXHAUSTED | 119 | 119 |
| VALID_WORD | 2251 | 2251 |
| PROTECTED | 780 | 780 |
| Expected non-original target in alternatives (3000 rows) | 2802 (93.4%) | 2811 (93.7%) |
| Total inspected states | 16,340,636 | 16,244,453 |
| Total verified terminals | 43,010 | 43,956 |

There were zero newly COMPLETE or newly incomplete rows. All 1714 previously COMPLETE rows retain the exact original certified global requested top-three output, including every exported candidate identity, order and feature field. This comparison uses the unchanged production certificate as its reference; it is not an independent exhaustive oracle rerun. All 237 changed candidate sets belong to incomplete retrieval. The caps remain 8192 states, 64 verified terminals and three alternatives on every row.

Target recall gained 10 rows and lost one. The loss is `ru-calibration-typo-05-2-5`, `шакаф` → `шкаф`: both versions exhaust 64 terminals, but depth scheduling reaches that cap after 493 states rather than 1599 and drops шкаф from the returned set. Original alternatives are шкаф / шакал / лакай; variant alternatives are шакал / лакай / лакая. Thus this is a measurable tradeoff, not uniformly improved retrieval. All changed incomplete outputs retain the automatic-replacement veto.

## Scope and reproducibility

Artifacts are under `build/smart-typing-0.3/retrieval-probe-20260906/`:

- `probe.py`, `wider.py`, `commands.json`: retained diagnostic implementation and exact compiler/runtime commands.
- `inputs-manifest.json`, `baseline-sources.json`, `deeper-sources.json`, `artifact-hashes.json`: SHA-256 identities for original/copied source closure, toolchain, unchanged lexicon assets, filtered calibration input, binaries, outputs and logs.
- `variant.patch`: the exact one-line scheduling change. Both full source copies and generator jars are retained.
- `baseline-named.stdout`, `deeper-named.stdout`, `baseline-calibration.stdout`, `deeper-calibration.stdout`: raw generator output with candidates and state/terminal counts.
- `comparison.jsonl`, `summary.json`: row-level before/after output and aggregate counts, including gained/lost target IDs.

Used the existing `CandidateExport.kt` host packed-lexicon observer with an explicit 18-file source closure, cached hash-verified Kotlin 2.2.10 compiler jars and Homebrew Java 17. Packed lexicon bytes are validated against `FrozenPackedLexicons` and were hash-checked unchanged after execution. Width was explicitly three. The existing exporter uses the default empty canonical-case lexicon; this probe isolates spelling candidate retrieval, and does not construct typing sessions, canonical-case product decisions, model requests or confidence decisions. Generator input does not contain target labels.

Initial discovery commands failed for two guessed tool paths, unavailable system `java_home`, and an absent Android Studio Java path; these are recorded in `inputs-manifest.json`. The located Java17 compiler and both named/full generator runs completed with exit zero. Compiler/runtime stdout/stderr are retained. No Gradle, devices, adb, native scoring, model scoring, network or additional agents were used. Product source, tools, tests, assets, budgets, thresholds and policies were not edited; original source/asset/toolchain hashes were rechecked after execution.

## Smallest justified next step

Keep this one-line variant as diagnostic evidence, without promoting it as a fix. It improves a small amount of partial suggestion recall and retrieves the Russian named target, but does not complete either exhausted named search, loses one calibration target, and leaves the Spanish and transposition demonstrations unmet. Any next retrieval change needs a separately scoped design and frozen candidate-set evaluation; this measurement does not justify automatic qualification or a threshold/budget change. The existing final review and unresolved named acceptance status remain in force.
