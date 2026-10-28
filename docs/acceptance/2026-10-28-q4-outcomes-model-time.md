# Q4 — original preference, window expiry and model response time

Explicit Original now records the current preferred source once, including a
current manual contextual proposal. This is preference evidence against a
proposal, not proof that automatic admission would pass. Stale IDs, repeated
manual/original state, absent proposals and restoration of a prior manual pick
do not invent source evidence. The original-returning editor path records only
inside its existing acknowledged callback. No additional qualification/admission
call is made. CONTEXTUAL remains manual-only for APPLIED.

A late local result records its first known preferred source after the existing
250 ms window. Unknown sources remain unlabelled. A pending model spelling
opportunity records expiry only while still owned and eligible; a one-observation
flag prevents duplicate timer/direct/discarded-reply labels. Policy loss or
cancellation is not expiry. The existing 250 ms literals, scheduling, request
cancellation, qualification and text-writing gates are unchanged. Independent
249/250/251 ms tests preserve accepted text/commands and exact expiry counts.

## Measured reply admission

Every actual existing model submission may capture a word-free, one-shot
QualityModelResponse permission while numeric metrics are ready/enabled/eligible.
It retains only the existing empty collection-period identity and consumed flag.
No snapshot or file stores it. Both normal and discarded callbacks can record the
engine-reported elapsedMillis once, including late/cancelled or unavailable
responses. Reset/restore, privacy/metrics transitions, a different recorder or
inactive current owner prevent recording. The five pre-existing v3 buckets are
used; no duration is reconstructed from host/UI timing or invented for a missing
response.

Only the latest eight numeric ScoringToken-to-permission associations are retained.
The immutable token contains numeric session/revision/request/candidate IDs, no
input, prefix, continuations, package or word fingerprint. Cancellation retains
this bounded sample for late replies; the oldest association is evicted rather
than growing an unbounded history. Shutdown discards it before cancellation that
can call back synchronously. The parent coordinator also discards admissions
before its existing cancellation step. No request/cancel ordering was changed.
This is a sample of reported replies, not a complete latency distribution or
end-to-end keystroke/battery/performance budget.

The dashboard's EN/RU note now explains that UNAVAILABLE includes CPU limit or
engine failure and that a zero refusal duration does not prove inference ran.
The actual worker reject path supplies zero; engine failure paths also use
UNAVAILABLE. Numeric IPC codes and model/runtime identities are unchanged.

## Actual checks

All 1,335 JVM tests pass without failures/errors/skips, with debug lint,
APK/test builds and profile privacy/R8 packaging. Coverage includes source
Original uniqueness, manual/absent proposals, contextual preference, exact
window boundaries and timer/discarded/direct duplicates, model duration edges,
late and UNAVAILABLE responses, collection/recorder resets, bounded numeric
history and synchronous close. The first broad run failed the newly added
synchronous-parent-close regression: parent cancellation preceded model close.
The metadata admissions now retire before that existing cancellation, and the
complete final suite passes. The failed raw output remains private evidence.

Four actual API 26 methods pass without skips on the exact final APK pair. The
real IME fixture now also selects Original through the actual accessibility
surface, observes one common-confusion KEPT_ORIGINAL, presses Space and verifies
that `teh` remains unchanged with zero automatic applications. Existing real
application/Undo, reset-with-live-Undo, rejecting/private fixtures and the three
dashboard/atomic-store/localization methods retain their assertions. This owned
emulator uses no owner profile or Fold. Model timing was tested through the real
coordinator with synthetic numeric replies; native GGUF timing is not claimed.

A freshly compiled final core host exactly matches frozen Q3 observations on
12,012 + 1,676 + 1,600 rows, excluding only the two existing host timing fields.
Current 90 selected sources and 69 assets are bound before/after execution.
Candidates, scores, allowed decisions, boundary events, commands, text and Undo
are unchanged. The historical baseline outputs were revalidated and reused;
no fresh natural-data qualification or correction-accuracy gain is claimed.
Android/coordinator/store paths have the separately scoped checks above.

Q4 remains open for debug-only numeric export, final release/owner-device
integration and two actual weeks of owner use. No observation period or owner
installation is claimed from these synthetic fixtures; the complete review stays
open.
