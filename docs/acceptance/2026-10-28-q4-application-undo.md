# Q4 — acknowledged applications, exact Undo and collection origin

All three existing automatic commit paths now record the already chosen source:
immediate boundary correction, delayed local correction and delayed model
correction. Source classification reads existing candidate kind and ranking flags;
it never re-runs qualification/admission or alters a decision. The committed
correction owns its immutable application metadata, retained by previous-word
Undo through a later word/candidate set. Both acknowledged Undo paths use that
origin, with no extra source/word reconstruction from the current candidate.

The 13 actual automatic cohorts are covered: common confusion, general local,
canonical case, compact public, neighbor recovery, joint short/long/rescue, word
context, contextual ranker, infinitive revision, noun-case revision and model.
The fixed CONTEXTUAL dimension remains manual-only in the current controller;
manual contextual selections are not invented automatic applications. Disabled
MODEL_REFINEMENT is not a source counter.

## Counted-application tickets

A source-only prototype passed the ordinary cases but a new independent regression
exposed an orphan Undo when collection had been off at application time. The
recorder now issues a single-use AutomaticQualityApplication only when its APPLIED
counter actually increments. It contains a fixed source enum, a text-free empty
collection-period identity and a consumed flag. No ticket enters a snapshot,
codec, queue payload, diagnostics stream or disk. It does not retain the recorder,
controller or editor. The application's normal editor Undo remains independent
of whether any metric was collected.

Metrics/eligibility transitions, reset and restore revoke the in-memory origin;
other recorders cannot consume it. Shadow toggles alone preserve it. Loading/failed repository states or saturated APPLIED counters cannot issue a
usable ticket.
Undo without an admitted application, repeat Undo and tickets from older periods
cannot label another source/period. Existing generic action counters retain their
own acknowledged-event semantics, including an Undo after a statistics reset.
The numeric v3 persisted schema and all policy/asset identities are unchanged.

## Actual checks

All 1,322 JVM tests pass without failures/errors/skips, including 115 boundary
methods and 34 quality model/repository methods. Cases cover all 13 source
cohorts, both delayed paths, canonical case, next-word visible Undo with a different
current source, repeated/stale Undo, refused editor calls, manual choices,
collection/privacy exclusion, reset/recorder changes, saturation and ticket
single-use/serialization exclusion. Debug lint, APK/test builds and profile
privacy/R8 packaging pass.

Four actual API 26 methods pass without skips on the exact final main/test APKs.
The new real IME method enables metrics through normal preferences, observes zero
applications at preview, touches Space for actual `teh` → `the`, then observes one
common-confusion application and one exact Undo; ordinary Backspace adds none.
A second actual correction is followed by a durable statistics reset: editor Undo
still restores `teh`, while source counters remain zero because its application
belongs to the old collection period. Rejecting and private fixtures add no
source applications. The three dashboard/reset/atomic-store/localization methods
also pass. Store-mutating fixtures require verified emulator hardware and an
explicit owned-emulator marker; no owner profile or Fold is used.

A fresh final-source host replay exactly matches frozen Q3 final observations on
12,012 regression + 1,676 stress + 1,600 historical calibration rows. Every field
matches except the two pre-existing host timing fields, including candidates,
scores, allowed decisions, actual boundary observations, editor commands, final
text and Undo. Current 90 selected sources and all 69 assets are bound before/
after compilation/execution. This reuses the bound historical baseline outputs;
it is not a new parent build, native model execution or fresh natural-data
qualification. The core host excludes Android storage; actual store/IME methods
provide separate adapter evidence.

Early fixture failures are retained: an incorrect score constructor was replaced
by the existing winningReply helper; a six-letter general-local fixture was
corrected to satisfy the existing seven-letter RU minimum; and the initial IME
locator was corrected to the established accessibility description for the
prefixed automatic preview. The collection-origin red regression is retained as
a real defect in the source-only prototype. None is counted as a final pass.

Q4 remains open for kept-original/expired-window hooks, real model-response timing,
unavailable/CPU copy, debug-only export, final release/device integration and two
actual weeks of owner use. This slice does not claim owner installation or the
start of that observation period; the complete review remains open.
