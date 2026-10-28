# Q7: exhaustive Python tools inventory and partial CI coverage

The versioned inventory covers all 103 tracked modules requested by Q7.
CI now runs 92 stdlib modules and five scientific modules in separate jobs,
using Python 3.12, isolated module subprocesses, and the existing pinned
scientific requirements. New/unassigned or stale modules fail validation.
Raw logs, exits, counts and skips are uploaded. Existing outputs cannot be
reused, empty suites/profiles fail, and module timeouts remain failures.

Actual local checks on 2026-10-28:

- Task-owned clean checkout at source base `ed24b42`, with only the four bound
  candidate runner/inventory files added; no owner-local experiment modules.
- Python 3.12.14 stdlib environment: 92 modules, 518 tests, zero skips/failures.
- Isolated scientific environment: five modules, 22 tests, one existing
  MLX-only skip; 21 passed. No MLX gradient-parity claim.
- All 17 `tools/ci/test_*.py` infrastructure tests passed, including actual
  child import failure/continuation, timeout, empty suite/profile refusal,
  inventory drift and duplicate assignment.
- Separate historical profile: six modules, 22 tests, nine errors caused by
  missing original historical artifacts. Exit 1 retained; no assertions
  replaced or absent data skipped.
- `git diff --check` passed. Original owner payload hashes and untracked paths
  were checked unchanged. Temporary candidate files removed from task clone;
  its tracked and untracked status returned clean.

The historical failure run preceded the final empty-profile guard, which does
not affect these six nonempty modules. Final stdlib/scientific runs used the
exact source hashes in the accompanying evidence JSON. Private raw logs and
receipts remain under `build/review-q7-tools-20261028/`.

Q7 remains **in progress**. Six historical modules are explicitly absent from
CI execution until their original source/data/model provenance is restored.
The Ubuntu workflow has been edited but not dispatched. Live CatBoost/Pymorphy
integration and supported Apple MLX parity need their own evidence. The two
new green jobs do not establish complete tools coverage. Commands, fixture gaps
and output semantics are in [python-tools-tests](../python-tools-tests.md).
