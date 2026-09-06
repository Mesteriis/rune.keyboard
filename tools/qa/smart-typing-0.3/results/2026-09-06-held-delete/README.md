# Held Backspace editor evidence

Base ac693666b9595fa229bff15292ad4ae2829f896f plus the enclosed four-file test patch. API 26 and API 37 each pass all four selected cases: unowned cancel, unowned detach, owned composition with both release/cancel, and one uninterrupted hold consuming model autocorrection Undo before ordinary deletion. Exact inputs and APK identities are in inputs.json; test sources and complete terminal logs are retained.

Actual key callbacks are counted and forwarded unchanged. Expected public editor text, prefix, caret and composing spans depend on that independent count; owned paths require exact editor command deltas and zero payload reads. Tests require at least three actions and a nonempty remainder, then verify stability after the terminal event. The model case uses the existing fake numeric engine through real model-service and editor Binder, with correction established before the hold.

API 26: 4/4 PASS in 54.975 seconds. API 37: 4/4 PASS in 54.540 seconds. No skips or assumptions. Full prescribed local gates pass, 240 tasks. These are focused correctness results; the prior full 152-test matrices remain separately attributed to their APKs. This does not claim physical Fold, exact-GGUF quality, long-running acceleration or performance qualification.

The production APK is unchanged. No phone installation or private diagnostic access occurred in this run.
