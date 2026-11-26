# A4: public-source screen of abbreviation controls

The 54 previously disclosed authored abbreviation controls were screened
against the exact `0011.parquet` shard of the public Russian Wikipedia
2023-11-01 snapshot, using the repository's pinned source lock. The 200,905,664
source bytes matched the pinned SHA-256 before and after decoding. Two complete
scans yielded identical counts over 92,622 distinct article IDs. The second ran
after tightening duplicate-ID validation. This source was used in earlier Rune
work; it is disclosed development evidence, not a fresh holdout.

The screen counts case-insensitive whole control tokens followed immediately by
`.` and then whitespace, end of text or closing punctuation. It excludes
hyphen-attached forms, longer words and continuations after the dot such as
`спб.рф`. It does not exclude a preceding domain component such as
`forum.мск.`. No article text, identifiers or positions were retained. A match may be an
ordinary word at sentence end, a name, a citation or an abbreviation: its
intended meaning is not verified. Therefore these are surface-use counts, not
validated abbreviation frequencies, usage rates or autocorrection precision.
The source is encyclopedic rather than representative of user messaging.

49 of 54 forms occurred at least once; 42 occurred in at least 10 articles and
21 in at least 100 articles. These cutoffs are descriptive, chosen after the
scan, and are not a qualification threshold. For the five review examples:

| Form | Raw matches | Distinct articles |
| --- | ---: | ---: |
| спб | 2,334 | 1,108 |
| мск | 6 | 6 |
| адм | 48 | 29 |
| пгт | 44 | 42 |
| экон | 22 | 13 |

The [retained aggregate](../../tools/typing_experiments/a4_controls/wikipedia-0011-frequency.json)
binds the exact source shard, source lock, controls and scanning helper. It
contains numeric aggregates and previously disclosed control forms only. The
helper rejects malformed or duplicate article IDs, checks input hashes again
after processing, and never authorizes independent qualification. PyArrow
25.0.1 on Python 3.12.14 decoded the source; its wheel and native dependency
chain were not independently attested. Five focused standard-library tests
cover matching boundaries, article counts, identity errors and retained
receipt bindings; the test is included in the CI inventory. Full scientific
and hosted CI were not run. The downloaded shard and temporary Python
environment were removed.

This supplies evidence that many control surfaces occur in a public corpus.
Meaning-level annotation, frequency-weighted sampling, independent controls and
the overall review acceptance remain open.

## Meaning review and exclusion of exposed articles

A deterministic hash-ranked sample was selected from the same pinned shard:
one first matching occurrence per article, up to ten distinct articles for each
of the five forms named in the review. Only six articles matched `мск`, so the
sample has 46 occurrences in 46 distinct articles. Selection was fixed before
review; the article sampling and first-occurrence rule do not produce a
frequency-weighted sample of individual occurrences.

A single model reviewed temporary excerpts in context, with this result:

| Form | Sampled | Interpreted as an abbreviation | Other or uncertain |
| --- | ---: | ---: | --- |
| спб | 10 | 10: Санкт-Петербург | All ten were `СПб`-style mixed case |
| мск | 6 | 5: московское время | 1 was part of a website name |
| адм | 10 | 10: 9 administrative, 1 admiral | — |
| пгт | 10 | 10: посёлок городского типа | — |
| экон | 10 | 9: economic | 1 uncertain |

These are reviewer judgments, not independently checked ground truth. In
particular, the `мск` sample does not demonstrate the intended city-name sense,
and the `спб` sample does not demonstrate lowercase usage. Repeated references
and related articles may bias the sample. No precision or natural-chat
qualification follows from these 46 examples.

The retained [sample](../../tools/typing_experiments/a4_controls/wikipedia-0011-review-sample.json)
contains public article IDs, NFC code-point offsets, case and hashes of bounded
source excerpts; the [review](../../tools/typing_experiments/a4_controls/wikipedia-0011-meaning-review.json)
contains only per-sample labels and meanings. No excerpt text is retained.
The pinned source is needed to reproduce the contexts; excerpt hashes are not
anonymization. Two full scans produced the same chosen articles and offsets;
the second additionally recorded case. The local PyArrow decoder and native
chain were not independently attested.

All 46 reviewed articles are now excluded through source-identity entries in
both the lexical holdout ledger and the public-control ledger. Before import,
2 of the 46 already appeared in the lexical article exclusions and none in the
control article exclusions. The new entries deliberately claim article-only
coverage, with lexical family, sentence and context axes still missing; global
coverage remains incomplete. The importer checks fixed sample and review hashes,
source and helper bindings, preserves previous entries and refuses duplicate
imports. Focused tests verify matching, sampling, frozen artifacts, all 46
identity keys, mutation refusal and real overlap rejection in both ledgers.
The temporary source shard, excerpts and Python environment were removed.

## Whole-shard exposure quarantine

The aggregate scan also read the entire `0011.parquet` shard, not only the 46
manually reviewed excerpts. Its 92,622 distinct public article IDs were
therefore hashed in each existing article-identity namespace and registered in
both ledgers. No article text or raw full-shard ID list is retained. Two
independent ID-column reads of the exact pinned shard produced identical complete
sets. All 46 reviewed articles are members of both sets. Immediately before the
whole-shard import, including the new 46-article review entry, 3,166 of these
article identities already appeared in lexical exclusions and 360 in control
exclusions. These counts are overlaps, not claims about prior model training.

The [source exclusion manifest](../../tools/typing_experiments/a4_controls/wikipedia-0011-source-exclusion-manifest.json)
binds the source, source lock, decoder version, scanner, identity helpers and
both complete key-set digests. The lexical registry stores this new set in its
existing packed format; the control registry uses its existing sorted article
keys. The additions grow the two existing registry files because neither guard
currently supports a whole-shard identity. Both entries exclude articles only;
family, sentence and context coverage remains incomplete. The matching source
can no longer pass either article-overlap guard as fresh, but this does not
establish independent qualification of any other source.

A current-source importer check validates the frozen manifest, hash helper
bindings, exact 92,622-key digests and the 46-article subset. Tests exercise
order independence, malformed and aliased IDs, source-key and manifest mutation,
and actual overlap rejection in both registries with the smaller review entry
removed. All pre-existing ledger entries were checked unchanged before appending
these two source-exposure entries. The Parquet decoder wheel and native chain
were not independently attested. Temporary source, generated intermediate key
lists, excerpts and environment were removed after validation.
