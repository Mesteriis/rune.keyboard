# Q6: historical word and epoch selector segments

The pinned public Wikipedia source and verified historical archives were
reprocessed using the original selectors. For every one of the 10,500 rows,
all matching source occurrences were recovered. The re-created four sets of
target-window keys and row counts exactly match their existing ledger entries.
Only normalized whole-selector-segment hashes were added; source text is not
stored in the ledger.

| Partition | Rows | Distinct segment hashes |
| --- | ---: | ---: |
| Additional epoch test | 1,500 | 524 |
| Word-ranking train | 6,000 | 2,788 |
| Word-ranking dev | 1,200 | 570 |
| Word-ranking test | 1,800 | 911 |

The historical segment delimiter is punctuation followed by whitespace, or a
newline. These are complete segments under that selector, not independently
verified linguistic sentences. Hashes use the existing normalized full-sentence
namespace for compatible cross-source exact matches; other Wikipedia window
identities remain separate. Parent article, target-context, family and window
exclusions remain necessary. Full linguistic-sentence coverage, missing
families, other histories and independent qualification are not established.

`import_word_epoch_segments.py` verifies the pinned sources and original
fixtures through the existing window recovery, retains every matching occurrence,
and rejects any drift from the four earlier window-key sets. Two independent
runs produced byte-identical ledger and receipt; raw evidence is under
`build/review-q6-word-epoch-segments-20261028/`. The receipt SHA-256 is
`f5d5b4d30734dd74256692810c5c9df1fd00c83050ecd7c8fb91f3bd1258d05e`.
No model was invoked. Selector unit coverage verifies the exact historical ID,
whole-segment hash, mismatched target and missing-capture refusal.
The stdlib inventory passed 754 tests across 148 modules with no skips; the
cross-source key assertion was added and passed in a focused follow-up run.
