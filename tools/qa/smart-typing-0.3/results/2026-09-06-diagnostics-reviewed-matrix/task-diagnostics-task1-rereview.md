# Diagnostics review fixes: scoped re-review

**Spec verdict: PASS. Code-quality verdict: PASS.** All three Task 1 findings and the remaining Task 2 contract-method finding are closed in the frozen handoff. No residual actionable finding or new breakage caused by these fixes was identified within this scope.

## Finding closure

### Task 1 P2: durable preferences and stale operations — CLOSED

[Frozen `DiagnosticsRecorder.kt:60`](/Users/avm/projects/Personal/rune-keyboard/.superpowers/sdd/2026-09-02-smart-typing-progress/task-diagnostics-task1-fix-frozen/app/src/debug/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/DiagnosticsRecorder.kt:60) separates preference-operation generation from input-event generation. Session changes no longer cause a confirmed save to persist successfully while reporting stale failure and leaving the live switch off. Save completion leaves admission unarmed, so a session begun before completion still cannot supply text.

Accepted preference commands derive from the latest requested state. A queued superseded operation does not write; an in-flight operation reconciles the latest request before returning. The cached completed result prevents its later queued command from turning an already-failed enable into a successful fallback-OFF acknowledgement. The control queue bounds accepted intervening changes and reconciliation work.

The retaining-backend regressions at [test line 245](/Users/avm/projects/Personal/rune-keyboard/.superpowers/sdd/2026-09-02-smart-typing-progress/task-diagnostics-task1-fix-frozen/app/src/testDebug/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/DiagnosticsRecorderTest.kt:245) cover queued/in-flight session changes, saved-map reload, fresh admission, supersession by OFF and failed reconciliation. A backend that refuses the compensating write can still retain its old durable choice; the tests explicitly require failed acknowledgements and verify a later successful stop. This is correctly treated as an I/O failure, not successful durable revocation.

### Task 1 P2: actual event/candidate payload pairing — CLOSED

[Frozen controller deferred-Space handling](/Users/avm/projects/Personal/rune-keyboard/.superpowers/sdd/2026-09-02-smart-typing-progress/task-diagnostics-task1-fix-frozen/app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/session/TypingSessionController.kt:318) now uses the saved selection, original ranking IDs and saved pre-Space context for its rejection payload. Contextual rejection uses the existing pending variants, while the accepted selection retains those variants for the later explicit tap. Winner/tap count and selected position refer to that same list. Payload construction remains inside admitted lazy callbacks; no policy or candidate generation is rerun.

[The paired hook tests](/Users/avm/projects/Personal/rune-keyboard/.superpowers/sdd/2026-09-02-smart-typing-progress/task-diagnostics-task1-fix-frozen/app/src/testDebug/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/TypingDiagnosticsHooksTest.kt:80) assert the event's origin IDs/count/index together with its original, complete candidate list and result for contextual winner/tap, contextual error/abstention, and deferred-Space error/abstention. They also verify resulting controller text.

### Task 1 P2: retained refusal and original operation identity — CLOSED

[Frozen `DiagnosticsRecorder.kt:175`](/Users/avm/projects/Personal/rune-keyboard/.superpowers/sdd/2026-09-02-smart-typing-progress/task-diagnostics-task1-fix-frozen/app/src/debug/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/DiagnosticsRecorder.kt:175) creates a one-shot refusal callback only for an admitted operation. Its captured state is numeric IDs, consent generation and stream flags. It accepts no payload supplier and serializes only fixed metadata fields into each originally admitted stream, including text-only mode.

Ordinary session invalidation can retain only these content-free terminal records. Off/delete change the preference generation and revoke both unused callbacks and queued outcomes; writing checks that generation and the stream setting again. Ordinary text records retain their session-generation requirement and are discarded on invalidation. The controller captures the callback before executing the editor operation, so a reentrant new session cannot relabel the old refusal.

[The four terminal tests](/Users/avm/projects/Personal/rune-keyboard/.superpowers/sdd/2026-09-02-smart-typing-progress/task-diagnostics-task1-fix-frozen/app/src/testDebug/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/DiagnosticsTerminalTest.kt:13) exercise the real recorder/controller with blocked managed I/O, metadata-only/text-only/both streams, a sensitive replacement session, original IDs, absence of text fields, off/delete revocation and one-shot/fresh/eligible admission. This matches the explicit terminal-outcome exception added to the brief and does not reopen text admission.

### Task 2 residual P2: serializer methods inside approved contract types — CLOSED

[Frozen source gate lines 257–260](/Users/avm/projects/Personal/rune-keyboard/.superpowers/sdd/2026-09-02-smart-typing-progress/task-diagnostics-task1-fix-frozen/tools/verify-scoring-boundaries.py:257) compare complete extracted declarations with the exact interface and constructor-only text DTO contracts. Extraction balances delimiters outside strings/comments and rejects a following supertype; canonical comparison preserves literal contents. Added/changed default methods, DTO encoder/getter bodies, serializer bodies after a supertype and changed defaults have rejection fixtures.

The approved terminal method is explicitly fixed to default-null behavior. Existing exact no-op and packaging-helper restrictions remain; no broader class allowance was added. The previously described method-level serializer path is therefore rejected by source admission before packaging.

## Related lint/status changes

The [frozen lint rule](/Users/avm/projects/Personal/rune-keyboard/.superpowers/sdd/2026-09-02-smart-typing-progress/task-diagnostics-task1-fix-frozen/app/lint.xml:7) expresses the assigned partial-Spanish locale decision using an anchored MissingTranslation message pattern. It excludes `diagnostics_*` names and does not match another or multiple missing locales. It leaves other lint issues enabled. This is English fallback for the existing non-diagnostic Spanish omissions, not a claim that the entire app is translated.

Management status now supplies its third message through localized `%3$s`; all three changed resources and the call agree. No completion or export-cancellation behavior was changed by this formatting repair.

## Evidence and scope

Reviewed the approved brief, original Task 1 review, Task 2 re-review, finalized implementer report, the 13 files frozen in `task-diagnostics-task1-fix-frozen/` and their identity map. Exact before/after artifact: `task-diagnostics-task1-fixes-diff.txt`, SHA-256 `cb3fc3c62eddd5c9b60863fe97dc5fedbda647b6874445233e1560479340c666`. Root verified the handoff's source identities before dispatch.

Read retained final JUnit XML: 16 recorder + 2 storage + 4 terminal + 8 hooks + 117 existing tests = **147 tests, zero failures/errors/skips**. `task2-review-round2-green-final.log` records **32 Python tests, OK**; `task1-review-source-gate-final.log` records the existing **17 negative + 6 positive** self-tests and actual debug/release/profile source graphs PASS.

During this review, root's `root-reviewed-fixes-gates.log` completed with actual packaging PASS for debug (597 pre-R8 / 2,727 DEX classes), release and profile (548 / 482 each), followed by **BUILD SUCCESSFUL**. These actual artifact counts are distinct from earlier synthetic one-class fixtures in that log. This report does not extend that command result to unexecuted device cases or unrelated release qualification.

No tests, Gradle, devices, model operations, implementation edits or delegation were performed by this reviewer. Only this report was written. Review covers the four original findings and changes made to fix them, including the assigned lint/status adjustment; it is not a new whole-feature or whole-branch audit. Historical failures and qualification receipts remain separate.
