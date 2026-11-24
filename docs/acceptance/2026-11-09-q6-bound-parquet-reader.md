# Q6: bound Parquet reader for text preflight

The versioned text-preflight wrapper reads the source Parquet itself with
PyArrow 25.0.1 instead of accepting a caller-provided decoding callback. It
requires string decimal article IDs and string text, records hashes of its own
reader and selected imported Python/native modules, and checks those hashes
and decoder version again after the existing source/input/dictionary drift
checks. The command-line path uses the tracked source lock; library callers
must separately establish trust in the lock they supply. Existing historical
verifiers and collectors were not changed.

These bindings identify the loaded files but do not authenticate the full
native dependency chain. The report deliberately retains
`sourceDecoderAttested: false`, does not qualify labels or independence, and
does not permit publication. Incomplete registries still block preparation.
The new test module is assigned to the scientific CI profile, whose existing
host requirements now include the same PyArrow version pinned in the model
toolchain; no hosted CI run is claimed.

Seven tests using actual locally generated Parquet files passed with PyArrow
25.0.1 under Python 3.11 and 3.13, including source and decoded-text mismatch,
duplicate article, malformed rows, decoder drift and wrong version. The same
seven tests passed in a clean temporary checkout without `build/`. The two v1
preflight modules passed 22 tests; the CI test-inventory suite passed nine.
The archived shared/all registration tests and historical verifiers also
passed using their original helpers and the existing isolated runner.

The pinned public Russian shard was downloaded using the source lock's
`parquetRevision`, and all 170,922,988 bytes matched the locked SHA-256. The
new reader decoded the first 128 rows. This checks the real source format and
identity; it is not a full-source preflight or corpus qualification. An
earlier attempt mistakenly used `datasetCardRevision` as the Parquet revision
and received HTTP 404; the correct revision was then used. The public shard,
temporary checkouts and test files were removed.

## Full-shard follow-up

The same pinned public shard was downloaded again, checked against the locked
size and SHA-256, and read to completion by the v2 decoder: 92,622 records
passed its ID/text type checks. A separate end-to-end diagnostic then used the
real lexical and control ledgers and the pinned Pymorphy dictionary. Its
temporary input assigned the first three distinct source articles with at
least three Cyrillic tokens, in source order, to train/dev/test; each text was
the first two lowercased tokens, with empty word-row files. This deliberately
small probe returned `BLOCKED_OVERLAP`, with 30 historical overlap signals,
`publicationPermitted: false` and `sourceDecoderAttested: false`. It confirms
that this input did not receive publication permission; it does not count
distinct overlapping records, attest typo labels, establish natural-corpus
quality or show that any fresh corpus is available. The temporary public
shard and all generated probe files were removed.

## Installed decoder package binding

A subsequent version binds all non-bytecode files recorded in the installed
PyArrow distribution, using a deterministic SHA-256 over relative names and
content hashes. Empty or duplicate lists, unsafe paths and missing files are
rejected; the package identity is checked both before and after the existing
preflight. Ten focused tests passed with actual Parquet under Python 3.11 and
3.13, including changed/missing package files and a simulated mutation during
the scan. The ten tests also passed in a temporary checkout without `build/`.
The full-shard run above preceded this extension and is not a full-shard test
of the new package binding.

The initial digest is not compared with a separately authenticated wheel,
files omitted from the distribution record are not covered, and native
dependencies outside the package are not covered. Accordingly the report
continues to mark decoder attestation false and refuses publication while
coverage is incomplete. No independent corpus or hosted CI is claimed.
