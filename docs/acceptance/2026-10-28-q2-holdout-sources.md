# Q2: historical holdout source preservation

This slice follows `cd03349`. It retains fifteen existing source files and nine
associated test modules without changing their bytes: the v6–v12 label-isolated
replay tools, v7/v8 preparers, v9–v12 HoldoutSpec wrappers and both shared
preparation/replay helpers. The base v6 preparer was already retained in the
previous slice. Source hashes are in the adjacent evidence JSON.

The twelve existing tests across those nine modules pass on Python 3.12.14.
All thirteen CLI entry points return successful --help output without producing
corpora or invoking Kotlin/models. The two shared helpers are imported by their
tests and wrappers. Three new cross-version tests pass on Python 3.12.14 and
3.14.6: all six source shard paths/digests/sizes match original public receipt
metadata; every replay rejects a different corpus version; all four shared
export wrappers forward their exact version and explicitly supplied Java path.
No source article content was fetched or scored in these checks.

Raw invocations and output remain in ignored local evidence. Public command
receipts spell the interpreter as python3, identify the actual tested version
and retain hashes of the original command/exit-code receipts, without publishing
machine-local interpreter paths. The exact tracked inventory is now 109 stdlib
and 19 scientific modules; the ten newly retained/new test modules are assigned
to the stdlib profile.

These are **historical disclosed corpora**, regardless of legacy filenames or
scope strings containing fresh/independent. Their presence in Git does not make
them fresh qualification data. Current generation still needs the complete
consumed-data registry, source/runtime bindings and the original selection
implementation; global Q6 closure and source/model replay are not established
by unit tests or --help. The original neighbor corpus-generator snapshot
bf2118a0 remains unrecovered after the bounded history lookup in this slice.

No app source, asset or policy bytes changed and no Android install, model
training or hosted CI job ran. Pending owner README additions remain unchanged;
only the reviewed source-status paragraph is integrated.

Clean-checkout integration: exact source `56a2b89` passes all 109 isolated
stdlib modules / 558 tests, with zero failures, errors or skips. The original
raw receipt remains local; its SHA-256 and exact totals are in the evidence JSON.
Scientific source and dependencies were unchanged by this slice; that profile
was not rerun. The preceding joint/neighbor receipt records its last actual run.
