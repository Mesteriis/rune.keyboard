# Review Q6: recover historical public source identities

Historical v7-v12 receipt. The subsequent [v6 import](2026-10-27-spelling-v6-history.md)
expands the article-overlap totals; counts below retain their original scope.

The six historical spelling corpora v7–v12 now have durable source-article and
source-window exclusions in addition to their original context/target keys.
This completes that recovery slice, **not Q6 or fresh-data qualification**.
No model calls, scoring, threshold changes, APK or device actions participate.

## Recovery and newly discovered overlap

All 10,200 frozen rows were recovered from the original public Wikipedia
Parquet shards, verified against each original manifest's revision, byte count
and SHA-256. Recovery retained 10,342 matching occurrences across 9,505 articles:

| Corpus | Frozen rows recovered | Occurrences | Articles |
| --- | ---: | ---: | ---: |
| v7 | 1,700 | 1,729 | 1,569 |
| v8 | 1,700 | 1,720 | 1,562 |
| v9 | 1,700 | 1,717 | 1,576 |
| v10 | 1,700 | 1,711 | 1,583 |
| v11 | 1,700 | 1,734 | 1,610 |
| v12 | 1,700 | 1,731 | 1,605 |

The recovered article set intersects **97 current v6 calibration articles and
115 reserved v6 holdout articles**. The existing corpora are therefore not
article-independent of historical spelling evaluation. The ledger records this
as `historicalArticleOverlap`; the existing rows, labels and scores are unchanged.
Reserved means unscored, not certified fresh. Earlier calibration/holdout
separation between those two parts does not establish separation from history.
New qualification must use source identities excluded by the completed registry;
no post-score filtering here is presented as fresh qualification.

## Source preservation and failure behavior

The original selector omits article ID from `selectionHash`. Choosing the first
matching article would silently lose exclusions, so all matching articles and
occurrences are retained. The scanner reconstructs each original selection and
requires exact parity with the original selector. Correct-control targets use
their original typed word; no replacement labels are inferred.

Two exact historical generator versions are archived under
`tools/typing_experiments/frozen_sources/`, with hashes
`2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65`
and `ed9928d64d80911c0182e03446d710a60abb990cb5fb1cff30730443db773225`.
The scanner checks bytes before importing only the required selector helpers.
It preserves the later mixed-script eligibility guard. The original mutable
working generator and unrelated changes are untouched. Relocated archives are
not supported standalone corpus-build entry points.

Source-window identities use the current right-context projection: a 256-character
prefix input bounded to 256 UTF-8 bytes, and a 128-character suffix, normalized
by the existing source-hash helper. These are window hashes, not full-sentence
hashes. Article exclusions cover every sentence of each recovered source article.

The merge checks original input and recovery hashes, requires all original row
IDs and selection hashes, unions added keys and preserves every existing key
and source binding. Incomplete recovery, changed bindings, unsupported generator
bytes and selector divergence fail explicitly. Rebuilding uses the original
bootstrap ledger explicitly, avoiding a dependency on earlier recovery outputs.
Commands and remaining limitations are in
[HOLDOUT_LEDGER.md](../../tools/typing_experiments/HOLDOUT_LEDGER.md).

## Validation and limits

The accompanying evidence receipt binds the final scans, inputs, ledger and
checks. Recovery was repeated after adding the explicit bootstrap option; all
six identity files matched the first scan byte for byte. The CI checks include
28 dependency-free tests: 13 ledger/snapshot, four normalization and 11 recovery/
merge tests. They also pass in an isolated source-only directory without ignored
build inputs, PyArrow, morphology libraries, Java, a model or a phone. Both a
current public article and a recovered historical article remain blocked there.
Schema validation still reports incomplete freshness coverage.

Canonical historical families remain unresolved; legacy normalization is not a
canonical lemma. Other public histories, remaining generator dependencies and
new-builder integration are still pending. Archived selector bytes do not prove
full historical training/toolchain reproducibility. No full JVM suite, Android
build, remote CI execution, Fold acceptance or runtime improvement is claimed.
