# Q6 historical retrieval disclosure

The historical public retrieval test corpus is retained at
`tools/typing_experiments/retrieval-history-v1/rows.jsonl`. Its 1,800 rows
reproduce the previously documented historical SHA-256
`cdc09d6b5885e0d6a01757c05b814d7efe97f7aaefb8932287dbaa673811098c`.
This corpus has already been exposed to evaluation and is **not** an independent
holdout or evidence of a qualified model.

The recovery matches every row to its prefix and target in the pinned Russian
Wikipedia source shard. It records 341 article identities and attribution links,
1,797 distinct target contexts, 6,319 selector-segment and bounded-window keys,
and 770 dictionary-only target families. No target lacked a dictionary analysis.
The control registry also retains 3,300 typed/target context keys and 2,491
surface keys. Segment keys do not assert linguistic sentence boundaries.
Attribution, the source lock, the dictionary receipt and ten hash-locked helper
snapshots are retained beside the rows; see the fixture NOTICE for licensing.

`tools/ci/register_retrieval_history.py --check` verifies the frozen rows,
projection, attribution, helper snapshots, and exact entries in both registries
without relying on `build/`. Its tests exercise modified rows and helpers and an
isolated checkout without `build/`. The original entries and coverage metadata
are preserved; the additions do not claim global registry completeness. Recovery
of row provenance does not prove the original model execution or provide a fresh
natural-data qualification. Other historical source and family gaps remain open.
