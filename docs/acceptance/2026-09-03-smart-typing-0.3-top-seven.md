# Smart Typing 0.3 — exact top-seven selection, 2026-09-03

Baseline: `991d7c56aa503fec023ce6b434ddd9737940d0ed`.

The production packed generator now stops when it proves the exact global seven
alternatives, instead of always enumerating the complete radius neighborhood.
Protection, routed membership, case policy and comparator remain shared with the
existing generator. The exhaustive scan API retains its original meaning.
The ready bridge uses the new selector on the existing serial candidate worker;
no editor reads, file loading, model requests or persistence are added to search.

The global covering frontier and strict pending-order certificate preserve both
routes, display dedup before fallback quota, and lower-priority display shadows.
Partially expanded regions cannot certify. The same 8192-state/64-verification
budget covers exact lookup and search. Exhaustion retains verified suggestions
and the AutoReplace veto. Cancellation overrides exhaustion; all temporary
query/path/DP/heap/handle state clears in finally. Detailed proof and origins:
`tools/lexicon/smart-typing-0.3/top-seven/README.md`.

Correctness evidence:

- Independent graph controls: 3209 distance pairs and 8218 prefix cuts; 94 frozen
  full-policy cases. Their generator reproduces all TSV bytes exactly.
- Existing independent graph tests now cover exhaustive and packed generators,
  including 468 finite route/order/case comparisons and radius-two controls.
- Exact state/verification boundaries, strict ties, every cancellation checkpoint,
  reuse and missing-handle behavior pass.
- Fresh full-neighborhood oracle comparison: **773/773 PASS**, 238 complete,
  498 incomplete with veto, 37 protected/valid-word cases. Two original controls
  are explicitly excluded from this UTF-8 harness: unpaired surrogate ID771 and
  cancellation ID774; both behaviors are separately covered in JVM. No 775-case
  fresh execution claim is made.
- Final JVM: **593/593 PASS**, zero failures/errors/skips. Full prescribed local
  gates plus test APK assembly PASS (267 tasks, 42 executed). Four tooling tests
  pass. Initial root test-filter failure and the superseded exhaustion fixture
  failure are retained, with no reduced budget or relaxed correctness assertion.

The initial oracle report listed exclusion IDs and reasons in separate arrays
with mismatched order. The corrected report binds each reason to its actual ID;
the initial report is retained. Final-source reruns produced identical calibration
candidate bytes and identical 773 oracle raw records. No algorithm, input,
expected output or threshold was changed between those runs.

Calibration-only results on 1000 typo rows per language:

| Measure | EN before → after | RU before → after | ES before → after |
| --- | ---: | ---: | ---: |
| Correct word present | 894 → 972 | 666 → 962 | 824 → 947 |
| Correct word present with complete search | 22 → 184 | 126 → 366 | 90 → 314 |
| All complete searches, including non-typos | 44 → 206 | 137 → 377 | 98 → 322 |
| Individual recall gains / losses | 82 / 4 | 301 / 5 | 128 / 5 |

All 279 previously complete searches preserve their exact alternatives. There
are 626 additional complete searches. The 14 individual recall losses all occur
in still-incomplete searches and keep their veto; their public IDs are recorded.
Corpus repeats and row weighting are unchanged. These are retrieval statistics,
not precision/AutoReplace counts or a final quality holdout. English still lacks
sufficient complete correct candidates even on calibration. No model or holdout
was executed, and the earlier failed model-quality report remains unchanged.

Scoped Android runs: **API26 30/30 PASS** (213.899 s), **API37 30/30 PASS**
(238.677 s), one completed run each. They include actual packaged assets, a
numeric production/exhaustive comparison, real IME composing/candidate/Undo
regressions through Binder InputConnection and persistent key-view checks.
Installed build inputs precede two final source-comment clarifications only;
their exact diff and source/APK hashes are archived. Final JVM/gates cover the
final comments as well. APK hashes identify build inputs, not device readback.

The fixed performance fixture takes the first 20 existing public development
queries per language. Both algorithms use the same validated mappings and policy,
with two unmeasured passes and five measured passes in alternating order.
Each strategy has 300 observations per emulator. p50/p95/max and raw numeric
records are archived; p95 uses nearest rank. No query text is logged.

| Emulator / strategy | CPU p50 / p95 / max, ms | Wall p50 / p95 / max, ms |
| --- | --- | --- |
| API26 exhaustive | 4.450 / 6.191 / 79.158 | 4.487 / 6.277 / 84.011 |
| API26 top-seven | 6.150 / 14.566 / 33.257 | 6.263 / 14.837 / 38.504 |
| API37 exhaustive | 6.130 / 7.855 / 13.788 | 6.315 / 8.239 / 14.222 |
| API37 top-seven | 12.221 / 39.394 / 76.181 | 12.771 / 40.707 / 106.751 |

Complete requests increase from 18 to 38 of these 60 development inputs, but
CPU cost rises. The additional fixed primitive scratch is 282524 bytes per used
engine, excluding object headers, candidate objects, existing generator/readers
and mappings. This is not measured allocation/RSS. No device energy benefit or
acceptable Fold latency is claimed. Before release, reduce unresolved equal-cost
region work and measure the resulting pipeline on physical Fold. A validated
frequency-derived subtree lower bound is a candidate next step; it must preserve
the proof, separate frequency licensing and unchanged caps.

Evidence: `tools/lexicon/smart-typing-0.3/top-seven/results/2026-09-03/`.
API26/API37 functional gates for this slice PASS. Physical Fold/performance,
final spelling quality, contextual punctuation and model publication remain
BLOCKED/unqualified. AutoReplace remains off; version remains 0.2.0. No push,
remote PR, model change or publication was performed.
