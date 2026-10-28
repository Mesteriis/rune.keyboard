# Q2: compact training and freezing source preservation

This slice follows `2d46552`. It versions fifteen existing public experiment
source/test/policy files without changing their original bytes: abstaining and
augmented rankers, margin refreeze, rare-word extraction/packing, compact product
and calibration evaluators, their seven test modules and the original cascade
policy. The already-versioned revised policy remains unchanged.

The augmented trainer SHA-256 exactly matches selected.scriptSha256 in packaged
experiment provenance (`653c6bfe61f448d33f6a3672cffa4f296ff9e1632d61b845a0d80870bf67d384`).
The packer exactly matches rare-word-manifest.json
(`c9d1b614da298140e59a0755019b7df2dba32c47ca9991b87f87caa842330656`).
The packaged provenance path gate now checks these two explicit source bindings,
as well as its original path/script/policy checks. Twelve gate regressions pass
on Python 3.12.14 and 3.14.6; the original eight provenance files plus the named
rare-word manifest are inspected. Missing metadata schema is checked separately
by the existing data-policy gate.

All 27 tests across the seven retained modules pass using the existing host
environment with NumPy 2.2.6 and CatBoost 1.2.8. All seven --help entry points
exit successfully without training or packaging. Seven inventory/runner tests
pass, and the exact tracked inventory validates at 95 stdlib / 14 scientific
modules. Six retained experiment test modules are assigned to those profiles;
the pipeline evaluator test is invoked explicitly in the stdlib CI job.
Exact source hashes and commands/exit codes are in the adjacent evidence JSON.

The compact controls tested include explicit original-word abstention, rejected
rows excluded from dev, public membership candidate augmentation, zero-regret
margin refinement, singleton generation completeness, promotion refusal after
wrong/control changes, unchanged legacy selections, and deterministic public
front-coded packing. These bounded tests do not prove end-to-end retraining,
transitive input closure, current product quality or fresh holdout independence.
Historical scripts remain historical implementations; no new training/promotion
was performed. Q2 README-command closure and Q6 provenance gaps remain open.

Only the new source-status paragraph is staged in the experiment README; its
older pending owner additions remain unchanged and uncommitted. No product
Kotlin, asset, policy bytes or Android install changed in this slice. Hosted CI
has not been run.

## Clean-checkout integration validation

The exact source commit `ddd86b4` passes the isolated versioned runners in the
existing clean validation clone: 95 stdlib modules / 531 tests, no skips;
14 scientific modules / 54 tests, one explicit MLX-environment skip, no failures
or errors. MLX execution belongs to its separately pinned backend job and was
not repeated here. The first scientific attempt failed three modules because
the required historical-data install step had been omitted. Its failure
receipt/logs are retained; after the same verified 15-file / 9,896,304-byte
preparation used in CI, the complete scientific profile passes. No source was
changed to hide these failures.

In that clone the 12 provenance regressions and five pipeline promotion tests
also pass, the exact asset NOTICE/data-policy gate passes, and CI YAML parses.
The clone's tracked tree is clean before and after validation. These local
results do not assert a hosted CI execution or fresh training qualification.
