# Resident contextual strip: implementation handoff

Implemented the bounded row 26 emulator slice. Source inspection and `git diff --check` passed; this implementation agent performed no compilation, tests, device actions, model calls, networking, commits, or delegation. Root's first runtime attempt found a fixture completion-enum assertion error; the exact source correction is documented below, and runtime validation remains root-owned.

## Exact scope and identity

Handoff HEAD: `07e29da5679fc9412c6a46df097def625a7b9cf2`. The source scope is exactly three files; the debug control AIDL and all production sources are unchanged. Corrected full copies, `diff.txt`, and `identity.json` are frozen in `task-live-contextual-strip-frozen-02/` beside this report. The initial `task-live-contextual-strip-frozen/` remains immutable.

| Source | SHA-256 |
| --- | --- |
| `app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderFixture.kt` | `f5674f31fe2c908c1084c7e13ccd115690db38b548b7037c22d5a2f167574615` |
| `app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderInstrumentedTest.kt` | `623641a17ea357ca8485c18ac1f204617e0649b11d8cb02f500ff07c0ee7f120` |
| `app/src/debug/java/io/github/mesteriis/rune/keyboard/intelligence/inference/LifecycleModelInferenceService.kt` | `549ae7bc83d09112e755176f96f2d1fe77ccf8613a001fedd4d3c6ebcb8aec16` |

Corrected frozen diff SHA-256: `1ecf014d4289ef2eac2433d57cbc83dea09c415eae6f1d065c45182a6765da27`.

## Initial runtime failure and exact fixture correction

Root reports the initial three-method runs on both API 26 and API 37 had the existing spelling control PASS and both new contextual methods FAIL before releasing the held result. The failing fixture assertion at line 248 expected `CandidateCompletion.COMPLETE`; actual known-word generation returned `VALID_WORD`. Original logs `api26-01.log` and `api37-01.log` under root's `live-contextual-strip-20260906` build evidence remain preserved, as does the initial freeze.

The sole correction is that assertion's expected value, now exactly `CandidateCompletion.VALID_WORD`. `CandidateGenerator.kt:151` explicitly returns this completion for exact lexical membership. `TypingSessionController.kt:362–369` explicitly admits a valid word with no alternatives for contextual ranking. The fixed public lexicon's exact `hello` is such a word. No alternate result is accepted, no production contract changed, and all ownership, seven-ID payload, remote completion, strip, editor-command, no-readback, and Undo assertions remain intact. Corrected contextual runtime results are pending root's rerun at this handoff.

## Added test methods and exact assertions

- `LiveFakeModelBinderInstrumentedTest.contextualCommaStripTapChangesOnlyOwnedBoundary` (line 13): actual typing produces `a hello`, caret 7, composing span 1..7; actual punctuation-cell tap produces `a, hello`, caret 8, span 1..8. The following actual Backspace produces `a, hell`, caret 7, span 1..7.
- `LiveFakeModelBinderInstrumentedTest.contextualPeriodStripTapAlsoCapitalizesOnlyFirstLetter` (line 16): the same owned input and geometry yield `a. Hello`, caret 8, span 1..8; Backspace yields `a. Hell`, caret 7, span 1..7. The left `a` and every other word letter remain exact.
- Shared private `verifyContextualStripTap` (line 19): editor text and every numeric editor statistic must remain identical after the held reply completes, its exact winner reaches the live coordinator, and the real strip renders. Keyboard and key references remain identical after ranking, tap, and deletion. Each tap and deletion has exactly one `compose` command and zero deltas for connections, region, finish, commit, keyDown, keyUp, and deleteKeyDown. The six payload-read counters remain zero. The existing legacy NORMAL capitalization lookup remains allowed during actual editor commands; the pre-tap no-edit snapshot still compares its counter exactly. Actual controller `lastAutoEdit` must be null before selection, after the explicit tap, and after ordinary deletion.

## Fixture and remote contract

`LiveFakeModelBinderFixture.blockedContextualWord` (line 202) sets actual preferences to spelling OFF, visible candidates, contextual SUGGESTIONS, and mechanical/double-space OFF. This is supported by the unchanged production `CandidateOwnerState.canRequestContextual` and `LocalCandidateCoordinator.requestCurrentWord`; contextual eligibility does not require spelling to be enabled. Real owner facts must confirm the resulting policy, runtime qualification, READY fact, and English language. Existing fixed public lexicon entries `a` and `hello` are reused without changes. Actual key input and the actual 400 ms coordinator pause are retained; intermediate unknown prefixes cannot start spelling work under OFF.

The existing private remote control arms one held public request. Admission must match the current production `pendingContextualRanking` token, IDs `[0,1,2,3,4,5,6]`, exactly one additional public start, zero newly invalid public requests, no spelling token, exact `VALID_WORD` local completion, and the live selected Original `hello`. The fake engine independently admits contextual modes only for prefix `a` and ordered continuations `[" hello", ", hello", ": hello", "; hello", ". Hello", "? Hello", "! Hello"]`. It captures the admitted mode before waiting. Comma ID 1 or period ID 4 receives sum -1, all other IDs sum -1000, each token count 1. Real policy margins/ID/number checks are unchanged. The existing ten-second latch and numeric worker-health failure checks remain bounded.

`awaitContextualSuggestion` (line 264) requires an OK callback for that exact completed token and the exact live list `[captured Original, expected punctuation]`, including the production opaque punctuation ID with session/revision/request/winner components. Original ID and selected state must remain unchanged; the actual visible punctuation cell is enabled and unselected, and the actual visible Original cell remains selected. `tapContextualSuggestion` (line 294) resolves that live cell, checks the live item still exists, and injects real DOWN/UP with finally-CANCEL on unsuccessful release. No controller-selection method or editor-success substitute is invoked.

The only existing helper change adds the already transmitted numeric `invalidRequests` field to the local public snapshot, enabling a contextual admission assertion. Existing spelling/equal modes and test methods retain their behavior. Existing `.use` cleanup releases pending work, closes the replacement pipeline, restores still-live parked coordinators, resets the remote mode, and unbinds; the driver restores the complete previous preference map.

## Provenance limits

This is ordinary-CI behavior coverage for the resident service/controller/coordinators, production client, real model-service Binder/worker, and real `:qa_editor` InputConnection. It replaces readiness, lexicon data, and numeric engine output through the already established test composition root. It does not exercise the production AndroidModelCandidates disk-readiness factory, GGUF/native inference quality, physical hardware, or every contextual variant/language. The two positive edit cases do not replace separate stale-token, ownership-loss, negative-field, or held-out quality evidence. No overall release verdict is implied.
