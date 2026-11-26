# Q7: preserve exact source identities for historical replay captures

The scientific profile failed two bounded word/retrieval replay tests because
three capture-bound source files had changed in the current tree. The same
three mismatches existed at the pre-compaction commit `854323c6`; they were not
caused by the compact registry. Their exact old SHA-256 identities were found in
Git history and retained under `tools/ci/fixtures/captured-sources/` with their
original paths, hashes and revisions documented there. Existing capture files
and their historical source hashes remain unchanged.

Both fixtures now request the exact captured bytes: use the current source when
its digest matches, otherwise use only one of three explicitly authorized
path/digest archives. Unknown identities, path traversal, symlinks and changed
archive bytes fail. The copied source snapshots are still rehashed by the
existing evaluation receipts. These are historical captures; this repair does
not imply the old capture describes current-product behavior or a fresh model
qualification. Current-product replay remains a separate Q7 gate.

The two previously failing tests passed locally. The complete pinned scientific
profile then passed all 23 modules: 79 tests, no failures/errors and one explicit
skip in `test_word_ranking.py`. The archive fallback has separate current-source,
corruption, traversal, unknown-identity and symlink checks. The failed earlier
profile and the successful rerun are retained respectively in
`build/review-q6-compact-scientific-20261029/receipt.json` and
`build/review-q6-compact-scientific-repaired-20261029/receipt.json`. No hosted CI
rerun or release qualification is claimed.
