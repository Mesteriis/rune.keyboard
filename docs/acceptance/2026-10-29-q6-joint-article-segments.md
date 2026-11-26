# Q6: complete historical joint article segment exclusions

The original joint corpus and both disclosed follow-up corpora select 5,173
article identities across seven partitions in four pinned public Wikipedia
Parquet shards. Their previous permanent entries covered article IDs, source
windows and known families. This importer additionally hashes every nonempty
selector-delimited segment in each complete source article, including all
possible source occurrences of the six ambiguous original rows. These are
normalized source segments, not independently checked linguistic sentences.
No article text is written to the registry.

| Corpus partition | Articles | Distinct segment keys |
| --- | ---: | ---: |
| Original train | 1,090 | 109,220 |
| Original calibration | 1,089 | 97,661 |
| Original holdout | 1,075 | 105,040 |
| Follow-up calibration | 475 | 46,702 |
| Follow-up holdout | 482 | 46,148 |
| Follow-up v3 calibration | 479 | 38,365 |
| Follow-up v3 holdout | 483 | 37,489 |

The importer binds original manifests, every row file, both existing parent
entries and source shard hashes, verifies all required article IDs exactly once,
and rechecks the captured inputs before output. Normal and `python -O` runs
produced byte-identical ledgers and receipts. The original 157 entries and the
incomplete-coverage status are preserved; seven entries add 480,625 per-entry
segment keys. A real previously disclosed calibration article was checked against
its new registry entry. Focused tests cover successful capture, missing parent,
row corruption, source drift and the shared duplicate/missing article checks.

At this checkpoint the ledger was 94,497,017 bytes, close to common Git hosting
file-size limits. A subsequent [compact representation](2026-10-29-q6-compact-ledger.md)
preserves the same logical entries in a smaller file. Exact identities and counts are in the [numeric receipt](2026-10-29-q6-joint-article-segments-evidence.json).
Logs and the two generated copies remain under `build/review-q6-joint-article-segments-20261029*`
and `build/review-hosted-editor/`. The emulator was running concurrently; no
timing claims are made.

The corpus is historical and disclosed. These exclusions neither complete Q6's
historical coverage nor qualify a new corpus, model or held-out evaluation.

The final full stdlib profile passed 153 modules / 777 tests with no failures,
errors or skips against the expanded ledger. Its receipt is
`build/review-q6-joint-article-stdlib-20261029/receipt.json`; focused integration
passed 37 tests. The generated source files, not an Android app or model, are
changed by this slice.
