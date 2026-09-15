# Personal typing implementation

User-approved scope: implement all five ideas from the morphology/style experiment in the Android keyboard: protect valid rare words, separate suggestions from automatic admission, learn explicit correction feedback, adapt touch geometry, offer personal phrase continuations.

## Constraints
- Continue codex/morphology-style worktree; preserve other work. No uploads of conversations; no private corpus or profile in git/APK.
- Existing editor ownership, sensitive/no-learning fields, explicit undo, language/layer and stale-result gates remain authoritative.
- New evidence may veto automatic correction and order manual suggestions; it must not bypass existing release qualification.
- Bounded local storage in no_backup, reset/disable controls, no logging of typing. Only acknowledged explicit feedback trains spelling and touch. Phrase training admits validated words, respects sentence boundaries.
- No claim of Android quality improvement without on-device measurements or independent unseen labels.

## Tasks
1. Implement dictionary membership/lemma asset and conservative automatic-admission guard; regression tests; reproducible dictionary export/provenance.
2. Implement bounded personal feedback and phrase model, local persistence and profile import format; tests. Explicit rejection overrides accepted pairs; raw frequency does not certify spelling.
3. Implement touch sample capture and bounded per-layout/size/language calibration from confirmed samples; tests. No automatic self-training from inferred corrections.
4. Integrate above in session and service, owned continuation selection UI, settings/import/reset, regression coverage across failed/stale editor edits, sensitive fields and lifecycle.
5. Run host tests, JVM tests, Android build/lint/privacy checks appropriate to changes; review final diff; document behavior and limitations.

## Interfaces / review preflight
| Tasks | Shared interface | Resolution |
|---|---|---|
| 1,4 | generation -> guard decision | worker owns guard and asset classes; controller integrates all automatic paths |
| 2,4 | feedback/continuations | worker owns pure model/store; controller owns session events/settings |
| 3,4 | physical sample -> confirmed word | worker owns UI callback/model; controller owns privacy/lifecycle/editor acknowledgement |
| 1 | membership and ambiguous candidates | real dictionary evidence, unknown analysis cannot establish intent |
| 2 | feedback and phrase learning | require explicit positive targets, reject overrides; bounded counts/files |
| 3 | calibration vs current taps | learn only after confirmation; partition by actual geometry |
| 4 | callbacks and ownership | post-success only; stale/failing edits never train |
| 5 | measurement | tests prove mechanics, not unseen correction accuracy |
