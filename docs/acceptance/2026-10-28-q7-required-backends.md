# Q7: required MLX and live Pymorphy checks

The optional backend gap now has real local execution evidence and permanent
workflow wiring. Missing packages or skipped mandatory cases cannot pass the
new backend gate. Original word-ranking test assertions are unchanged.

## Actual supported-profile checks

On a task-owned clean tracked checkout at source base 29e84b4 plus the bound
candidate overlay, using isolated Python 3.12.14 environments:

- MLX 0.32.2 / mlx-metal 0.32.2 / NumPy 2.4.6 / PyArrow 25.0.1: all seven
  original WordRankingTests pass on CPU with zero skips. This includes the
  previously skipped loss parity, shipped initialization, finite/nonzero
  gradient and finite-difference check. No optimizer, epoch, model selection or
  persistent training output is run.
- Pymorphy3 2.0.6 / dictionaries 2.4.417150.4580142 / dawg2-python 0.9.0:
  all five live contracts pass with zero skips. These exercise real dictionary
  inflections and ambiguous lemmas, refusal of guesses/unsupported tokens,
  context decisions using the existing ranker, case normalization/cache bounds
  and a content-hashed dictionary/parser receipt.
- All six existing morphology modules also pass, 62 tests, in the new fresh
  hash-locked environment. These are host dictionary/math contracts, not a new
  natural corpus, product quality qualification or Fold test.

The local test host is macOS 27 / ARM64. The workflow targets `macos-26`, which
GitHub lists as an ARM64 standard runner in its
[official reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
The hosted macOS 26 job has not run; it is not relabelled as local evidence.
PyPI's MLX 0.32.2 release publishes Python 3.12 wheels for macOS 14, 15 and 26.
An early inference that the selected macOS 26 wheel was the minimum OS was
incorrect and was corrected. The final gate checks Darwin/ARM64 and imposes no
minimum OS version. Other OS versions were not exercised in this slice.

## Locked dependencies and refusal behavior

A fresh `--require-hashes --only-binary=:all:` morphology install initially
failed because the old lock omitted required transitive setuptools>=68.2.2.
The lock now includes setuptools 84.2.1 and its reviewed wheel SHA-256. The fresh
install then succeeded without bypassing dependency or hash checks. Historical
three-package experiment receipts remain historical; the backend gate records
all four installed versions and the actual dictionary/parser package hashes.

The gate rejects missing/wrong dependencies, missing required case IDs, empty
suites, skipped tests, ordinary/expected failures, unexpected successes and
source/model input drift. Output directories must be fresh. Versions, case IDs,
raw logs and source/model hashes before/after are retained. A real invocation
in the bare stdlib environment returned exit 1 with no tests claimed. Six gate
regressions cover success, skip/failure/expected-failure refusal, missing cases,
wrong versions/platform, missing backend, existing output and changed inputs.

All 41 CI infrastructure tests passed. The exact F-Droid data policy and
`git diff --check` passed. No app source/assets, original historical test bodies,
owner preferences, phone state, corpus exclusions or reference models changed.
The original owner payloads/untracked paths were preserved.

## CI and remaining scope

The Linux scientific job installs the complete hash-locked morphology closure
and requires the live Pymorphy gate. The separate `python-mlx` job installs the
existing pinned neural requirements on `macos-26`, selects CPU and requires all
seven original cases, including the gradient method. Both upload logs/receipts
on failure. The Linux suite keeps its explicit MLX platform skip; the Apple job
is responsible for executing that case.

Actual hosted Ubuntu/macOS workflow execution and the broader review acceptance
remain open. No source push, workflow dispatch, APK update or device operation
was performed in this slice. No independent distribution/build-server result
is claimed.
