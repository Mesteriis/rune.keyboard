# Q6 refinement evaluation receipt

The maintained evaluator now emits a typed receipt for its selected model
bytes, selection, main corpus files, test observations, export receipt/files,
checked generator sources, baseline weights, evaluator sources and both
permanent registries. Input bytes, code and registry snapshots are rechecked
before an exclusive report write. Explicit identity/role checks remain active
with optimized Python; existing reports are never overwritten.

Historical evaluation requires the explicit reproduction option and records
`independentDataEvaluation=False`. Default independent evaluation requires
complete registries, matching corpus preparation and final new-family checks.
Current incomplete coverage refuses it. Promotion reconstructs new receipts,
checks their data role and canonical payload checksum, and rechecks all captured
evaluation inputs before writing. Legacy reports remain historical-review-only.
The checksum detects changed recorded metrics; it is not a signature or a
second numerical evaluation.

The original complete evaluator is retained by SHA/original path, and packaged
provenance retains its original digest through an explicit archive map. Neither
packaged model bytes nor existing provenance is rewritten.

Actual checks:

- Six receipt tests pass on Python 3.12/3.14: row substitution despite an updated
  outer hash, changed inputs/code/registries, modified metrics, resealed false
  independence, promotion consumption and real default refusal under `python -O`.
- Full stdlib: 116 modules / 615 tests, zero failures/errors/skips.
- Scientific: 20 modules / 73 tests, zero failures/errors and one explicit MLX
  environment skip. A new permanent scientific test invokes the real evaluator
  and historical export on four disclosed original main rows, four disclosed
  original legacy rows, 100 source characters and published frozen weights.
- The same versioned smoke command passes standalone, produces a sealed report
  and six review files, rejects a changed metric, and preserves all inspected
  packaged assets/provenance/Kotlin identities/parity bytes.

Two earlier QA attempts are retained: the first lacked the baseline context
asset; the second computed metrics but export refused a noncanonical temporary
root alias. The completed versioned harness supplies the actual published
baseline and canonicalizes the temporary promotion root, without weakening the
production path restriction.

See the [source/evidence receipt](2026-10-28-q6-refinement-evaluation-evidence.json).
This bounded disclosed-data run is not original full-corpus reproduction or
fresh qualification. The separate legacy-regression data graph retains its
existing loader/fixture checks; it is not fully rebound by this new main-data
receipt. Other evaluation/promotion drivers, complete historical provenance,
canonical families and full Q6 acceptance remain open.
