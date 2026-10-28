# Q8: independent editor profiles and late composition cleanup

An independent `EditorSimulator` now owns its own document, caret and composing
span and runs the real `EditorCommandExecutor` through an `InputConnection`
proxy. It does not change the existing `CorrectionBoundaryTest.Fixture`.
Callbacks are queued until a controller command returns; batch results coalesce.
External prefix insertion shifts the editor's own span before its acknowledgement.
Payload-read attempts are forbidden and explicitly checked after every test.

The profile contracts were recorded before the first execution:

| Profile | Availability and safety outcome |
| --- | --- |
| Normal control | Correction and exact snapshot Undo; external prefix intact. |
| No callback on stationary cursor | Session stays active; next word corrects and Undo remains exact. |
| Selection before composition | Conservative session disable, intact word and no revived Undo. |
| Prefix insertion before region acknowledgement | External prefix intact, session disabled, Undo absent, later literal input preserved. |
| Silent span loss | Documented duplicate-composition degradation, session disabled, Undo absent; not a compatibility pass. |

## Reproduction and fix

Against the original controller, five tests ran and one failed. With a two-phase
selection/composition callback, the editor contained the word but first reported
no composing span. Rune revoked ownership and disabled the session. The later
span report was ignored, leaving the span live, so a subsequent plain Space
replaced the word. The expected `outside teh ` became `outside `.

The controller now remembers that lost owned composition for the same session.
Its first later reported span receives one non-text `FinishComposingText`, even
while Smart Typing remains disabled. This never restores composition ownership,
text replacement authority, candidates or Undo. The marker clears before cleanup
and on disable/end/start lifecycle transitions. A new password session cannot
receive the obsolete cleanup. Refusal and exceptions are attempted once; an
editor that refuses cleanup is not guaranteed to remove its span.

All nine simulator tests pass, including both refused/throwing cleanup and
session replacement. Silent unreported span removal remains an explicit
unsupported degradation. These are synthetic protocol profiles; actual callback
traces from qa_editor/WebView and third-party editors remain required.

## Integration evidence

- All 1,352 JVM tests pass with zero failures/errors/skips; the scoring boundary
  also passes. The complete existing boundary fixture is unchanged.
- The actual two-profile CI replay command passes all 14,160 rows. Both fresh
  JVM projections agree for each profile and match the existing separate
  baselines; no baseline was updated and no model was called. Runtime sources
  and all 69 assets remain bound by the existing driver.
- Debug/test APK compilation and debug lint pass. The separate numeric-export
  navigation repair restores the pre-existing architectural boundary failure,
  with an API26 native UI check. That check is not a native callback-profile test.
- Initial combined integration failures are retained: the pre-existing numeric
  export dependency closure, then the expected strict dirty-source refusal for
  the release build. A fresh tracked-clean checkout of committed source e2c49c4
  then passed `imeIntelligenceBoundary`, `privacyGateRelease` and
  `privacyGateProfile` offline, including actual debug/release/profile packaging.
  Git was clean before and after; signing material was not copied. All three
  APK hashes are recorded. No exemption was added to either guard.
- The task-owned API26 emulator was stopped and deleted. Fold was not used.

The [machine receipt](2026-10-28-q8-editor-simulator-evidence.json) binds the
original failure, recoverable initial fixture bytes, final tests, replay
comparisons, sources and cleanup. Q8 remains in progress for trace calibration,
qa_editor profiles/debug reasons and APP-001…005 continuation measurements on
Fold. This does not establish universal editor compatibility or full review
completion.
