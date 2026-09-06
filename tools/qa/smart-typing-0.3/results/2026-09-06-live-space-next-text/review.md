# Live next-text invalidation during Space grace — review

**Specification verdict: PASS. Code-quality verdict: PASS.** No actionable correctness or false-green gap was found in the two-file QA delta against `3504f31521ec531bb58734d8318b86e8af401220`.

The shared `observeOwnedSpaceWithinGrace()` helper still establishes the same real Space boundary as the reviewed positive case: it caches Space geometry before injection, identifies the unique focused QA editor/window/class, observes the exact `a helllo` → `a helllo ` text-change event, reads the real coordinator's `spaceStartedAt`, and requires the captured old token to remain the controller's current Space correction before the unchanged 250 ms deadline. Event and touch resources retain `finally` cleanup. The API 26 null-source fallback remains constrained by package, event type, window, class, exact before/after text, and the previously established unique editor identity.

The new `spaceThenTypeAAndReleaseWithinGrace()` caches the lowercase `a` key geometry before Space, so no accessibility lookup can consume the live window after the Space barrier. It injects actual DOWN/UP events, then requires current production state to contain composing word `a`, exact context `a helllo a`, no automatic edit, no pending ranking, and neither old Space nor old model-ranking ownership. It checks elapsed uptime below 250 ms both before release and after the synchronous release command returns. The case therefore cannot qualify through ordinary Space expiry, an ignored next key, or release after expiry.

After exact remote completion, the test requires editor text `a helllo a`, caret 10, and owned composing span 8–10. Relative to the pre-Space snapshot, only `finish +1` and `compose +2` are allowed; region, commit, connection, and raw-key deltas remain zero, and all six payload-read counters remain zero. A subsequent idle snapshot must be identical. The actual coordinator and visible strip must contain exactly the current selected Original `a`, with the old `helllo` Original and `hello` correction absent, no pending or revived old token, and no observed callback for that token. These assertions exclude a stale correction followed by reversal and retain the stated limitation that cancellation may suppress the old callback before main-thread delivery.

The existing `releasedReplyWithinSpaceGraceCorrectsAndCanUndo` test body is unchanged. Its extracted wrapper preserves release of the exact held request, separate waits for engine completion and asynchronous Binder delivery, the post-delegate callback timestamp within 250 ms, exact correction command deltas, and immediate Undo. It remains the companion positive proving that an otherwise current response is accepted within the same real grace window. Recycling the already matched accessibility event now occurs when the helper returns; it does not alter the Space action or production state, and both emulator runs passed the paired methods.

Frozen evidence is coherent:

- Source hashes match `inputs.json`: fixture `ed64f2a2986318bdeabf73114ee25b8c660963b8e54ce7c101cd76782a3a870a`; instrumented test `c439b3bf74b6ebc06dd1cbc1e076f0a5301f2c3d37625b093b1c24c36b29fdfe`.
- `qa.patch` is byte-identical to the current two-file diff from `3504f31`, SHA-256 `0023032a6721b67fe338292f0b8fe6f07cbb04bd75c3a04386602a2037aa8e11`.
- API 26: both methods passed in 23.876 seconds; log SHA-256 `b37edd3dadbced901d01a12d53c1b7aeb8c5b1941d68723086b8a9595537cf7e`.
- API 37: both methods passed in 22.414 seconds; log SHA-256 `254725e4669c62e050d6ba451b1fc09f5281d7253df32f929a6e2073d880ce37`.
- Both logs contain two code-0 method completions, `OK (2 tests)`, and final instrumentation code `-1`.

This closes the emulator-only next-text row of `task-live-late-replies-brief.md`. It exercises the resident IME, coordinator/controller, fake-engine process, and real editor Binder with fixed readiness, lexicon, and numeric scores. It does not add physical-device, real-GGUF, latency, or already-dispatched-stale-callback coverage.

Review activity was read-only except for this report. No Gradle, device, model, network, or source command was run.
