# Q6: compact exclusion registry without changing logical entries

Long sorted lists of SHA-256 keys may now be stored as `sha256-raw-base64-v1`:
32-byte hashes concatenated in the existing sorted order, with a count, SHA-256
and canonical base64 encoding. The shared ledger validator expands these lists
before consumers inspect them and rejects malformed encoding, invalid size,
checksum drift, duplicates and non-sorted keys. Ordinary schema-1 lists remain
supported. Older readers do not understand packed lists and must be updated;
the format is not silently compatible with them.

A verified compaction of the current registry reduced its file from 94,497,017
to 54,412,432 bytes. All 164 fully decoded entries, their canonical per-entry
hashes, and the incomplete-coverage state are identical. The registry file hash
necessarily changed; receipts bound to the previous raw bytes remain historical
and must not be reused as current bindings. A second compaction was byte-identical
and an actual public source segment remained blocked by the decoded registry.
[Numeric evidence](2026-10-29-q6-compact-ledger-evidence.json) records both hashes
and sizes.

To produce a fresh compact copy without changing the source:

```sh
python tools/typing_experiments/compact_holdout_ledger.py \
  --input tools/typing_experiments/holdout-ledger.json \
  --output build/holdout-ledger-compact.json
```

The command checks round-trip equality, input drift and exclusive output. Existing
importers may output expanded JSON; run compaction on their result before a
large ledger update, then validate the exact copy to integrate. This representation
is embedded in the tracked JSON and requires no ignored build files or extra
runtime dependency. It is reversible by loading and serializing the validated
ledger. Compaction alone does not complete Q6 or qualify data/models.

Focused tests cover round-trip/overlap, malformed data and checksums, excessive
counts, unsorted or duplicate keys and refusal to overwrite an output. The full
stdlib profile passed 153 modules / 780 tests with no skips; the final focused
rerun also passed after an additional negative assertion. The first scientific
profile ran 23 modules / 78 tests with one skip and two errors: both bounded
historical replay fixtures required three older source snapshots absent from the
current tree. Those mismatches existed at pre-compaction commit `854323c6`.
Logs are under `build/review-hosted-editor/`; the Android emulator ran
concurrently, so no timing claim is made.

The failed scientific runner receipt is
`build/review-q6-compact-scientific-20261029/receipt.json`; the full stdlib
receipt is `build/review-q6-compact-stdlib-20261029/receipt.json`. Neither a
failed scientific profile nor its skipped case is counted as a pass.

The two scientific errors were subsequently repaired using exact archived
capture sources; the repeated scientific profile passed 23 modules / 79 tests
with one explicit skip. See [the source-identity receipt](2026-10-29-q7-historical-capture-sources.md).
