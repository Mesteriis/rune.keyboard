# Declared late-training source archive

Exact source bytes referenced by 17 historical plan/selection receipts for
right-context training v4–v8 and residual v9–v14. The manifest replaces only
machine-specific reference prefixes with repository-relative paths; it retains
each original receipt hash and every declared source hash. Source bytes are
unchanged. Multiple original paths can share the same archived file.

Do not run or import these relocated scripts. Some perform writes or training
at module scope and depend on old models, corpora, runtimes and working paths.

Run `python3 tools/typing_experiments/audit_late_source_closure.py` to verify all
archived bytes and direct references with no historical build directory.
Add `--historical-root .` while original receipts are present to verify their
hashes and normalized reference maps as well. Neither mode executes scripts.

This archive establishes direct declared source identities only. It does not
establish transitive import coverage, feature parity, model execution or model
identity. The distinct role-v4 and left-sequence-v1 corpus feature versions
are tracked in the [frozen source archive](../frozen_sources/manifest.json).
Their recorded hashes are verified by the authored-history auditors. Existing
family/context exclusions are recorded in `../holdout-ledger.json`.
