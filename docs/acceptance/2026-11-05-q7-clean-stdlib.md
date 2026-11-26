# Q7: standard-library tests in a clean Git checkout

At source commit `aa1de646`, a shared local Git clone was checked out without
an existing root `build/`. The standard-library inventory runner wrote its
results outside that checkout. It completed with exit code 0: 176 modules,
866 tests, zero failures, errors, timeouts or skips. The complete original
runner receipt is retained as `2026-11-05-q7-clean-stdlib-evidence.json`, with
SHA-256 `8521c25b8e9b23b8d7f97af30a16d93b883cb1569ebfd46c1ab8c15ec66e6234`.
The disposable clone, runner logs and intermediate files were removed after
collection. This covers the standard-library profile only; it does not imply
that scientific, Android, native, device or hosted checks passed in this run.

The current and historical product-replay fixtures and frozen projections were
validated from tracked files without the ignored build directory. The actual
CI replay command then ran from a separate clean clone on the current
controller: its two passes were deterministic and matched both frozen
projections, covering 2,160 and 12,000 rows respectively. The command exited
zero. The current and historical projection SHA-256 values were
`e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea` and
`b7b49f16aed912ea4c80d811c834f059dc1ac47f6b655e9798923651ec47f512`;
their run receipt SHA-256 values were
`15bfe7de035adaa46062f85759f05aebe26c5a2be30812a5c074cf7c423ed824` and
`8afd5242252a6395289842adafd78dff1f9d867c712502210189b6abc3664dd7`.
Replay intermediates, raw logs and the temporary clone were removed. This
model-free disclosed replay is not fresh-holdout quality or device evidence.

The latest hosted GitHub CI run observed on 2026-11-05 was a failed push run
for `2c1ff9751e74ef11241e0a6e5e3557ff22353724` from 2026-10-28. It predates
these local changes and cannot establish their hosted status. Q7 remains open
for current hosted CI and any other outstanding acceptance requirements.

A later run at source commit `23923ba2` used an ephemeral Ubuntu 24.04
x86_64 container under emulation on an arm64 Mac, with Python 3.12.3 and a
clean shallow source checkout including the pinned llama.cpp submodule. The
same inventory check and standard-library profile passed: 178 modules, 879
tests and no failing modules. This profile is not the replay job, a
scientific backend check, or a hosted CI run. The temporary checkout,
container, task-created image and runner outputs were removed afterwards.
The earlier claim of zero skips was withdrawn: the summary read `skips`
instead of the receipt's `skipped` field, and the temporary receipt was removed.

At source commit `d49d05e8`, the actual multilingual CI replay was attempted
on Ubuntu 24.04 x86_64 under emulation, using OpenJDK 17.0.20.1. The Gradle
toolchain task verified all five pinned Kotlin JARs. The current 2,160-row
corpus was deterministic across its two passes but failed comparison with the
macOS-captured baseline: 123 rows differed. A second isolated run reproduced
the same row count. Its 462 differing fields were all floating-point values in
`jointModelScores`, `rescueModelScores` or `compactScores`, with maximum absolute
difference `2.220446049250313e-16`. The comparison reported no other differing
paths, including product decisions, candidates and Undo. Neither run reached the
historical replay because the wrapper stops on the first failed baseline. This
does not establish whether architecture, Java build, or another environment
difference caused the numeric drift. The strict gate remains unchanged and
Linux replay is not considered passed. Temporary checkouts, images and outputs
were removed.

At source commit `a2dd48dc`, an additional Linux x86_64 emulation check ran
the current 2,160-row input through six independent JVM processes using the
same controller, compiler dependencies, settings and real clock as the CI
replay. All six complete projections matched the first exactly, including
model scores; this check compared the passes with one another and did not
perform a new baseline comparison. It did not reproduce or explain the earlier
intermittent nondeterminism. The temporary checkout, observations and
task-created container image were removed. Hosted CI and Android-device
acceptance remain separate.

The baseline comparison now accepts an absolute difference up to
`4.440892098500626e-16` only for the numeric entries of `jointModelScores`,
`rescueModelScores`, and `compactScores`' `combinedScore`/`contextScore`.
Every other field, including decisions, candidate order, text and Undo, is
compared exactly. The two actual passes are still compared exactly, including
scores. The comparison retains both projection hashes and counts every
tolerated score difference; the CI wrapper checks those hashes and row counts
instead of claiming the platform-specific candidate hash equals the baseline.

On an isolated Ubuntu x86_64 run under emulation with OpenJDK 17.0.20.1, both
actual CI replay profiles passed: 2,160 and 12,000 rows, respectively. Their
two passes matched exactly; baseline comparison found zero behavioral
differences and reported 462 and 2,296 tolerated score values. The same actual
CI command passed both profiles on macOS arm64 with zero tolerated differences.
The Linux run used the pinned Android SDK stub and five hash-verified Kotlin
JARs; an earlier Linux preparation separately passed the Gradle toolchain task.
An intervening Linux attempt reported `REPLAY_NONDETERMINISTIC` on the first
profile and its detailed diff was not retained; a subsequent full run passed,
so that intermittent failure remains unexplained. These checks are not hosted
CI, Android-device evidence or independent model qualification. All task-owned
images, checkouts and replay outputs were removed.

At source `24f5214c`, the standard-library inventory was run again in a
disposable Git checkout with no initial root `build/`; the pinned llama.cpp
source was exported from the locally available Git object at the recorded
submodule commit. It completed successfully: 180 modules, 887 tests, zero
failures, errors, timeouts or skips. The temporary runner receipt SHA-256 was
`9a59ff42c07ab3523aaba4447d693f980066a46548e34c2536b2fe5bac510aaa`;
the checkout and receipt were removed. This run precedes the later apostrophe
diagnostic fix, whose focused tests are documented separately. It does not
establish scientific, Android, Fold or hosted CI acceptance.

At source `c2a8684b`, after correcting the missing dependencies in the
isolated registry test, the complete standard-library inventory passed in a
fresh temporary Git checkout with no initial root `build/`: 181 modules,
894 tests, no failed modules, timeouts, missing receipts, failures, errors,
expected failures, unexpected successes or skips. The pinned llama.cpp source
was exported from the locally available Git object. The temporary receipt's
SHA-256 was `9b97c8bd06adb2fb9a2c7559c4d0ab62e6a22e792efea71ff485fb280f866dce`;
the checkout and receipt were removed. This is not a scientific-backend,
Android, physical-device or hosted-CI result.
