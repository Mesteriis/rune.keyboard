# Q6: preserve early RU spelling components and recover deleted generators

Historical component receipt. Article/window identities were subsequently
[recovered separately](2026-10-27-early-ru-source-recovery.md).

Imported RU spelling components from qualification-v2 and compact-v3/v4:
3,400 rows and distinct target/context identities per component, 10,200 total.
Each exact manifest, RU row-file hash, public RU Parquet hash and archived
original generator hash is verified. Personal-message exclusion and historical
frozen-before-scoring flags are checked. Existing entries/keys/bindings, spelling
article-overlap disclosure and incomplete coverage are unchanged.

This is explicitly a component import. Article/source-window recovery remains
pending for these rows. Punctuation and protected-token components, EN and ES
are not imported. Current article and family namespaces are RU-specific; using
foreign Wikipedia numeric IDs without a language namespace would be ambiguous.
Other language/task rows are rejected by this importer rather than mixed in.

Canonical family exclusions are generated only from the pinned dictionary's
supported target analyses. Each component adds a historical family addendum;
171/222/261 respective target rows remain unresolved, 654 total. No legacy
surface-family strings are relabeled as canonical lemmas. Correct controls use
their original typed word; typo labels and source rows are untouched.

The deleted qualification-v3 and v4 generator files were recovered from local
Git objects and preserved byte for byte at original manifest SHA-256 values:

- v3: `60cb1cdf671dcc0781d47225d225eebc178392f7b616a7ae77d084e4906126a7`.
- v4: `9615bc8033760257bc384ece09d67f6b92e0b7541e144ea6ec746a2f4cc06de4`.

The evidence records source commits. Tests check all v2/v3/v4 archive hashes and
syntax without executing their imports. The missing old evaluation/helper/
source-lock/runtime bindings remain a separate provenance task. Archived code
is not a supported relocated entry point or evidence of a full corpus rebuild.

The first extraction attempt failed because the local source files were in
version-specific cache directories rather than the assumed shared cache. The
paths were located and corrected; the final run verified all source hashes.
No row or manifest was changed to bypass that failure.

Five importer tests cover correct/typo context identity, language/task scope,
empty/duplicate/missing-label failures, unknown legacy family names and archive
bytes. All 63 registry/recovery/import/restoration/audit tests pass in a source-only
directory without build inputs, models, PyArrow or morphology packages. A new
durable early-qualification context probe works without original data. CI
includes these unit checks; no remote CI execution is claimed.

Across the explicitly imported spelling/ranker/joint histories there are now
74,416 rows, including the previously classified 5,385 protected controls and
1,402 unresolved lexical target rows (not necessarily unique words). Article,
context and family counts measure different scopes and must not be conflated.
The existing family-audit receipt covers its earlier bound corpus set; this
component receipt adds the 654 later rows explicitly.

Q6 remains open for the missing components/history, unresolved dictionary words,
source-identity recovery, dependent source/runtime archival and versioned-builder
integration. No model fitting, threshold change, APK or Fold action.
