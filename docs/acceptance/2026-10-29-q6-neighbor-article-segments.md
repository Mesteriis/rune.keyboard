# Q6 historical neighbor source-article segments

The exact seven historical Wikipedia shards were scanned for every source
article of the retained neighbor corpus. All 2,426 article identities were
found. Their complete source texts were split by the existing historical
punctuation/newline delimiter and projected into 279,056 distinct segment keys;
264,249 keys were absent from the preceding lexical registry. These are
source-article segments, not independently verified linguistic sentences or a
claim that every segment was used for training.

The importer checks the retained corpus and attribution, the exact parent
article scope, each shard's historical size/hash before reading and hash after
reading, duplicate/missing articles, and drift of its tracked helper sources. It
stores the source-segment keys as a separate compact entry and keeps existing
entries and incomplete coverage unchanged. Two independent scans and imports
produced byte-identical outputs. The new ledger SHA-256 is
`f06cd82ea2a7121928e6fd99008e43ac22652834a6d044dad52339e411c9710d`;
the numeric receipt SHA-256 is
`326c7db72f8e9321547e9b3b2acc5903487b3d4b950e2065820fe18255b9ffb2`.
A source-derived segment accepted by the previous incomplete ledger was rejected
by the updated gate, with the completeness check explicitly disabled for that
comparison. Three focused tests cover duplicate, missing and empty articles, cross-shard identity and segment projection.

`--check` verifies the recorded segment-key digest, parent article keys and
tracked source bindings without `build/`; it does not reread the Wikipedia
shards. The preceding family-registry checkpoint passed 804 stdlib tests across 164 modules, with no failures or skips; its receipt SHA-256 is
`751b1f1e38c5091b6be8c7fc6f3ed2b288ae404999fba4cf92ddac9d56f05782`.
The new segment entry has focused tests and no-build verification; a full suite
at this exact checkpoint has not yet run. The original generator remains unrecovered and global provenance and
independent qualification remain incomplete. No model was trained or scored.
