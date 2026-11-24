# Q6: disjoint selector admission and separate text safety

The registry-checked refinement and word-ranking selectors now resolve every
candidate against the pinned dictionary before admitting it. The first accepted
partition reserves all dictionary lemmas, source article, source window and
whole selector segment. A candidate sharing any reservation with another
partition, or lacking a dictionary analysis, is skipped without reserving its
other identities. The final independent partition and dictionary checks still
run. Historical reproduction does not use this admission logic.

With initial and final registry barriers and the separate text barrier
intercepted solely for this diagnostic, two independent executions on the
pinned public Parquet produced identical JSONL outputs, met the original row
quotas and passed the actual final disjointness and dictionary checks:

| Selector | Accepted | Cross-partition refusals | Unresolved refusals | Identical JSONL files |
| --- | ---: | ---: | ---: | ---: |
| Refinement | 7,500 | 12,788 | 3 | 6 |
| Word ranking | 9,000 | 45,154 | 11 | 7 |

These numbers describe selected word rows, not unbiased estimates or model
quality. The intercept explicitly prevents claiming registry clearance. Actual
default execution still rejects the incomplete registries before input access.
The two collectors and the epoch collector also emit separate training-text
fragments. Their row-level identifiers do not prove those fragments independent,
so the real registry-checked path now refuses with
`SELECTOR_TEXT_CORPUS_UNCHECKED` before output until text-level checks are
implemented. A real diagnostic run with that barrier intact confirmed no output
for all three. The retrieval selector emits no separate text corpus and reached
the intercepted final gate; its unavailable prior-observations manifest was
stubbed only in this diagnostic.

Historical refinement and word runs reproduced all 6 and 7 JSONL files byte
for byte, respectively. Focused tests cover atomic reservation, multiple
analyses, unresolved words, conflicting partitions and unchecked-text refusal.
The full stdlib inventory passed 771 tests across 153 modules with no skips;
provenance-path verification and `git diff --check` also passed. The test runner
receipt is in `build/review-q6-disjoint-admission-20261028/`.
Logs and independent row checks are in `build/q6-admission-{final,diag1,diag2,verify}.log`.
Q6 remains open for text-level coverage, complete historical lineage and
independent qualification; no generated test output is promoted.
