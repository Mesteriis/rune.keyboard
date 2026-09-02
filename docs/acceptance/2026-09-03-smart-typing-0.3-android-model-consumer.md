# Smart Typing 0.3 — Android model consumer, 2026-09-03

Baseline: `f65c079cf7df488366a58e60b42406c5761dbad9`.

The production IME now creates the suggestion-only model coordinator through
`AndroidModelCandidates`. Local suggestions remain immediate. After metadata
Ready and a subsequent accepted local result, the main Handler pause permits
the bounded client to send the current Rune-owned candidate set to the private
inference service. The existing process CPU duty policy applies. Ready callbacks,
rendering and reconnect do not replay input. There is no automatic word replacement
or calibrated combined ranking in this slice.

Readiness uses one background metadata worker and one replacing numeric epoch.
Inactive/sensitive owners do not probe. End/close invalidates queued callbacks
without waiting for disk work. The probe takes the existing operation lock
nonblockingly in read-only mode, never creates the store and never opens or
hashes GGUF. Busy locking yields UNKNOWN, retried only on explicit candidate
activity. READY/MISSING/BROKEN have no polling timer; an inactive/active edge
refreshes metadata. READY is a descriptor/file-stat hint, not model qualification.
Current NO_MODEL/LOAD_FAILED results detach and clear readiness; stale failures
cannot detach newer work. No additional editor readback is introduced.

The source gate permits only the exact Android composition root to enter the
client/readiness implementations. It follows their transitive dependencies;
pure client contracts cannot hide implementation imports. New fixtures reject
delivery, persistence, payload coupling and a helper bypass. All **16 negative
and 4 positive boundary fixtures PASS**.

Fresh JVM: **586/586 PASS**, zero failures/errors/skips. Coverage includes
off-owner metadata execution, coalescing, stale epochs, UNKNOWN retry,
nonblocking close, missing/malformed metadata, lock contention and stale versus
current model errors. An initial fixture incorrectly invented pointer JSON
keys; its failure is retained. The corrected fixture uses the production pointer
codec. No production parsing assertion was weakened.

Prescribed lint/build/privacy/dependency/native gates and test APK assembly:
**PASS**, 267 tasks (48 executed, 1 from cache, 218 up-to-date).
Selected Android matrix: **API26 54/54 PASS**, 211.299 s;
**API37 54/54 PASS**, 256.049 s, each in one completed run.
The three new factory tests use real main Handler, metadata reader, client and
remote Binder with a synthetic scoring engine and owned editor callback fixture.
They prove Ready does not bind/replay, next-edit numeric results do not write the
editor, no main-thread metadata root access, inactive/sensitive suppression and
session refresh after pointer deletion. Existing candidate/composing tests cover
real IME Binder InputConnection separately; the remaining selected tests exercise
client/service lifecycle. These are scoped runs, not the entire release matrix.

Logs, counts and exact source/APK hashes are archived in
`tools/qa/smart-typing-0.3/results/2026-09-03-android-model-consumer/`.
APK hashes identify installed build inputs, not device readback. Tests used an
isolated metadata directory and disabled screenshot/hierarchy failure capture.

| Gate | Status for this slice |
| --- | --- |
| JVM / local build and boundary gates | PASS |
| Selected API26 / API37 matrix | PASS / PASS |
| Physical Fold model typing and battery | BLOCKED: no measurement in this slice |
| Combined ranking / AutoReplace holdout | BLOCKED: pipeline not complete |
| Contextual punctuation | BLOCKED: consumer not complete |
| Remote CI / immutable model publication | BLOCKED: separate authorization and qualification required |

No real-GGUF typing, battery, latency or quality qualification is claimed.
The earlier failed model holdout remains unchanged. Version stays 0.2.0;
no push, remote PR or publication was performed.
