# Q6 refinement legacy snapshot binding

The evaluator now reads its legacy regression rows from the validated frozen
snapshot instead of a later independent loader call. Receipt v2 binds the
original v2 corpus manifest and RU rows, legacy export receipt and all declared
output files, plus the candidate-generation dependencies checked by the original
loader. Observation indexes/original tokens and corpus-row alignment are checked
with runtime errors that remain active under optimized Python. All captured
bytes are rechecked before a report or review export is written.

The original corpus manifest must match the versioned project manifest exactly.
An export with recomputed outer hashes cannot substitute another original token
or relabel the corpus. Snapshot roots must stay inside the project; reports use
a project-relative locator. The full original corpus/export graph remains bound
when a numerical smoke uses a subset. A legacy row limit is allowed only in
explicit historical mode and is itself bound into the receipt. Packaged
promotion requires a bound legacy graph. Typed v1 reports need reevaluation for
the v2 contract; untyped legacy reports retain review-only handling.

The versioned real-driver smoke now nests the baseline snapshot inside its QA
project and uses the explicit bounded API. It no longer substitutes the legacy
loader result. Its actual snapshot contains 4,000 exported rows, 3,400 source
corpus matches and 39 checked generator sources. The numerical smoke still uses
four main and four legacy rows, with 100 source characters: it is not a complete
historical numerical replay or new independent model qualification.

Actual checks:

- Eight receipt tests pass on Python 3.12 and 3.14, including mutation of every
  captured legacy input, recomputed outer hashes with a wrong token, corpus
  relabeling, root escape and invalid subset limits.
- Full stdlib: 116 modules / 617 tests, zero failures/errors/skips.
- Scientific: 20 modules / 73 tests, zero failures/errors and one MLX-environment
  skip. The real-driver test covers legacy-input drift before export.
- CI tools: 41 tests pass. The standalone versioned smoke also passes and keeps
  inspected packaged assets, provenance, Kotlin identities and parity unchanged.

See the [source/evidence receipt](2026-10-28-q6-refinement-legacy-binding-evidence.json).
This closes the identified refinement legacy-input binding gap. Compiler/native
execution qualification, remaining evaluation/promotion drivers, complete
historical inventory/canonical families and fresh Q6 qualification remain open.
