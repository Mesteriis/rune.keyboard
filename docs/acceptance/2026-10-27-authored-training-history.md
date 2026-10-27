# Q6: reproduce authored template history and retain an unproven-origin gap

Archived the exact three right-context contrast generators from Git revisions
9e31f24, 6c0cd91 and ab8e019. Each archive matches its historical generator hash.
The shared corruption selector also matches its pinned historical hash before
any archived code executes. Regeneration with dictionary-only morphology
reproduces the original sorted JSONL bytes and skipped cases for all three
versions: 1,968 / 3,472 / 4,872 rows. These are related corpus versions, not
10,312 independent examples. Their templates and candidate paradigms are in
the archived source; no owner sentences are supplied to these generators.

For each version, the corpus hash matches the selection receipt; the selected
group file hash/count matches both that receipt and the training plan. This
establishes consistency of the surviving historical chain. It does not prove
that a model fit executed, reproduce a model binary or qualify any source.

The primary authoring paradigms name 24 families, but all dictionary analyses
of their candidate forms yield 29 canonical families. Two of those, весло and
красить, were absent from the default supervised/prepared-training exclusions.
All 29 are now conservatively quarantined for each reproduced version through
prepared-training-quarantine, rather than assigning unproven model consumption.
Corrupted unknown inputs and unknown retention targets are not guessed lemmas.
This does not assign these ambiguous readings as the intended labels.

Added 472 unique left-context/target exclusions across the three versions.
Candidate forms and retained applied states are included; the projection
deliberately ignores the right suffix, conservatively blocking reuse with a
different suffix. Existing 85 entries, their bindings and global incomplete
coverage are unchanged. Existing spelling family gaps are not cleared.

The separate context-feature authored file has 120 observed rows, matching its
manifest count and hash. That manifest has no generator/source binding. A
matching hash establishes file identity, not who authored it or whether it
contains owner-derived text. Its origin remains UNPROVEN_ORIGIN. No rows,
prefixes, row identities or private corpus fingerprints from that file enter
the public registry or this evidence; only counts and local comparison outcomes
are retained. The audit does not manufacture a source citation for it.

All 166 tests pass in a fresh source-only directory without build corpora,
models or morphology packages. Both ledger schemas validate with incomplete
coverage. Six new tests cover ambiguity without predicted lemmas, unknown
families, exact reproduction, archive tampering, training-chain mismatches and
redaction of unproven examples. Snapshot tests preserve the two newly blocked
families; real preparation CLI tests reject them with exit code 2 and create no
output. CI includes the audit tests; no remote CI run is claimed. The full
dictionary-backed audit itself exits 0, with no model calls.

Remaining Q6 work includes later authored transformations, unresolved historical
word families and source/generator chains, and origin evidence for the separate
120-example file. No fitting, scoring, production policy or device change.
