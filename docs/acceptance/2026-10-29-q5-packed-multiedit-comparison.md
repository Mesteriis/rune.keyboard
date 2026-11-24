# Q5: packed rare-word candidate on disclosed multi-operation inputs

The seven-word packed candidate from the earlier post-hoc colloquial experiment was replayed against the verified 1,800-row historical word-ranking test partition. The isolated observer used the actual candidate bytes and changed only the asset identity constants; the original qualification gates remained unchanged. The candidate has a different rare-asset fingerprint and the six earlier qualification checks reject it. These observations therefore describe an unqualified diagnostic build, not an authorized or independently qualified correction policy.

| Synthetic operations | Rows | Baseline exact targets | Candidate exact targets | Lost exact matches | New exact matches |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0: unverified source controls | 300 | 300 | 300 | 0 | 0 |
| 1 | 600 | 492 | 298 | 195 | 1 |
| 2 | 600 | 247 | 0 | 247 | 0 |
| 3 | 300 | 34 | 0 | 34 | 0 |

Across the 1,500 synthetic typo rows, 476 previously exact synthetic targets were lost and one new target was obtained. Exact matching is assessed against the actual pre-boundary text; baseline and candidate pre-boundary text matched on all rows. These are disclosed synthetic cases, not population accuracy estimates. The earlier screen found that the changed asset invalidates six source qualification fingerprints; it is consistent with the substantial reduction in correction, but this aggregate comparison does not attribute each changed row to a specific gate. Requalification or a different protection design would be needed before drawing a conclusion about a viable new dictionary policy. No production asset or policy was changed.

The source archive and both replay receipts and observations are hash-bound in the [initial comparison](2026-10-29-q5-packed-multiedit-comparison.json). The candidate replay ran once; the comparison itself ran twice with byte-identical results. Its first pass found three output contexts absent from the permanent exclusions. A separate public [disclosure fixture](../../tools/typing_experiments/wordrank-packed-disclosure-v1/NOTICE.md) was added to both registries: three normalized contexts, three control keys and two previously absent surface keys. The [post-registration comparison](2026-10-29-q5-packed-multiedit-registered.json) found no missing output contexts or surfaces among all 1,800 cases. Prior entries and incomplete coverage declarations were retained. This does not certify global registry completeness or independent qualification.
