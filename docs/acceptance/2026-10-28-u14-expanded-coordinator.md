# U14: coordinator admission for expanded candidates

The coordinator now opens and resolves the controller's single-use hidden
candidate snapshot only while the current editor and input view permit
suggestions, the strip and spelling are enabled, and the candidate language
matches the current owner. The coordinator binds its handle to the complete
owner state and its own epoch. Closing, editing, invalidation, normal candidate
selection, new accepted replies and coordinator shutdown clear the handle.
A click rechecks these conditions before using the existing guarded controller
transaction; the automatic path remains independent of hidden choices.

Tests exercise successful selection, single-use behavior, input invalidation,
and owner changes after opening: editor policy, suggestions, active view,
selection, layer, strip, correction mode, manual-expansion setting and
language. Disallowed state returns no editor commands. All 1,358 JVM tests
passed without skips, `lintDebug` passed, and the scoring-boundary verifier
passed. The adjacent evidence binds the tested sources.

This is still an internal API; no visible expansion control or popup is wired.
UI touch cancellation, accessibility, first-two visual parity and Fold display
measurements remain required. The 12,000-row controller replay recorded in
u14-expanded-core precedes this coordinator change; no new replay or physical
phone test is claimed here.
