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
