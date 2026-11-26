# Q5 capitalization homographs: public source screen

The pinned public Russian Tatoeba CC0 source contains ten occurrences of the
three exact forms investigated in the disclosed capitalization review: four
`клавы`, one `моника`, and five `читы`. Each occurs with a lowercase initial
outside sentence start. Manual inspection of their source sentences shows common
uses referring to keyboards, a monitor or game cheats. Five are the already
reviewed control occurrences; the other five occur elsewhere in the same public
source. All ten source article identities are already in the permanent exclusion
ledger. The scan found no title-case occurrences of these exact forms, so this
source alone cannot provide the matching proper-name contrast.

The [screen](../../tools/typing_experiments/audit_case_homograph_source.py)
checks the pinned compressed source hash, TSV structure, token boundaries,
article uniqueness and ledger exclusions; it rejects a hit whose source is not
excluded. The adjacent [receipt](2026-10-28-q5-case-source-screen.json) lists
public article identities and binds source, ledger and code. Two final runs
were byte-identical. Two focused tests cover token/case boundaries, quoted TSV
text, malformed or duplicated articles and unregistered sources. An earlier
attempt incorrectly treated raw TSV as CSV and failed; it was corrected before
these runs.

This is an exposed source screen, not independent evaluation, not a replay of
the five additional contexts, and not evidence that any changed policy works.
The source may contain further spelling errors; original capitalization alone
is not a universal indicator of author intent. To compare a proposed context
rule, explicit proper-name contrast cases and broader held-out controls remain
necessary. No production behavior or phone state changed.
