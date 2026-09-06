# Smart Typing: finish an admitted spelling request after Space

Date: 2026-09-05. Base: `608ea2ed022e0ea0cc1919f8cb1d69128c0fe97e`.
This follows the user's report that Space discarded useful processing of the
previous word. It refines the earlier boundary-only rule for ordinary Space.

Space is delivered immediately. With a ready, connected, qualified model and
AutoReplace enabled, an existing pause may dispatch once at Space; an in-flight
request continues with its original session/revision/request/candidate IDs.
There is no second request and no wait in the text action. The controller may
apply its calibrated result for **250 ms after Space**, only to the complete
Rune-owned word plus that single composing space. The same owner certifies the
old request against the exact new document revision, caret, composing region and
RAM suffix. Transport additionally requires its current connection generation
and latest full token. Callback dispatch cannot bypass the elapsed deadline if
the main-thread expiry timer was delayed.

The next text action, Backspace, Original selection, cursor/layer/language/editor
or preference change, lost connection and expiry invalidate the request. OFF,
suggestions-only, unavailable/unqualified runtime, protected/unknown token
boundaries and overlong composing regions do not admit this path. No candidate
set ready at Space means ordinary fallback. Enter/SEND, punctuation and the
double-space gesture retain their existing boundary behavior. A ready result is
still consumed immediately at Space, without an additional request.

A late correction uses a three-call guarded editor batch: select only the known
suffix, commit its correction, then compose the trailing space. The same single
Undo restores the complete original spelling as composition on first Backspace.
Subsequent typing closes it. Refused commands and reentrant ownership loss stop
the batch without replay. The implementation adds no editor reads, generated
text, persistent payload, model binding on readiness callbacks, or worker CPU
allowance. The 250-ms window is a limit on late UI changes, not a model latency
or battery qualification.

## Verification

- Targeted controller/coordinator JVM suite: **86/86 PASS**, including exact
  RU/EN/ES Unicode restoration, invalid request IDs, timeout with a delayed timer,
  single submission, next-key cancellation, policy/lifecycle loss, rejected and
  reentrant editor calls. Its editor proxy rejects reads and ordinary deletes.
- **API 26: 32/32 PASS**, 138.330 seconds; **API 37: 32/32 PASS**, 167.281 seconds.
  Classes: `ScoringLifecycleInstrumentedTest`, `AndroidModelCandidatesInstrumentedTest`,
  `SmartTypingComposingInstrumentedTest`.
- Factory/client tests use the real private Binder with a synthetic numeric
  engine and a controller editor fixture. They verify that one explicitly owned
  post-Space token is accepted while other old-revision replies are rejected,
  with zero main-thread metadata reads and immediate Undo. They do **not** prove
  real-GGUF correction quality or a complete automatic IME/editor/model flow.
- Separate composing tests use the actual `:qa_editor` Binder `InputConnection`.
  The Backspace regression now verifies that deleting Rune's space reopens all
  of `ab`, then typing `d` maintains composition/Original for `abd`.
- Prescribed lint, debug/release/profile, privacy, architecture/dependency and
  native symbol gates passed. Integration JVM suite: **680/680 PASS**, zero
  failures/errors/skips. The mandatory fresh post-commit command is
  `./gradlew testDebugUnitTest --rerun-tasks`; its output is retained locally at
  `build/smart-typing-0.3/space-correction-postcommit-jvm.log`.
- The final gate rebuild produced byte-identical app/test APKs to those installed
  for both Android runs; the later source adjustment changed comments only.

Numeric Android results and tested APK identities are retained in
`tools/qa/smart-typing-0.3/results/2026-09-05-space-completion/`. Phone disconnected:
physical optimized cold/warm inference, duty/energy and complete Fold acceptance
remain **UNRUN**. `ModelRuntimeQualification.CURRENT` stays false and the version
stays 0.2.0. No model thresholds, frozen corpus or holdout were changed.
