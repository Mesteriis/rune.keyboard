# Q7: clean scientific profile and required backends

At source commit `a005f1c7`, the scientific profile was run in a fresh local
Git clone using Python 3.12. The clone began without `build/`; the versioned
historical data archive was verified and installed only inside that disposable
clone. Host dependencies were installed from the local package cache using the
project's pinned scientific requirements and hash-locked morphology closure.
This was macOS ARM64 execution, not the hosted Linux CI job.

The scientific inventory runner exited zero with 23 modules and 79 tests: 78
passed and one MLX parity/gradient test was skipped because this environment
had no MLX backend. The original runner receipt is
`2026-11-05-q7-clean-scientific-evidence.json`, SHA-256
`e6c471ecdf51333817252faa1520668b581b9b5ecdc3f748d86cf24de406820e`.

The separate required-backend gates ran in clean Python 3.12 environments:

- Pymorphy: all five required dictionary tests passed with no skips. Receipt:
  `2026-11-05-q7-clean-pymorphy-evidence.json`, SHA-256
  `8af0281fa8a4dd26c4fe0c0f7e4c9b0d0bf5e9db6d542f2d74a948f422f1f687`.
- MLX on CPU: all seven required tests passed with no skips, including the
  parity/gradient test skipped in the scientific environment. Receipt:
  `2026-11-05-q7-clean-mlx-evidence.json`, SHA-256
  `ed2795ba20b1dd59709e757eebf6a421bb1f46fc52594ee491471ad615c10751`.

The three historical data, source and model-fixture verification modules also
passed 22 tests without skips. The source audit itself did not claim candidate
regeneration, original export verification or external runtime identity. Both
clones, temporary virtual environments, restored build data and raw logs were
removed after their receipts were collected. These local checks do not prove a
current hosted CI result, fresh-data qualification or device acceptance.

At commit `94279248`, the scientific profile also completed in a clean Ubuntu
24.04 x86_64 container under emulation, with Python 3.12.3 and the CI-pinned
dependencies. The Pymorphy backend gate passed; historical fixture modules
passed 7, 5 and 10 tests respectively; the scientific profile reported 23
modules, 79 tests and no failing modules. The skip count cannot be recovered:
the summary mistakenly read `skips` instead of `skipped`, and the temporary
receipt has been removed. In particular, this run does not establish the MLX
case on Linux. The source checkout, restored data, environment and container
image were removed. This is not a hosted CI result or model qualification.

At commit `3763acd6`, the Linux x86_64 scientific profile was repeated with
the corrected aggregate receipt: 23 modules, 79 tests, one skip and no
failures, errors, timeouts, expected failures or unexpected successes. The
skipped test is the MLX-only case in `test_word_ranking.py`, which requires
the Apple MLX environment; Pymorphy passed its separate required-backend gate.
No module lacked a receipt. This run used Ubuntu 24.04 under emulation, Python
3.12 and the pinned dependencies; it is not hosted CI. The temporary source,
restored data, environment, output and task-created image were removed.

At source `65e44991`, the scientific profile was rerun in a clean macOS ARM64
Git checkout with Python 3.12.14 and no initial root `build/`. The pinned direct
scientific requirements and hash-locked morphology dependencies were installed
from the local cache; transitive scientific dependencies were resolved from that
cache. The original public fixture archive was verified and restored only in
the disposable checkout. The runner passed 23 modules and 79 tests, with one
skip and no failed modules, errors, failures, timeouts, missing receipts,
expected failures or unexpected successes. The temporary runner receipt
SHA-256 was `b0ed23a8a388a371bc34046929be9adfd8c15f991bc66a6448d7eca6b9cab661`;
its per-test skip reason was not retained, so this record does not identify it.

The separate required Pymorphy gate passed five tests with no skips (temporary
receipt SHA-256 `03bf78a07570b21a1c5c816cc7b6981dbdabbd9bff1469a56895463a18a52f06`).
In another clean checkout and offline virtual environment, the pinned MLX CPU
gate passed with no skipped tests; its receipt SHA-256 was
`ed2795ba20b1dd59709e757eebf6a421bb1f46fc52594ee491471ad615c10751`.
These separate gates are not a replacement for the scientific run's missing
skip detail. All task-created checkouts, virtual environments, restored data
and receipts were removed. This is not hosted CI or a device qualification.
