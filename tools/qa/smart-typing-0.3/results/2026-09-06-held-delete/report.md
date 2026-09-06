# Bounded held-Backspace implementation handoff

Implemented against base `ac693666b9595fa229bff15292ad4ae2829f896f`. Exactly the four Android-test files authorized by `task-held-delete-brief.md` changed: 155 inserted lines, nine removed lines. No production, debug editor/service, manifest, model, settings-policy or repeat-schedule change was needed.

**Verification state:** source inspection and `git diff --check` completed without whitespace errors. No Kotlin compilation, Gradle, instrumentation, device, network or model call was run by this agent. No runtime PASS or red/green claim is made. Root owns the build and both emulator runs.

## Exact methods for API26/API37

1. `io.github.mesteriis.rune.keyboard.qa.ImeLifecycleInstrumentedTest#backspaceRepeatStopsAfterCancel` — strengthened existing case.
2. `io.github.mesteriis.rune.keyboard.qa.ImeLifecycleInstrumentedTest#backspaceRepeatStopsWhenImeViewDetaches` — strengthened existing case.
3. `io.github.mesteriis.rune.keyboard.qa.ImeLifecycleInstrumentedTest#ownedBackspaceRepeatsPreservePrefixAndStopOnReleaseOrCancel` — new case; tests both terminal events in fresh sessions.
4. `io.github.mesteriis.rune.keyboard.qa.LiveFakeModelBinderInstrumentedTest#heldBackspaceUndoesModelCorrectionThenRepeatsOrdinaryDeletion` — new case.

## What changed and why

[ImeTestDriver.kt:301](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/ImeTestDriver.kt:301) adds `holdDeleteForActions`. It resolves Delete geometry and the actual resident key before DOWN, temporarily wraps its existing `actionListener`, counts `KeyboardAction.Delete` deliveries, and forwards every action to the original callback unchanged. It injects a real DOWN, waits for at least three actual deliveries with a deadline of the platform long-press timeout plus 1000 ms, then uses the caller's real UP/CANCEL or detach-plus-CANCEL. There are no accessibility queries or editor reads while waiting for progress.

The callback observation is necessary to give expectations an independent action count. Reading `repeatCount` immediately before CANCEL could miss an action before the terminal event, while reading it afterward yields zero because the product resets it. Counting the real callback avoids both races and does not supply a fake successful editor result. The wrapper adds no sleeps, dispatch changes, qualification override or direct controller call. Inspection failures are propagated to the test thread by `runCatching` within `runOnMainSync`.

Every held Delete is guarded by `try/finally`. Failure before a successful terminal event injects CANCEL; successful UP is not immediately followed by another CANCEL that could conceal broken release cleanup. A second `finally` restores the original listener if the observer is still installed, preserving any listener installed by legitimate key reconfiguration.

[ImeLifecycleInstrumentedTest.kt:17](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/ImeLifecycleInstrumentedTest.kt:17) strengthens both existing unowned seeded-text tests. They first assert the literal public canary, then require at least three Delete actions without exhausting it. The final text must equal the exact canary prefix after that many deletions. Existing cancel/detach and subsequent 900 ms stability checks remain. A no-op or single-click path can no longer satisfy a passive unchanged-afterward assertion.

[ImeLifecycleInstrumentedTest.kt:47](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/ImeLifecycleInstrumentedTest.kt:47) adds the owned-word case with public `a abcdefghijklmno`, features disabled except strip visibility, real key typing and real composing/editor counters. Each release/cancel subcase requires positive owned composition before the hold; at least three delivered Deletes; a nonempty remaining word; the exact prefix, caret and owned span; one composing write per delivered Delete; and no connection, region, finish, commit or raw-key-event deltas. It rechecks exact text and command/span/caret stability after 900 ms and keeps all six payload-read counters zero. Thus committed-prefix corruption, duplicate/missing edits and unexpected raw-key fallback fail.

[LiveFakeModelBinderInstrumentedTest.kt:56](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderInstrumentedTest.kt:56) adds the uninterrupted correction/Undo/repeat sequence. The existing fixture must admit the exact public remote request, receive the matching successful numeric correction, select candidate 1 without an edit, and perform the actual Space correction `a helllo` → `a hello `. Only then does one actual held Delete begin. For N delivered actions, the exact expected result is `a helllo` with N−1 trailing letters deleted: the first action must Undo, and subsequent actions must delete ordinarily. N must be 3–6 so at least two ordinary deletions occur and a letter remains. The real remote editor must report exactly one region write for Undo and N composing writes, with all other existing command deltas zero. The fixture's acknowledged, settled text/span/caret and no-payload-read checks remain active, followed by its complete snapshot stability assertion after 900 ms.

The only fixture addition, [LiveFakeModelBinderFixture.kt:268](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderFixture.kt:268), delegates the held gesture to the shared test driver. Existing `.use` cleanup still closes/restores the fake pipeline, and the normal test watcher restores settings/IME state.

## Identity and limits

| File | SHA256 |
| --- | --- |
| `ImeLifecycleInstrumentedTest.kt` | `2ad9943b21450c2b7a971e53b82bc39c141bf91da3f09551f3489066d5c20430` |
| `LiveFakeModelBinderInstrumentedTest.kt` | `f6dc7c2f925f1c30958c7369375d58571b3496a06aad398038f839040c32e5c4` |
| `LiveFakeModelBinderFixture.kt` | `d895947f65373bf84901e371a601043a33c07b00f3a49d5e8134cb08191da1b8` |
| `ImeTestDriver.kt` | `3e867f416efb9200a715244e99b33ca45d7eb0a3c696c3a3e325d4a1dec5f8e4` |

The callback wrapper is a test-only observation seam in the real key. It forwards the resident IME action path, and correctness is judged against independently observed remote editor writes/text. A refactor of the private callback field will require updating this test helper. The fake engine, fixed readiness and fixed lexical input retain their previously disclosed limits; this is not JNI/GGUF/model-quality evidence.

These are bounded correctness holds with variable action counts, not acceleration, continuous-latency or physical-device performance qualification. The unowned plain editor still has its existing observation surface; no debug readback-counter hook was added. The owned and model-Undo cases assert existing editor payload-read counters. Original passive-test logs remain historical evidence; only new root-owned runs can qualify the stronger assertions.
