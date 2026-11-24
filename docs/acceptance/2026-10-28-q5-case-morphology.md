# Q5 case errors: source and morphology screen

The actual baseline observations for all five reviewed lowercase-preservation
cases identify `CANONICAL_CASE` as the automatic correction source. Their
records mark the title-case surface unambiguous. The frozen asset builder sets
that bit when the lowercase surface is absent from its particular source file;
it does not prove that a lowercase common-word use cannot exist elsewhere.

The pinned dictionary-only Pymorphy3 host analyzer offers an independent
lexical view, not a context decision. For all five problematic occurrences it
returned only proper-name or geographic-name analyses: `клавы` and `моника`
as personal-name forms, `читы` as a geographic-name form. It also returned
proper-only analyses for 23 of the 24 post-hoc proper-name occurrences, and
both proper and other analyses for the remaining one and the ambiguous case.
Consequently a rule that simply trusts this dictionary's proper-name evidence
would not distinguish these five errors from most named entities in this sample.
The existing analyzer deliberately excludes guessed analyses.

The [screen](../../tools/typing_experiments/audit_chat_case_morphology.py)
binds the disclosed review, exact analyzer code and installed pinned package
files in the adjacent [receipt](2026-10-28-q5-case-morphology-screen.json).
Two runs matched byte for byte; two isolated tests cover dictionary-category
classification and reject invalid scope, labels and duplicate IDs. The review is
post-hoc, small and previously exposed. It establishes neither the quality of a
new context policy nor a population error rate. No runtime or packaged asset was
changed; a candidate still needs broader contextual controls, impact measurement
on names, replay and independent qualification.
