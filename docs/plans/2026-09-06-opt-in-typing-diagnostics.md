# Opt-in typing diagnostics implementation plan

> Execute with the existing subagent-driven-development workflow. The user's September 6 request explicitly authorizes this debug feature; no additional design approval is required.

**Goal:** Two independent debug settings for content-free diagnostics and recorded Rune input, with two explicit confirmations before text collection.

**Architecture:** A main-source no-op-capable observer contract connects existing typing decision points to a debug-only recorder. Separate debug preferences, bounded asynchronous storage, and an explicit export/delete screen remain outside model IPC, delivery and runtime. Release and profile providers expose no settings and create no recorder.

**Tech stack:** Existing Kotlin/framework Android views, JVM tests and actual Binder editor instrumentation; API 26 minimum; no new dependencies or permissions.

## Global constraints / design

- Both switches default off. They are independent: text recording can work with metadata off and vice versa. This explicit debug opt-in is the sole exception to the original no-input-persistence contract.
- Text enable is OFF → scope confirmation → local-storage confirmation → ON. Only the second positive button persists consent version 1. Back, dismiss, stale generation and activity destruction leave it off. Malformed or unsupported preference/consent values fail closed. Disabling needs no confirmation.
- Eligible sessions satisfy `EditorContext.supportsSmartTyping`. No recording in passwords, NO_PERSONALIZED_LEARNING, email/URL/numeric/raw or other excluded fields. Do not read editor text, editor identity, clipboard or existing files outside managed logs.
- Recording arms only at a fresh input session after consent; never snapshot a pre-consent word/context. On editor/session invalidation, sensitive transition or destroyed ownership, close admission before finalization. Never join text across session gaps.
- Metadata contains only fixed enums, booleans and bounded counts/IDs/timings. No arbitrary strings, key values, text hashes, package names, exception messages or `toString` of payload objects. Distinct gated text records may contain bounded Rune-owned input/context, original/candidates and actual decisions/outcomes. Gate before copying payload and again at writing. Observer/storage failures cannot change typing decisions or editor behavior.
- One off-main debug writer, immutable queue records, at most 256 events / 512 KiB queued / 8 KiB per record. Keep at most 1 MiB metadata and 4 MiB text on disk, with bounded rotation. Overflow drops rather than blocking typing. Control commands cannot be starved by a full event queue.
- Consent changes and delete invalidate queued generations. Stop/delete acknowledgements occur after in-flight I/O ends; UI must not claim completion early. Delete disables both switches and removes all managed logs. Export tickets are invalidated by delete/new export; stale picker callbacks write nothing.
- A terminal editor outcome may survive session invalidation only as fixed enums and bounded numbers tied to the original eligible, consented operation. It contains no text snapshot in either stream; off/delete still revoke it. This narrow exception preserves refusal evidence without reopening text admission after an ownership loss or sensitive transition. Never label an old operation with a new session's IDs.
- Separate manual metadata and text export through ACTION_CREATE_DOCUMENT, no automatic upload. Snapshot and copy off-main; only a bounded immutable snapshot may be held during provider I/O. Explain that the chosen document provider may sync and exported copies are outside Rune's control.
- Debug strings disclose optional local logs. Release/profile expose no diagnostic UI/writer/serializer/export component; source and APK gates prove this without weakening existing network, JNI or editor-read boundaries.
- No version bump, model change or push in this task. The user's later explicit permission covers phone uninstall/reinstall; the current app and model/settings have been restored and verified. Existing editor verification and open 0.3 release gates remain distinct.

### Task 1: Recorder, consent, settings and typing integration

**Files:** New `smarttyping/diagnostics` contracts under main and variant providers under debug/release/profile; focused debug consent/store/UI files and resources; small hooks in `SettingsActivity`, `RuneInputMethodService`, `TypingSessionController`; focused JVM tests. Debug manifest only for a non-exported management activity.

- [x] Write and execute failing consent/admission/queue tests first; retain red output.
- [x] Implement pure consent/record admission and bounded writer with an injectable storage backend for race/failure tests.
- [x] Add debug settings contribution with two toggles in the settings screen, explicit two-dialog text consent, status/export/delete management, and localized EN/RU/ES strings following existing resources.
- [x] Add existing-decision observer hooks: candidates ready, ranking accepted/rejected, boundary reason and editor outcome, manual choice and Undo. Never recompute correction policy for recording. Record actual branch reasons, not inferred reasons from changed text.
- [x] Verify default off, each cancellation, malformed values, session provenance, sensitive transitions, stop/delete races, queue/disk caps and failure containment in JVM tests. Build all variants after integration.

### Task 2: Boundary gates and device verification

**Files:** `tools/verify-scoring-boundaries.py`, gate fixtures, debug instrumentation under `qa`, privacy/architecture docs.

- [x] Extend source resolution by variant; retain exact existing allowed model dependencies. Add an exact debug recorder storage allowance and fail release/profile if recorder/UI/text serializer becomes reachable or packaged. Add negative fixtures for transitive writes/network and wrong-variant implementations.
- [x] Actual settings tests cancel at each dialog, confirm both, recreate, disable and delete; actual Binder tests show permitted text/candidate/decision records and absent sensitive canaries in both streams with unchanged editor-read counters.
- [x] Run focused API 26/API 37 cases then required final variant/lint/privacy/dependency/native gates. Archive initial failures and final receipts separately.
- [ ] Commit reviewed slices; after every commit run `./gradlew testDebugUnitTest --rerun-tasks` with JDK 17. Phone signature incompatibility is resolved under explicit authorization; retain initial and current physical results separately.
