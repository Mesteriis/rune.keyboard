# Requested candidate width — 2026-09-03

Baseline: `7816103` (test lifecycle synchronization). Local branch remains
`feature/smart-typing-03-pr06-lexicons`; version remains 0.2.0.

## Implementation

`CandidateGenerator` accepts an immutable constructor limit from1 through7,
with the existing default7. Both packed and exhaustive selection honor it.
`CandidateLexicon.selectTop` requires that limit explicitly; every packed result
carries it. `REQUESTED_IN_GLOBAL_ORDER` certifies exactly that many accepted
representations, while `FRONTIER_EXHAUSTED` proves the shorter complete list.
The generator rejects a reader returning a different limit. Exhausted searches
retain their veto and cannot be recast as completed smaller requests.

Shared8192 states/64 verifications, comparator, original preservation, protection,
case/dedup/fallback order and cancellation remain unchanged. Fixed scratch still
reserves capacity7; reducing the request avoids work, not an asserted heap saving.
No confidence bucket or AutoReplace is enabled by this retrieval certificate.

The public calibration tool now passes the actual production constructor
argument. It no longer rewrites Kotlin source. Receipts record that argument;
the full-neighborhood verifier rejects mismatches and keeps historical receipts
usable with their historical harness. The earlier overlay outputs remain frozen.

## Correctness and local gates

50 targeted JVM tests PASS. The94 independent frozen policy cases now run at
all seven widths (658 comparisons), including case expansion, routing and dedup.
Additional checks cover exact/generic prefix agreement, wrong-width reader failure,
invalid widths and proof-size mismatch. Every cancellation checkpoint is exercised
at1/3/7 alternatives with clean subsequent reuse. The64/65 verification controls
cover all widths; a separately identified primary-language certificate can finish
before visiting its lower-prior fallback. No budget assertion was weakened.

Full JVM598/598 PASS, zero failures/errors/skips. All prescribed lint,
debug/release/profile assemblies, privacy, IME boundary, dependency and native
symbol gates plus Android test assembly PASS (277 tasks executed). Python parser
and width protocol checks PASS. Required post-commit JVM is reported separately.

Initial broadened test expected64 verifications even for a proved primary-only
prefix; the final test distinguishes that case from exhaustion. Initial combined
lint failed in Kotlin FIR analysis; a run on completed, stable sources passed
without suppressions. Three concurrent host compilations hit120s timeouts; all
three sequential exports passed with the same limit. Initial logs are retained.

Fresh6000-row calibration and773-request full-oracle exports ran at each of
2/4/8 total candidates. All three raw result/candidate/input streams are byte
identical to their frozen prior overlay experiment. No oracle violations:

| Total candidates | Complete | Incomplete | Policy |
| --- | ---: | ---: | ---: |
| 2 | 683 | 53 | 37 |
| 4 | 393 | 343 | 37 |
| 8 | 238 | 498 | 37 |

Calibration correct-candidate recall / complete correct-candidate rows per1000
original typo rows (prepared-panel repeats are not independent observations):

| Total | EN | RU | ES |
| --- | --- | --- | --- |
| 2 | 855 / 852 | 798 / 791 | 813 / 802 |
| 4 | 952 / 475 | 925 / 583 | 925 / 537 |
| 8 | 972 / 184 | 962 / 366 | 947 / 314 |

These counts are retrieval evidence only. No new model scoring, confidence fit,
holdout, precision PASS or AutoReplace count is claimed.

## Android and physical Fold

User explicitly authorized installing the exact app/test debug APKs on `phone`.
Both replacement installations succeeded without uninstall or data clearing.
The USB device was independently verified as SM-F966B, Android16/API36.
The requested-width instrumentation test passed (1/1,39.937s), exercising60
public fixture words with two warmups and five measured passes per width.
All900 numeric records are present, unique, bounded and repeatable. For every
complete larger result, the smaller result equals its exact prefix. Smaller
requests inspect no more states or terminals. No editor text is read or exported.

| Total candidates | CPU p50 / p95 / max ms | Wall p95 ms | Total CPU ms (300 observations) |
| --- | --- | ---: | ---: |
| 2 | 5.287 / 15.175 / 20.726 | 15.791 | 1879.340 |
| 4 | 11.096 / 51.638 / 69.870 | 51.968 | 4605.048 |
| 8 | 18.381 / 57.585 / 68.874 | 59.555 | 7494.921 |

Four total candidates used38.6% less aggregate CPU than eight in this fixed
search run; two used74.9% less. This debug-APK microbenchmark excludes load time,
model inference and actual editor typing. It is not a confidence interval,
latency budget, battery qualification or complete cover/inner Fold acceptance.
The release default width still requires final pipeline calibration.

API26 requested-width test1/1 PASS (24.115s); API37 test1/1 PASS (21.469s).
Each has all900 bounded numeric observations and the same prefix checks.
Emulators ran sequentially after host export/build work completed. APK identities
and all three device logs/reports are recorded in the accompanying evidence.
Complete IME lifecycle/editor matrix, combined model quality, physical energy,
contextual punctuation and release/model publication remain open. No push,
remote PR, publication or version bump occurred.

Evidence: `tools/lexicon/smart-typing-0.3/top-seven/results/2026-09-03-production-widths/`.
