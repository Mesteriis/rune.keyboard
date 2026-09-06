# Released late numeric replies on real editor Binder

Base d0631f9 plus the enclosed two-file test delta. The existing resident-controller fixture first proves real normal composition, model binding/scoring, selected correction and Space replacement. It then holds a second exact public request in the separate fake-engine process and performs an actual editor action before releasing the numeric result.

Covered cases:

- Space followed by at least 300 ms, beyond the unchanged production 250 ms grace: Original plus boundary remains exact; expired token is invalid; release completes the exact remote request without editor command/text changes, strip resurrection or accepted coordinator callback.
- Actual language swipe to Russian: the English text is preserved and its composition finished; releasing the captured English reply leaves exact editor state and strip unchanged; subsequent Russian typing works.

Initial two-method runs (`*-01.log`) each contain one language PASS and one Space assertion failure. The Space test initially expected the correction batch (commit + region). Source inspection of `TypingSessionController.typeText` shows ordinary Space instead calls finishComposition then compose(boundary). The exact expectation was corrected to finish=1 and compose=1, with all other command deltas zero; no product or deadline change. Both original failures and exact initial patch/APK hashes remain preserved.

The changed Space case alone was rerun (`*-02.log`): API26 PASS in 19.118 s; API37 PASS in 19.517 s. Language was not changed or rerun; its original passing evidence is separately attributed. Full prescribed local gates pass, 240 tasks in 7 s. Inputs01/02 bind both APKs and test sources; deterministic gzip patches preserve the complete deltas.

These results close the expired-Space subcase and live language-switch case. They do not establish allowed within-grace delivery, next-text invalidation within grace, a different editor-field transition, exact-GGUF quality or physical-device performance. Engine numeric output is real fixture output transported through the production service/client guards; cancellation is allowed to suppress its delivery. Exact remote completion and unchanged editor/strip are asserted rather than treating cancellation alone as the outcome.
