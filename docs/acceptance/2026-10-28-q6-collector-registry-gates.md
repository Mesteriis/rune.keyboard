# Q6 legacy collector registry gates

Current v7–v12 spelling collector commands and the joint follow-up collector
could previously publish an independent-looking holdout using only supplied
ignored exclusion corpora. They now consult both permanent registries before
reading corpus inputs or importing the optional Parquet runtime. Incomplete
coverage raises `NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE`, with no output.

The final selected rows are also routed through the shared new-family
preparation gate before any output is created. Registry drift is checked against
the initial snapshots. Missing source/identity fields cannot be synthesized or
skipped to obtain approval. Current coverage remains incomplete, so this work
does not establish a successful new independent collection.

The explicit `--historical-reproduction` option retains disclosed historical
collection. Its manifest and CLI summary identify
`scope=historical-disclosed-regression` and `independentQualification=False`;
the manifest also declares `newUnseenHoldout=False` and binds the current guard
sources. Original bytes of all eight changed collector/helper files are retained
by exact SHA-256 in the frozen source archive. The seven new archive files plus
the existing joint follow-up source preserve historical identities. The
historical integrity test now checks the original archived bytes and path,
rather than requiring the maintained collector to retain its old implementation.

Actual checks:

- All seven CLI entry points refuse current incomplete coverage before reading
  intentionally absent inputs; none creates output.
- Six focused tests pass on Python 3.12 and 3.14, including the real CLI refusals,
  explicit historical scope, actual registry row overlap and row parity with
  three original archived builders on four deterministic fixture rows each.
- The first broad run found the stale current-versus-historical source assertion;
  the corrected full run passes all 113 stdlib modules / 598 tests, with zero
  failures, errors or skips.

See the [source/evidence receipt](2026-10-28-q6-collector-registry-gates-evidence.json).
Full natural historical corpora were not regenerated in this slice. Other
historical builders still require inventory; canonical-family/history gaps,
independent qualification and the full Q6 card remain open. No APK or model
behavior changes.

## Source-bound future v7–v12 rows

The shared maintained spelling builder previously discarded Wikipedia article
IDs and source segments. Its final two-registry preflight therefore lacked the
article, sentence, source-context and canonical-family evidence needed for a
new proposal. In the nonhistorical path, each selected candidate is now tied
to a unique source occurrence and whole token, its original article, segment
hash and source-context hash. All pinned dictionary analyses are retained;
unknown or ambiguously mapped candidates are excluded. Selection skips
overlapping canonical families across typo and control cohorts. The source,
frequency, exclusion files, selector helpers and dictionary receipt are
checked for drift before output and bound in the manifest.

This does not make the registries complete: the actual entry point still
refuses current incomplete coverage before collection. A synthetic preparation
test substitutes that initial guard, uses the real joint preflight on fixture
registries and confirms refusal for known article/family overlap and incomplete
coverage. It also verifies that source, exclusion and dictionary drift prevent
output. A separate two-row probe used a real Parquet fixture and pinned
Pymorphy dictionary, but substituted the initial guard and used fixture
registries; it reached the real preflight with no row-identity errors and was
blocked by coverage. Neither probe produces an independent holdout or qualifies
a model.

Historical reproduction does not attach new fields or change selection. A
700-row synthetic comparison against the previous builder was byte-identical
(SHA-256 `6c857015a4bc0d9a23ca05f0e04480223cf1d3a7576cd977ad91a4cd776fe7c2`);
this is not a full historical-corpus replay. The focused selector suite and
historical wrapper tests passed in a staged archive without `build/`; both
isolated historical boundary and suspended-retrieval checks passed. Temporary
archives, fixture data and Python dependencies were removed. Hosted CI, full
historical provenance and independent qualification remain open.
