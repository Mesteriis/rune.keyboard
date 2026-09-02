# Local mechanical punctuation integration evidence

Final API26 and API37 runs each passed 18 tests: MechanicalPunctuationInstrumentedTest (3) and SmartTypingComposingInstrumentedTest (15). The initial API37 accessibility-popup lookup failure is preserved separately; its replacement test uses actual hold/release of the default first alternate and rejects early fallback insertion. No screenshot or hierarchy artifact was captured.

Both final AVD runs used the same built app/test APK identities recorded in source-identities.json, after successful `adb -e install -r` for each APK. These are build identities, not installed-file readback. Tests use only public QA editor fixtures and restore the pre-test preferences and IME selection. The two test classes were passed as a comma-separated `-e class` argument to `am instrument -w -r`, with `-e runeFailureArtifacts false` and runner `io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner`.

The logs are functional integration evidence, not latency or energy measurements. Six named readback counters exclude ordinary NORMAL caps lookup. Fold was unavailable over USB, so this slice has no physical install/test result. Remote CI, full physical lifecycle/performance, spelling quality and model publication remain open. See the dated mechanical acceptance report for boundaries and exact local gates.
