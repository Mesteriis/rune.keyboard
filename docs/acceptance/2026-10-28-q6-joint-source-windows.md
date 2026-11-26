# Q6: historical joint source-window exclusions

The original joint corpus and both follow-up corpora retain numeric family IDs
and initially had no source-window exclusion axis. The importer verifies each
pinned manifest, row file, existing parent binding and public Wikipedia shard,
then finds every matching target and prefix in the declared article. It uses
exact archived generator bytes and the existing normalized 256-character left /
128-character right source-window convention. It rechecks all bound bytes before
output; an unmatched target, missing or duplicate article, changed input, or
unregistered parent fails the import.

The seven new source-only addenda preserve all previous entries. They cover
44,816 rows across the three corpora and 5,387 distinct window keys summed over
the seven corpus partitions. No corpus text or private material is added to the
ledger. Tests exercise successful import and source drift before and during
capture. Existing historical parent gaps remain explicit: these bounded windows
are not full sentences, and their recovery does not complete canonical family
provenance, registry coverage, or independent model qualification.

The [numeric evidence](2026-10-28-q6-joint-source-windows-evidence.json) binds
the audited sources, importer and capture implementation.

## New joint collector boundaries

Both current joint collectors now reject a Cyrillic match when it is only a
fragment of a larger source token, including hyphenated, combining-mark,
zero-width and apostrophe-connected forms. Historical reproduction retains the
original selector. The new mode also snapshots its collector helpers and pinned
dictionary receipt before selection, checks them again before writing output,
and records helper hashes in its receipt. A changed input, helper, or dictionary
refuses output.

Synthetic collector tests exercise the primary path through output and verify
source, helper and dictionary drift; a separate follow-up test checks selection
before output. These fixtures substitute the public source and initial registry
admission and do not establish independent qualification. The historical
holdout tests and the separate historical text-boundary and suspended-retrieval
checks remain applicable; full registry coverage and Q6 qualification remain
open.

An additional local probe used real PyArrow 25.0.1 Parquet files, the packaged
Russian morphology asset and the hash-locked Pymorphy dictionary. Three synthetic
articles generated 26 rows through the unmodified row generator; the actual
preflight returned `BLOCKED_COVERAGE` with no identity errors and no output was
published. The source lock identities and split assignment were substituted for
the fixture, as were initial admission and the test registries; this is not a
real-source qualification. Two earlier fixture setup attempts failed before
selection (an unavailable morphology word and an unresolved temporary path);
the corrected run above passed. Temporary data and the virtual environment were
removed.
