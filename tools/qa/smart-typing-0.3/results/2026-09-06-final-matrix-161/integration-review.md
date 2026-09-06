# Final whole-branch integration review

Reviewed 2026-09-06 by independent final reviewer.

- Base: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`
- Head: `6f7c35eda1ee11a9f0a510eadadd0fbf2912356c`
- Immutable review package: `final-branch-review-b5400cb-6f7c35e.diff`
- Package SHA-256: `fe60016e3dd09049e042f31126f1000d1e3273ea2cb2cb51aeca9d982ff5be82`

## Verdict

**No actionable remaining blocking code finding was established in this integration review.** This is a bounded source review, not a claim that every changed line or every possible editor behavior has been independently verified. **Not ready for formal release or main merge:** the acknowledged physical, external CI, and final acceptance requirements remain open. There is no newly identified code fix requested by this review.

## Scope and method

Used the requesting-code-review reviewer method against the original Smart Typing specification, execution ledger, consolidated acceptance report, and explicitly supplied user overrides. Reviewed source directly at the unchanged requested HEAD, using the base-to-head diff to identify primary implementation and build changes. Archived failed evidence was not treated as a new implementation defect. No builds, tests, network/model calls, device actions, source edits, branch changes, or nested agents were performed. This report is the only intended review write.

The review concentrated on integration boundaries rather than repeating corpus scoring or all prior slice reviews:

- `RuneInputMethodService`, `EditorContext`, `EditorCommandExecutor`, `TypingSessionController`, `SessionTextContext`, and both candidate coordinators: editor eligibility, selection ownership, lifecycle barriers, ordinary/late Space, action fallback, Original/manual selection, punctuation and unified Undo.
- Local candidate worker and lazy lexicon ownership; generator admission and canonical-case agreement; spelling qualification/calibrated policy and contextual variant/policy selection.
- Bound scoring client, AIDL/parcel contract, inference service and latest worker; active-model resolver/watch/load adapter and native handle lifecycle.
- Debug diagnostic consent, recorder, storage, settings and export activity; release/profile no-op enforcement, source dependency gate, pre-R8/final DEX packaging verifier and Gradle wiring.
- Runtime request/wire validation, JNI score/cancel/unload paths, shared scoring implementation, and CMake pin/patch/optimization enforcement.

Selected regression test bodies were checked alongside these paths, including `CorrectionBoundaryTest` and `LocalCandidateCoordinatorTest`; additional controller, client, lifecycle, diagnostics and settings test inventories were inspected. Existing run results below are attributed evidence, not tests executed by this reviewer.

## Strengths and integration findings

1. Editor changes require a current owned span, revision/session identity and live owner policy. Guarded batches keep one InputConnection, stop between commands on invalidation, and clean up without replaying text after refusal. External selection/lifecycle events clear retained context and pending work. Whole-word reopening uses retained Rune text and a known boundary; it does not reconstruct arbitrary editor text.
2. Automatic spelling, mechanical edits, manual candidate changes and contextual suggestions have distinct admission paths. One stored automatic transaction restores the original on immediate Delete; later actions revoke that transaction. The post-Space exception is bounded by exact suffix ownership, request identity, live automatic policy and elapsed time checked on callback, including when the expiry runnable has not executed. The next text action cancels it.
3. Contextual scoring is reachable independently of spelling mode for eligible valid words. Replies store a bounded suggestion; only the current explicit selection edits the composing continuation. Allowed boundary variants and optional first-letter capitalization come from the local rule engine, with no free generated text or preceding committed-prefix rewrite.
4. Lexicon completion and model readiness do not replay saved input. Local and model workers coalesce pending work; cancellation invalidates delivery ownership. Binder contracts bound allocation and accept numeric replies only. Private service declaration and same-UID admission complement transport generation guards. Version changes and watch retirement invalidate service work without granting editor ownership.
5. Runtime admission checks cancellation after resetting its native flag, under the lifecycle monitor, and uses independent cancellation tokens. The scorer enforces candidate/byte/token/context limits, compares predefined continuations, clears failed-score memory, and handles cancellation during tokenization/decode. The build verifies the pristine upstream pin and patch digest before applying the patch to a private build copy.
6. Authorized debug recording requires persisted independent preferences and a fresh eligible session; text suppliers are gated before capture. Session/policy invalidation closes admission, queues and managed files are bounded, and export is explicit. Release/profile provider bodies are checked as exact no-ops; packaging checks both pre-R8 definitions and mapped final DEX, preventing obfuscation from disguising the debug recorder.

## Remaining acceptance boundaries

These are acknowledged incomplete qualification/evidence items, **not new code defects**:

- The parent reports postcommit JVM `743/743` and prescribed `240`-task gates passing, plus exact-model public Android runtime tests passing on both APIs. The final complete API26/API37 app matrices were still in progress when this review was requested; this report does not claim their outcome.
- Current real physical Fold transitions, broader real-editor/rapid-input coverage and physical performance/energy qualification remain incomplete. The user has taken the phone; no phone action or request is made here.
- Revealed-data spelling reproduction and contextual source attribution have the limits recorded in the acceptance document. Source agreement is not independent semantic punctuation precision, and historical failed gates remain historical failed gates.
- Current external CI and formal release/main integration have not been established. Experimental exact-digest HF publication is authorized and is not itself a release approval. Version remains `0.2.0` as directed.

The user-selected 95% point-precision policy and separately authorized local debug text recording were evaluated as explicit scope changes, not flagged against superseded original requirements.
