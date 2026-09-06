# Short-word frequency-policy probe

2026-09-06; baseline production source `6f7c35eda1ee11a9f0a510eadadd0fbf2912356c`. Build-only calibration experiment. Prior depth-scheduling evidence and immutable final review are unchanged.

## Policy and scope

For folded scalar lengths below five, the variant bypasses `selectTop`, executes the existing complete UNIT-radius-one `scan` path with unchanged shared controls, then sorts by descending language prior, ascending frequency rank and the existing deterministic comparator. Long queries retain the original path. Protection, valid-word checks, casing, deduplication, fallback quota, cancellation, completion status and 8192-state/64-terminal/three-output limits remain unchanged. No distance weights, confidence thresholds, lexicon assets, product source, tests or policies were edited.

The baseline is the exact frozen production generator and calibration output from the prior probe. Original source, toolchain and asset hashes and filtered calibration input identity were verified before reuse. The existing host `CandidateExport.kt` remains the observer, with its default empty canonical-case lexicon: this measures spelling retrieval, not full typing/model or canonical-case decisions. Input remains only index, language and typed token. Only the previously filtered 6000 calibration rows were consumed; no holdout reads, model scoring, Gradle, devices, network or additional agents.

## Initial controls

`teh` now returns COMPLETE `the / ten / eh`, versus COMPLETE `ten / eh / tea`. Counts rise from 1639 states/21 terminals to 2564/22. This retrieves the target through a general policy, not a transposition exception.

Independent Russian `горп` exposes a loss immediately: original `горе / гора / гори` becomes `горы / горе / гору`; both COMPLETE. Spanish `avis` is already a dictionary word and remains VALID_WORD despite its authored intended target aviso. Valid controls vase, гора and muro retain exact outputs and counts; protected NASA retains ALL_CAPS and zero work. The successful teh retrieval triggered the authorized full calibration run.

## Full calibration result

| Expected non-original target recall | Baseline | Variant | Gains / losses |
| --- | ---: | ---: | ---: |
| All 3000 target rows | 2802 (93.4%) | 2836 (94.53%) | 39 / 5 |
| Russian, 1000 | 925 | 941 | 20 / 4 |
| English, 1000 | 952 | 959 | 7 / 0 |
| Spanish, 1000 | 925 | 936 | 12 / 1 |
| Short target rows, 205 | 126 | 160 | 39 / 5 |
| Long target rows, 2795 | 2676 | 2676 | 0 / 0 |

All 6000 completion statuses are identical: 1714 COMPLETE, 1136 STATES_EXHAUSTED, 119 VERIFIED_EXHAUSTED, 2251 VALID_WORD and 780 PROTECTED. There are zero newly COMPLETE or newly incomplete rows. Every long-query output field and state/terminal count matches the original, including all 1525 long COMPLETE rows. Candidate sets change on 115 rows. Limits remain satisfied on every row. Total inspected states increase 16,340,636 → 16,443,601; verified terminals increase 43,010 → 43,605. Maximum states/terminals remain 8192/64.

All five target losses are explicit policy tradeoffs:

| Input | Lost target | Before | After |
| --- | --- | --- | --- |
| горп | гора | горе / гора / гори | горы / горе / гору |
| ьему | тему | тему / ему / нему | ему / нему / чему |
| сыо | сыр | сыр / сыт / со | со / сын / сто |
| Чее | Чек | Чек / Чае / Чем | Чем / Ее / Нее |
| oan | pan | pan / kan / own | tan / han / van |

The Russian автокрекция and Spanish correcion named queries are long and therefore exactly unchanged from production; this experiment does not combine the prior depth variant.

## Independent short-word oracle

All 189 short COMPLETE rows match an independent exhaustive UNIT-radius-one neighborhood oracle, with zero mismatches. The diagnostic enumerates every insertion, deletion, substitution and adjacent swap using all characters present in each packaged trie, checks membership against all packaged terminals of length at most five, and verifies accepted edits with the existing independent `top-seven/reference.py` distance implementation. It applies the new prior/frequency order, independent routing/casing and unchanged deduplication/fallback quota/width. The comparison checks ordered display, canonical key, terminal key and language. Oracle enumeration is a separate unbounded diagnostic, not a change to runtime budgets or a claim about incomplete searches.

## Retained evidence and interpretation

Everything is retained under `build/smart-typing-0.3/retrieval-probe-20260906/short-frequency-01/`: `probe.py`, `wider.py`, `oracle.py`, exact `variant.patch`, source copies, generator jar, `commands.json`, `identities.json`, raw compiler/runtime stdout and stderr, named inputs, `comparison.jsonl`, `summary.json`, `oracle-comparison.jsonl`, `oracle-summary.json`, and `artifact-hashes.json`. No compiler/runtime/oracle failure occurred. Original source/assets/toolchain and baseline input/output hashes were rechecked after execution.

This is a promising generic retrieval-policy hypothesis with a measured net recall gain and five concrete losses. It is not qualified for automatic correction and does not inherit current candidate-set qualification. The smallest justified next step is to retain this policy and its losses for a separately scoped review and fresh evaluation before any promotion. It does not complete the remaining long-word named acceptance gaps or establish model precision/false-change gates.
