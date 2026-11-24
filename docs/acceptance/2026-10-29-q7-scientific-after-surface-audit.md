# Q7 scientific and backend checks after Q6 surface audit

At source commit `dfcc4bf4`, the isolated scientific profile completed all 23
modules: 79 unittest cases, no failures/errors, one MLX-environment skip. Its
receipt SHA-256 is `1f3619db6eee739a26d14cf78ad3b1041143c8018a4ef61171e5d403f39164f0`.

The separate required backend gates ran in their existing local environments:
MLX CPU passed all seven original cases without skips (including the case skipped
by the scientific profile); live Pymorphy passed five cases without skips.
Their receipts are respectively
`ed2795ba20b1dd59709e757eebf6a421bb1f46fc52594ee491471ad615c10751` and
`ee429e8922204b4f1f23e08d2634e524e2e155e6e75ebe13d92ae5a1a75cd3d5`.
Raw results are retained under ignored `build/q7-current-*-20261029/`.

These local checks do not establish hosted CI, Android API 26 success or fresh
independent corpus/model qualification.
