# Q6: verify the six early contextual-ranker partitions

Added 23,977 rows from the original word-context corpus, its extra corpus and
context-feature evaluation (calibration/holdout each). Each original manifest/
row hash must match the historical availability-plan exclusion binding, whose
plan hash is already anchored in the registered natural-context pool. The public
Parquet hashes are independently pinned by the joint-source import.

Every target word/prefix capture is found in the actual source article. All
matching projected windows are retained, rather than choosing the first match.
Window hashes are projections, not whole sentences. The first capture pass used
a stricter boundary that excluded hyphens; original joint.WORDS code showed that
old selection permits them. Recovery now matches that exact historical rule,
with a regression. This changes no runtime word/admission policy.

Native lemma IDs and ambiguous `form:<surface>` fallbacks are not trusted as
canonical families. Dictionary-only analyses for source/expected lexical targets
cover every row; protected @word controls are validated and not treated as
unknown lemmas. There are no unresolved candidates in this batch. Each partition
therefore stores article/window/context/family keys without missing axes.

All previous entries/keys/bindings/quarantine and incomplete global coverage are
preserved. These partitions add no current v6 calibration/holdout article overlap;
the earlier 122/131 spelling-overlap finding is unchanged. No scoring or fitting
is performed and old corpora are not promoted as fresh evaluation.

All 136 tests pass in an isolated source-only directory without build data,
models, PyArrow or morphology packages. Five new tests cover historical hyphen
captures, all matching windows, canonical versus surface families, protected
mentions, invalid IDs/scope and durable partition snapshots. CI includes these
checks; no remote CI run is claimed. Extraction additionally uses original public
sources and pinned morphology.

The receipt binds the verified source/plan chain, dictionary and checks. Rejected
unmanifested material and owner-authored regression provenance remain separate
inventory questions; full Q6 completion is not claimed. No APK or Fold changes.
