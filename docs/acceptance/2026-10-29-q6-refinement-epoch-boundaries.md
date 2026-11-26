# Q6 refinement and epoch source-token boundaries

The pinned public source shard was checked against the archived historical
refinement and extra-epoch rows. Of 7,500 refinement rows, 65 targets were
prefixes of hyphenated source tokens; of 1,500 epoch test rows, 10 were. All
other rows in these two audited sets had standalone source targets. Repeated
source matches occurred for 29 refinement and two epoch rows; the audit requires
all matches for each row to agree on the same boundary and full token.

The complete forms and contexts are preserved in
`tools/typing_experiments/refinement-epoch-boundary-origin-v1/`, with source
attribution and receipts bound to the archive, source lock and analyzers. Two
separate captures were byte-identical. Control and lexical context exclusions
now include all 75 disclosures; no compound lemma is inferred. Registry
validation and mutation tests run in CI. This previously exposed material is
not an independent qualification corpus, and the remaining Q6 provenance and
coverage gaps remain open.
