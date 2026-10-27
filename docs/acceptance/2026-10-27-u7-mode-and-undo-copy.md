# U7: accurate mode, source, arrow and immediate Undo explanations

The old HIGH_CONFIDENCE description attributed automatic spelling correction to
a ready downloaded local model and a single frozen precision profile. Current
SpellingQualification also admits independent bundled/local sources without that
model. The EN/RU description now states that sources have their own checks,
explains Russian/Spanish/English availability and makes downloaded-model fallback
explicitly optional. Local name capitalization remains separately explained.

The owner-selected labels Auto-replace (95%) / Автозамена (95%) are unchanged.
Neither new description promises a single accuracy for every phrase. Both the
mode summary and actual setup help explain the → Space preview and immediate
Backspace restoration; the mode summary also explains the optional Restore
button. The shared Suggestions label and contextual punctuation strings are
unchanged. No static candidate demo was added to the interactive preview.

The actual KeyboardSetupActivity help TextView has a stable ID so the test can
scroll it into view and verify the displayed explanation. USER_GUIDE and
ARCHITECTURE now agree with the copy and source availability. The architecture's
stale contextual-punctuation default was corrected to OFF, matching
KeyboardSettings. Existing unrelated guide changes remain unstaged.

Validation on a fresh isolated Android 36 emulator: four instrumented tests pass.

- Real settings controls preserve independent choices and show the new summary;
  EN/RU resource contexts assert arrow, Backspace, optional model/Restore and the
  unchanged 95% labels. Descriptions contain no 95% accuracy promise.
- Actual setup help is scrolled on screen and equals the localized resource.
- Real RU input `зочу` shows the automatic `→ хочу` preview; Space produces
  `хочу `, immediate Backspace restores `зочу`, with no editor payload reads.
- Candidate-strip accessibility/tooltip verification confirms the automatic
  action label and clears the arrow/hint when returning to manual suggestions.

Debug app/test builds and final debug lint pass. Spanish continues to use the
intentional default English UI; the existing translation policy was not relaxed.
Only two string values per locale and the help view ID changed in product
resources. All runtime Kotlin, manifest, packaged assets, policies, model
parameters and thresholds are unchanged from 50822c6. No fresh quality,
performance, physical Fold or remote CI result is claimed by this copy slice.

The task-owned emulator and fresh AVD were removed after tests completed. The
adjacent evidence JSON binds resources, tests, owning policy/UI sources, APKs,
check outputs and the staged guide version. U7 local acceptance is verified;
the complete review remains open for the other cards.
