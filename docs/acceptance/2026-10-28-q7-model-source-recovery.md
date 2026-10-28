# Q6/Q7: historical model source recovery and numeric parity

All 71 project source versions directly declared by the original baseline and
refinement candidate-export receipts are available again. Twenty-nine changed
versions were recovered by matching their original SHA-256 to Git blobs; the
exact source bytes, original paths and blob IDs are now versioned under
`tools/ci/historical-model-sources-v1`. Forty-one unchanged versions remain
hash-bound to repository files; one public all-rows input is reconstructed from
the three original refinement row partitions. Archived code is never executed
by the auditor.

The actual original receipts also matched their pins, and all 12 advertised
export payloads passed their original hashes. Both direct source-reference maps
matched the recovered index. External compiler/JDK/Android runtime references
remain an explicit inventory, not verified execution evidence. This is direct
source identity recovery, not transitive closure or candidate reproduction.

## Actual model math checks

The original CatBoost models were loaded with pinned CatBoost 1.2.8/NumPy 2.2.6.
Candidate observations and public rows were checked against their original
export hashes, indices and row identities. The baseline retained the original
public-row filter and template split; refinement retained partition manifests,
all source rows, 4,942 nonempty training groups and exact parent-export records.

| Frozen model comparison | Full vectors | Maximum absolute error |
| --- | ---: | ---: |
| Baseline CatBoost vs original RET1 Python decoder | 5,699 | 5.318170082091456e-08 |
| Refinement CatBoost vs original RET2 Python decoder | 2,856 | 2.375358487682888e-08 |

Both pass the existing 1e-5 tolerance. Baseline input comprises all 3,400 public
rows selected by the original loader; refinement covers all 984 nonempty dev
groups. These are original full reference models, not new tiny replacements.
This does not establish Kotlin parity, new candidate-generation execution,
neural parity, model quality or admission qualification. Vectors were recomputed
with current tracked Python feature functions over the original observations;
this does not establish feature-function identity with historical training.

The reproducible command is:

```sh
python tools/ci/check_historical_numeric_parity.py --historical-build ORIGINAL_BUILD --output FRESH_REPORT.json
```

It pins both reference CBMs and both decoded exports and uses explicit integrity
checks. A one-byte CBM mutation was rejected with
`HISTORICAL_REFERENCE_IDENTITY` before prediction, including with Python `-O`.
The isolated mutant was removed; original archive files were not changed.

## Word-ranking corpus and permanent exclusions

The original word-ranking producer still matches its manifest's source hash.
It ran against the pinned public parquet and vocabulary, using the original
prior-data bindings. All eight advertised files, including manifest
`8a5a11a16543315ff3114bf0034f54b455b5e432828098cf2030f85737c34466`,
reproduced byte for byte. The manifest is now versioned as provenance metadata.
The original row/text payloads remain in local build evidence pending a complete
portable historical fixture bundle.

The durable ledger previously omitted all 4,920 articles consumed by this
corpus's 9,000 rows and text fragments. A new historical-exclusion entry binds
the original manifest, source lock and exact producer and excludes every article.
All 124 previous entries remain byte-for-byte equivalent as parsed records;
global completeness stays false. Canonical families, target contexts and full
source sentences are explicitly missing, not inferred from target spellings.

## Validation and remaining work

- Source auditor passed against original receipts/build and all 29 Git objects.
- A clean tracked checkout with only the bound candidate overlay passed the
  source auditor and 92-module stdlib profile: 518 tests, zero skips/failures.
- All 29 CI infrastructure tests and 23 public-ledger checks passed locally.
  New coverage rejects changed archived bytes, unknown source references and
  removal of the word-corpus exclusions and Git-object option injection; all article keys are checked against
  the original manifest.
- The new direct-source auditor/tests are wired into the scientific CI job.
  No hosted workflow was dispatched. Existing eight scientific modules were
  not rerun in this slice; the preceding historical-data receipt remains their
  execution evidence.
- Exact F-Droid data-policy check and `git diff --check` passed. No new full
  source scan, device cycle, training, push or APK update was performed.

Q7 remains open: three original modules still need portable historical
receipts, exports and reference files. Source bytes and numeric parity are
prerequisites, not replacement tests. MLX, live Pymorphy, full hosted CI and all
other review-card requirements retain their separate outstanding scope.
