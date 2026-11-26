# Q7: current scientific profile and captured source recovery

A clean temporary clone of `b2f99855` with the pinned llama.cpp submodule,
Python 3.12.14 and the CI scientific dependencies first ran the scientific
profile. It failed two of 24 modules (89 tests, two errors and one MLX skip).
The word-ranking and retrieval evaluation drivers both failed with
`CAPTURE_SOURCE_IDENTITY`: their already recorded JVM captures refer to three
source versions that had since changed in the product tree. This failure is not
a passing result. Its receipt SHA-256 was
`3373579272801b0978ee48cd0279ac439ac1c7478ed5e0833f7038314487b7cb`.

The original bytes for `AutoCorrectionAdmissionGuard.kt`,
`ContextualCorrectionPolicy.kt` and `JointCorrectionPolicy.kt` were recovered
from the Git revisions documented in the [archive notice](../../tools/ci/fixtures/captured-sources/README.md).
Each byte sequence matches the SHA-256 recorded in both capture manifests. The
reader accepts only explicit original path/digest pairs and rechecks the
archive hash; it still refuses unexpected paths, symlinks and altered bytes.
An added regression resolves every bound source in both captures. These
snapshots are historical evidence and do not replace or execute product code.

In a new isolated source copy with the fix applied, both previously failing
real numerical driver tests passed. The complete scientific profile then
passed 24 modules: 90 tests reported, no failures or errors, and one skipped
MLX test. Its receipt SHA-256 was
`b8d98783dc17337248da6865eb8b83d4be32f5a350fbbba5d26a97e7dfd21d04`.
The pinned Pymorphy backend gate also passed five real-dictionary tests with no
skips. Historical public data and model fixtures were verified before this
profile ran.

MLX uses a separate pinned NumPy environment. Its CPU backend gate ran in a
separate temporary source copy and passed seven tests with no skips, including
the original MLX parity/finite-gradient test skipped in the scientific
profile. Its receipt SHA-256 was
`ed2795ba20b1dd59709e757eebf6a421bb1f46fc52594ee491471ad615c10751`.
The scientific skip remains a skip in its own receipt; the separate gate is
additional evidence, not a rewrite of that result.

All temporary clones, isolated environments, installed dependencies and
outputs were removed. These are local tests on disclosed fixtures, not hosted
CI, a device result, independent data qualification or proof that Q6/Q7 is
complete. No product model or packaged assets were changed.

## Current-source repeat

At `1eb66812`, a clean temporary checkout with the pinned native submodule and
Python 3.12.14 used separate disposable scientific and MLX environments. The
historical public-data and model fixture checks passed. The scientific profile
completed 24 modules and 90 tests with zero failures, errors, timeouts or
missing receipts; one MLX-dependent test was skipped because the scientific
environment does not include MLX. The separate pinned MLX CPU backend gate
passed all seven required tests without skips, including that same parity and
finite-gradient case. The pinned Pymorphy backend gate passed all five tests
without skips. Dependency installation, runner logs and receipts remain
locally in `build/ci-editing-investigation/q7-current-scientific-clean`.

The temporary checkout, both environments and restored build fixtures were
removed. These checks do not establish hosted CI, a fresh independent corpus,
model qualification or physical-device behavior.

## Repeat after Taiga and neighbor exclusions

At clean source `b66b699055872da1446036c3a42b83195a99a97f`, an isolated
Python 3.12.14 checkout initialized the pinned native submodule, installed the
CI scientific requirements and hash-locked Pymorphy requirements, and verified
the retained public data and historical model/source fixtures. The scientific
inventory passed all 24 modules: 90 tests, zero failures/errors, timeouts or
missing receipts, with one MLX-dependent skip.

The live Pymorphy backend gate passed all six required tests without skips,
including the historical neighbor partition-overlap check. A separate pinned
MLX CPU environment passed all seven required backend tests without skips,
including the test skipped in the scientific environment. The latter remains
a skip in the scientific result; the separate MLX pass is additional evidence.
The temporary checkout, downloaded dependencies, restored fixtures and reports
were removed. This local check does not establish hosted CI, physical-device
acceptance or independent data qualification.

## Repeat after Wiktionary exclusions

At `f0679f67fa08b0b3b85c322c0fd180d3937dd80d`, a clean temporary clone with
the pinned llama.cpp submodule and no initial root `build/` used Python
3.12.14 and the CI scientific and hash-locked morphology requirements. The
historical data, source and model fixture tests and verifiers all exited zero,
as did the Pymorphy backend gate. The scientific profile reported 24 modules and
90 tests: zero failed modules, timeouts, missing receipts, failures, errors,
expected failures or unexpected successes; one test was skipped. The skip's
identity was not retained by this invocation. The receipt SHA-256 was
`02134bcf6ed509331b5fe5c9059e792b0119158f1115ccf8496213d0d902dcd3`.

The tracked checkout remained clean; the temporary clone, environment,
restored fixtures and output were removed. The MLX backend was not separately
run at this revision. This local run does not establish hosted CI, independent
qualification or physical-device acceptance.

At `1192a9bf353fd6d14015f28f12e9f22daf7c243e`, a separate clean temporary
checkout ran the CI MLX CPU gate with Python 3.12.14 and the pinned neural
requirements. All seven required tests passed without skips, including the MLX
loss-parity and finite-gradient case. The receipt SHA-256 was
`4f7020adb937cda4ae3979721a19fef89f35f5e3905a001ce511022298f50ee3`.
The checkout remained clean and the temporary environment, source and output
were removed. This is a separate run; it does not change the scientific
profile's recorded skip or establish hosted execution.
