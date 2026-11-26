# Q5: extended disclosed overlay parity

The post-hoc seven-word in-memory overlay was compared against a fresh current
product capture on 4,720 Russian inputs: 720 from the versioned FrequencyWords
parity corpus and 4,000 from the historical spelling parity corpus. Both frozen
input sources and their disclosure registries validated before extraction. The
selection was generated twice with identical rows and manifest. Eight previously
reviewed chat controls were added only to verify that the overlay was active.

Both source-bound local observers completed 4,728 rows. Across the 4,720 parity
inputs, **all non-timing observation fields matched**, including candidates,
editor commands, boundary text and Undo. The eight already disclosed controls
changed at the boundary and were all preserved by the overlay. This comparison
uses opaque controller IDs; only IDs are normalized before comparing all other
non-timing fields. Thirty-nine focused Python tests passed, including a mutant
candidate and boundary comparison.

These parity inputs are previously disclosed and unlabeled. The result is not a
natural-language accuracy estimate or an independent holdout, and it says
nothing about English/Spanish cases or future app/editor behavior. The layer
is an isolated synthetic rank-1000000 lookup, not a packed product asset. The
phone and APK remain unchanged. Broader qualification, provenance of any new
production dictionary and physical acceptance remain necessary.

The subsequent [real packed-candidate experiment](2026-10-28-q5-chat-packed-candidate.md)
demonstrates that this overlay does not represent an APK asset change: unchanged
qualification gates reject the new fingerprint and 658 of the 4,720 unlabeled
boundary outputs differ. The candidate has not been promoted.

Reproduction uses `chat_guard_extended_corpus.py` to freeze inputs, then
`replay_joint_correction.py --mode current-product` for the baseline,
`chat_guard_experiment.py` for the overlay and `chat_guard_extended_compare.py`
for all non-timing observer fields. The generator requires the disclosed chat
rows produced by the command in the [typing experiments guide](../../tools/typing_experiments/README.md).

[Input manifest](2026-10-28-q5-chat-guard-extended-manifest.json),
[full aggregate comparison](2026-10-28-q5-chat-guard-extended-comparison.json),
[hash-bound evidence](2026-10-28-q5-chat-guard-extended-evidence.json).
