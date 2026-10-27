# Q6: wire both registries into new versioned preparation entry points

Added prepare_public_spelling_v1.py and prepare_public_controls_v1.py, sharing a
mandatory dual-registry preflight. They finalize upstream source-extracted
canonical proposals without rewriting any old generator or changing historical
hash-bound receipts. Both registry inputs, proposal bytes and source-manifest
bytes are pinned before any output is created.

The gate checks lexical article/window/context exclusions, supervised versus
historical family protocol, protected and punctuation context exposure, and
language-qualified punctuation source articles. Source-identity errors do not
skip control checks. Both control kinds are checked regardless of requested
builder task. Boundary label changes do not make old punctuation contexts fresh.
No profile permits incomplete registry coverage or disables a registry.

Current registries remain incomplete; their validators do not certify overall
freshness. Accordingly **no new final corpus is published**. A future complete
registry protocol is required before the finalization success path can be used.
That path is not claimed as exercised. Source/label/cohort/model audits remain
separate; proposal flags and input hashes alone do not certify public origin,
correct canonical families or source labels. Report qualification flags stay false.

All 105 existing/new tests pass in an isolated source-only directory without
original corpora, models, PyArrow or morphology packages. Fourteen new tests
exercise both independent article registries, protected cross-task checks,
relabeling, family profiles, invalid identities/second registry, empty/duplicate/
unsupported rows, proposal tampering and CLI no-output behavior. Synthetic
proposals are tested against actual persisted registries; they are not new
qualified public data or training examples.

Four recorded CLI probes each exit 2 and leave no output directory:

- Known supervised family: BLOCKED_OVERLAP.
- Punctuation source article 4327487, absent from lexical article history:
  BLOCKED_OVERLAP via the control registry.
- Known protected token/context: BLOCKED_OVERLAP.
- Artificial unseen family identity: BLOCKED_COVERAGE.

The initial unseen-coverage test used the real lemma `пробный`; the actual
supervised registry correctly blocked it. That finding became a separate
regression. An explicitly artificial identity now isolates the incomplete-coverage
case; no production exclusion was weakened to make a test pass.

CI includes both entry-point suites and the shared gate tests. Local checks are
not a remote CI run. The evidence binds code, registries, test results and all
intentional nonzero CLI outcomes. No successful fresh-data build, new qualification,
model fit, threshold change, APK or Fold action is claimed.

Q6 remains open for unresolved lexical families, other historical context/
conversation corpora, foreign lexical namespaces and remaining provenance/source
and runtime coverage. Versioned preparation now enforces that incomplete state.
