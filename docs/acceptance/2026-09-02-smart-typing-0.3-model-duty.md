# Smart Typing 0.3 — process CPU duty, 2026-09-02

Baseline: `b4d76cdbd53780ed83f77ef5e15f3e3022fbe4dc`. The service now accounts
whole-process CPU across load/score/failure/cleanup and Service recreation.
Its numeric owner and exclusive native lease survive until process exit;
new workers cannot enter a retiring worker's runtime. Cancellation precedes
native signalling, cleanup remains serial and incurs debt, and denied requests
neither retry nor prolong idle residency. The IME still has no model consumer.

The development profile is capacity/refill 8000 CPU-ms per 60000 elapsed-ms,
7500 CPU-ms minimum admission, separate 3000 ms queue/active deadlines, and
50 ms delay between active checks. No checks run while idle/unloaded. These are
sampled admission/cancellation rules, not a strict CPU ceiling or measured energy
budget. Cooperative cancellation and mandatory cleanup can overshoot.

Critical/background/low-memory latches suspension before worker cancellation.
Revision changes, model invalidation and duplicate binds cannot clear it.
Actual unbind followed by bind/rebind can rearm, retaining debt. Invalid clocks
fault closed until process restart. Existing 60-second idle unload is preserved.

## Integration findings and corrections

The eleven applied source files initially matched independently reviewed
proposal `d10b6a56ce939df1997a2e241ceb573ed07c3be81441b2a4f6f536496ea6b817`.
Parent integration then found two defects not caught by the saved review:

- Full lint rejected `scheduleAtFixedRate` because cached-process pauses can
  cause accumulated checks to execute in bursts. Production now uses
  `scheduleWithFixedDelay`; the existing DiscouragedApi gate passes without
  suppression. The failing gate log is retained.
- Both Android matrices initially ran 42 tests with two failures: after actual
  scoring unbind/bind while a separate control binding kept the Service alive,
  requests 703/304 still returned UNAVAILABLE. Returning false from `onUnbind`
  left no lifecycle callback to rearm the worker. Production now returns true
  and handles `onRebind`. This replaces the earlier proposal's false-return
  decision, following the [Android bound-service lifecycle contract](https://developer.android.com/develop/background-work/services/bound-services#Lifecycle).
  The debug fixture acknowledges actual unbind and bind/rebind callbacks through
  bounded latches. It does not call the worker's rearm method from a test command.
  The original failed runs and strict recovery assertions are retained.

The archived independent review applies to the initial proposal. These two
parent corrections received local source review and the executed gates below;
they are not represented as independently reviewed patches.

## Executed validation

- `./gradlew testDebugUnitTest --rerun-tasks`: **555/555 PASS**, no failures,
  errors or skips, 46 tasks executed, after the final source corrections.
- Prescribed lint/debug/release/profile/privacy/dependency/native gates plus
  `:app:assembleDebugAndroidTest`: **PASS**, 267 tasks, 45 executed.
- Final complete Android matrix: **API 26 42/42 PASS**, 17.446 s;
  **API 37 42/42 PASS**, 17.850 s. Each contains 13 client tests using real main
  Handler, 10 remote Binder lifecycle tests, 15 adapter/watch tests with a
  synthetic runtime, and 4 IPC/manifest/observer tests. Model-duty owner/worker
  tests add 25 controlled-clock cases to JVM coverage. Android adapter fixtures
  use isolated real-clock owners; the remote service uses the process singleton.

Evidence and final source/APK hashes are in
`tools/qa/smart-typing-0.3/results/2026-09-02-model-duty/`. APK hashes identify
installed build inputs, not device readback. No screenshot/hierarchy capture was
requested. Android runner exit code alone was not used as a pass criterion;
terminal JUnit counts were checked. Initial sandbox failures accessing Gradle's
cache/ADB were resolved through approved execution before tests ran.

## Remaining gates

The predeclared 2/4/8-candidate synthetic trace experiment, actual model duty
coverage/overshoot, usable-before-boundary rate, full physical Fold matrix and
energy qualification remain **UNRUN**. ADB currently reports only emulators;
physical Fold is **BLOCKED** for this slice. External CI and immutable model
publication are unrun. Functional test durations are not model latency results.
Readiness monitoring, PR7 model-assisted ranking/AutoReplace and PR9 contextual
suggestions remain open, as do final quality and release gates. Version remains
0.2.0; this slice neither publishes a model nor qualifies Smart Typing 0.3.
