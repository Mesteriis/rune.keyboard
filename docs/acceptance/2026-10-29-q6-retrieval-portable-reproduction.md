# Q6: portable historical retrieval reproduction

`tools/ci/reproduce_retrieval_with_fixtures.py` runs the maintained retrieval collector in explicit historical-reproduction mode with the isolated, hash-verified public prior fixture workspace. The prior-data readers accept an explicit root instead of relying on machine-local build paths; the normal default remains the project root. Passing a prior root to independent preparation is rejected with `PORTABLE_PRIOR_HISTORICAL_ONLY` before source access. The output records `priorFixtureScope=historical-test-projection-not-original-observations`, `scope=historical-disclosed-regression`, and `independentQualification=false`.

With the pinned public Wikipedia Parquet and frequency list, the command generated 1,800 rows across 341 articles after scanning 12,091 articles. The result was byte-for-byte identical to the retained original historical `test-rows.jsonl`, SHA-256 `cdc09d6b5885e0d6a01757c05b814d7efe97f7aaefb8932287dbaa673811098c`. The original comparison file came from an ignored historical worktree archive; this is a local exact comparison, not independent qualification. Historical prior fixtures are assembled in a temporary directory and removed afterwards.

Run with the pinned scientific environment and fresh output, for example:

```sh
python3 tools/ci/reproduce_retrieval_with_fixtures.py --parquet PATH_TO_PINNED_RU_0007 --frequency PATH_TO_PINNED_RU_50K --output build/retrieval-historical-reproduction
```

The historical fixture and independent-holdout suites passed 24 tests; the original word-ranking data module passed three tests; CI inventory check passed. The historical source and data archive bindings still apply. This command does not reconstruct original observation bytes or authorize fresh qualification; the full Q6 lineage, registries and independent data remain open.
