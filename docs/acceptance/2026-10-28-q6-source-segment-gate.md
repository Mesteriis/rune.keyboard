# Q6: source-segment overlap in new corpus preflight

The earlier ledger addenda stored normalized hashes for whole historical
selector segments in the shared full-sentence namespace. New Wikipedia proposals
previously supplied only a target-window `contextHash`, so an identical segment
under a different article identity could evade that particular comparison.

Source-backed Russian Wikipedia proposals now require `sourceSegmentHash` in
the new-corpus preflight and direct new-sentence ledger CLI. The ledger compares
both the existing target-window key and the normalized full-segment key; Tatoeba
and EWT retain their existing source identity route. Source-free authored
protected controls and old historical ledger rows remain readable. The helper
`source_segment_hash` normalizes NFC, casefold and whitespace consistently with
the stored hashes. Missing or malformed segment identities block preparation.

The helper hashes a supplied segment; upstream still has to establish that it
came from the claimed article and follows the documented selector boundaries.
The hash is not itself provenance, a guarantee of complete semantic overlap
checking, or a linguistic sentence annotation. Existing incomplete registries
still block fresh qualification. No historical corpus was rewritten or promoted.

Focused tests verify a shared full-segment overlap under a different source
identity, missing and malformed hash refusal, and the preserved target-window
path. A direct check against a retained historical text segment returned
`BLOCKED_OVERLAP` with one sentence-key overlap. The full stdlib inventory passed
762 tests across 153 modules with no skips; raw receipt is under
`build/review-q6-segment-gate-tests-20261028/`.

## Joint proposal collectors

The current joint and joint-followup collectors now compute
`sourceSegmentHash` directly from the normalized public article and the selected
token's source position, before typo variants are made. A delimiter index is
built once per article. The selector delimiter is tested against the historical
recovery expression. Canonical projection preserves the hash and rejects a
shared segment across train/calibration/holdout, in addition to existing
family and target-window checks. The new field is only populated on the
registry-checked path; historical reproduction does not change its row schema.

Unit tests cover delimiter positions, wrong-source matches, preserved hashes and
cross-split reuse. The full stdlib inventory passed 763 tests across 153 modules
with no skips (`build/review-q6-joint-segment-tests-20261028/`). A fresh actual
historical reproduction of the original joint collector completed and all three
row files matched the retained original byte for byte. Its output is under
`build/review-q6-joint-segment-historical-20261028/`. This does not establish
historical followup parity or a new qualified corpus: the real registries remain
incomplete and the registry-checked collector still fails closed before source
processing. At that point other collectors had not yet been adapted to this
source-segment requirement.

## Refinement, word, epoch and retrieval selectors

These four maintained collectors now attach the normalized whole selector
segment to each row on the registry-checked path. Historical reproduction
retains the original row schema. Focused tests cover the shared helper, segment
overlap and historical behavior; the existing refusal test still checks all
collector CLIs against the incomplete real registries.

An intercepted test run over the pinned public Parquet checked each produced
hash against a segment of its recorded article: 7,500 refinement, 9,000 word,
1,500 epoch and 1,800 retrieval rows, with zero mismatches. The final registry
gate was deliberately intercepted for this diagnostic; retrieval also used a
stubbed prior-data exclusion because its observations manifest was unavailable.
Neither this run nor its output is a qualified corpus. The original attempt
without that stub failed on the missing manifest. Separate historical-mode runs
reproduced all seven word and all seven epoch JSONL outputs byte for byte.
Raw scripts and logs are under `build/q6-collector-segment-live-check*` and
`build/q6-{word,epoch}-segment-reproduction*`.
The complete stdlib inventory passed 764 tests across 153 modules; packaged
provenance checking and `git diff --check` passed. Raw test outputs and the
runner receipt are under `build/review-q6-collector-segments-20261028/`.

This step supplied just one required identity. The subsequent
[selector projection](2026-10-28-q6-selector-projection.md) adds source windows
and dictionary families and exposes cross-partition reuse; the real incomplete
ledgers continue to block fresh proposals. Q6 remains open.
