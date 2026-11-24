# Q6: public refinement exclusion coverage

The versioned public historical-data archive reproduces 7,500 refinement
rows: 5,000 prepared training, 1,000 development and 1,500 test. Its manifest,
source lock, generator identity, article attribution and member hashes were
verified. The audit matches every source article and typo-independent target
context against the durable registry, and uses the pinned dictionary's complete
set of analyses for each target.

All 1,954 training family keys are already covered by supervised or
prepared-training quarantine entries. One training occurrence has no verified
dictionary analysis; its exact public surface is already quarantined, without
guessing a lemma. All 672 development and 921 test family keys are covered by
the broader historical family exclusions. Across all three partitions there
are zero missing article, context, applicable family or unsupported-surface
keys. This requires no new registry entries.

Training and evaluation scopes remain distinct: the audit does not claim every
prepared row was consumed by a model. Exact-surface quarantine does not prove a
canonical family for the unresolved form. Full source sentences, other
historical gaps and independent qualification remain open. No text from user
input, model execution, APK or phone change is involved.

The [numeric evidence](2026-10-28-q6-refinement-coverage-evidence.json) binds the
ledger, archive, source implementation and pinned dictionary. Focused tests
reject a training family covered only by historical evaluation, a missing
unknown surface, duplicate IDs and input scope mismatches.
