# Q4: numeric observation period comparison

The owner Fold's retained numeric `RUNE_QUALITY_3` file was captured through
read-only ADB as a private baseline, without resetting or changing the device.
The ignored `build/fold-owner-q4-observation-*` directory is owner evidence,
not a disposable build artifact. Its snapshot and metadata are owner-readable
only; do not commit, publish, or delete them as routine build cleanup. The
quality-metrics preference was enabled before and after capture. Its exact
values are deliberately not recorded here.

The snapshot is persisted asynchronously, so it may lag current in-memory
state. Endpoint preference checks, timestamps, hashes and nondecreasing
counters do not prove uninterrupted collection, ordinary owner use, or absence
of a reset between snapshots. A capture clock can also be incorrect. The
original Q4 requirement for two weeks of actual owner use and an acceptance
report remains open.

`tools/qa/quality_period.py BASELINE BASELINE_META FINAL FINAL_META` compares
strict, hash-checked v3 snapshots using UTC-aware `captured_utc` and
`snapshot_sha256` metadata. Keep both snapshots and metadata private. It rejects
counter decreases, saturation, incompatible schema, invalid hashes and
non-increasing timestamps. It reports counts per fixed source, and only reports
the explicit-undo/application ratio when that source has at least 100 period
applications. An undo may concern an application immediately before the
baseline; the ratio is not a correctness measurement. A ratio over 1 is
possible across the boundary and should be investigated, not silently clipped.
App version changes during the period also limit attribution. Independently
establish the observation period and collection continuity before drawing a
conclusion; the comparison does not certify either.

The automated test checks the actual Kotlin source/outcome order, threshold,
period boundary, hash/schema validation, counter decrease, saturation and
cross-boundary undo. The CI workflow runs this test in its stdlib profile;
hosted execution has not been established by this local change.

## 2026-11-24 baseline integrity recheck

The retained owner baseline passed the v3 parser, its metadata SHA-256
check and the saturation check. Its UTC capture timestamp is at least
14 calendar days before this recheck. The sole Fold baseline and its
metadata remain in the private ignored directory. Counter values are
omitted from this receipt.

Capture the final snapshot through read-only ADB before any candidate
installation or typing fixture on the Fold. Use the ordinary owner-use
interval and the observed bounds of collection to evaluate the report.
The calendar window alone does not establish two weeks of ordinary use
or uninterrupted collection. ADB did not show the Fold at this recheck,
so the final endpoint and acceptance remain open.
