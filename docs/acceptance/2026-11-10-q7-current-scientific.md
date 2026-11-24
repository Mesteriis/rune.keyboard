# Q7: current scientific and backend checks after source quarantine

At `d042b1268f006cf9833ad0f64dfa652908a176bd`, the scientific profile ran in
a disposable clean local Git clone with no initial root `build/` and the pinned
llama.cpp source checkout. Two disposable Python 3.12.14 environments separated
the scientific and MLX dependency versions. `uv` installed the pinned project
requirements; the Pymorphy dependency closure used `--require-hashes` and
binary wheels. The scientific and MLX requirement files otherwise pin versions
but do not hash every wheel or transitive dependency. This is not independent
decoder or supply-chain attestation.

The Pymorphy backend gate passed all **6 tests**, with zero skips. Historical
data, source and model-fixture tests passed **7, 5 and 10 tests** respectively;
the synthetic word-ranking label suite passed **3 tests**. Their fixture
installation commands all completed before the inventory run. The scientific
inventory exited zero: **30 modules, 123 tests, zero failures or errors, one
skip**. The skipped case was
`test_word_ranking.WordRankingTests.test_mlx_loss_parity_initialization_and_finite_gradient`
because MLX was unavailable in that environment.

The separate pinned MLX backend gate then passed **7 CPU tests**, zero failures
and zero skips, including that exact skipped case. This does not change the
scientific profile's recorded skip; it supplies separate evidence on the
required backend. Neither gate evaluated the keyboard on a phone or qualified
a new model.

Original machine-readable receipts, with relative paths and no local home or
temporary paths, are retained:

- [Scientific profile](2026-11-10-q7-current-scientific-evidence.json), SHA-256
  `6d3d8843e5ff6f4107181c9802320f94c004f706c11223d213328fca81192f6c`.
- [Pymorphy gate](2026-11-10-q7-current-pymorphy-evidence.json), SHA-256
  `50f7122f1d700905706e9578fbaff2672bbe39dc5ca1249f949fa1d7fbf23d18`.
- [MLX gate](2026-11-10-q7-current-mlx-evidence.json), SHA-256
  `4f7020adb937cda4ae3979721a19fef89f35f5e3905a001ce511022298f50ee3`.

The local tracked checkout in the disposable clone was clean after the run.
The clone, two environments, task-specific package cache, restored build
fixtures and raw logs were removed. This was macOS ARM64 using `uv`, not the
hosted workflow on GitHub or an exact Linux CI run. Hosted CI, Android and the
remaining review qualification requirements remain open.

## Follow-up after historical corpus registration

Clean local clones at `b84ac23e` ran the scientific profile and the CPU MLX
gate with Python 3.12.14 and the repository's pinned requirements. The
inventory check and all three historical fixture installation commands exited
zero. The fixture and synthetic-label suites passed 25 tests, and the Pymorphy
gate passed six tests. The scientific profile exited zero with 30 modules and
123 reported tests, including one skip. It recorded zero failures, errors,
timeouts or missing receipts. The separate MLX CPU gate exited zero with seven
passing tests and no skips. It explicitly ran the loss parity, initialization
and finite-gradient case.

Both disposable clones, environments and task-specific dependency caches were
removed. Hosted workflow and physical-device acceptance remain pending.
