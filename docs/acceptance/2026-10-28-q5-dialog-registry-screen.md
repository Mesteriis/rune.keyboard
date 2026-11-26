# Q5: dialogue source exact-context screening

The pinned synthetic dialogue source screened in [the earlier receipt](2026-10-28-q5-dialog-source-screen.md)
was checked against all target-context keys in the permanent Q6 ledger. Each
unique eligible 2–6-word phrase was decomposed into successive prefix/target
contexts, including the empty prefix before its first word. No model was run.

Of 6,326 unique phrases, 419 have at least one exact context already in the
ledger; four have a first-word match, 415 a later-word match, and two a match at
the final word. These categories may overlap. There are 10,304 distinct token
contexts in all and 32 distinct matching context keys. This is different from
comparing entire phrases with the previous Tatoeba controls, where no exact
phrase match was found. Repeated templates can make one context key appear in
many different phrases.

The [numeric receipt](2026-10-28-q5-dialog-registry-screen-evidence.json)
binds the CSV, card, ledger and relevant audit code. Two independent runs
matched byte for byte. Focused tests cover repeated contexts, differing last
and intermediate positions, malformed input and source identity. This is only
an exact prefix/target screen; it does not check article, source, family, right
context or semantic overlap, nor correctness of the text. The ledger reports
incomplete coverage. No phrase is therefore certified as fresh or independently
labelled, and no data is registered, trained or scored by this audit. Q5 and Q6
remain open.
