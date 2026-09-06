# Duty trace atomic idle transition — 2026-09-03

Candidate-width tooling was committed as `03cea4523079d57b3efc9066157f09cbe807ee4e`.
Its mandatory fresh JVM run produced596 tests /1 failure, in
`ModelDutyTraceTest.fixedTypingPressureAndRecoveryTrace[ES-8]`, at the second
idle-phase `assertNull(checks.task)`. The failed log and JUnit XML are preserved
in `tools/qa/smart-typing-0.3/results/2026-09-03-duty-trace-idle-transition/`.

The fixture advanced its clock90000 ms and then separately sampled the owner
and scheduler. Between those operations the real worker could observe the new
idle age, start required unload, and correctly keep the cleanup CPU timer active.
This was not a retained scoring timer. `LatestScoringWorker.runNext` reads idle
age through synchronized `ModelDutyOwner.account`; cleanup starts its operation
before `engine.unload` and retires it in finally. The existing deterministic
blocked-unload test separately proves that the timer must remain live there.

The fixture now performs its clock advance, credit accounting and both timer
assertions while holding the same owner monitor. This defines one atomic
virtual-time transition before another worker action can observe its new time.
No worker monitor is acquired in that block, preserving owner/worker lock order.
An expired idle unload may execute after the snapshot is released. Assertions,
trace phases, public requests, simulated costs, limits and production code are
unchanged; no sleeps or retries were introduced.

Targeted27 tests PASS (nine traces and18 duty-worker cases). The trace report
validator accepts all nine rows; every numeric result equals the frozen prior
report, including request counts, simulated CPU/wall totals and final debt.
The first combined run passed the duty traces but exposed an independent fixture
race in `LazyPackedLexiconsTest`: release could win before the interrupted source
entered its latch wait, so catching `InterruptedException` was not guaranteed.
The test now observes the interrupt before releasing the source; its stale-ready,
pending-drop and next-language assertions are unchanged. Initial failure retained.

Final JVM596/596 PASS, zero failures/errors/skips. All prescribed lint, three
build variants, privacy, dependency, IME boundary and native-symbol gates PASS.
All nine numeric trace rows remain identical to the prior frozen report.
The required fresh post-commit run is reported against the resulting commit.
These test synchronization changes do not qualify physical battery behavior
or close any model/quality/device release gate.
