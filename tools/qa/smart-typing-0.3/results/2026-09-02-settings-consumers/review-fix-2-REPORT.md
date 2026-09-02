# API26 empty-editor assertion: use actual numeric length

One test-only change relative to the current integrated root. Patch SHA-256: `ac20e2ee5b88ceebee87db464404d83eed4c72e262c06e218377792cf1a163f4`.

## Evidence and diagnosis

The preserved `settings-consumer-api26.log` reports 12 tests / 1 failure, 166.162 s. The sole failure is the empty-field comparison at `SmartTypingSettingsInstrumentedTest.kt:135`: UiAutomator returned `Composing Binder fixture`. The exact failed log SHA-256 is `7eb4ef60b4eb55e7a19fbe6328c2a30da0f13f8bc1856c73cb24772f924a639a`; this author did not modify it.

`ComposingQaFixture.kt:37` calls `setHint(R.string.qa_composing_hint)`. The debug resource value is exactly the observed string; the editor constructor does not insert it as Editable content. `ImeTestDriver.awaitFieldText` compares `UiObject2.text` directly, with no distinction for a hint. The API26 accessibility contract explicitly allows node text to represent the hint (`isShowingHintText`); therefore an accessibility text comparison against `""` is not an adequate empty-Editable oracle. [Android API reference](https://developer.android.com/reference/android/view/accessibility/AccessibilityNodeInfo#isShowingHintText()).

The existing debug fixture already publishes `length = editor.length()` alongside selection and composing statistics (`ComposingQaFixture.publish`, lines 100–110). It publishes initially and on existing editor/connection callbacks. That value excludes the hint and is content-free. A search of the existing QA tests found this new scenario was the only `awaitFieldText(..., "")` call; no shared driver normalization is necessary.

The failed run did not separately log its actual length value, so this report does not claim that value was observed as zero. The source and matching hint establish the faulty oracle; the corrected runtime assertion will independently fail if actual text remains.

## Change and preserved checks

Replace only that empty-string call with `assertEquals("Private editor retained text", 0, stats().getValue("length"))`, plus a comment explaining the distinction. This accepts no nonempty Editable, including real text equal to the hint. It does not alter the shared driver, fixture, production privacy/rendering policy or Undo.

The following real `w` insertion still must produce exactly `w`; old Original candidates must remain absent; composing must remain zero; all six readback counters remain checked. Earlier UP/CANCEL/identity assertions are untouched. The parent-reported other eleven API26 passes, including held geometry, remain historical results, not rerun claims.

## Narrow verification

Only the affected Android test and unchanged internal key-identity helper were compiled against current cached app/test/Android signatures: **exit 0**. Exact compiler command and output: `compile-command.json`, `compile.log`. The helper is included solely to preserve Kotlin internal visibility in the narrow compilation.

Isolated `patch --dry-run -p1` against the copied current test baseline: **exit 0** (`patch-command.json`, `patch.log`). `identities.json` binds the baseline, proposal, fixture, resource, driver/helper and original failed log. No tests, full JVM suite, Gradle, device, model, corpus or algorithm run was performed. Parent owns independent review and the corrected API26 / full affected API37 runtime gates. Root sources and parent documentation remain untouched.
