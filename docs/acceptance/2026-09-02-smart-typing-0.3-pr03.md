# Smart Typing 0.3 — private inference checkpoint, 2026-09-02

Baseline: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`.
Slice parent: `585f380691baabb7bec25ae5bd25067880d54158`.
PR3 supplies private scoring infrastructure. IME/controller integration, spelling,
contextual punctuation, settings and final quality/energy qualification remain
later slices. App version remains 0.2.0.

## Implemented contract

- Private bound ModelInferenceService in `:model_runtime`, exported=false, without
  intent-filter, foreground service or extra permission; explicit same-UID check.
- Oneway request/callback AIDL, scalar length checks before allocations, bounded
  strict-UTF-8 text and 1–8 unique candidate IDs. Replies carry only opaque IDs,
  numeric scores/counts/timing and stable codes; no arbitrary Bundle or model path.
- One worker with one active and one replacing pending request. Cancellation marks
  the request token before immediate native cancellation; it does not join scoring
  or queue cancellation behind inference. Idle unload is 60 seconds; critical
  memory, model invalidation, unbind and close cancel/drop work and request unload.
- Main-thread client uses session/revision/request/candidate guards plus live
  composition revision. Process death makes it unavailable. Only an eligible
  session retains one delayed rebind; prior payload is never replayed. Ending the
  session removes retries and registrations. IME does not yet instantiate it.
- Neutral read-only active resolver/pointer codec/operation gate are separated
  from delivery. Install activation remains mutable install-worker code. Resolver
  and load share the existing physical operation lock with installation; score
  releases it and revalidates identity under lock afterwards. This is a version
  check, not atomicity with a later activation before callback delivery.
- Three FileObservers cover root, versions and active version. A bounded read-only
  OPEN handshake establishes registration before load; failure rejects the load.
  The resolver does not create storage or perform AtomicFile read-side recovery.
- Source dependency gate traverses IME/client/IPC/storage/inference dependencies;
  10 negative and two positive fixtures cover network, delivery, JNI, logging,
  filesystem/persistence and indirect helper violations. Runtime adapter is the
  sole allowed JNI consumer; URI is permitted only for pure manifest parsing.

## Evidence mapped to requirements

| Requirement | Actual covering evidence |
| --- | --- |
| Manifest and actual remote process | ScoringIpcInstrumentedTest.privateManifestContract; ScoringLifecycleInstrumentedTest.debugFixtureIsPrivateSameUidAndActuallyRemote |
| Bounded numeric IPC, invalid/oversized/count rejection | ScoringIpcInstrumentedTest parcel roundtrip/oversize tests; ScoringInfrastructureTest.boundedContracts |
| Active model load, absent/corrupt pointer, update/delete | ActiveModelLifecycleInstrumentedTest load/rotation/deletion/absent/corrupt/oversized/size/path cases using actual adapter and kernel watches |
| Read-only resolver and interprocess lock | Backup-preservation, path containment and nativeLoadKeepsSharedPhysicalLockUntilSourceIsConsumed tests |
| Replacement and nonblocking cancel | Oneway remote active/latest-pending and immediateCancelSuppressesCallbackAndDoesNotWaitForScore tests |
| Idle unload, trim and model invalidation | Real remote fixture worker counters and ActiveModelLifecycleInstrumentedTest invalidation cases |
| Process death/rebind/no replay | Real private service process self-kill with production client and Android ServiceConnection delivery |
| Sensitive/ineligible/end/close binding ownership | Client eligibility tests, balanced registrations/retries; actual IME policy wiring is a later PR7/10 gate |
| Stale reply/connection and current revision | Late actual numeric callback after cancel; live revision mismatch; obsolete ServiceConnection events injected with a previously real Binder; pure LatestReplyGuard regression |
| Failed bind cleanup | Real Handler instrumentation with controlled false/SecurityException Context, no surviving registration/retry; injected late connection events ignored |
| Runtime failure | ScoringInfrastructureTest.runtimeFailure; PR2 native contract qualification remains separate |
| No logs/network/persistent input | Reviewed source boundaries, negative fixtures, privacy/dependency gates and numeric-only fixture counters |
| Debug fixture excluded from release | Release/profile merged manifests and APK Analyzer defined DEX classes with R8 mappings |

The debug service overrides only engine factory/idle duration; production Binder,
queue and lifecycle methods stay shared. Its synthetic engine stores numeric IDs,
counts, cancellation tokens and bounded coordination latches, not request text.
A debug-only oneway control Binder drives deterministic failure scenarios. These
fixtures are absent from release/profile manifests and DEX.

## Measured checks

| Gate | Status |
| --- | --- |
| Fresh JVM before commit | PASS, 313/313, zero failures/errors/skips |
| Full requested lint/build/privacy/dependency/native gates | PASS, post-compatibility run 238 tasks, 17 executed |
| Debug and Android test APK assembly | PASS |
| API37 new PR3 scenarios | PASS, 22/22, 15.219 s |
| API37 complete app suite | PASS, 79/79, 486.037 s; before test-only API28 callback guard |
| API26 complete app suite | PASS, final 79/79, 382.370 s; initial 76/79 failure retained |
| Release/profile manifest and DEX fixture isolation | PASS |
| New remote CI execution | BLOCKED pending separately authorized push |
| Physical Fold, latency, RSS/PSS and energy | BLOCKED pending physical device qualification |
| End-to-end model-assisted typing quality | NOT IMPLEMENTED; frozen PR1 Rune Text suitability remains FAIL |
| Model publication | BLOCKED pending exact-digest physical qualification and publication authorization |

Independent base review found and fixed one failed-bind registration leak.
Lifecycle review found one test that could pass via server suppression without
exercising the client guard. The corrected test waits for post-dispatch worker
state, requires main-thread evaluation of callback 601, and verifies no delivery
before submitting 602. Positive, missing-callback and broken-cancel host controls
were checked; scoped re-review approved. Actual API37 execution then passed.

API26 initially exposed three test-injected calls to ServiceConnection.onNullBinding,
which was added in API28. The independently reviewed fix guards only those calls;
all API26-supported callbacks and cleanup assertions remain. The three affected
tests passed in 8.384 s, followed by the complete 79-test rerun. API37 takes the
same true branch as its earlier passing run; this guard changes no product code.

A suspected idle-worker payload-retention issue was investigated against the actual
compiled worker class. Default-JVM and interpreted success/cancel probes collected
the request and byte arrays while the worker waited; a retained-reference positive
control remained reachable. No defect was reproduced and no speculative fix was
added. This host check is not an ART secure-erasure guarantee.

Source tests do not prove arbitrary dynamic/reflection behavior outside the gate's
recognized source graph. Callback-owner process death in a separate third caller
process and inotify quota exhaustion are not deterministically injected; service
process death and real successful/failed watch registration are covered. No
physical/native timing guarantee follows from the fake scorer. PR2 separately
qualifies the exact native model on API26/API37 and inside-tokenizer cancellation
on the host. API36 and historical baseline CI are not substitutes for this slice.

Content-free local evidence lives in `build/smart-typing-0.3/`: `pr03-base-api37.log`,
`pr03-lifecycle-api37.log`, `pr03-all-api37.log`, `pr03-all-api26.log`,
`pr03-all-api26-final.log`, `pr03-api26-compat-regressions.log`,
`pr03-gates-compat-final.log` and `pr03-apk-isolation.log`. Fresh post-commit JVM results
will be recorded with the exact local SHA in the execution ledger. No push,
remote PR, publication or version bump is part of this checkpoint.
