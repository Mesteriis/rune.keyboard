# Q6: detect disclosed English source overlaps in corpus preflight

The existing holdout ledger contains article/document and normalized-sentence
exclusions for the disclosed English Tatoeba snapshot and English Web Treebank
(EWT). The corpus preflight previously skipped all lexical axes for English,
so it did not report those known overlaps. It still refused English spelling
qualification because that language is unsupported; the omission affected
coverage diagnostics and would have left a gap in a future admission path.

The preflight now checks the existing English Tatoeba and EWT article/document
and sentence keys, including for source-backed protected controls. It reports
an overlap before the remaining unsupported-identity status. English lexical
families remain unsupported, and source-backed protected inputs in other
unsupported languages remain blocked. This change does not mark either
registry complete, approve any holdout or change a model or keyboard.

Regression tests reproduced the old omission, then verified both source
namespaces, cross-source sentence matching, missing sentence identities,
source-backed protected controls and a real row from the hash-verified retained
English Tatoeba snapshot against the actual ledger. A separate local check used
the three hash-verified EWT files and the actual ledger: both a Tatoeba row and
an EWT row produced `BLOCKED_OVERLAP` with one article and one sentence
intersection, while English remained in `unsupportedLexicalLanguages`.
The EWT control-registry identity remains unsupported and is not silently
accepted. Source text was not included in the report. The complete current
preflight test module passed 23 tests; the inventory check passed.

The final standard-library profile passed 826 tests in 169 modules with zero
failures, errors or skips; receipt SHA-256
`e4c86d4bef6d187dd3fb3652b6ceb6742306f5d96d12411640bd56cb954c23c4`.
The full 23-test preflight module also passed in a staged source archive without
`build/`. Before the fix, the two new English overlap/missing-identity tests
failed as expected, demonstrating the omitted checks. Hosted CI and the
scientific profile were not rerun for this source-gate change.

Follow-up: [EWT control document identities](2026-11-03-q6-ewt-control-source.md) are now supported and source-excluded; English family qualification remains blocked.
