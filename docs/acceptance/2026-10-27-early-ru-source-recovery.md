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

## Complete retained v3/v4 corpus bytes

A later SHA-256 search matched 12 previously missing `build/` binding values
covering 44 registry references to reachable Git objects under the original v3
and v4 qualification corpus paths. The original manifests each list seven
files; all 14 files, including English and Spanish spelling rows not among those
12 matches, were read from the original recorded commits and verified against
their respective original manifests. The two manifests and 14 files are now
retained in deterministic bzip2 tar archives under
`tools/typing_experiments/historical-qualification-v3-v4/`; their combined size
is 2,359,286 bytes. A second independent archive creation reproduced both
compressed files byte for byte. The local Git-object search covered 8,793 blobs
up to 64 MiB and skipped 38 larger blobs; it did not recover available-v6 rows.

The new source-only checker verifies fixed original manifest hashes, member
names, regular-file types, bounded sizes and every original member hash without
extracting files. Three tests pass, including changed content with a recomputed
archive hash and a traversal-member negative case. The stdlib CI inventory
includes the checker test. The F-Droid data guard inventories both archives
without scanner suppression; its focused policy/prepared-source tests pass 29
cases. A clean clone plus the staged changes and pinned llama.cpp passed the
local F-Droid 2.4.5 source scanner with zero fatals and two pre-existing warning
categories. This used packaged SUSS defaults, not hosted build-server state.

Gitleaks 8.30.1 scanned the 16 archive members individually: 14 exited 0, while
both original manifests produced one generic-key finding each; each value was
verified as the SHA-256 of an actual corresponding archive member. The scanner
therefore did not report a clean zero-finding result for all members. Temporary
scanner environment, reports and reproduction artifacts were removed. An
initial test creation command used the wrong relative path, and the inventory
check initially saw the new test as untracked; after fixing the path and staging
it, the final tests and inventory check passed.

These are previously disclosed historical evaluation inputs, not an independent
holdout, approval for retraining, historical model parity or reconstruction of
available-v6. Original manifests declare Wikipedia CC-BY-SA-3.0/GFDL-1.3 and no
personal messages; complete per-row attribution and independent privacy review
are not established. Publication and distribution acceptance remain open.

### Portable source-only restore

The historical archive tool can now restore both verified datasets into a fresh
caller-specified directory under `build/`, without executing historical scripts
or reading Git. It checks both archives before creating output, refuses an
existing destination, outside-build path and a symlink destination, writes only
fixed validated names, and removes the newly created destination on a write
failure. Archive validation now reads the same in-memory bytes it hashed, so a
file change between separate hash and tar reads cannot bypass the check.

Five focused tests pass, including byte-exact restoration, existing/outside/
symlink refusal, write-failure cleanup, corrupted row data and archive traversal. A minimal isolated
copy containing only the checker and retained archives, with no `.git` or old
build files, restored both corpora; an independent script rechecked all 14 row
files against the original manifests. The isolated copy and restored bytes were
removed. This does not recreate original model scores, establish per-row
attribution, recover available-v6, or qualify the historical datasets as fresh.

### Early RU importer uses the retained archives

`import_early_ru_history.py` now reads the original v3/v4 files when both are
present and valid. If both are absent, it loads the verified retained archives
and binds the resulting entry to the actual archive, catalog and executed archive
checker, instead of inventing bindings to missing `build/` files. A partial or
corrupt original corpus fails closed rather than falling back. The retained
checker verifies original manifest and row bytes; its source is also compared
with the copy bound by the importer. The original v2 input and the pinned public
Parquet SHA-256 requirements remain unchanged. Receipts identify which storage
path was used; no existing ledger was modified.

An integration test used the real v3/v4 archive bytes and frozen generator
sources in a temporary source-only tree, processing 3,400 RU rows per corpus
through the actual importer. The public Parquet identities and dictionary were
explicitly mocked for that positive fixture; a separate negative assertion
confirmed that missing real Parquet files fail. It verifies the generated
archive bindings, not natural-source provenance or a production dictionary run.
A 52-test importer, archive, historical recovery and both-ledger suite passed;
a subsequent seven-test importer repeat passed after adding the missing-source
negative assertion. The stdlib inventory check passed. Early attempts to add a
test from the wrong working directory failed before changing the file; the
corrected test ran. No model, APK, phone or fresh qualification was involved.

### Real-source importer integration and registry comparison

At clean source `ca46d073116911944265c6747a3da82c70d8bb0c`, a temporary
checkout used Python 3.12.14 and the hash-locked `tools/morphology/requirements.lock`.
The three pinned Wikimedia RU Parquet shards were downloaded into that checkout;
the importer checked each against its original manifest. The v2 corpus came
from its tracked historical files, while v3 and v4 came through the verified
archive fallback. An isolated minimal base ledger was used, and the real
Pymorphy dictionary processed all 10,200 RU rows. There were no model calls.

Two independent importer invocations both exited 0 and produced byte-identical
ledger and receipt files. Per version, rows resolved by the dictionary were
3,229/3,400 for v2, 3,178/3,400 for v3, and 3,139/3,400 for v4; the remaining
171, 222 and 261 row identities were retained as unresolved. The generated
context-key and family-key sets for each of the six entries were compared with
the corresponding current permanent lexical-ledger entries: each set matched
exactly, with no missing or additional keys. The integration used a minimal base
ledger and did not replace or regenerate the user's permanent ledger.

The generated ledger SHA-256 was
`5d2cfd078450bab90610a56d26cc93cf00911d21eedbb9e9f9d8e01b458b44dc`;
the receipt SHA-256 was
`35c8c0efeef94ee128eadbfcc16165af0399e6485c5c7c8ddae51e6dc0cc8041`.
A separate negative probe changed one byte in the disposable v2 source: the
importer exited 1 with `EARLY_RU_PUBLIC_SOURCE` and created no output. The byte
was restored and the original file hash rechecked. The temporary checkout,
downloads, outputs and Python environment were then removed.

This establishes local importer equivalence for these inputs and dictionary,
not complete dictionary-family coverage, independent holdout freshness,
per-row publication rights, historical model-score parity, or recovery of
available-v6. The existing ledger's broader missing axes remain unchanged.

### Punctuation and protected-control importer integration

The historical control importer now uses the same retained v3/v4 archives when
its corresponding old component files are entirely absent. If any expected
legacy file exists, the full component set must be present, regular and valid;
partial or altered input fails rather than silently falling back. The v2 path
remains the original tracked corpus. The importer verifies the archive checker
and binds the archive and catalog bytes in the new receipt; the original frozen
selector and source-lock checks remain in force.

With actual retained sources, the punctuation importer processed 1,200 rows per
version and the protected-token importer 1,800 per version. Two independent
runs for each kind produced byte-identical temporary ledgers and receipts. All
18 generated language/version/kind entries had the same row counts and exact
control keys as their existing counterparts in the current registry. The
punctuation ledger SHA-256 was
`43a8c702cbba41323d39a7ed966b900f84831d0eda8b8e7292c11a4eba06e615`; the
protected ledger SHA-256 was
`dab1c54a4d41f2099d660bfeb00f9cf29d00deeede7f5a384b3ce4a4437e4b16`.
Both v3/v4 inputs used `verified-archive` and v2 used `historical-files`.

Sixty-eight tests passed across the control and RU importers, archive and v6
checks, early source/punctuation recovery, both registries and the new unknown
surface registration. The control tests exercise real corpus reconstruction,
partial inputs, altered original components, corrupted archives and unsafe
member names. The first test invocation from the repository root failed to
import the module; rerunning from its tools directory passed. The stdlib
inventory and early-unknown registration checks passed. No current registry
was modified by these import runs; their temporary outputs were removed.

These are disclosed historical examples, not fresh qualification. They do not
establish complete source attribution, all historical families, model parity,
available-v6 recovery, hosted CI or Fold behavior.
