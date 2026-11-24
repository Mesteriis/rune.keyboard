# Q6: share the v7 and v8 holdout builder

The v7 and v8 entry points now delegate to `fresh_spelling_holdout.HoldoutSpec`
and its common builder. The original paths, command-line arguments, public
`build_rows` and `prepare` signatures, source constants, counts and seeds are
retained. The shared specification now permits version 7; versions below 7
remain invalid. New collection still refuses incomplete registries before
reading the input or creating output, and historical reproduction remains
explicitly labelled as disclosed rather than independent.

The historic v7 and v8 generator hashes remain in their existing ledger
entries and their exact original bytes remain in the frozen source archive.
The refactored scripts produce new source hashes. New manifests also bind the
shared builder, so they are not byte-identical to older manifests; no historic
manifest or ledger entry was rewritten.

For each version, the common row builder matched all 1,700 synthetic rows from
the hash-verified original archived implementation. A separate temporary
before/after integration comparison exercised the full `prepare` pipeline with
synthetic source, vocabulary, generator, Parquet decoder and registry receipt:
the 1,700 JSONL rows matched byte for byte and all manifest fields matched
except the expected changed script hash and added shared-builder binding.
The row hashes were `bbd0040a7174ae741a6a7d7156c2c43dcb4abade590df021428545b623344277`
for v7 and `671b1dc678a73e96c34d33a03f8e2b52361b6de95ed48373e7e9dc4b593a7ed9`
for v8. These synthetic controls do not reproduce the original public corpora
or prove fresh-data quality. The first temporary comparison setup failed on a
macOS `/var` versus `/private/var` path mismatch; the second loaded the old
module through its altered import path. Both harness issues were corrected
before the reported comparison; neither was a successful check.

The 21 shared-holdout and five cross-version tests passed on Python 3.12 and
3.14; the v7/v8 builder tests also passed. These include the original-source
hash checks, full synthetic row parity, CLI and public-function forwarding,
incomplete-registry refusal and loading by absolute path in an isolated Python
process. The 26 tests passed again in an exported source tree without `build/`. The original historical-source and recovery
suites, isolated text-boundary checks and suspended-source verifier passed.
The complete standard-library inventory passed in the working checkout: 183
modules, 908 tests, zero failures, errors, skips, timeouts or missing receipts.
Temporary comparison files, source snapshots and test outputs were removed.
Hosted CI, scientific backends and physical-device checks were not run for
this change.

This completes the requested v7/v8 consolidation, not Q6 as a whole. Registry
coverage, independent source/label qualification and historical lineage gaps
remain open; no new holdout or model was promoted.
