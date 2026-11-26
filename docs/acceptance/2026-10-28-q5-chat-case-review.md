# Q5 post-hoc review of case-only changes

The disclosed chat-shaped baseline changed only capitalization in 30 source
controls. A contextual editorial review classifies five occurrences for lowercase
preservation: two uses of `клавы` for a keyboard, two of `читы` for game cheats,
and one `моника` for a monitor. Rune capitalized these as if they were names.
Another 24 occurrences refer to apparent proper names or places; this classification
alone does not establish whether a user wanted automatic capitalization. One
`майн` gaming reference is ambiguous and is not treated as a defect.

This review was made after seeing the outputs, using the previously disclosed
Tatoeba regression data. It is neither independent qualification nor an estimate
of the false-change rate; the remaining controls were not individually labeled,
and their authors' actual intentions are unknown. No runtime policy, model or
APK was changed.

The [review labels](../../tools/typing_experiments/chat_regression/source-control-case-review-v1.json)
cover all 30 observed case-only changes. The [audit](../../tools/typing_experiments/chat_case_review.py)
validates the full observer output, exact original rows and changed boundary text,
checks that each reviewed article is excluded in the holdout ledger, and fails
on missing or extra cases or source drift. It reports 5 lowercase-preservation,
24 proper-name and 1 ambiguous case. A separate comparison mode reports **0 of
5 lowercase cases preserved** in this disclosed baseline and can assess a later
observer run without requiring it to reproduce the old output. Both modes bind
input hashes in the adjacent JSON receipts.

Five focused tests cover case coverage, changed source/output, unknown labels,
exact lowercase comparison and missing IDs. This adds actionable regression
examples; broader independently sourced, proofread controls and a true
multiword revision/Undo replay remain open.

## Comparison reports both reviewed sides

The post-hoc comparison now reports apparent-name source-case matches and
failure IDs alongside lowercase-preservation results, and counts ambiguous
cases separately without assigning them a desired output. It also rejects a
review baseline that is not a genuine case-only change. This makes it possible
to see if a candidate preserves the five common-word controls while losing
previously reviewed apparent-name outputs. These are source-case contrasts,
not proof of the author's desired automatic correction, and the separate
21-row Wikipedia contrast remains a distinct check. This change does not
implement or qualify a product policy.

Six focused case-review tests and seven related candidate/extractor tests pass
on Python 3.14. An initial invocation from the repository root failed to import
the local module; rerunning from the tools directory passed. The existing
30-entry review was also checked to contain only genuine case changes. No
current-product replay or Android test was run for this tooling-only change.
