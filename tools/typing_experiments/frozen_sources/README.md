# Frozen historical generator bytes

These are byte-exact snapshots of Rune's own qualification-v2 generator used by
the six historical public spelling corpora. `manifest.json` binds each file's
full SHA-256 and its original repository path. The original working generator
is not modified, replaced or reset.

These relocated files are **not supported CLI entry points**: their original
path-relative corpus/resource defaults belong to the historical tree layout.
`recover_legacy_holdout.py` verifies the snapshot hash and calls only the pure
selection/normalization helpers, with explicitly pinned rows, seed and source.
The recovery tests exercise both versions, including the later mixed-script
eligibility guard. No model or historical threshold is rerun or refitted.

Do not refactor these snapshots. A different historical SHA requires its own
verified file and manifest entry. Complete historical corpus reproduction still
requires its other original generator/runtime/source bindings; archiving these
two files does not claim that the entire training toolchain is now preserved.

Two joint builders are also preserved byte for byte: the original joint builder
`cfa5777d...` and the v3 follow-up builder `b9cc4859...`. These archives preserve
source evidence only; they are not executed by the history importer and their
relocated path-relative defaults are not supported. The older follow-up SHA
`964b7c6505cf5b3a0d766563e29ff750b3db70638302267db9c0318ffa05aef8`
is now restored byte for byte and archived as well. The deterministic restoration
removes the later v3 article/extra-corpus exclusions and verifies both the v3
input hash and v1 output hash from the original manifest. See
`restore_frozen_followup.py`. These sources still depend on other historical
helpers/runtime/files; preservation does not claim complete corpus reproduction.

The original spelling-v6 preparation helper is preserved at
`956436a1fbd708706bddb3bad44c1fdf7bff838ef95a8c06911008148590fe01`.
Its bytes match the original v6 manifest. The v6 history importer verifies this
archive but calls only the previously archived qualification selector helpers;
it does not execute the relocated prepare helper or claim a full corpus rebuild.

The original qualification-v3 and v4 generators were recovered from local Git:
`60cb1cdf671dcc0781d47225d225eebc178392f7b616a7ae77d084e4906126a7`
and `9615bc8033760257bc384ece09d67f6b92e0b7541e144ea6ec746a2f4cc06de4`.
Their bytes match the early compact corpus manifests. The early-RU importer
checks these snapshots but does not execute them. The archives' dependent
helper/evaluation/source-lock/runtime bindings still need separate preservation.

Exact qualification source-lock JSON files v2-v4 are preserved as well. Their
manifest hashes, original paths, seeds, article selection rules and RU Parquet
bindings are checked before early source recovery. Restoration used matching
Git blobs; no source-lock field was rewritten to fit the current environment.
