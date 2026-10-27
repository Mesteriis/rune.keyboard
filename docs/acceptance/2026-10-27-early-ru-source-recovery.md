# Q6: recover source articles/windows for early RU spelling history

Recovered all 10,200 frozen RU spelling rows from qualification-v2 and compact
v3/v4, retaining 10,278 matching occurrences in 6,875 source articles:

| Component | Rows recovered | Occurrences | Articles |
| --- | ---: | ---: | ---: |
| qualification-v2 | 3,400 | 3,433 | 2,282 |
| compact-v3 | 3,400 | 3,432 | 2,332 |
| compact-v4 | 3,400 | 3,413 | 2,261 |

The exact original source-lock JSON files were restored from local Git at their
manifest SHA-256 values, without changing fields. Each archived generator and
lock, public RU Parquet hash/byte count, original manifest and row file is
verified. The evidence records original lock commits and final scan exit codes.

The old builders select articles using SHA-256(seed:ru:article ID), modulus 4
and a version-specific residue. Recovery respects that filter: 23,195 / 23,199 /
23,116 articles are eligible respectively. Choosing all source articles would
silently change historical selection semantics. V2 passes literal corpus seed
3042026; v3/v4 use corpusSeed from their archived locks. The initial restoration
probe assumed the newer key in v2; inspecting v2 source resolved that difference.

Calibration/holdout template wrappers are normalized only in copied rows before
calling the existing frozen-selection recovery. Original row IDs, prefixes,
family strings and labels are preserved. Each reconstructed candidate must match
the archived selector exactly. Because selection hashes omit article IDs, every
eligible matching article/occurrence is retained, without choosing a first match.
Source-window hashes use the existing whole-article prefix/suffix projection;
these are not full-sentence identities. Full-article exclusions cover all source
sentences even when a window projection differs.

The merge verifies all receipt input hashes, original row coverage and selection
identities; source binding changes, incomplete receipts and model calls fail.
It unions article/window keys while preserving every prior key and source binding.
Only the three early parent entries change. Their family gaps stay explicit,
all other entries and pending coverage stay unchanged.

The spelling article history now covers **17,963 articles** in ten component
entries. The newly recovered articles add no current v6 calibration/holdout
intersection. Existing totals remain **122 calibration articles and 131 holdout
articles**. Original corpora/scores are unchanged and do not certify freshness.

All 72 registry/recovery/import/restoration/audit tests pass in a source-only
directory, without original build inputs, PyArrow or morphology packages. Eight
new recovery/merge tests cover copied split wrappers, article selection, exact
source-lock archives, tampered bytes, occurrence preservation, missing rows,
wrong selections, incomplete/model-call receipts and immutable old bindings.
A recovered early article remains blocked using only the committed ledger.
CI includes these tests; no remote CI run is claimed.

The first isolated run exposed two test fixtures that assumed checkout layout;
they now create their own nested archive fixture and the final isolated run
passes. Production source was unchanged by that fixture repair. The failed raw
check and successful final check are retained separately under the build evidence.

Q6 remains open for punctuation/protected components, EN/ES namespaces, other
context/conversation histories, unresolved lexical families, dependent evaluation/
runtime archival and versioned-builder integration. No model fitting, threshold
change, Android build or Fold interaction is part of this migration.
