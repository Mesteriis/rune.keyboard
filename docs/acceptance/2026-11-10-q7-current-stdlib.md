# Q7: current clean standard-library inventory after A4 source quarantine

The tracked stdlib profile was run at commit `f4355668e4963fa70bd79f0fd8c64df590932a60`
in a disposable local shared Git clone with no initial root `build/`. The
pinned llama.cpp submodule was checked out at
`36b10154383b60eb15baac2c7a40d2a5f784faa7` from the local Git object store.
The inventory check found 207 stdlib and 30 scientific modules. Python 3.12.14
ran the actual stdlib inventory runner with output outside the checkout.

The runner exited 0 with **207 modules and 1,005 tests**. Its receipt reports
zero failed or timed-out modules, missing module receipts, failures, errors,
expected failures, unexpected successes and skips. The clone had no tracked
changes after the run. The unmodified runner receipt is retained as
[structured evidence](2026-11-10-q7-current-stdlib-evidence.json); its SHA-256
is `c0604d68cb6653f9f9670a05a9016153de89b6808cdabe8c7efe55c2c90b1955`.
It includes relative test paths and numeric timings, but no local workspace or
user-home path. The clone, build products and raw per-module logs were removed.
Existing owner diagnostic backups were not touched.

This is the local macOS standard-library profile only. It is not the scientific
profile, full Android instrumentation, physical-device acceptance or a hosted
GitHub Actions result. The actual replay run, historical source and model
qualification, and public-release review remain separate. Q7 and the overall
review are not declared complete by this result.

## Registry and workflow checks after historical article attribution

At `3001b212`, the repository's three GitHub Actions workflows passed
`actionlint` 1.7.12 with the local ShellCheck available. The official
Darwin ARM64 release tarball matched its published SHA-256 before the
temporary binary ran. The tarball and binary were removed afterward.
All four historical control registration checks added since the prior
`78ce557b` JVM/replay proof also exited zero. The app, native runtime and
top-level Gradle inputs have no tracked changes between those commits.
The only workflow delta adds the four registry checks.

GitHub Actions still showed a failed push run for `2c1ff975` as the latest
result for this workflow at inspection. The workflow lint is local and
the current source awaits hosted execution.

The same source ran the entire stdlib profile in a temporary local Git clone
on Python 3.12.14 with the pinned llama.cpp submodule. The runner exited zero
after 210 modules and 1,031 tests. It reported zero failures, errors, skips,
timeouts or missing module receipts. The test runner left no tracked changes.
The temporary clone and its raw logs were removed.
