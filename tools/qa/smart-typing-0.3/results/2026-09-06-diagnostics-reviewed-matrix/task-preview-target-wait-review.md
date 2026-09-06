# Preview target wait review

**Spec verdict: PASS. Code-quality verdict: PASS.** No actionable finding in this delta.

The change at [`ImePrivacyInstrumentedTest.kt:37`](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/ImePrivacyInstrumentedTest.kt:37) replaces two immediate character-label lookups with one bounded wait for the actual `b`/`B` target, using the existing 5,000 ms fixture timeout. It runs before bounds are frozen, baseline capture and DOWN. It does not retry a touch or visual assertion, change the three policies/controls, or query accessibility during the held touch. The complete 1,000 ms observation window, pixel thresholds and finally-cancel paths remain unchanged.

The precondition is supported by source: `focusField()` ultimately waits for Delete, whereas `keyPreview` changes affect the keyboard view and `RuneInputMethodService.onSettingsChanged()` recreates it. Delete availability does not prove this character target is already available. This supports waiting for the needed target; it does not prove the exact scheduling cause of the original miss.

The new lookup returns the first label match rather than the driver's bottom-most match. This does not introduce a false-pass route in the reviewed fixture: the normal editor is seeded with `leftright`, the QA labels are not single `b`/`B`, and every touch still requires [`assertPreviewFixture()`](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/PreviewPolicyAssertions.kt:13) to match exactly one real Rune key at the frozen screen bounds, with CHARACTER style, no long-press alternates, and the expected live preview setting/input policy. An unrelated matching node fails that check before touch. If the fixture later introduces another standalone matching label, target scoping should be revisited; no such competing target was found here.

Reviewed `task-preview-target-wait.md`, exact `task-preview-target-wait-diff.txt`, the changed test and relevant driver, QA seed, policy-assertion and settings/view-recreation source. Independently confirmed the changed file SHA-256 is `7a77563188f65ff08eace1b55de6e29ee326a436d0b354fbaa3f49d2880cfbf2`.

Retained `api26-matrix-152.log` shows phase 0 observed 4,662 changed pixels over 15 samples/1,003 ms, then phase 1 failed at `Character key not found`, before touch. `preview-target-wait-build.log` records BUILD SUCCESSFUL. Root reports API 37's full 152-test run passed. These records do not establish the changed test's runtime result; root owns the failed-case run and full API 26 gate. No additional repeats are requested.

No source edits, tests, Gradle, devices, model operations or delegation were performed. This report covers only the target-wait delta and its target-selection implications; it does not reopen diagnostics or the existing visual-policy test design.
