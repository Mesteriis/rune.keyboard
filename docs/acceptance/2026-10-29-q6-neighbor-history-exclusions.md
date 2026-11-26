# Q6 historical neighbor-recovery corpus exclusions

The original public neighbor corpus is now retained under
`tools/typing_experiments/neighbor-history-v1/`. Its train, calibration and
holdout files match the original manifest hashes byte for byte: 15,000 disclosed
rows in total. Source attribution for all 2,426 Wikipedia articles was recovered
from the exact seven hash-verified source shards, with titles and links to each
article's edit history. The retained data is licensed public source material,
not personal typing or an independent holdout.

Both permanent registries now include a source-bound entry generated from these
rows. The lexical entry has 2,426 article keys and 5,000 context keys, of which
1,950 and 4,980 respectively were absent from the prior lexical registry. The
control entry has 15,000 context/input keys, 15,000 exact surfaces and 2,426
article keys; 15,000, 14,845 and 2,426 respectively were new on their axes.
The protected forms retain both the base-word and protected-token context keys. The original entries and incomplete-coverage declarations are unchanged. An
actual previously unblocked context and regression input are rejected by the
new registries; these checks used the old incomplete ledger only with the
explicit completeness check disabled where necessary.

The original corpus's numeric native morphology family IDs are not canonical
lemma IDs. The new lexical entry explicitly declares `family` and `sentence`
as missing axes; no family mapping or whole-source sentence coverage is
claimed. Existing registry gates therefore still refuse to certify freshness.
Original generator bytes, other historical lineage and independent qualification
remain open.

The importer verifies the original receipt, all three row hashes, source
attribution, partition counts and schema, and binds its own source and every
fixture file. Two independent imports produced byte-identical registries; the
lexical output SHA-256 is
`769aad5fdb958bc606abe8c639c0071ea8a610be9ca4fd38d55687427010f670`,
and the control output SHA-256 is
`77c3ff7722871989a7dbb3d6d9e06e1b1c1ca63cc58628aa36a67e14496073a5`.
Four importer tests and the exact F-Droid data-policy check pass; `--check`
reconstructs and verifies the entries in an isolated staged-source checkout with no `build/` directory. This does not rerun the
model, score examples or qualify an accuracy improvement.
