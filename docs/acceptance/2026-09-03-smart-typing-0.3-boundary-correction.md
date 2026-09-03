# Qualified boundary correction and Undo — 2026-09-03

Baseline `c1a2bc75e68fe248f66ef1c08d74135b8e509da9`. This slice implements
Space/comma/question/exclamation/semicolon correction transactions and their
immediate Undo. Production automatic spelling remains disabled: the independent
`SpellingQualification.CURRENT` admits no language/model branch before the final
product holdout. Preferences and model Ready cannot override it. Tests inject
synthetic admission through the internal controller constructor; no APK setting,
debug switch or alternate IME bypass was added.

The coordinator cancels outstanding computation/callback ownership before an
action, retaining the latest accepted generation long enough for the controller
to consume it. The boundary never waits for scoring or starts another model
request. A missing model result uses the existing deterministic decision; an
insufficient or missing decision preserves Original. HIGH_CONFIDENCE, current
language/layer, eligible input policy, complete retrieval, original/manual veto,
owned composition and qualification of the actual deterministic/model branch
must all pass before replacement.

Only a whole token whose beginning is established by Rune whitespace or document
start is eligible. Email, URL, code and hostname fragments, and unknown text
before a session, retain Original without editor reads. First dot/colon boundaries
also retain Original because subsequent input can still form a hostname or URI.
This conservative abstention does not delay the boundary; punctuation processing
and explicit suggestions remain independent.

The executor commits the corrected owned span plus boundary in one guarded batch,
then composes only the boundary. The first Backspace reopens the exact known
applied region and restores the original composition in one batch, removing the
committed boundary without an additional Delete. Original/correction candidates
are restored with fresh revision IDs and Original selected. The next text action
retires that transaction. Double-space/mechanical edits continue using the same
single `lastAutoEdit`; there is no second Undo stack. Context restoration uses
the original bounded RAM snapshot, including different prefix eviction caused
by a length-changing correction.

Batch commands are limited to 1–3 text/region operations. All writes remain in
`EditorCommandExecutor`; its connection is fixed for the batch and cleanup.
Session/revision/candidate epoch are checked between writes and after cleanup,
so reentrant lifecycle or policy changes stop the remaining operations. Rejected
or throwing writes disable the session; cleanup is attempted without replaying
text, and cleanup failure cannot revive the operation. `endBatchEdit` returning
false at nesting zero is not treated as a failed text mutation. The known-span
contract still cannot universally detect editors silently rewriting text or
discarding spans without timely callbacks, as accepted in the original plan.

Validation: fresh JVM 630/630 PASS, zero failures/errors/skips, including 23 new
tests. Coverage includes all three languages, decomposed Unicode, length changes,
context eviction, missing/late/losing model evidence, original/manual choice,
mode/policy/language/layer/partial-search vetoes, region/commit refusal, exceptions,
synchronous acknowledgements and ownership loss between batch operations.
The actual closed production quality gate is exercised separately from injected
admission. Full lint, three variants, privacy/dependency/IME and native-symbol
gates plus Android test assembly PASS (277 tasks). Post-commit JVM remains required.

The source dependency gate initially rejected `internal fun interface` because
its function regex consumed `interface` as a function name. Symbol recognition
was fixed without expanding the allowlist. A valid functional-interface fixture
and a transitive network violation fixture now prove 17 negative / 5 positive
cases. Initial compilation/fixture failures and the gate failure are preserved;
the Unicode fixture was corrected from an NFC-equivalent original/candidate to
an actual typo. One automatic approval review expired before Gradle started;
the permitted retry ran successfully.

API26 and API37 each passed 22/22 composing, live-candidate, mechanical and new
owned-batch tests (346.855 s / 518.148 s). These APKs preceded the additional
whole-token/ambiguous-boundary/cleanup guards. The new protocol test uses the real
IME-to-`:qa_editor` Binder connection and checks final text/regions, exact operation
counts, zero readback and unchanged key instances. It directly exercises the
executor; it does not override quality or claim full automatic IME integration.
Final-APK executor protocol: API26 1/1 PASS (9.171 s), API37 1/1 PASS
(12.556 s), APK SHA256
`617e97a9d250c9bcbc409b20a7b3c66275351a398a399570c4418865dfdbf4a7`.
This narrower final run does not claim full automatic IME integration.

The physical phone reconnected. The user-authorized final debug APK above was
installed successfully on SM-F966B / Android16 through the named phone profile;
launch and fresh setup UI confirmed. Status remains `Не включена`: installation
and app launch PASS, actual keyboard typing and full Fold qualification remain
open. No app data clearing, uninstall or screenshot/hierarchy persistence occurred.
No physical performance/energy claim, model publication, push or remote PR occurred.
Version remains 0.2.0.

Enter/newline/editor-action integration, automatic availability with the strip
hidden, contextual punctuation, final frozen end-to-end holdout, automatic IME
Binder integration, full device/energy matrices and external release gates
remain open. This is implementation progress, not completion of Smart Typing 0.3.

Evidence: `tools/qa/smart-typing-0.3/results/2026-09-03-boundary-correction/`.
