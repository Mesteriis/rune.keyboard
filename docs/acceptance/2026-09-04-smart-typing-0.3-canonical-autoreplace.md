# Smart Typing 0.3 canonical-case AutoReplace — 2026-09-04

Baseline `e6e00f8`. An exact lowercase valid word with one packaged canonical-case candidate now
selects that candidate locally and applies it on Space, supported punctuation, or Enter when
`AutocorrectionMode.HIGH_CONFIDENCE` is active. The model is neither loaded nor queried for this
decision. Both canonical source metadata states use the same behavior; protected tokens, malformed
sets, non-text/sensitive/raw editors, non-letter layers, explicit Original, and disabled or
suggestion-only autocorrection retain their previous vetoes.

The edit uses the existing typing-owned correction transaction. The first Backspace restores the
exact lowercase original as composition and selects Original; no editor-wide undo stack or new
readback was added.

Fresh focused JVM tests passed 41/41. The required complete rerun passed app 643/643 and
runtime-llama 19/19, with zero failures, errors, or skips. On the physical Fold/API 36, the exact
debug build first demonstrated explicit candidates for public fixtures `москва`, `россия`, and
`иван`. A new real Binder instrumentation scenario then verified boundary AutoReplace and immediate
Undo for `я москва`; the isolated direct runner completed 1/1 PASS in 16.415 seconds.

The first Gradle connected attempt failed all four selected tests in shared setup before input because
the QA Activity did not become visible. A direct inspection after that run found the target Activity
absent. Reinstalling the exact app and test APKs and invoking the isolated AndroidJUnitRunner exposed
one fixture-only capitalization expectation (`Я` versus the actual `я`); after correcting that
expectation, the unchanged product scenario passed. The optional AndroidX test-services AppOps setup
warning remains visible in the Gradle run and is not counted as product evidence.

Ordinary spelling AutoReplace continues to cover the bounded candidate categories through the
existing calibrated ranking and correction transaction, but production qualification remains closed
until a candidate passes its frozen calibration and holdout gates. Candidate-05 prepared calibration
was still running when this slice was recorded. No model was published and version remains 0.2.0.
