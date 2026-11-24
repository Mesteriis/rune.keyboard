# Q6 acceptance entry bindings

The public corpus preparation report now records both exact ledger snapshot
hashes and canonical SHA-256 for every full entry. The canonical digest includes
keys, source bindings and metadata; JSON object key order/formatting cannot
change entry identity, while any original ledger byte change changes its
snapshot hash. A saved report must agree with its own existing `inputBindings`
and with both current versioned ledgers.

The [corpus acceptance template](TEMPLATE-corpus.md) requires the preparation
report SHA, both ledger SHA values, relevant entry IDs and canonical entry
digests, including the consumed corpus registration. It provides an executable
snapshot verification command. This covers the review's template requirement;
it does not close historical inventory or fresh qualification.

An actual CLI preparation of the already disclosed standalone `зочу → хочу`
case exits 2 with `BLOCKED_OVERLAP`. Both typed and target surfaces are excluded:
two regression and two surface overlaps. Missing source/family/context
identities are also reported, so this deliberate refusal probe is not a valid
new natural corpus proposal. No frozen corpus directory is created. The report
binds all 126 lexical and 27 control entries. An initial postcheck incorrectly
expected one overlap; inspection confirmed both identities are correctly
counted and the corrected postcheck verifies the preserved CLI output.

Actual saved-report verification passes; removing one entry binding from either
registry is rejected. Regression tests cover exact-byte snapshots, canonical
entry ordering, changed provenance/keys/metadata, missing or conflicting
bindings, invalid ledgers, and binding retention in blocked preparation.

All 113 stdlib modules pass: 594 tests, zero failures/errors/skips. Final focused
tests pass on Python 3.12 and 3.14: 14 tests each. The last consistency guard was
followed by these focused reruns. See the
[source/evidence receipt](2026-10-28-q6-acceptance-registry-binding-evidence.json).
No APK, phone behavior, model training or independent qualification is changed.
