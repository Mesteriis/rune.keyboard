# Q6: historical joint corpus against public source articles

A source-bound audit traversed the original three public Wikipedia Parquet
shards and the disclosed original joint train/calibration/holdout corpus. It
checked the exact original manifest, all three row files, all three shard hashes,
the native morphology asset, dictionary-only Pymorphy analyses and the current
source-checking code. Each row's word and prefix were matched to its article;
context and selector-segment hashes and canonical lemmas were derived from the
article and dictionary. These fields were not present in the original corpus.

Of 25,647 rows, 25,641 have a uniquely identifiable source window and pass the
row attestation. Six rows have multiple matches with the same original word and
prefix but different context or segment identities. The old selection hash does
not distinguish those occurrences, so the audit retains them as ambiguous. It
includes every possible context and segment for those six rows in its
conservative cross-partition comparison. No overlaps were found among train,
calibration and holdout for article IDs, context hashes, segment hashes or
canonical dictionary lemmas. These results cover this exact disclosed corpus and
its available source articles; they do not prove typo-generation parity or
complete global exclusion coverage.

The versioned diagnostic command is:

```sh
PYTHONPATH=tools/typing_experiments:tools/morphology \
  python tools/typing_experiments/audit_joint_history_sources.py
```

It needs the exact historical source files under `build/`, PyArrow 25.0.1 and
the pinned Pymorphy dictionary environment. Normal and `python -O` runs produced
identical aggregate results. Three mocked digest mutations for manifest, row
file and shard were rejected even under `-O`; no original data was changed.
[Numeric evidence](2026-10-29-q6-joint-history-articles-evidence.json) binds
source/code hashes and dictionary receipt identity; full logs are under
`build/review-hosted-editor/joint-history-source-audit-bound*.log`. The Android
emulator was running concurrently, so no timing claims are made for either run.

These are previously disclosed rows, not an independent holdout. No model is
trained, no exclusion ledger is modified, and Q6 remains open for the six
ambiguous source identities, other historical exposures, fresh-corpus source
attestation and training/holdout independence.
