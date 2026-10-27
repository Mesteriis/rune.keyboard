# Q6: preserve verified natural Wikipedia context-pool exposure

Imported all seven availability pools bound by the frozen natural-context plan:
1,204 contexts. Every original plan/output/collector hash is checked; each public
Parquet source and source-lock binding is verified. Every target occurrence's
prefix and right suffix are reconstructed from the actual source article and
its normalized source-window hash is recomputed. No model, score or prediction
is read or executed.

All targets and rivals have dictionary-only analyses in the pinned Pymorph
installation. Every supported analysis from both candidates is excluded; native
numeric or legacy surface families are not substituted. Each pool therefore has
article/window/context/family keys without a missing axis. No previously stored
entry, key, binding, coverage flag or spelling-overlap scope is changed. The seven
pools add no current v6 calibration/holdout article intersection.

The original collector source bytes are archived at frozen plan hashes. They
are not run by the importer; their top levels bind old models and write files.
Archival does not claim complete historical runtime reproduction. Rebuilding
requires the original public Parquet/context outputs and dependent receipts.

All 110 tests pass in a source-only directory without build data, PyArrow or
morphology packages. Five new tests cover exact article captures, source-window
identity, both candidate families, unknown rivals, duplicate pool IDs and durable
snapshots. CI includes these checks; no remote CI run is claimed. The extraction
itself additionally reads the pinned dictionary/source Parquet files.

Q6 remains open for other context/conversation histories and existing unsupported
lexical families. Public Tatoeba sentence IDs must receive an explicit namespace;
they must not be treated as Wikipedia article IDs. No Android or model change.
