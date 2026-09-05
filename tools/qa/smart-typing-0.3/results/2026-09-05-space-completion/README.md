# Post-Space completion: local Android evidence

September 5, 2026. Existing dedicated ARM64 AVDs `rune_smart_typing_api26` and
`rune_smart_typing_api37`; runtime SDK properties checked as 26 and 37. Both were
started without snapshots for this run and shut down afterward, without wiping
their data. App/test APKs were installed with `adb install -r -t`. The phone was
disconnected and was not used.

The full numeric/status Android runner logs are `api26.log` and `api37.log`.
Each has 32 test-start and 32 success records, no failure/skip records, and
`OK (32 tests)`. Results, log SHA-256, source hashes and both installed APK
identities are in `results.json`. The final build's APK hashes match the tested
APKs. This is a scoped functional pass, not full release/energy acceptance.

After building and installing the APKs on the explicitly selected emulator,
the test command used was:

```sh
adb -s emulator-5554 shell am instrument -w -r \
  -e class io.github.mesteriis.rune.keyboard.intelligence.inference.ScoringLifecycleInstrumentedTest,io.github.mesteriis.rune.keyboard.intelligence.readiness.AndroidModelCandidatesInstrumentedTest,io.github.mesteriis.rune.keyboard.qa.SmartTypingComposingInstrumentedTest \
  io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner
```

API 37 used `emulator-5556`. These serials refer to the local processes started in
this run, not future target discovery. Never use an unqualified default ADB target.

The model-process/factory fixtures use a synthetic numeric engine. The composing
fixture separately exercises the real `:qa_editor` Binder `InputConnection`.
See `docs/acceptance/2026-09-05-smart-typing-0.3-space-completion.md` for exact
behavior, safeguards and remaining physical/exact-model gates.
