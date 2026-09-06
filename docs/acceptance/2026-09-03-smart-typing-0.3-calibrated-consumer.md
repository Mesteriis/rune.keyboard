# Calibrated suggestion consumer — 2026-09-03

Baseline `d1959bb`. The production controller now orders live spelling
suggestions with the same deterministic/model coefficients used in calibration.
Raw average model probability is no longer the only ordering signal. A candidate
must pass both calibrated margins and minimum length to be highlighted; Original
remains available. Partial retrieval can order suggestions but never supplies a
preferred correction. These changes do not enable automatic spelling replacement.

The local coordinator fixes three alternatives before starting search, yielding
at most four model candidates including Original. It never lowers the requested
width after exhaustion. The generic and packed generators retain their shared
search/verification bounds. This choice follows the four-candidate calibration
and prior physical search measurements; it is not a new energy measurement.

Each accepted generation is copied with its immutable records and the active
language captured at request creation. Model callbacks retain the exact existing
session/revision/request/candidate-ID/selection-identity checks. Ranking performs
no editor operation and does not change composition, the original-tap veto or
the existing inference debounce/CPU duty limits. Bad numeric evidence falls back
to deterministic ranking. Manual candidate IDs continue to address source
indices, even when candidates move into or out of the visible strip.

The 6000 numeric calibration controls now also check all six product coefficient
sets and every product deterministic/combined preferred ID. Added tests prove
that generated features can defeat the raw model favorite; request language fixes
minimum-length policy; partial search preserves its veto; and four-candidate
width reaches the lexicon before enumeration and the model before submission.
Five original tests failed because they asserted the old order/highlight. Their
expectations now describe the calibrated behavior, preserving editor-write and
identity assertions. One synthetic length-difference fixture now uses absolute
difference, matching the actual generator.

Fresh JVM 607/607 PASS with zero failures/errors/skips; final targeted 76/76 PASS.
Full prescribed gates and Android test APK PASS. The first full build executed
277 tasks; final build after numeric constructor validation and Android assertion
updates passed 267 tasks, 44 executed. Post-commit fresh JVM remains required.
API26 live-candidate/settings/remote-Binder suite: 12/12 PASS, 223.156 s.
API37 initial suite: 11 PASS / 1 FAIL, 268.482 s. The Ready/remote-client test
did not observe its model callback within 5 s. Exact unchanged isolated retry:
1/1 PASS, 0.478 s. Exact unchanged full suite repeated separately: 12/12 PASS,
151.343 s. Initial cause remains unestablished; no timeout or assertion was
relaxed to obtain the retries. This is scoped synthetic-model integration,
not real-model or full device qualification. Python contracts 19/19 PASS.

Evidence: `tools/qa/smart-typing-0.3/results/2026-09-03-calibrated-consumer/`.
The initial failure and all retries are retained with source/APK identities.

The phone later reconnected. The user-authorized debug APK was installed using
the named `phone` profile, with `Installation successful!`; app launch succeeded.
Fresh UI inspection showed Rune setup and `Не включена`. Thus installation and
app launch PASS, but keyboard activation and physical typing are not claimed.
No screenshot or hierarchy was saved. No app data was cleared or package removed.

Installed APK SHA256:
`9675067496e9509af9350969b7e5fa87aa2c974006b2477a388c89ea297a7157`.
Device: Samsung SM-F966B, Android16. Version remains 0.2.0.

Full correction Undo/automatic boundary consumer, contextual punctuation, frozen
final holdout, complete Fold/energy qualification, external CI and model
publication remain open. No push or remote PR was performed.
