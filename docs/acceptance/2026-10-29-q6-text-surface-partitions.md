# Q6 text surface overlaps between partitions

The selector text exposure diagnostic now reports exact normalized surface
identities shared across train, dev and test. This catches a shared word even
when the dictionary returns no family; the previous cross-partition summary
only reported article, segment, family and context identities. The count sums
pairwise set intersections and covers all observed surfaces, not just unknown
ones; a word present in three partitions therefore contributes three pairs.
The existing tokenizer also includes a truncated final surface in this
conservative diagnostic, so the count is not a count of complete words alone.

A focused regression uses the same unknown surface in two source articles with
no dictionary analyses. Before the change it failed with a missing `surface`
field; afterwards the family overlap is zero and the surface overlap is one.
All 19 `test_fresh_spelling_holdout` tests pass. The first attempted focused
command used the wrong test class name and failed to load; the corrected command
reproduced the missing field. This is diagnostic evidence only: registry
coverage remains incomplete, unchecked text is still refused and no corpus or
model is qualified by this change.

A real diagnostic repeat on the previously disclosed intercepted word-ranking
output checked 430 fragments against the pinned public article shard and current
registries. It reports 4,819 pairwise cross-partition surface identities, 2,078
unresolved distinct surfaces, four fragments truncated inside a word and no
unmapped source fragments. These figures do not establish how many overlapping
surfaces are unresolved or how many are meaningful independent evaluation
collisions. Two runs were byte-identical (SHA-256
`f62281193bec5538f2ddac3de1c668eaa9b707e9b10fc2e5050c52c66144db2a`). The
registry and dictionary receipts differ from the earlier original-context audit,
so the older registry-dependent counts are not directly comparable. The report
is retained under ignored `build/q6-text-surface-partitions-20261029.json`.

The diagnostic now also separates unresolved dictionary surfaces from the
whole surface count. A mixed known/unknown fixture proves that the separate
count does not include dictionary-resolved words; the prior implementation
failed that test because the field did not exist. All 19 focused tests pass.
Two byte-identical runs on the same 430 exposed fragments found 187 pairwise
unresolved-surface overlaps within the 4,819 surface overlaps. This is still a
conservative tokenizer count, including possible truncated surfaces, and does
not establish canonical identities or qualify the corpus. The resulting report
hash is `4d31c423f6b7826af37567caea13deadcd7ac3e406bd44847c5f583675d620dd`.

A follow-up local coverage probe found 131 distinct unresolved surfaces shared
between partitions (187 counts the same surface once per partition pair). All
131 have exact unsupported-surface keys in the then-current validated lexical
ledger; none lacks a representable key or a matching exclusion. This agrees
with the historical word-text family import: the three inspected text files are
byte-identical to the retained word-ranking files. The probe counted only exact
surface coverage, including possible truncated surfaces; it did not establish
canonical families, global registry completeness or independent qualification.
Two executions produced identical aggregate output (SHA-256
`473122e57f1e9cc1043c0cade68e9dca40eeacce83182e54bb1ba29ecaf9c68a`); the
validated ledger SHA-256 was
`ad11f81bf3d5a4c5fba6dbeed5f24c950f8857bf4ef1e3ab8ecb0f096b7596b7`.
The bounded local probe and result are retained under ignored
`build/q6-unresolved-coverage-20261029.py` and `.json`; this is not a new
portable qualification gate.
