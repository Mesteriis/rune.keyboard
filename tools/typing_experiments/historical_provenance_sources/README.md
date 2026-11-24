# Historical provenance source bytes

`refinement_test_9a183595c9f52c6a6d6f39d79d6f168369b7a7ae966ecc6b475f1798e2e155d9.py`
is the exact `tools/typing_experiments/test_refinement.py` blob from commit
`79868bd`, retained for the shipped experiment provenance. Its filename carries
its SHA-256. The current test has portable fixture setup added in `29e84b4`.
The archive preserves source identity and is not imported or executed by the
provenance-path checker. It does not establish model reproduction.

`available_calibration_v6_reconstructed.py` and
`available_clean_v6_reconstructed.py` are source-text reconstructions from the
recorded creation and subsequent text replacement commands. The [exact
clean-v6 plan](v6-inputs/available-clean-v6-plan.json) confirms the original
SHA-256 of the clean preparer. The calibration preparer still has only a
capture-integrity digest. Both scripts use historical `build/` paths. The
recovered v6 selection and assessment remain historical diagnostic data.

`sentence_pairs_v2_v6_availability.json` and `available_clean_v6_manifest.json`
are recovered aggregate metadata. Their bytes match the original hashes in
`docs/acceptance/2026-10-27-right-context-numeric-bridge-evidence.json`.
The original availability was reconstructed from a logged JSON object and the
manifest from logged JSON, with exact historical formatting verified by hash.
They do not contain corpus rows and do not recover or qualify the corpora.

`available_clean_v6_identity_audit.json` is the recovered aggregate audit. Its
bytes match `identityAuditSha256` in the recovered manifest; the model hash in
that manifest also matches `app/src/test/resources/right-context-model-parity/model.bin`.
The audit explicitly states that prior family metadata was not exhaustive and
that no quality qualification was performed.

`available_clean_v6_prior_context_exclusions.json` is the original exclusion
report recovered from the aggregate values in the numeric-bridge evidence.
Its original SHA-256 verifies the serialization. It records ten removed
holdout rows and the two corresponding context hashes.

`available_clean_v6_logged_calibration_row.json` is one previously disclosed
calibration example observed in an original local command output. The logged
command read the historical calibration JSONL and exited successfully. This
fixture is a normalized serialization of the observed object: its own SHA-256
is a new integrity marker, not an original per-row signature, and the missing
whole-file hash cannot be revalidated from one row. Its article, family,
source-context and target-context keys already occur in the historical v6
calibration entry. It must not be treated as fresh evaluation data. The source
was labelled as a Wikipedia-derived public shard, but source-article attribution
and redistribution rights for this individual excerpt have not been reverified;
this fixture is not publication clearance.

The logged observation was subsequently checked against the exact historical
public shard using `tools/typing_experiments/verify_available_v6_observation.py`.
The unique article and context matched. See the v6 recovery receipt for source,
attribution limits and reproduction; this source match is not proof of original
corpus-file membership, selection or independent qualification.

`word_context_v3_counter.py` and `word_context_v3_packer.py` preserve the
recorded historical Word Context training-count and binary packing commands.
The counter includes the original indexed-tail exclusion patch. The source
digests are integrity markers for the captures. The independent historical
output pins and observed totals live in
[`v6-inputs/word-context-v3-count-source-recovery.json`](v6-inputs/word-context-v3-count-source-recovery.json).
The scripts refer to historical `build/` paths. The binary was rejected by
the original evaluation and remains outside runtime assets.

`conversation_supervised_v1_preparer.py` preserves the rejected first
supervised conversation builder from its original creation command.
Its capture SHA-256 is
`1a7548ffee3a16956cb2cf199e413cd1384b74955254a9f0cfda88c450168083`.
The [replay and registration receipt](../../../docs/acceptance/2026-10-27-unmanifested-conversation-audit.md#exact-replay-and-control-exclusions-for-the-rejected-corpus)
binds the three original corpus digests and the original split-overlap refusal.
