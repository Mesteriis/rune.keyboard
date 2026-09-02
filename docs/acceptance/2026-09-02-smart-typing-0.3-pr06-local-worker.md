# Smart Typing 0.3 — PR6 local worker checkpoint

Date: 2026-09-02. Reader checkpoint base: `773fb15c531859ced3ec7843c946c4b0a3a67c97`. This checkpoint adds the local deterministic candidate worker. It does not enable spelling suggestions in the IME or close PR6.

`LocalCandidateWorker` owns one serial compute thread, one replacing pending request and one replaceable reply slot. It accepts explicitly eligible bounded token snapshots with numeric session/revision/request IDs. Cancellation and payload invalidation are signaled directly, without waiting behind computation. Results pass freshness checks both at compute completion and at owner-thread delivery. A coalesced owner action retains the worker rather than a captured request or result. Failure diagnostics contain no input text.

The worker delegates to the existing generator and changes no routing, weighted features, ranking, shared 8192-state/64-verification budget or partial-result veto. It neither opens indexes nor calls a model, network or editor. Validated index ownership, lazy loading, the main-thread dispatcher, live editor/session/composition checks and strip publication remain consumer work. It does not authorize AutoReplace or model inference on each key.

## Verified checks

- Independent review approved the unchanged worker proposal `a1bc7446b737b8f4210b0209f05e230e598eb97ea06f6487d9c67852cf888078`.
- **17 new worker tests PASS** in root. Coverage includes active/pending replacement and cancellation, latest-request delivery, stale queued callbacks after cancel/close, reused numeric IDs, callback reentrancy, failures followed by success, bounded/protected admission and partial/valid-word vetoes.
- Actual-worker weak-reference tests cover pending, idle and queued-delivery payload release, with strongly retained positive controls. These prove JVM reachability behavior, not ART secure erasure or immediate release of an active reader's stack. Active cancellation still depends on reader checkpoints; close does not join the worker.
- Fresh integrated root JVM: **391/391 PASS**, zero failures/errors/skips; 46 tasks executed. Evidence: `build/smart-typing-0.3/pr06-local-worker-jvm-integrated.log` and the corresponding JUnit XML reports.
- Subsequent full prescribed build/lint/privacy/dependency/native gates: **PASS**, 298 tasks / 64 executed. Evidence: `build/smart-typing-0.3/pr06-packaged-assets-gates.log`. Build success is not Android reader-runtime qualification.

The required post-commit fresh JVM rerun remains pending and must be recorded against the actual worker commit.

No live IME consumer, final weighted/cross-language development or holdout quality, calibrated AutoReplace, model duty policy, Fold typing lifecycle or physical energy result is claimed here. The old unit-distance format measurements remain distinct from the weighted production contract. Version remains 0.2.0.
