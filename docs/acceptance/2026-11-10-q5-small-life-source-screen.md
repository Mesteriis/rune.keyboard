# Q5: Small-Life dialogue source screen

[Small-Life-Dataset-ru-eng](https://huggingface.co/datasets/SonexaAI/Small-Life-Dataset-ru-eng/tree/e80111242bbcee1979794f9702898b9ea5e99bca)
declares CC0 and 50,000 question/answer rows. Its card describes broad
conversation and coding categories but does not establish the authorship,
spelling review, original sources or naturalness of individual entries. The
card's configured `dialogues_dataset.jsonl` path is not in the pinned file
list; the actual file screened here is `train.jsonl`.

Two downloads at revision `e80111242bbcee1979794f9702898b9ea5e99bca` matched
the advertised Git blob `e84ab598414ee3b598a5c69a21fbdb61fc01e92a`, 8,911,884
bytes and SHA-256
`a0d316a9c131b6f35f2c77dfd309f8092d122d539ce3a3db8d1577e4c4b1ce73`.
Both independent in-memory scans produced identical counts. All 50,000 lines
parsed as objects with the five declared fields; language totals were 25,135
Russian and 24,865 English, and category totals 24,944 General and 25,056
Coding. These counts match the card but do not establish content uniqueness.

For the 12,492 rows labelled both Russian and General, a separate hash-checked
download found 80 distinct exact question/answer pairs, 80 distinct questions
and 20 distinct answers. The most repeated exact pair occurs 575 times. IDs
were unique within that subset; unique IDs therefore do not imply unique
dialogues. The union of question and answer texts has 100 unique strings.

With the strict Q5-shaped screen of 2–6 whitespace-delimited, Cyrillic-only
words and no punctuation stripping, 4,372 answer occurrences qualify but
collapse to seven distinct lowercased texts; no question occurrence qualifies.
Neither the filter nor the dataset's category proves spelling correctness or
represents real chat frequency. No source text or per-row fingerprints were
retained; no keyboard, model or corpus registry was changed. This source does
not supply the required 3,840 independent, labelled chat controls. It is not a
fresh holdout or a Q5 false-change baseline.
