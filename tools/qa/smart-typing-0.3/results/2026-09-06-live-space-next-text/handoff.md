# Live next-text invalidation during Space grace — handoff

Implemented against `3504f31521ec531bb58734d8318b86e8af401220`, changing only `LiveFakeModelBinderFixture.kt` and `LiveFakeModelBinderInstrumentedTest.kt`: 97 insertions, 16 deletions. No product, service, editor, settings, clock, deadline, scorer or qualification changes.

**Verification state:** `git diff --check` is clean and the scoped diff was inspected. No compilation, Gradle, device, model, network or test execution by this agent; root owns execution. No runtime PASS or red/green claim is made.

Run these exact methods on API26/API37:

- `io.github.mesteriis.rune.keyboard.qa.LiveFakeModelBinderInstrumentedTest#releasedReplyWithinSpaceGraceCorrectsAndCanUndo` — existing positive test; its body remains unchanged.
- `io.github.mesteriis.rune.keyboard.qa.LiveFakeModelBinderInstrumentedTest#nextTextWithinSpaceGraceRejectsOldReplyAndKeepsCurrentOriginal` — new negative test.

[observeOwnedSpaceWithinGrace:304](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderFixture.kt:304) extracts the reviewed actual Space observer into a private helper returning the real `spaceStartedAt`. It retains the unique focused QA editor/window/class identity, API26 source-ID fallback, exact before/after text event, real injected Space, current production Space token/selection and unchanged elapsed-time assertion. The helper recycles its event before returning. The positive wrapper retains its separate release-time, exact remote completion, asynchronous callback and post-delegate `<250 ms` checks.

[spaceThenTypeAAndReleaseWithinGrace:374](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderFixture.kt:374) caches the actual lowercase `a` key geometry **before** Space. After the shared observer proves that Space ownership is live, it injects real `a` DOWN/UP without an accessibility query inside the window. It requires the resident state to contain current word `a` and exact context `a helllo a`, no automatic edit or pending ranking, and both old model/Space token predicates false. Invalidation must happen before the production 250 ms window expires. After releasing the held remote latch through its real Binder control, it checks the time again: even the synchronous release response must return within the unchanged window. It then waits for the exact old public token's remote completion and correction mode.

[The new test:89](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderInstrumentedTest.kt:89) starts with `blockedWord(SCORES_PUBLIC_CORRECTION)`, preserving the existing exact request identity/public payload/readiness checks. After Space and `a`, it requires actual remote editor text `a helllo a`, caret 10 and owned span 8–10. From the pre-Space snapshot, only finish +1 and compose +2 are permitted; connection/region/commit/raw-key deltas remain zero. Existing six payload-read counters stay zero. A final snapshot stability check rejects a later mutation.

[assertCurrentOriginalAAndNoOldReply:408](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderFixture.kt:408) requires the actual strip's Original `a` to be selected, with the old `helllo` Original and `hello` correction absent. It also checks the current coordinator has exactly one Original candidate, text `a`, the controller's current opaque ID and matching selected ID, no automatic edit/pending ranking, and no revived old token. After these UI/state checks it requires the old token to be absent from delivered listener replies. The public known word `a` deliberately avoids the unrelated new ranking that the fixed fixture lexicon can produce for `z`.

The negative case cannot pass because Space ownership was never established, because expiry happened before the next key/release, because the next key was ignored, or because a stale correction was applied and later reversed: live ownership, the strict time checks, exact resulting text, and zero correction command deltas distinguish those cases. The positive case remains the companion proving that an otherwise current reply is accepted within grace.

All injected gestures retain `try/finally` cancellation on failure; the existing fixture `.use` lifecycle releases/closes its controlled service/client and restores the parked coordinator and settings. No editor-success callback, fake accessibility node, direct controller edit or time substitution was introduced.

Final source identities:

- `LiveFakeModelBinderFixture.kt`: `ed64f2a2986318bdeabf73114ee25b8c660963b8e54ce7c101cd76782a3a870a`.
- `LiveFakeModelBinderInstrumentedTest.kt`: `c439b3bf74b6ebc06dd1cbc1e076f0a5301f2c3d37625b093b1c24c36b29fdfe`.

Limits: ordinary-CI resident IME/coordinator/model-service/editor Binder with the existing fixed numeric engine/readiness/lexicon. The negative test permits the worker to suppress cancelled delivery; it does not independently force an already-dispatched stale callback through the IME main thread. No physical-device, real-GGUF quality or general latency claim is added. Root's fresh positive-plus-negative runs are required before updating acceptance evidence.
