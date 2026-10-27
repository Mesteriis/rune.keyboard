# U12: personal phrases continue after long owned typing

PersonalTypingModel previously rejected every prefix longer than 512 UTF-16
units. Rune's owned session context can retain more than that, so phrase
learning and continuation lookup silently stopped during uninterrupted typing.

contextWords now examines the final 512 UTF-16 units. If the window splits a
letter token, its leading fragment is discarded through the next nonletter
boundary. A real boundary immediately before the window preserves the complete
first word. Existing sentence/message/symbol/control/digit boundaries still
discard preceding context, and only the final two validated words are used.
A 513-letter input without boundaries still yields no usable context. Short
inputs, word normalization, dictionary validation, support thresholds, language
scoping, storage formats and learning/phrase consent settings are unchanged.

Added six regressions in PersonalTypingModelTest, TypingSessionControllerTest
and CorrectionBoundaryTest. The initial run on the old implementation produced
165 tests with five failures, reproducing missing learning/continuations; the
clipped-word negative control already passed. After the focused implementation
change, all 165 targeted tests pass.

The rolling-session test types beyond 1,024 ASCII characters without changing
session identity or invalidating ownership, learns see you → soon three times,
and retrieves the continuation from a bounded context still exceeding 512.
The independent editor/executor fixture checks exact final text, unchanged
session ownership and no editor content reads. The suggestion inserts only after
an explicit current tap; its acknowledged commit increases phrase support to
four. Model tests also prove no implicit confirmed-word/feedback entries and
retain sentence, message, invalid-token and cross-language protections.

Integration command:

```text
./gradlew :app:testDebugUnitTest :app:imeIntelligenceBoundary :app:privacyGateRelease --console=plain
```

It exits 0: all 1,159 app JVM tests in 123 suites pass, zero failures/errors/skips;
17 negative/six positive boundary fixtures and debug/release/profile scoring
dependency checks pass; debug/release diagnostic packaging and the release
privacy gate pass. The integration command also builds a release APK, whose
hash/size are recorded in the adjacent receipt. No installation, device test or
remote CI run is claimed. The privacy gate is a boundary regression check, not
proof that all privacy/documentation review requirements are complete.

U12's requested model/controller acceptance is verified. The only production
change is phrase-context extraction over already Rune-owned text; automatic
correction admission, model assets, editor ownership and persistence policy are
untouched. Other review cards retain their separate acceptance requirements.
