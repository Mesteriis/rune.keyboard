# Held Backspace QA — independent review

**Verdict: PASS.** I found no actionable specification gap, false-green path, or regression risk in the frozen four-file slice. The archived API 26 and API 37 executions each pass all four requested methods without failures, skips, or assumptions, and the full 240-task gate passes.

## Dispatch observer and gesture timing

`ImeTestDriver.holdDeleteForActions` resolves both accessibility geometry and the resident in-process `KeyboardKeyView` before DOWN. It wraps that key's existing `actionListener`, increments only for actual `KeyboardAction.Delete` delivery, then invokes the original callback synchronously and unchanged. The counter does not supply an editor result or call the controller directly.

This aligns with production timing in `KeyboardKeyView`: a held Delete first dispatches at the platform long-press callback, then repeats according to `BackspaceRepeatSchedule`; UP after a triggered hold does not synthesize another click. The helper waits on observed callbacks rather than assuming an exact elapsed-time count, requires the initial action plus two repeats, injects the caller's real UP/CANCEL or detach sequence, drains the main thread, and returns the final delivered count.

Cleanup is sound. Failure before a completed terminal callback injects CANCEL in `finally`. Listener restoration occurs on the main thread only if the old key still owns the observer, so a legitimate listener installed by reconfiguration or view replacement is preserved. Every call site supplies a real terminal action. The later 900 ms text/counter checks would expose repeat work that survived release or cancellation after the observer was removed.

## Positive controls and exact outcomes

- The two seeded unowned cases first prove the exact public canary, require 3 or more dispatched Deletes without emptying it, and require the final editor value to be exactly `CANARY.dropLast(deliveries)`. A no-op, single-click-only path, duplicate deletion, or deletion after cancel/detach cannot pass the exact text and later-stability checks.
- The owned-composition case runs both CANCEL and UP in fresh sessions. It positively establishes the owned span and caret before the hold, requires more than one deletion, preserves the exact committed prefix, derives exact remaining text/span/caret from the independently observed dispatch count, and requires exactly one composing write per Delete with no region/finish/commit/raw-key-event delta. It also keeps all payload-read counters at zero and verifies command/span/caret stability after the terminal event.
- The Binder case establishes an actual successful fake-model ranking and the Space autocorrection `a helllo` to `a hello ` before one uninterrupted hold. For `N` delivered actions, it requires the exact result `"a helllo".dropLast(N - 1)`, one region write for immediate Undo, and exactly `N` composing writes for Undo plus ordinary deletion. Starting from corrected text and merely deleting cannot match both the text length/content and command ledger. The `3..6` bound guarantees at least two ordinary repeats and a nonempty owned remainder. Resident-controller acknowledgement, exact caret/span, zero payload reads, fixture restoration, and 900 ms stability remain enforced.

The observer counts before forwarding, but this does not create a false green: any dropped/refused forwarding is independently detected by exact editor text and command deltas, while an exception fails the instrumentation process. The private-field observer and the short fixed correction word are maintenance-sensitive and may conservatively fail after a key-view refactor or severe scheduling delay; they cannot make broken repeat behavior pass. The tests correctly make no acceleration, continuous-duration, physical-device, or model-quality claim.

## Scope and evidence

Only the four authorized Android-test files differ from base `ac693666b9595fa229bff15292ad4ae2829f896f`; the archived copies are byte-identical to the working files:

| File | SHA-256 |
|---|---|
| `ImeLifecycleInstrumentedTest.kt` | `2ad9943b21450c2b7a971e53b82bc39c141bf91da3f09551f3489066d5c20430` |
| `LiveFakeModelBinderInstrumentedTest.kt` | `f6dc7c2f925f1c30958c7369375d58571b3496a06aad398038f839040c32e5c4` |
| `LiveFakeModelBinderFixture.kt` | `d895947f65373bf84901e371a601043a33c07b00f3a49d5e8134cb08191da1b8` |
| `ImeTestDriver.kt` | `3e867f416efb9200a715244e99b33ca45d7eb0a3c696c3a3e325d4a1dec5f8e4` |

Archived execution evidence under `tools/qa/smart-typing-0.3/results/2026-09-06-held-delete/`:

- API 26: 4/4 PASS in 54.975 seconds; `api26.log` SHA-256 `f33e7d0bfe4358dd8d48c5ceb872bda6d4764b01bc808a106652984ae29e7349`.
- API 37: 4/4 PASS in 54.540 seconds; `api37.log` SHA-256 `da34af03047c784afa9ed457d834e9c2119b58a8343d8fcf11debe58de786d63`.
- Full gate: 240 actionable tasks, BUILD SUCCESSFUL in 7 seconds; `gates.log` SHA-256 `657186e7fe3dfd48b77eeff516e6b388db4fa405e4ed4fd79b3a42ccdd8cfa4a`.
- APK/source binding: `inputs.json` SHA-256 `5de1b0d04317b9f9160d4f47971be3fc7592f0e86756fd212713c9c160eb8902`; `results.json` SHA-256 `46c36406c010a7d06373c5b8fcf3d2311f4dfb4ff7a3a3a5ffab00159add8786`.

This review performed no source edit, Gradle invocation, device action, model call, or network access. It adds only this review report.
