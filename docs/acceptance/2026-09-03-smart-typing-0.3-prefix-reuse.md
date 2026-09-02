# Smart Typing 0.3 — prefix DP reuse, 2026-09-03

Baseline: `3459033462f90eb6fb4048e9e96f92bbcf501a52`. Branch remains
`feature/smart-typing-03-pr06-lexicons`. Version remains 0.2.0.

## Change and correctness

`PackedTopSeven` previously replayed the entire scalar prefix from root for
every popped frontier region. `PrefixDistance` now retains the common prefix's
recurrence rows and full last-occurrence history within one query/language.
Changed suffixes are recomputed, language changes force depth zero, and the
entire cache is cleared on cancellation/completion. Extra primitive scratch:
4352 bytes per engine, total 286876 bytes. No new dictionary arrays/assets,
frequency data, persistence, frontier ordering, bounds or budget changes.

Regression coverage adds branch/sibling/query/language/Unicode/repeated-symbol
reuse and deterministic row-work checks. Existing independent edit-graph,
full-policy, cap and cancellation tests remain. Fresh full JVM **596/596 PASS**,
zero failures/errors/skips. Six Python comparison/qualification tests PASS.
`testDebugUnitTest --rerun-tasks`, lint, debug/release/profile assemblies,
privacyGateRelease/Profile, imeIntelligenceBoundary, forbiddenRuntimeDependencies,
nativeSymbolGate and Android-test assembly PASS (277 tasks, all executed).

The 6000 calibration inputs, full raw records and candidates JSONL are each
byte-identical to the previous generator export. The 773-request full oracle
passes with exactly 238 complete / 498 incomplete / 37 policy results, zero
violations. Cancellation and malformed UTF-16 controls remain JVM-only. This
optimization therefore does not improve coverage or enable AutoReplace.

## Android comparison

The previously installed app/test APKs were pulled from each emulator and their
hashes matched the archived top-seven integration APK hashes. Both APIs then ran
sequentially: reinstall baseline, execute search and asset tests; install current
APK, repeat the same two tests. No parallel Gradle build or host evaluator ran
during this final comparison. Four completed runs, **2/2 tests PASS each**.
This is scoped reader/search evidence, not a replacement for the full IME matrix.

Each run uses the same 60 public development queries, two warmups and five
measured rounds for each of two strategies. All 600 per-run numeric records are
present, unique and bounded. Before/after states, verifications, completion and
alternative counts match exactly for every request/strategy/round. Exhaustive
scan remains a timing control. All 28 APK lexicon/provenance assets are identical.

CPU milliseconds for top-seven (300 measured observations per variant):

| API | Variant | p50 | p95 | max | Total |
| --- | --- | ---: | ---: | ---: | ---: |
| 26 | before | 5.866 | 14.401 | 16.401 | 2149.626 |
| 26 | after | 6.035 | 13.321 | 15.720 | 2030.909 |
| 37 | before | 12.271 | 39.205 | 52.093 | 5155.985 |
| 37 | after | 10.694 | 31.586 | 36.134 | 4283.362 |

Measured CPU totals decreased 5.5% / 16.9%; p95 decreased 7.5% / 19.4%.
API26 median increased 2.9%. Exhaustive-control totals changed +1.0% / +0.1%.
Wall p95 changed API26 14.444→13.465 ms, API37 40.207→32.913 ms. These are
emulator observations, not confidence bounds, final latency budgets or battery
measurements. Keeping the exact semantics and small fixed scratch is justified
by the measured reduction in total CPU and heavier queries, not by a universal
per-query speedup claim.

Asset load/PSS/Java-heap observations are retained in the raw logs. A single
load per language is not a distribution or an energy acceptance result. In
particular, API26 RU validation still takes about 14 seconds of CPU; this separate
load cost remains a hardening concern. APK-size differences between builds are
recorded, but not attributed to this scratch-only optimization.

## Rejected experiment and remaining gates

A preceding subtree-frequency-bound trial passed correctness and gained 85
complete calibration rows, but added 7.6 MB dictionary metadata with no observed
API26 CPU improvement. It was removed; its exact patch, failed fixture evidence,
successful gates, calibration/oracle output and measurements are preserved in
`tools/lexicon/smart-typing-0.3/top-seven/results/2026-09-03-rank-bound-experiment/`.

Current evidence is in
`tools/lexicon/smart-typing-0.3/top-seven/results/2026-09-03-prefix-reuse/`.
Reproduce calibration and oracle with the commands in the parent README, then
compare before/after Android logs using `compare_prefix_reuse.py` with explicit
`--measurements`, `--baseline-export`, `--current-export`, and `--output` paths.
The comparison rejects missing/failed runs or changed search outcomes.

**API26/API37 scoped checks: PASS. Physical Fold: BLOCKED (not in current USB
ADB inventory). Model/AutoReplace quality, final latency/energy, full IME/device
matrix and model publication: NOT QUALIFIED.** No model or holdout ran in this
slice. EN complete correct-candidate calibration coverage remains 184/1000;
the full calibrated pipeline, autocorrection/Undo, contextual punctuation and
release work remain open. No push, remote PR or publication was performed.
