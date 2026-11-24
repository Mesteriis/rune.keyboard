# Q7 scientific inventory run

The scientific inventory completed with status PASS: 79 tests across 23
modules, zero failures or errors and one explicit skip. The skipped
`test_word_ranking` MLX parity/finite-gradient case requires an MLX environment;
it was not exercised in this run. The receipt SHA-256 is
`39187250eb2d231be14f67370645ad474024785e0257922195a4db618c97190e`.

The run used the existing local scientific virtual environment and started
before later CI-runner and documentation edits; those changes are not tested by
this receipt. The profile does not prove hosted CI, Android behavior, fresh
independent corpus qualification or the skipped MLX case.

The separate required-backend gates were subsequently run on the local macOS
ARM64 host using the previously prepared isolated environments. MLX ran all
seven required word-ranking cases on CPU, including the previously skipped
finite-gradient case, with zero failures, errors or skips (receipt SHA-256
`ed2795ba20b1dd59709e757eebf6a421bb1f46fc52594ee491471ad615c10751`).
The Pymorphy gate ran its five required live dictionary contracts with zero
failures, errors or skips (receipt SHA-256
`ee429e8922204b4f1f23e08d2634e524e2e155e6e75ebe13d92ae5a1a75cd3d5`).
The original scientific-inventory result still contains its explicit skip;
the separate MLX gate supplies the actual CPU execution evidence. Hosted CI
and independent model qualification remain open.
