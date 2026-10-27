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
identity. In particular, it does not recover the different missing role-feature
hash in the v4 **corpus** manifest or the missing left-sequence-v1 feature hash.
The available source referenced by a later training plan cannot replace either
missing historical version. Existing family/context exclusions remain in
`../holdout-ledger.json`; no new independent examples or training are claimed.
