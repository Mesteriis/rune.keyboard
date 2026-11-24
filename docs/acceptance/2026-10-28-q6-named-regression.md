# Q6 disclosed named regression replay

The pending Russian cases `заьыл → забыл`, `заберай → забирай` and
`зочу → хочу` are retained with their correct-word, mention and email controls.
The complete public set has 56 rows: EN 12, RU 36, ES 8. These are disclosed
spelling examples, not an independent holdout or new training material.

Actual production Kotlin JVM replay with the model unavailable passes all 56
cases: exact final text, unchanged correct/protected controls, exact immediate
Undo, and no missing Original candidate. No phone test or model training was
performed. The runner now enforces every named result separately: a regression
test demonstrates that 100 correct results plus one wrong result can pass the
old 99% aggregate gate but must fail named acceptance.

The first full historical qualification attempt failed with
`GENERAL_LOCAL_MUST_REMAIN_DISABLED` on calibration. Its holdout and named
stages did not run. The historical admission check remains intact. A separate
`--named-only` mode performs no policy selection and makes no qualification
claim. This is a current regression replay, not proof that the historical
finite-only configuration is still applicable.

Checks: 13 unit tests pass on Python 3.12 and 3.14; the actual named JVM run exits
0. Source and private artifact hashes are retained in the
[evidence receipt](2026-10-28-q6-named-regression-evidence.json).
Q6 remains open for durable exposure coverage, missing historical lineage and
independent fresh qualification.
