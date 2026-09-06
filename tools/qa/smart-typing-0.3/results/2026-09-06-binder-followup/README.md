# API26 punctuation editor follow-up — 2026-09-06

Source e718072 plus the three test-file identities in corrected-preflight.json.
The installed APKs are also identified there. Public synthetic fixtures only;
no full model is installed in this emulator.

- Initial contextual3/settings6 run:6/9 PASS,91.055s. All three contextual tests
  stopped during setup at an invalid lifetime-zero read-counter expectation.
- The isolated diagnostic named the counter:legacy NORMAL caps-mode reads=5.
  The resident IME performs its pre-existing getCursorCapsMode lookup in response
  to editor callbacks while the separate test controller owns the edits.
- Corrected contextual3/settings6/mechanical4 run:**13/13 PASS**,191.748s.
  Settings now assert exact effective availability instead of unconditionally
  expecting Unavailable. Payload read counters remain zero throughout the
  contextual tests; every counter including caps stays unchanged during checked
  score-only/no-edit operations after preceding callbacks settle.
- Mechanical fixtures enter3.14,1.2.3,example.com through real Rune keys without
  layer changes. Owned comma spans and unchanged connection/key instances are
  asserted; same-session ordinary-word insertion and Undo are positive controls.
- Prescribed local gates PASS. Policy e718072 post-commit JVM707/707 PASS.

Initial failures and the diagnostic are retained. The revised contextual test
and mechanical addition passed independent source review before this receipt.
The full application instrumentation suite is a separate run; these13 tests do
not establish the complete API26 matrix, API37 or physical Fold acceptance.

Contextual scores and valid-word membership are synthetic. The real
controller/executor-to-:qa_editor Binder boundary is exercised, but the test
forwards numeric selection observations to its separate controller. It does not
exercise a physical candidate-strip tap or actual model service scoring. New
phone APK installation still awaits confirmed reinstall/restore because the
installed debug signing key differs; old phone passes do not verify these tests.
