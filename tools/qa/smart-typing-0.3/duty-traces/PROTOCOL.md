# CPU duty synthetic trace v1

Frozen before first execution on source baseline `6fb5880`. This is ordinary-CI
simulation of the actual worker, not native execution, service throughput,
latency, quality, a battery measurement or physical trace qualification.

Nine independent traces: EN/RU/ES with 2/4/8 complete public candidate strings.
Original is candidate 0. No generated candidate is removed to satisfy duty.
Each trace creates one worker and one owner; all phases share its CPU debt.
The clock starts at zero and advances explicitly; no real CPU cost is inferred
from test duration. Warm simulated wall/CPU pairs use ceiling wall p95 and
process-CPU p95 from `docs/acceptance/2026-09-02-smart-typing-0.3-fold-runtime.md`:

| Language | 2 wall/CPU ms | 4 wall/CPU ms | 8 wall/CPU ms |
| --- | --- | --- | --- |
| EN | 257/862 | 469/1666 | 1004/3634 |
| RU | 600/2138 | 1076/3937 | 2063/7656 |
| ES | 369/1272 | 767/2702 | 1432/5263 |

Phases, with monotonic unique request IDs:

1. Start request 1. At +100 wall/400 CPU ms submit 2 then 3. Request 2 is
   replaced. At +25 wall/100 CPU ms complete cancelled 1; latest 3 reaches the
   engine and completes with the configured warm cost. A synthetic boundary
   1000 wall ms after request 3's receipt determines usable-before-boundary.
2. Submit 4 immediately; record the actual admission outcome without granting
   more credit. No spontaneous recovery/retry is allowed.
3. Advance 90000 wall/0 CPU ms without work. Verify no watchdog is active.
   Submit 5, then 6 while 5 is blocked. Advance 3000 wall/0 CPU ms and tick:
   active 5 cancels at its deadline, pending 6 expires without engine entry.
4. Advance 90000 wall/0 CPU ms. Submit 7; simulate failed load at +360 wall/
   355 CPU ms. Return LOAD_FAILED, retaining its CPU charge.
5. Apply critical pressure and await serial unload. Submit 8 and then 9 after
   model invalidation; both must be UNAVAILABLE. Actual worker unbind/bind
   rearms, without resetting the owner. Submit 10 and execute its warm cost.
6. Advance 90000 wall/0 CPU ms. Submit 11. Advance 2000 wall/8400 CPU ms,
   tick the watchdog, then simulate cancellation tail +25 wall/100 CPU ms.
   The trace records tail CPU/wall and negative credit without treating them
   as measured overshoot. Required close/unload remains possible in debt.

Emit only numeric counts, language/candidate configuration and simulation
totals. Count engine entry as admitted, OK replies as completed, explicit
LOAD_FAILED as failed, UNAVAILABLE before entry as denied (expired subset separate),
and flag-cancelled engine entries separately from pending replacements. Every
submission must finish exactly once. Input identity, full candidate IDs,
finite numeric outputs, no stale success, no active idle timer and final lease
release are invariants. Any deviation fails the test and is retained in evidence.

The idle phase verifies absence of active watchdogs and credit recovery. It
does not advance the worker's real `Object.wait` timer; actual 60-second idle
unload remains covered separately and requires physical trace measurement.
Do not relabel these virtual times as Android observations. Profile changes
need a new version and separately retained output, not replacement of v1.

Harness correction after the first simulation: phase 4 originally returned
NO_MODEL instead of LOAD_FAILED. It now exercises the named load-failure code;
timing, inputs, profile and phase order are unchanged. First output is retained
as first-execution.xml and does not prove the final LOAD_FAILED path.
