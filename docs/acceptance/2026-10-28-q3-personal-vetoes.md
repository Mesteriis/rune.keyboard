# Q3 — personal and protected-word veto explanations (partial)

The three existing ordinary/refinement/compact checks share the same bounded
veto explanation. With protected words enabled, unavailable controls now report
`RESOURCE_UNAVAILABLE`; an actual protected-word match reports `PROTECTED_WORD`.
An eligible ready personal model's original confirmation or explicit pair
rejection reports `PERSONAL_VETO`. The recovery preflight also distinguishes
unavailable rare-word evidence from morphology unavailability.

All gates retain their previous positions. In particular, ordinary admission
still checks public/morphology evidence before personal feedback; refinement
still checks feedback before accepting the unchanged original; compact admission
still performs its own resource/source checks before the personal veto. Disabled
protection does not read the word list. Disabled/unready learning retains its
existing non-veto behavior. No model, qualification, threshold, store format or
learning mutation changes. Admission VERSION remains 1 and diagnostic schema
remains 8. The two new numeric diagnostic codes are appended after code 63.

Evidence:

- Three JVM policy tests cover the eight enabled/ready/protected combinations,
  the eight ready/confirmed/rejected combinations, case normalization, language
  isolation, exact pair scope, and snapshot immutability.
- Ten controller scenarios exercise all five specific admission reasons across
  immediate and delayed model boundaries. The independent editor document stays
  unchanged except the requested space, suggestions survive where applicable,
  no Undo transaction is created and no editor payload is read.
- Three actual API 26 instrumentation tests exercise ordinary, refinement and
  compact decisions against real Android stores and real packaged RU dictionaries: protected original, disabled protection,
  pair rejection, disabled learning and explicit confirmation. The tests require
  an explicit disposable-emulator argument and an emulator hardware check before
  obtaining stores. Only task-created AVDs were used, then stopped and deleted.
- The first instrumentation command used an incorrect runner package and failed
  before tests started. Its raw failure is retained privately. The corrected
  runner was read from APK metadata and checked against the device instrumentation
  inventory; the corrected two-test run passed; the final expanded three-test run also passed. This failed launch is not counted as a
  passing test.

All 1,285 JVM tests pass with zero failures/errors/skips, as do debug lint,
all 29 analyzer tests, the scoring boundary gate and Android test assembly.
Fresh baseline/candidate source-bound compilations replay all 12,012 regression,
1,676 stress and 1,600 calibration rows. Against pre-Q3 commit `3c3abe6`, only
previously declared reason renames differ. Against the frozen preceding step's
candidate observations, every non-timing field is identical. Candidates, allowed
booleans, scores, editor commands, text and Undo match. The two existing host
timing fields alone are excluded. All 69 asset identities match across versions
and are checked before/after; inputs, sources, compiler/JVM/stub and outputs are
bound in the adjacent evidence JSON.
The product replay does not compile the Android store adapter; its ordinary
candidate/boundary/Undo parity is separate from the real-store instrumentation
and explicit policy truth tables above. Actual boundary-journal stress accounting remains for full Q3 integration.
Candidate response rejections, bounded mechanical refusal events and editor
class/variation metadata/schema 9 are still open. This receipt does not close Q3
or claim a phone update.
