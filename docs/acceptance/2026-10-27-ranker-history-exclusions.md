# Q6: import public ranker training/dev/test history

Imported the frozen `typing-ranker-v2/data` corpus after checking its pinned
manifest, every advertised row/text file and the original Wikipedia shard's
SHA-256. The manifest identifies the public repository/revision and explicitly
excludes personal messages. This imports existing exposure, without rebuilding
training data, fitting models or reading predictions.

All 1,158 declared text-exposure articles are persisted: 889 train, 98 dev and
171 test. This deliberately includes articles with no selected target row.
The 5,000/1,000/1,500 target rows are checked against their original partition
and source-article membership. Existing entries, keys, bindings and pending
coverage are preserved.

Dictionary-only target-family addenda retain every supported analysis. Train
families are supervised exclusions; dev/test families are historical exclusions.
One training target is unknown to the pinned dictionary; all dev/test targets
are recognized. Missing family/window/context axes remain explicit. Canonical
family strings from the old rows are not trusted without dictionary analysis.

There is no article intersection with the current v6 calibration or holdout for
this particular archive. That does not erase the 97/115 intersections already
disclosed for historical spelling v7–v12.

The accompanying receipt binds the inputs, package code/data and counts. All 38
ledger/normalization/recovery/import tests pass in an isolated directory without
build inputs or morphology packages. Durable probes verify both an imported
article and a supervised training family. Four importer tests cover whole-text
article exposure, supervised versus historical families, unresolved targets and
malformed source/partition/count/ID fields. CI includes these unit tests.

Q6 remains open. Original preparation source preservation, other histories and
versioned-builder integration are still pending. No full historical training
reproduction, remote CI execution, Android build, Fold test or runtime change
is claimed.
