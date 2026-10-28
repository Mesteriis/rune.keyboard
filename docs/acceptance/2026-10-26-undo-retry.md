# Correction Undo and repeat-boundary regression checks

> Historical material from 2026-10-26. The original body is retained.
> Its source, model and device claims are not fresh acceptance. Current scope
> and outstanding evidence are in the [review completion map](../plans/2026-10-27-review-completion.md).

Additional local work while AURA owns Fold. No device commands, installation, product-code or model changes were made.

Three regression tests were added to `CorrectionBoundaryTest` using its real session controller and independent editor/executor fixture. English admission uses the existing synthetic qualified fixture; Russian finite confusions use the actual `CandidateGenerator` through the existing `publishCommon` helper. This validates editing/session behaviour, not independent spelling accuracy.

- 36 combinations: English `helllo → hello` and Russian `всее → все`, `зочу → хочу`; Space/comma/exclamation/question/semicolon/newline; synchronous and deferred editor acknowledgement. An emoji prefix survives correction and Undo exactly. Undo selects Original, blocks another candidate request, and repeating the boundary retains that original without another automatic edit.
- Two acknowledgement variants: completely erase the restored word, type a fresh word letter by letter, verify exact controller/editor context and first-letter retention, then correct and Undo again. Rejection does not permanently disable subsequent words.
- Two acknowledgement variants: erase/retype the final letter of an explicitly restored Russian word. Rejection persists for that word; after finishing it, candidate requests resume for the next word.

The first run found two test-fixture errors: the generic synthetic publication helper did not provide the finite-confusion evidence needed by these Russian inputs. No product bug was inferred from that run. Switching those cases to the existing real-generator `publishCommon` helper made all scenarios pass; the failed run and XML are retained.

Validation:

- Targeted `CorrectionBoundaryTest`: 95 tests, zero failures/errors/skips.
- Full `:app:testDebugUnitTest`: 1,083 tests in 110 suites, zero failures/errors/skips; Gradle exited successfully.
- `git diff --check`: passed.

Ignored evidence directory: `build/undo-retry-20261026/`, including the before-source snapshot, original fixture failure, corrected targeted check, complete unit-suite log and final receipt. Native behaviour remains to be checked in the agreed Fold window.

Subsequent physical window: see [physical coverage, the initial Undo failure and unchanged full-suite replay](2026-10-26-fresh-phrase-ranking.md#physical-fold-results). The 40 combinations above remain JVM coverage; they are not relabelled as 40 physical tests.
