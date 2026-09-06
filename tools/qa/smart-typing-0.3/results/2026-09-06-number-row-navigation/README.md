# Number-row settings navigation — 2026-09-06

Baseline product commit: c0b0280abfc4f0093835a99245d7e42ccc9d47f8. Test-only change; product behavior and assertions are unchanged.

The original cover scope had 26 PASS and one failure finding the number-row setting, before numeric/version/hostname assertions. An unchanged isolated run passed (57.964 s), but the unchanged five-case mechanical class reproduced the same failure (4 PASS, 1 FAIL; 54.675 s).

The fixture used default UiScrollable swipes spanning 80% of the full display. Device debug logs showed 2016px swipes, with Settings ending below the missing target. The selector used the correct Russian title, the row is constructed unconditionally, and the library already scrolls to the beginning before searching.

One variable changed: a 37.5% swipe dead zone gives 25%-height steps (630px on this cover). This bounds navigation steps while retaining the real Settings click, preference persistence, next input view, key visibility, three protected-token examples, composing ownership, immediate Undo and zero readback assertions. No timeout or assertion was relaxed.

Validation:

- Fold cover/API36: mechanical class 5/5 PASS, 101.773 s.
- API26: affected test 1/1 PASS, 56.401 s.
- API37: affected test 1/1 PASS, 56.755 s.
- Full prescribed lint/build/privacy/dependency/native gates: PASS, 240 tasks.

The experiment supports the shorter navigation step as a fixture repair; it does not establish a production punctuation defect or fully attribute framework gesture internals. Original failures remain included. Raw phone screenshots/XML and private diagnostic files are excluded. APK and source hashes are in number-row-quarter-inputs.json. Mandatory postcommit JVM validation is recorded separately after commit.
