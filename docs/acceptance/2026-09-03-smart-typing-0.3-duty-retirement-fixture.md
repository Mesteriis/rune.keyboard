# CPU duty fixture synchronization — 2026-09-03

The mandatory fresh JVM run after commit
`17d539c0b1f938d31a92d389689411b0b1a14691` had 592 passes and one failure:
`deniedRequestsNeverEnterEngineOrExtendExistingIdleUnload` observed a still-active
timer after the fake engine's unloaded latch fired.

The latch fires on entry to `engine.unload()`. `LatestScoringWorker.cleanup`
correctly keeps CPU accounting active throughout that call, then retires its
operation/timer in finally. Waiting for engine entry did not establish that the
finally block had executed. The test now observes scheduler stop before asserting
idle state. A new blocked-unload case deterministically proves that the timer is
present during cleanup and absent after retirement. The test also crosses the
worker control monitor for the already-completed request before advancing its
virtual clock, so the finish callback cannot race later idleAt accounting.

No production code, timeout allowance or assertion about idle behavior was
relaxed. Targeted duty tests: **18/18 PASS**. Final full JVM: **594/594 PASS**,
zero failures/errors/skips. Prescribed product build/lint/privacy/dependency/native
gates: PASS, 238 tasks (27 executed). Android/runtime behavior is unchanged;
this is not an additional device or energy qualification.

The original failed run and actual passing logs/source identity are preserved in
`tools/qa/smart-typing-0.3/results/2026-09-03-duty-retirement-fixture/`.
The broader Smart Typing objective, quality and physical performance gates remain
open. No push, remote PR, version bump or publication occurred.
