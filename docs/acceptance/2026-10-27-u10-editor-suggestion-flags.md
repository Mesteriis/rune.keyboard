# U10: editor-owned suggestions and unchanged search submission

Two regressions first failed against the old production code: application
completion/filter fields still enabled Smart Typing, and NO_SUGGESTIONS still
allowed a candidate request. That targeted run executed 96 tests with two
failures. No runtime change preceded this reproduction.

`EditorContext` now keeps NO_SUGGESTIONS as normal TEXT for owned composing and
mechanics while independently denying `editorAllowsSuggestions`. The candidate
owner gates every visible/local/model/contextual path with that flag; the
controller independently rejects requests and boundary/editor-action correction.
The service disables personal, phrase, touch and pattern learning/adaptation in
such fields. AUTO_CORRECT cannot override suppression. The effective diagnostic
features retain configured mechanics and app profiles only; the appended stable
reason is EDITOR_SUGGESTIONS_DISABLED.

AUTO_COMPLETE and VARIATION_FILTER use APPLICATION_COMPLETION with the usual
letter layout and plain commits, without composing or Smart Typing. Existing
password/sensitive handling remains unchanged. Ordinary text retains its prior
policy. USER_GUIDE and ARCHITECTURE document the compatibility tradeoff, including
AutoCompleteTextView chat/mention fields and search fields without these flags.

Validation:

- All 1,168 JVM tests pass, including six new tests for metadata combinations,
  owner/request/model gates, unchanged search, exact finish operation and refusal.
- IME intelligence boundary, release privacy gate and final debug lint pass.
- On a fresh isolated Android 36 emulator, ten instrumentation tests pass: three
  new editor-flag scenarios plus seven existing sensitive/special-field cases.
  Each scenario first proves the normal pipeline's real composing, caps lookup,
  scoring bind and model requests are observable. Suppressed fields then have a
  hidden strip, no new candidate/model activity and no delayed model work.
  The test model backend uses the real Binder lifecycle; this does not measure
  downloaded-model quality or performance.
- Actual remote SEARCH receives exactly `helllo` with the original spelling and
  action ID for AUTO_COMPLETE, FILTER and NO_SUGGESTIONS. NO_SUGGESTIONS retains
  real composition, rejects learning despite enabled preferences, and preserves
  double-space mechanics via a real injected double-tap gesture. The initial
  test used two ordinary spaced UI taps and failed the gesture assertion; it was
  replaced with the existing timed gesture driver without changing product code.
- Both source-bound current-controller replays complete all 12,000 original
  frozen inputs (4,000 per language). Every observation field except the two
  explicit host timing fields has byte-identical canonical JSON before/after.
  All 2,292 automatic changes retain exact Backspace Undo. No row is dropped and
  no error row is accepted. This is regression parity, not fresh qualification.

The first replay exposed 210 long protected-input failures in diagnostic-only
policy/morphology observers. Two failed runs are preserved. After classifying
that pre-existing harness problem, lexical-only observers were guarded or made
candidate-dependent; all protected inputs still traverse the real controller.
A focused 216-row protected/control smoke passed before the complete baseline.
The same repaired harness was used for both sides of the policy comparison.
Production spelling thresholds, model parameters and source certificates were
not changed by that repair.

The adjacent evidence JSON binds production/test/harness sources, APKs, frozen
input, observation projections and actual check outcomes. The disposable
emulator/AVD was removed after draining tests. No physical Fold check or remote
CI result is claimed. U10's local acceptance is verified; other review cards
retain their own requirements.
