# Smart Typing: session-owned model preparation

Date: 2026-09-05. Base: `09e904cd0ab9308e687f2323cc2898bb5bea9b81`.
The phone is disconnected; this is an implementation and emulator slice, not
physical runtime qualification.

Previously, cold loading belonged to a scoring request. Cancelling an obsolete
word while `load` was in progress discarded partial weights, so the next word
could restart the expensive work. The first eligible Rune edit now attaches the
private service before local lexicon readiness and the existing 400-ms scoring
pause. Its serial worker prepares weights without receiving any text or request.
Pending words can be cancelled/replaced during preparation; only the latest
uncancelled request proceeds. A valid word causes no score and no longer discards
an already eligible binding. Rendering or a Ready callback cannot start work.

Preparation uses the existing read-only resolver, shared operation lock and
version watchers. Unbind, model invalidation, memory pressure, invalid clocks,
CPU debt and wall timeout cancel it before native cancellation is signalled.
These control operations do not wait for load. Partial state is unloaded before
the next load. An ordinary word cancellation does not cancel preparation.
Failed preparation preserves its stable numeric error and does not retry the
same queued word. Unsupported synthetic engines retain ordinary score behavior.

The existing 8,000 CPU-ms capacity, 7,500 CPU-ms admission threshold, process CPU
accounting, 3,000-ms queue limit and active deadline are unchanged. Preparation
and its first score share one admission and the original active deadline, with
no credit refund. The reservation stores only generation/start time, expires at
the original deadline and is consumed once. Later scores require normal credit.
The watchdog runs only during work/cleanup. Prepared weights unload after the
existing 60-second idle period, even if no word was ever scored; context creation
remains lazy. No foreground service, permission, network, editor readback or
persistent payload was added.

## Validation

- JVM: **691/691 PASS**, zero failures/errors/skips. New preparation coverage
  checks pending replacement/cancellation, exact CPU debit, shared deadline,
  expired admission, idle unload, failure codes and no automatic load retry.
  Coordinator tests cover early preparation before lexicon readiness and vetoes
  for unavailable/unqualified runtime, sensitive fields and disabled features.
- API 26: **33/33 PASS**, 9.945 s. API 37: **33/33 PASS**, 10.186 s.
  `ActiveModelLifecycleInstrumentedTest` uses the production adapter/resolver/
  worker and real file locks/watchers with a synthetic runtime. It proves that
  cancelled words share one load, whereas session unbind cancels partial load
  and rebind loads afresh. `ScoringLifecycleInstrumentedTest` and
  `AndroidModelCandidatesInstrumentedTest` exercise the real private Binder with
  synthetic numeric engines, stale-result rejection and post-Space Undo.
  These are not complete real-GGUF IME/editor flows or device performance tests.
- Prescribed lint, debug/release/profile assembly, privacy, intelligence
  boundary, forbidden-dependency and native-symbol gates: **PASS**.
- Host exact-model startup diagnostic and native contracts are archived under
  `tools/test-native-scoring/results/2026-09-05-startup-stages/`.
  This identifies startup stages on macOS; it does not predict Fold timing or
  battery use. Android results and tested APK identities are under
  `tools/qa/smart-typing-0.3/results/2026-09-05-model-preparation/`.

The mandatory post-commit fresh JVM command is
`./gradlew testDebugUnitTest --rerun-tasks`, with local output at
`build/smart-typing-0.3/model-preparation-postcommit-jvm.log`.

Physical optimized cold/warm scoring, energy/duty and complete Fold acceptance
remain **UNRUN for this slice**. `ModelRuntimeQualification.CURRENT` stays false;
version stays 0.2.0. Corpus, frozen thresholds and model bytes are unchanged.
No remote push or PR was made.
