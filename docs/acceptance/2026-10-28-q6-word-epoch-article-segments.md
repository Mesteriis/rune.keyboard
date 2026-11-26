# Q6: source article segment exclusions

All article identities in the four word-ranking and additional-epoch manifests
were found in the exact pinned public Wikipedia parquet. For each source text,
all segments under the historical punctuation/newline delimiter were hashed;
the ledger stores hashes and article identities, not article text.

| Partition | Article identities | Distinct segment hashes |
| --- | ---: | ---: |
| Additional epoch test | 230 | 5,028 |
| Word-ranking train | 3,717 | 35,536 |
| Word-ranking dev | 334 | 4,201 |
| Word-ranking test | 869 | 7,922 |

The importer checks the original archives and ledger parents, the parquet
SHA-256, every manifest article's presence, duplicate source IDs and before/after
input hashes. Two independent runs produced byte-identical outputs. Receipt:
`build/review-q6-word-epoch-article-segments-20261028/receipt.json`, SHA-256
`0334e1a998420a7e60d31d214625cd64af111ce556fb9b22354b6080235b0066`.
No model was run.
The stdlib inventory passed 756 tests across 150 modules with no skips; the
focused importer test covers complete capture, duplicate IDs and missing IDs.

These are complete source texts as stored in the pinned parquet, split using a
simple historical delimiter; they are not independently verified linguistic
sentences. Hashes share the normalized full-sentence namespace used by compatible
sources, while historical window keys and article identities remain necessary.
Other source histories, canonical-family gaps and complete registry coverage
remain open. This does not qualify any new model or holdout.
