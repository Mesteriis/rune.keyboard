# Live second-editor stale-result review

Spec: **PASS for the bounded editor-switch case**. Code quality: **PASS**. No remaining actionable finding in the reviewed two-file delta.

Reviewed base `634cd1e19b1bbdaabc11e738071a16ced5db1a7a`, current sources and [qa-04.patch](/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/live-editor-switch-20260906/qa-04.patch), SHA256 `a95ca101d11aba86d7f68e8c0d306fe9cce0bcec4725f28e812c583815443589`. Source hashes match [inputs-04.json](/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/live-editor-switch-20260906/inputs-04.json):

- Fixture: `a1e456af357bf9f1fe6f4a2a7ef2d0ccc36de656a3cf88a45c5bdecce779d5f2`.
- Test: `bba5ab11d0874fa8d653a6e882e7faf106f067b9b8c779e2bd1b0865d0439d1b`.
- Test APK: `691e06062c2166d234363c31819afbde484b4e96862ad07a2373b3d45532484f`; product APK unchanged at `6a7d0d179b5c0446d88991cb14359ca63f97ce570e1ec09e2692667399f721e1`.

[releasedReplyAfterEditorSwitchPreservesBothFields:101](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderInstrumentedTest.kt:101) first proves normal model correction, then admits and holds the exact public old request. Explicit `NEW_TASK | MULTIPLE_TASK` uses the existing default-launch-mode QA activity in `:qa_editor`, retaining the old task. Explicit focus plus [the new-session assertion:272](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderFixture.kt:272) requires a newer resident controller session, eligible editor and no pending ranking. Exact `a`/caret/span in the second editor prevents merely continuing to type into the original field from passing.

The shared release helper requires the old token to be invalid before release, verifies the exact remote completion identity/mode and checks the second editor's complete settled snapshot and resident owner remain unchanged. Returning to the original editor requires exact `a helllo`, preserved caret and finished composition. [The return counter check:280](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderFixture.kt:280) forbids compose, region, commit and raw-key writes across the switch/return while correctly allowing connection creation and finish calls caused by focus lifecycle. Existing payload-read assertions remain intact. This is actual service/editor Binder evidence, not a successful-write stub.

[The structural comparison:295](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderFixture.kt:295) preserves every `SmartTypingViewState` field: enabled, selected candidate ID and ordered candidate list. Candidate data classes compare type, ID and text; the list is defensively copied and unmodifiable. This corrects an identity comparison on an ordinary class whose getter can return fresh equivalent instances. It does not weaken candidate-content/identity/selection checking.

Preserved harness history:

- **01:** plain launch did not establish a new typing session; the new-session assertion failed on both APIs.
- **02:** explicit separate task exposed missing target readiness on API26. On API37, the chosen `z` input could legitimately start a new request through the fixed `z`→`a` lexical candidate; a blanket no-pending precondition therefore failed. The final public known word `a` avoids that unrelated workload while still proving real input in the new editor.
- **03:** both runs reached the candidate assertion and failed equivalent `SmartTypingViewState` object identity. The structural correction addresses that precise mismatch.
- **04:** [API26](/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/live-editor-switch-20260906/api26-04.log) has one explicit code-0 PASS in 23.663 s; [API37](/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/live-editor-switch-20260906/api37-04.log) has one in 22.304 s. These are changed-case receipts, not a new full matrix. No product defect is established by 01–03.

Limits remain those of the existing fixture: fixed numeric scores/readiness/lexicon, no real-GGUF or physical-device qualification; coordinator candidate-state comparison rather than pixel rendering; and cancellation may suppress the score in the worker before a callback is dispatched. This closes the bounded row20 scenario of a held request completing after an actual editor/session change, not independent main-thread evaluation of an already-dispatched stale callback or allowed post-Space grace. Root is separately running the existing Space/language cases against the changed helper and owns gates.

Read-only review: no source changes, builds, tests, device/network/model calls or delegation. Only this report was written.
