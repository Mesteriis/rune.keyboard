# Q7: integrated local Python CI recheck

At `0aff65dc`, a temporary clean Git clone with the pinned llama.cpp submodule
and no initial root `build/` ran the Python CI checks on Python 3.12.14. The
stdlib profile passed all 198 modules and 970 tests, with no failures, errors,
skips, timeouts or missing receipts. The scientific profile passed all 26
modules and 103 tests, with zero failures, errors, timeouts or missing receipts
and one skip. A skipped test is not a passed test.

The inventory and runner tests, Chrome numeric oracle tests, compact pipeline
tests, disclosed-fixture audit and all seven workflow documentation, privacy,
source and provenance checks and their paired tests returned zero. The
scientific environment installed the pinned requirements and the morphology
closure with hash checking and binary-only dependencies; the live Pymorphy
backend gate passed. Historical data-fixture tests and installation, model
source and fixture tests and verification, word-ranking label tests and model
fixture restoration all returned zero before the scientific profile.

The source clone was tracked-clean after the run, and its temporary source,
outputs and Python environment were removed. This is local evidence on macOS;
it is not a hosted Ubuntu run, MLX backend gate, Android/device acceptance,
source-rights clearance or independent corpus qualification. The aggregate
runner output reported one scientific skip but its individual reason was not
retained in this run.

## MLX backend follow-up

At `777ee46c`, a separate clean source archive and Python 3.12 environments
re-ran the word-ranking tests. With the workflow's scientific requirements and
no MLX package, six of seven tests passed and
`test_mlx_loss_parity_initialization_and_finite_gradient` was skipped with
`MLX environment required`. This repeat demonstrates the skip in that isolated
module; the earlier full profile's individual skip record was not retained, so
its exact identity is not independently recovered.

The separate required MLX backend gate then passed all seven tests with no
skips on CPU, using the exact versions in `requirements-neural.txt` on this
Apple Silicon Mac. This gate checks numeric parity, initialization and finite
gradients; it does not represent GPU, Android, hosted CI or qualification
acceptance. Both temporary environments, output and source archive were removed.
