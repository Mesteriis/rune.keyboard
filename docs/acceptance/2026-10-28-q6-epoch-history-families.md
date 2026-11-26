# Q6: additional-epoch historical test families

The original additional-epoch test is a public, previously exposed regression
corpus, not a fresh holdout. Its archived manifest, source lock, exact generator,
article attribution and row bytes were verified. All 1,500 test target words
had pinned dictionary analyses, producing 832 distinct family keys. Two of those
keys were not present in the existing family exclusions for new-family
qualification. No target required an inferred lemma or unsupported-surface key.

A single `historical-family-exclusion` addendum retains all 134 previous ledger
entries and the incomplete global coverage state. It excludes these families
for the new-family protocol without claiming that the test words were supervised
training examples. The original parent keeps its missing-axis declaration;
full source-sentence identity, other historical gaps and independent
qualification remain open. Source text is not added to the ledger.

The [numeric receipt](2026-10-28-q6-epoch-history-families-evidence.json) binds
source identities, audit implementation and pinned dictionary. Tests verify
that test-family exclusions differ from supervised training exclusions, and
reject changed split, article, repeated import and malformed input. The portable
15-member public fixture still verifies after the ledger change. No runtime,
APK, model or phone change was made.

The final standard-library profile passed 687 tests across 123 modules, and the
focused ledger/preparation group passed 31 tests.
