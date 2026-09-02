# Settings rendering regression evidence

Old service on API37 failed the new held-key identity assertion after ACTION_UP. The tests-only patch was built and installed against the previously installed baseline app before the production branch was applied. The fixed service then passed the full three-case mechanical class on API26 and API37 with the same final built APK pair, installed successfully using install -r.

Runner: `io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner`; arguments `-w -r -e runeFailureArtifacts false -e class io.github.mesteriis.rune.keyboard.qa.MechanicalPunctuationInstrumentedTest`. The old-service control selects only `#cachedMechanicalTogglePreservesHeldKeyInstancesAndNextInputUndo`.

The test compares actual in-process keyboard/key references before release and after UP and queue drain, requires exactly the expected composing output, immediate Undo and six zero readback counters. API26 uses test-only legacy window reflection; API37 uses WindowInspector. Neither screenshots nor hierarchy dumps are recorded. The fixture restores prior preferences and IME state.

Source and built APK hashes identify the build, not installed-APK readback. Durations are functional test execution times, not typing latency. API27/28, physical Fold and remote CI are unrun. The separate dated acceptance report describes the scope and open release gates.
