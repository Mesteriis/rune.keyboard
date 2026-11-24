# Q6 historical text-boundary verifier isolation

The two historical text-boundary registrations bind the then-current
`control_ledger.py` and `independent_corpus_guard.py` bytes. The new
`tools/ci/check_text_boundary_history.py` runs both unchanged registration
suites and checks in an isolated temporary source tree, overlaying the two
previously archived versions only after checking their exact SHA-256 values.
CI calls this runner in place of the four direct commands. Registry entries,
fixtures, and historical verifiers are unchanged. A corrupt archived helper
fails before any verifier is invoked; the live checkout is never modified.

The isolated tree retains symlinks so the historical checks can detect them.
It contains no `build/` directory. The checks still bind the remaining
historical inputs and run their existing fixture-mutation and gate tests. The
runner does not freeze or independently qualify a new corpus and does not
change the current incomplete-coverage guards. It isolates only these two
helpers and these two historical registrations; other historical bindings must
be audited before changing additional files or relying on broader migration.

Validation used a staged-source archive without `build/` or `.git` in which a
newline was appended to each live helper. Both historical suites passed (three
tests each) and their registry checks verified 179 and 470 source rows. Two
runner tests passed, including refusal of a corrupt archived helper and a check
that both archived helpers are used only in the temporary tree. The hosted CI
workflow is wired but was not run here.

Follow-up: the named-regression source check also uses this archived helper;
it is now run in the same temporary tree. See [control source identity guard](2026-11-03-q6-control-article-overlap.md).
