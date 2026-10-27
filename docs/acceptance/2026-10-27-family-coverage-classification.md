# Q6: distinguish lexical family gaps from protected controls

Audited the 62,516 previously imported historical rows against their registered
file hashes and counts, using the same pinned dictionary-only analyzer:

- 56,493 dictionary-supported lexical targets.
- 5,385 protected nonlexical controls, not missing ordinary-word lemmas.
- 638 unresolved lexical targets: 637 historical spelling targets and the ranker
  training target `делла`. No ordinary joint/follow-up target is unresolved.

Every protected row is verified against the exact original builder construction:
cohort and group `protected`, `noAuto=true`, a Cyrillic lexical base in `word`,
and identical typed/expected `@` + base. The audit does not strip punctuation
from arbitrary tokens or infer a canonical lemma from native numeric IDs.
Malformed protected metadata fails rather than silently skipping a row.

This refines the interpretation of the prior 5,385 unresolved *target-analysis*
records. Those original receipts remain unchanged; the analyzer correctly does
not treat mentions as ordinary lexical words. The remaining 638 targets are
mostly names and rare forms; this audit does not assign guessed lemmas or clear
missing family axes. The old ledger keys and coverage state are untouched.

The accompanying receipt lists source bindings, unresolved row IDs, protected
control IDs and pinned dictionary package hashes; it contains no source phrases.
Four regression tests cover protected versus lexical status, unknown words,
invalid control construction, duplicate IDs and explicit public-source routing.
All 52 tests pass in a source-only directory without original corpora or morphology
packages; CI includes the audit tests. No model fitting or Android change.

This audit predates the separate spelling-v6 import; its totals describe only
its explicitly bound input ledger and source files.
