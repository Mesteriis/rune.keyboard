# Q6: recover public spelling v6 source history

Added the missing spelling-v6 history: all 1,700 frozen rows recovered from the
original pinned `ru-0011` source via its archived original selector. All 92,622
articles were scanned. Every matching occurrence is retained: 1,729 occurrences
across 1,583 articles, with original target/context and projected source-window
keys. A second scan produced a byte-identical identities file.

The importer verifies the exact corpus manifest, personal-data exclusion flag,
frozen-before-scoring flag, row hash, public repository/revision/source path,
Parquet SHA-256 and byte count. Original selection hashes, target words and
prefixes are reconstructed by the previously verified selector. Missing row IDs
or mismatched selections fail; no model, prediction or changed label participates.

The original v6 prepare helper is also archived at its exact manifest SHA
`956436a1fbd708706bddb3bad44c1fdf7bff838ef95a8c06911008148590fe01`.
Its bytes are verified but not executed. The original mutable helper is untouched.
Complete helper/runtime/frequency/toolchain reproduction is not claimed.

Dictionary-only recovery adds 1,626 target lemmas; 110 ordinary targets remain
unresolved. Prior entries/keys/source bindings and incomplete coverage are
unchanged. The spelling-overlap summary is explicitly expanded from v7-v12 to
v6-v12: 11,088 historical articles, intersecting **122 calibration articles and
131 holdout articles**. V6 contributes 25 and 16 respectively. The earlier 97/115
counts remain correct for v7-v12 only. Existing corpora and scores are unchanged;
neither existing part certifies article-independent freshness.

The updated family audit now covers 64,216 rows: 58,083 dictionary-supported
lexical targets, 5,385 exact protected mention controls, and 748 unresolved
lexical targets (638 previously reported plus 110 from v6). No guessed lemmas
or native numeric IDs are substituted. The audit does not clear missing axes.

All 57 registry/recovery/import/restoration/audit tests pass in an isolated
source-only directory, without build inputs, PyArrow or morphology packages.
Four v6 tests cover full occurrence/control preservation, missing/changed IDs,
append-only preservation and the archived prepare source hash. A new durable
v6 article probe remains blocked without original inputs. CI includes these
unit checks; no remote CI run, Android build or Fold test is claimed.

The evidence receipt binds both scans, final identities, source inputs, current
ledger, audit and checks. Q6 remains open for other historical corpora, remaining
lexical gaps and toolchain bindings, and versioned-builder integration. This
step changes validation data/provenance only.
