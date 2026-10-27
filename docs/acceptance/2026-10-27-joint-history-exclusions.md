# Q6: import joint and follow-up historical exclusions

Historical import receipt. The previously missing v1 builder was subsequently
[restored exactly](2026-10-27-followup-generator-restoration.md).

Imported the original joint corpus and both historical follow-up versions:
44,816 rows, 5,173 unique source articles and 10,770 distinct target-context
keys across their seven partitions. Every prior entry/key/binding and incomplete
coverage status are preserved; the old corpora and predictions are untouched.

The importer verifies three exact corpus-manifest hashes, every row-file hash
and four public Wikipedia source-Parquet hashes. Public-source locks bind the
revision and source byte counts. Each row's source name, partition, language
and article membership are checked; article membership is read directly from
the source Parquet ID column. These checks do not certify old labels or replay
old model results. The row counts and source hashes are existing history.

The numeric native family IDs in these corpora are not canonical Pymorph lemmas.
Dictionary-only target-family addenda instead retain all supported analyses.
Training families are supervised; calibration and already-disclosed holdout
families are historical. There are 5,385 unresolved target-row analyses, including
repeated variants. No lemmas are guessed. Parent entries retain missing family
and source-window axes. Whole-article and typo-independent context exclusions
are already enforced by the persisted registry.

This import has no source-article intersection with current v6 calibration or
holdout; the separately disclosed v7–v12 spelling overlap remains unchanged.
No data is filtered after scoring or promoted as fresh qualification.

The original joint builder (`cfa5777d...`) and v3 follow-up builder (`b9cc4859...`)
are archived byte for byte. They are source evidence, not supported relocated
entry points. The older follow-up builder (`964b7c65...`) remains unavailable;
the importer preserves its original recorded hash rather than substituting v3.
Complete toolchain reproduction remains pending.

All 45 ledger/normalization/recovery/import tests pass in a source-only directory,
without original build inputs, PyArrow or morphology packages. Six joint-import
regressions cover article/context preservation, native-ID separation, unknown
targets, source/partition/count failures, changed source bytes before reading,
and archived builder hashes. A persisted joint article is rejected without the
original corpus. CI includes the unit checks; no remote CI run is claimed.

The accompanying evidence binds the final import, sources, archived builders,
checks and ledger. Q6 remains open for the other qualification/context/conversation
histories, unresolved families, missing generator versions and new-builder
integration. No Android build, Fold test, model fitting or runtime change.
