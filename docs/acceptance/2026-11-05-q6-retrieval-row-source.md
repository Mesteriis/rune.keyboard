# Q6: source-attested selector rows

The file-bound selector diagnostic now retrieves articles named by word rows,
including articles with no separate text fragment. For each proposed row it
checks the article identity, exact preceding context, complete source-token
boundary, source-window and segment hashes, and the full set of dictionary-only
analyses. Missing articles, forged identities or hashes, partial tokens,
ambiguous source occurrences and missing or mismatched analyses are reported
as blockers. Word rows with existing lexical/control overlaps remain blocked
for overlap as before. A verified source word does not validate a generated
typo or its label. The diagnostic still forbids publication and cannot certify
freshness while registry coverage remains incomplete.

The source file is checked against the supplied lock and rehashed after
reading. The library accepts an injectable decoder, so its report explicitly
sets `sourceDecoderAttested` to false; callers must trust the decoder and the
bound lock. The CLI uses PyArrow. The source, inputs, relevant helpers,
generator and dictionary receipt are bound and checked for drift. Historical
verifiers and their bound helper bytes were not changed.

The retained public retrieval corpus contains 1,800 disclosed rows in 341
articles. Two independent runs of `audit_retrieval_row_attestation.py` against
the exact pinned Wikipedia shard produced identical numeric reports. They
reconstructed source-window fields for 1,790 whole-token rows and the new
checker matched all 1,790; 10 source fragments were rejected at a compound
boundary. A forged dictionary family was rejected. These reconstructed window
fields were not originally stored in those rows; this audit does not recover
historical source code, establish original training execution or qualify a new
holdout. The dictionary receipt SHA-256 is
`dc4745f9ac4d89dfc60f201cc2c1845d3ffa7d4197f6da6cf5e3c7d33c3596de`;
it differs from the prior archived receipt. The [numeric receipt](2026-11-05-q6-retrieval-row-source-evidence.json)
has SHA-256 `1ea722a96052feb5700dade1507ac16d2f58c821e34ef249c77b3629244f812f`.
The public shard was downloaded to a temporary directory, checked against its
source lock and removed after both runs.

In a staged source archive without `build/`, 20 selector-preflight tests, two
retrieval-audit tests, 25 corpus-preparation tests and 19 selector-guard tests
passed without skips. The disposable archive was removed. The original root
`build/` and its lost historical reports were not recreated. Q6 still needs a
validated coverage migration, provenance completion and independent labels.
