# Q6: exact restoration of the missing follow-up v1 generator

Restored `prepare_joint_followup.py` at the exact original SHA-256
`964b7c6505cf5b3a0d766563e29ff750b3db70638302267db9c0318ffa05aef8`
recorded by the frozen follow-up corpus manifest. This is byte equality against
that historical hash, not a behaviorally similar replacement.

The v3 source was already preserved at SHA-256
`b9cc4859e08021f851711bcabff12d329d6219312d3d988157b9716a1af574b6`.
Reversing its article and extra-corpus exclusion additions produces exactly the
v1 bytes. `restore_frozen_followup.py` reproduces this transformation, rejecting
any changed source hash or unexpected output hash. Its output is exclusive.
Both versions remain archived; the current mutable builder is untouched.

Three regression tests check exact restoration/archived equality, syntax without
executing imports, tampered input rejection and the archive's original-path
binding. All 48 registry/recovery/import/restoration tests pass in a source-only
directory without build inputs or morphology packages; CI includes these checks.

The restored source still requires original helpers, native morphology assets,
frequency data, public sources and runtime bindings. This is not a complete
historical corpus rebuild, qualification, model evaluation or Android change.
Other Q6 provenance and exclusion gaps remain open.
