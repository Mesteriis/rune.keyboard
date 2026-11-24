# Q6 freshness admission and historical verifier migration blockers

This inspection follows commit `7043daf6`. The current registries are
incomplete; none of these observations changes their coverage or qualifies a
corpus. The original review requires a fresh natural holdout checked against
durable historical exclusions even without `build/`.

Three separate barriers currently prevent that end state:

1. `control_ledger.validate` requires `coverageComplete` to be exactly false
   and `pending` to be nonempty. On a temporary in-memory copy of the current
   ledger, setting completeness to true and clearing pending produced
   `CONTROL_LEDGER_SCHEMA`. `assert_disjoint` also ends with
   `CONTROL_COVERAGE_INCOMPLETE` after its overlap checks. A future coverage
   assertion therefore needs an explicitly designed, evidence-bound schema and
   admission path, not merely a change to the stored flag.
2. `reject_unchecked_texts` always rejects nonempty new text outputs. A direct
   call with a nonhistorical snapshot and one synthetic text returned
   `SELECTOR_TEXT_CORPUS_UNCHECKED`. The refinement, word-ranking and epoch
   collectors call this guard; their word-row checks do not establish text
   corpus disjointness. A safe replacement must check the actual emitted text
   and its source and partition identities, unresolved forms, family and context
   exclusions, and input drift before publication. The existing text exposure
   audits are diagnostic and do not certify those properties.
3. Historical verification binds current helper bytes. In a disposable staged
   source archive without `build/`, the all-text registration check passed
   before mutation. Appending a newline only to that copy of
   `control_ledger.py` caused its check to exit 1 with `ALL_SOURCE_BINDING`.
   The tracked source was not modified. The receipt binds the helper hash and
   the registry entry binds the verifier itself; changing either in place can
   invalidate historical checks and registry-entry identities. A migration must
   retain and verify original source versions and historical receipts while
   explicitly recording any new verifier and registry bindings.

The next implementation needs a versioned migration and tests of both old
historical verification and the future admission path, including overlap,
missing evidence, source drift and absent `build/`. It must continue to reject
the present incomplete ledgers. Completing this engineering work alone will
not prove the outstanding provenance, establish independent labels, or pass
model quality and device acceptance.

An additional read-only EWT scan at lexical-ledger SHA-256
`9527a9811a9cf38a890e85702deaf7ae747690e0c43618a86f51fb5f48a8569d`
found 878 distinct supported-shape exact token surfaces in 5,164 integer-token
rows for which the annotated lemma is already in the family-key registry but
the surface is not itself a registered family key. The three source files
matched the existing source lock. This is a diagnostic of the difference
between annotations and surface spellings, not a count of unprotected families:
matching a candidate's real lemma may already catch it. The current source-only
control schema refuses `surfaceKeys`, so recording these without mislabelling
them as lemmas or controls requires a versioned surface-exclusion design and
migration of historical verifiers. No words, labels or new corpus were retained,
and the scan does not establish complete coverage.

At source `275a3a07`, a clean-checkout attempt to discover all `tools/ci`
tests together exited 1: 190 tests, two failures and two errors. Re-running
the two affected three-test modules directly reproduced exactly those four
outcomes: their historical registration checks require archived guard bytes
and instead saw the live guard (`ALL_SOURCE_BINDING` and
`SHARED_SOURCE_BINDING`). The other 184 tests in the broad run did not fail.
This broad discovery command is not the CI workflow: CI deliberately runs
both historical modules through `check_text_boundary_history.py`, which was
verified separately at this source. The broad run's raw output SHA-256 was
`3e0543d9d340ffda9bf92fb745c8d531f039c1f57ff8d5619e2ab57f17026c67`;
the temporary output and checkout were removed. No hosted CI execution is
claimed. Synthetic failure and skip messages in the output were emitted by
tests of the test gate itself; the outer run's four failures are the historical
binding failures described above.

At `8fabb87ae3c1cf35b1a3e07ecb30618a8599e81a`, a fresh clean clone with
the pinned native submodule repeated broad `tools/ci` discovery on Python
3.12.14. The outer run exited 1 after 247 tests in 417.408 seconds, with two
failures and two errors: the source-bound and rehashed-unrelated-token tests
in each of the same all-text and shared-text registration modules. This
confirms that normal broad discovery remains incompatible with their archived
helper bindings. The output also included intentional failing, skipped and
expected-failure inner probes of the backend gate; those are not additional
outer failures. This was not the CI workflow's isolated historical runner and
is not a passing full-suite or hosted-CI result. The temporary checkout and
output were removed. The next fix must preserve the original source bindings
while making the discovery route use isolated historical helper bytes; do not
silence or skip the affected checks.

The two test modules now use an isolated snapshot with the exact archived
helpers when ordinary discovery starts from the live source tree. Each of the
six original tests runs separately in that snapshot; child failures, empty
runs and skips are rejected. In the existing historical runner the archived
helpers are already present, so the original tests run directly. The live EWT
entry is verified before its temporary old-schema projection, as before.

At `3a66e0a96e8ed6ae2fe020cdce80566561883d25` plus this staged change,
clean-clone broad discovery passed 249 outer tests in 437.235 seconds, with
exit zero and no outer skips. Its output contains intentional failure, skip
and expected-failure probes inside the backend-gate tests. Fourteen focused
text-registration tests and five historical-runner tests passed; the full
historical runner also passed its six original tests and registration checks.
Two proxy tests reject child failure, empty results and skips. The temporary
checkout and output were removed. This does not establish hosted CI or
complete registry coverage, and does not admit new selector text.

The discovery proxy originally rebuilt all three historical test methods even
when `unittest -k` had filtered the original suite. It now proxies exactly the
selected methods, preserves an empty selection and refuses duplicate method
names rather than silently merging them. Four proxy tests pass, including
filtered, empty, duplicate, failed, skipped and zero-test child cases. A real
filtered discovery ran exactly four matching methods across the four boundary
modules; a nonmatching filter ran zero and exited 5. The five historical-runner
tests and the complete historical runner also passed. No full broad discovery
or hosted CI was repeated for this fix.
