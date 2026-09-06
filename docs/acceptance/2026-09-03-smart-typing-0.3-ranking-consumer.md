# Smart Typing 0.3 — suggestion ranking consumer, 2026-09-03

Baseline: `99c0c06fc3eda0c918b6aad7ca9585b371209ff8`.

The typing controller previously discarded all but the first two generated
alternatives. It now retains all seven immutable candidate records, including
their deterministic features, while still projecting Original plus two items.
Correction IDs refer to source indices, not screen positions. A formerly visible
ID cannot select a different word after ranking, and a currently hidden ID is
rejected. All existing editor mutation and Original restoration paths remain
owned by the typing controller.

`beginModelRanking` snapshots the full candidate set and Rune-owned context;
the prefix excludes the current typed word but includes its leading boundary.
Strict IPC value contracts enforce byte/ID bounds. No editor readback occurs.
One numeric stamp holds the exact source selection identity. Replies must match
session/revision/request/candidate IDs, current composition and that selection.
Cancellation, edits, manual selection, failures and lifecycle changes prevent
stale responses from publishing. A successful response consumes its stamp once.

`acceptModelRanking` uses average log probability; ties preserve source order
with Original first. It changes only strip ordering and selection, not editor
text, composition revision or the Original-tap veto. A completed ranking is not
resubmitted for the same local selection. This is suggestion ordering, not a
calibrated combined ranker, confidence margin or AutoReplace decision. Retrieval
completion and features remain available for the later calibrated pipeline.

`ModelCandidateCoordinator` is an optional consumer wired into the real local
coordinator. It starts only after an accepted local reply, with cached suitable
owner policy, Ready and alternatives. A development 400 ms pause retains only
identity/policy; input is snapshotted when sending. Text/tap cancels immediately.
Lifecycle/settings invalidation also detaches. Readiness, rendering and reconnect
cannot replay old input. Policy, language and eligibility are checked again on
timer/callback. The existing process CPU duty policy still governs real service
work; the pause is not a measured energy or latency budget.

The IME **does not yet instantiate this consumer**. Android composition-root
factory, read-only Ready monitor and actual model-suggestion device integration
remain the next slice. Current device tests exercise the existing dictionary
path with the enlarged retained candidate set. JVM integration uses the actual
local worker/coordinator/controller with a fake model client and controlled
pause scheduler. No real-model quality claim follows.

The dependency gate now permits the exact pure `ModelDemand.kt` value contract
transitively through `ModelScoringClient`; transport implementations, storage,
delivery and JNI remain forbidden from IME. An additional negative fixture
proves a filesystem import in the newly allowed demand file still fails. Gate
self-tests: 11 negative and 3 positive cases PASS.

Fresh JVM: **574/574 PASS**, zero failures/errors/skips. Ten new tests cover full
eight-candidate retention, owned prefix, normalized numeric ordering, stable tap
IDs, every token identity field, cancellation/manual/error fallback, local-first
rendering, retired timers, stale callbacks across boundaries and languages,
readiness/reconnect non-replay and absence of demand for valid words.
Prescribed lint/build/privacy/dependency/native gates plus Android test assembly:
**PASS**, 267 tasks, 46 executed. Scoped API26/API37 candidate/composing/view
regression: API26 **28/28 PASS**, 199.180 s. API37 initial **27 PASS/1 FAIL**,
231.908 s: `boundaryKeepsTypedOriginalAndDropsPreviousSuggestions` failed in
setup because QA activity did not become visible. Exact unchanged-code targeted
retry **1/1 PASS**, 16.591 s. The initial startup cause is unestablished; no test
timeout or assertion was relaxed. This is not a final clean 28-test API37 rerun.

Evidence, both API37 runs and exact source/APK identities are archived in
`tools/qa/smart-typing-0.3/results/2026-09-03-ranking-consumer/`. APK identities
describe installed build inputs, not device readback. Screenshots/hierarchy
capture was disabled. There is no independent review claim for this slice.

Physical Fold, real-model suggestions, quality, battery and external CI remain
unqualified. No Android read-only readiness path or model binding is claimed
implemented by this slice. Version remains 0.2.0; no publication or push.
