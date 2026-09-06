# Resident contextual strip QA — scoped review

**Final verdict: PASS for specification and code quality after the exact one-line correction.** Frozen 01 supplied meaningful RED evidence for a wrong fixture enum assertion. Frozen 02 corrects only that assertion, both contextual methods pass on API 26 and API 37, the existing spelling control remains independently proven by frozen 01, and no remaining actionable gap was found in the scoped three-file delta.

Reviewed scope:

- Base `07e29da5679fc9412c6a46df097def625a7b9cf2`.
- `LiveFakeModelBinderFixture.kt`, `LiveFakeModelBinderInstrumentedTest.kt`, and debug `LifecycleModelInferenceService.kt` only.
- `task-live-contextual-strip-report.md`, both frozen identity directories, `inputs-{01,02}.json`, `qa-{01,02}.patch`, and terminal API 26/37 `*-{01,02}.log` evidence.

Review activity was read-only except for this report. No build, Gradle, device, model, native, or network command was run.

## Closed finding

### 1. [QA code, closed] Exact known-word completion was asserted as the wrong enum

Frozen 01 `blockedContextualWord()` required `CandidateCompletion.COMPLETE` after the real local generator admitted exact known word `hello` (`LiveFakeModelBinderFixture.kt` line 248). The fixed public lexicon reports this successful no-alternative result as `CandidateCompletion.VALID_WORD`. Production contextual ranking admits it through `generation.isValidWord && alternatives.isEmpty()`; it does not require the `COMPLETE` enum.

Both frozen API runs independently fail both new contextual methods at this assertion with `expected:<COMPLETE> but was:<VALID_WORD>`. The existing spelling control passes. Each terminal log reports three tests and two failures:

- API 26 log SHA-256 `59ecb4162396626cf263a304e65c6497d1d9a70d6f6344cdaa5cad46a372a545`.
- API 37 log SHA-256 `8e3435cc570311e7f5b2012a9a1db60c0a7ddd614edc700adec884503d927e9c`.

Frozen 02 changes that one assertion to exact `CandidateCompletion.VALID_WORD`. Its diff against `07e29da5679fc9412c6a46df097def625a7b9cf2` differs from frozen 01 only by this line, and the preserved frozen 01 logs remain the RED evidence.

## Closure evidence

- Corrected source identities are fixture `f5674f31fe2c908c1084c7e13ccd115690db38b548b7037c22d5a2f167574615`, test `623641a17ea357ca8485c18ac1f204617e0649b11d8cb02f500ff07c0ee7f120`, and debug service `549ae7bc83d09112e755176f96f2d1fe77ccf8613a001fedd4d3c6ebcb8aec16`.
- Corrected `qa-02.patch` and frozen-02 `diff.txt` both hash to `1ecf014d4289ef2eac2433d57cbc83dea09c415eae6f1d065c45182a6765da27`. Frozen-02 `identity.json` hashes to `369d9662475346b5a02e3a5480405a19238f43a5629a872d54cb526051488adc`; `inputs-02.json` hashes to `dd096e0c41a1a05f008fc57bf472d504bc9d5f3ff8fae9614b1f8ba9f77f1275`.
- The corrected APKs are bound in `inputs-02.json`: app `f0b4cc3c8c7b9ea5601803c98047eeaea9ecb5ec69a6e5a4acc06f19131fca35` and test `4eb35b9cec4b2debf2cd8a0cde80e364e1d70497b2701fd63fb38b2b12787f9d`.
- Corrected API 26 is terminal `OK (2 tests)` in 23.304 seconds, log SHA-256 `b204695852adee4f3888f1017cb01644d8b137e7ff67e5e27f0f487bd2a0f6c7`. Corrected API 37 is terminal `OK (2 tests)` in 22.993 seconds, log SHA-256 `6ebbd2afd9bd3dc19993698f623f2a816ef62872d725421a8eb7c5c6e961611d`. Both report instrumentation code `-1`.
- The corrected compile receipt is `BUILD SUCCESSFUL` with 74 tasks; `build-02.log` hashes to `37b0197b0f67aa1b48cea5ec9bdecd0fec3a384d485574d845e62d58e1d87506`. The prescribed gate receipt is `BUILD SUCCESSFUL in 7s` with 240 tasks; `gates.log` hashes to `6df779541c6519724666082fe4b9875b37e6edeb43766ee7a022e3e1cbfc71d3`.

## Passing static checks

The remaining implementation is well bounded:

- The fixture sets actual preferences to spelling `OFF`, visible candidates, contextual `SUGGESTIONS`, and mechanical/double-space off, then checks the current resident owner facts. This proves contextual eligibility independently of spelling mode.
- The debug engine admits contextual modes only for prefix `a`, candidate IDs `[0,1,2,3,4,5,6]`, and exact ordered continuations `[' hello', ', hello', ': hello', '; hello', '. Hello', '? Hello', '! Hello']`. It records the captured mode before blocking, selects only comma ID 1 or period ID 4, and retains the production numeric schema and worker/Binder path.
- The fixture requires one exact additional public start, no increase in invalid public requests, exact current contextual token identity, no spelling token, and selected Original `hello`. A contextual mode cannot accidentally admit the old two-candidate spelling payload.
- Reply completion and the exact OK callback are tied to the captured token and mode. Before tap, the coordinator list must be exactly `[captured Original, expected punctuation]` with the opaque production punctuation ID, Original still selected, and no automatic edit. The subsequent full editor snapshot proves reply/ranking/strip rendering changed no text or editor counter.
- The punctuation cell is resolved from the actual visible resident strip and receives real DOWN/UP with cancellation in `finally`; no controller selection or fake editor-success call is used.
- Comma must yield exact `a, hello`; period must yield exact `a. Hello`, preserving the left context and changing only the intended first-letter case. Each explicit selection permits exactly one composing-text command and zero connection/region/finish/commit/raw-key deltas. The six payload-read counters remain zero.
- Actual Backspace must remove the final `o`, producing `a, hell` or `a. Hell`, again with exactly one composing-text command. `lastAutoEdit` stays null after the explicit tap and after deletion, so Backspace is ordinary deletion rather than automatic-correction Undo.
- Keyboard and all key object identities must remain unchanged after ranking, tap, and deletion.
- Existing public spelling modes retain their original exact payload branch and score behavior. The existing `originalControlThenModelCorrectionOnSpaceAndOwnedUndo` method passed in both API frozen-01 runs, providing direct regression evidence despite the contextual fixture assertion failure.

Frozen 01 identities retained with the RED evidence:

| Artifact | SHA-256 |
|---|---|
| `LiveFakeModelBinderFixture.kt` | `94e4ac9274781cf71764631cfd9c20e98cf7b5914bf056903e9eefd521c7731c` |
| `LiveFakeModelBinderInstrumentedTest.kt` | `623641a17ea357ca8485c18ac1f204617e0649b11d8cb02f500ff07c0ee7f120` |
| debug `LifecycleModelInferenceService.kt` | `549ae7bc83d09112e755176f96f2d1fe77ccf8613a001fedd4d3c6ebcb8aec16` |
| `qa-01.patch` / frozen `diff.txt` | `446123176b7c96207501b67a39cb18585091a79ac50c89b8ddf4f00bf3f35da7` |

The intended claim remains emulator-only resident service/controller/coordinator/strip/InputConnection behavior with test-owned readiness, lexicon, and numeric scores. It does not cover packaged disk readiness, GGUF/native quality, physical hardware, other languages/variants, or the already separate negative/stale cases.
