# Q5 canonical-case ambiguity overlay: disclosed replay

A current-product host baseline and a candidate were run on the same 34,330
previously disclosed Russian chat-regression rows. The candidate changes only
the canonical-case ambiguity result in an isolated copy of the observer: for
the ten Russian keys with lowercase source evidence, the existing canonical
candidate is marked ambiguous. The source asset, app, runtime code and APK are
unchanged. This is an in-memory experiment, not a packaged lexicon or release.

The two runs completed with all rows accounted for and bound input/source hashes.
Six boundary outputs changed, all in unproofread source-control rows. The
candidate preserved lowercase in all five reviewed common-word cases, whereas
the baseline preserved none. All 24 reviewed apparent-name outputs remained
identical. The sixth difference was the explicitly ambiguous `майн`, changed
from `Майн` to `майн`; its intended case is unknown. Source-control changes
fell from 41 to 35, but this is not a false-change rate. No synthetic typo
label gained or lost its expected spelling. No exact-Undo failures were observed
among candidate boundary changes. The replay is token-based and does not test
multiword revisions or Android UI.

This is the **same corpus that informed the ten-key selection**. The result is
post-hoc and cannot qualify the rule, its 95% threshold, natural typing or
broader names. The other selected keys include potentially meaningful names;
these particular controls do not test every context. Actual packaged source
provenance, fresh independent name/common-word contrasts, wider replay and device
acceptance are needed before any production decision.

The [runner](../../tools/typing_experiments/replay_case_evidence_candidate.py)
verifies the source-screen bindings and baseline identities, refuses unexpected
input/output shapes and compares editor state, boundary outcomes and Undo.
Three focused tests pass. The original runner version is recorded in commit
`2da069e`; it was later extended for a separate parity comparison. The [receipt](2026-10-28-q5-case-evidence-overlay.json)
records output and harness hashes; complete bindings, logs and large raw
observations are retained locally under ignored `build/q5-case-*`.
