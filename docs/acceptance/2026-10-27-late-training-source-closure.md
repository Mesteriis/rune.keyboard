# Q6: preserve declared sources for late authored training chains

Preserved the exact bytes behind all 56 source paths declared in 17 historical
plan/selection receipts for authored right-context training v4–v8 and residual
v9–v14. There are 52 distinct source hashes and 276,585 archived bytes. Four
identical source payloads were referenced through more than one original path.
Twenty-eight of the source paths were scripts stored only in ignored build
folders. The archive now survives removal of those folders.

The durable manifest records repository-relative original paths, exact source
hashes, original receipt hashes and each receipt's complete normalized source
map. The audit verifies every archive byte, rejects missing/rebound references
and unreferenced entries, and optionally compares actual historical receipts
and their reference maps. It never imports or executes archived scripts. Every
archived Python file also parses successfully without execution.

These are direct **declared** references. This does not prove complete
transitive imports, feature/vector parity, training execution, model identity
or independent quality. No scores, weights or generated corpora changed. The
later training-v4 plan references an available role-feature version; it does
not recover the different missing version named in the v4 corpus manifest.
The original left-sequence-v1 feature hash also remains unavailable in the
checked current files and Git history. Neither is silently substituted.

Validation: six new regressions pass, including changed archive bytes, stale
receipt hashes, rebound/unused sources, path escape and duplicate normalized
aliases. All 208 source-only registry/preparation tests and both registry schema
checks pass in an isolated directory without historical build data, morphology
packages or models. CI now runs the new source audit and tests; no remote CI
result is claimed. Exact commands, outcomes and identities are adjacent.

The lexical ledger remains at 121 entries and the control ledger at 18. No new
family/context keys were needed for these already registered corpora. The
unsupported-family quarantine, separate 120-example origin gap, disclosed
historical article overlap, remaining provenance and fresh qualification work
keep Q6 open. This step changes no runtime behavior or phone installation.
