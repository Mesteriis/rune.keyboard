# Q6: dictionary-supported historical family exclusions

Recovered 6,975 distinct Pymorph lemmas from 9,563 of the 10,200 historical
spelling rows v7–v12. Every dictionary-supported analysis is retained for
ambiguous forms. No predictive morphology, label inference or model call is
used. The pinned dictionary implementation and installed package bytes are
bound in the accompanying evidence receipt.

637 rows remain unresolved. A separate family-only historical addendum preserves
all original entries and their missing family axes, all original keys/bindings
and incomplete coverage. Legacy normalized surface strings are not silently
relabeled as lemmas. Historical family exclusions affect the new-family profile;
they are not mislabeled as supervised learning exclusions.

The extractor verifies original row/manifest hashes and counts, rejects missing
targets and duplicate IDs, and refuses an already-imported addendum. Correct
controls use their existing typed word. Unit checks cover ambiguous dictionary
analyses, unresolved rows, controls, hash tampering and append-only preservation.
The schema rejects non-family keys in the new family-only usage.

All 33 ledger/normalization/recovery tests pass in a source-only directory,
without build inputs or morphology packages. A recovered family (`жара`) is
blocked there using only persisted hashes. CI includes the extraction unit tests;
no remote CI run is claimed. No Android, APK, threshold or runtime changes.

Q6 remains open for unresolved families, other historical corpora, archived
source dependencies and versioned-builder integration. Existing v6 calibration
and holdout remain historically overlapping as disclosed in the preceding
[source recovery](2026-10-27-legacy-holdout-recovery.md).
