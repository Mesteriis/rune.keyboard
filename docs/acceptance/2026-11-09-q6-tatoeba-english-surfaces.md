# Q6: disclosed English Tatoeba surface exclusions

The retained public CC0 English Tatoeba snapshot was parsed against its locked
compressed SHA-256 and the previously registered article/sentence entry. Both
parent key sets were recomputed from all 41,513 source rows and matched. Of
562,128 supported whole-token occurrences, 26,735 distinct case-folded exact
surface keys were not already protected by the EWT token-surface fixture.
They are now registered as `unsupportedSurfaceKeys` in a new historical
context-exclusion entry. The entry also contains one actual source context to
fit the existing schema; it does not assert that all source contexts or English
families are covered. The hashes are unsalted and reversible; source sentences,
labels and sentence identifiers are not added to this entry.

Comparing these 26,735 keys against the pre-existing entries found no overlap
with other lexical unsupported-surface keys and 411 keys already present in
control-surface exclusions. Thus 26,324 keys extend the union of the prior EWT,
lexical unsupported-surface and control-surface protections. These are exact
surface counts, not distinct families or an estimate of independent coverage.

For English `new-families` proposals, the common preflight checks both typed and
expected forms against these keys. A match blocks the proposal; `new-sentences`
does not apply this added exact-surface rule. English lexical qualification is
still unsupported, both registries remain incomplete, and this change does not
qualify data or a model. The source is exploratory and previously disclosed;
its CC0 notice is retained with the source archive.

Two independent registrations produced identical ledger bytes, preserving all
210 prior lexical entries and coverage metadata. The source-bound checker
recomputes the exact surface set and verifies the parent source identities.
One disclosed test token that was absent from the preceding exclusions is now
blocked by the real family preflight. The input snapshot, checker, source lock,
EWT fixture and key helpers are bound; changes fail the check. The moving
preflight implementation is not an input to the historical source extraction.
No historical source bytes or prior entries were rewritten.

In a staged source archive without `build/`, the three new importer tests,
27 public-preparation tests, one no-build registry test and 22 text-preflight
tests passed; the source-bound registration check also passed. The isolated
historical boundary and named-regression checks passed locally. The tracked
test inventory now contains 182 standard-library modules. Temporary source
archives and the task-created registration directory were removed; hosted CI
and device checks were not run.

The first complete standard-library run at `a8a259f2` failed: one existing
ledger test expected exactly 13 older Russian surface entries and counted the
new English entry as a fourteenth. The run covered 182 modules and 900 tests,
with one failure, no errors and no skips; its temporary receipt SHA-256 was
`bbf1f5103793ce45a25d4180b563c3007b5d1c67dee004d6d2854c9c618d714f`.
The test now checks the new English entry explicitly and retains the original
checks over the Russian entries. The source importer's bindings were also
corrected to omit the moving preflight file, which is not used by historical
extraction; the registry entry was regenerated without changing its keys or
any prior entry. This failure is not counted as a passing full run.

After that fix, a clean Git checkout at `1a185117` with no initial root `build/`
passed the complete standard-library profile: 182 modules and 900 tests, with
no failures, errors, timeouts, missing receipts or skips. The temporary receipt
SHA-256 was `3dc1249b43f82a63d343f633c53876cf960d052050203f3db543e166ce7bc65b`.
The checkout and receipt were removed. This is not hosted CI or device evidence.
The importer tests, minimal no-build registry test and source-bound registration
check also passed again in an archive of `1a185117` without `build/`; the
temporary archive was removed.
