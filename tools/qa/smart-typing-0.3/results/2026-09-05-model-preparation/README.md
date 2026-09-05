# Session-owned preparation: Android evidence

September 5, 2026. Dedicated ARM64 AVDs `rune_smart_typing_api26` and
`rune_smart_typing_api37`, SDK properties checked as 26 and 37, boot completed
before installation. Started with no snapshot load/save and no data wipe;
stopped after the run. Phone disconnected and unused. Debug app/test APKs were
installed using `adb install -r -t`; their hashes are in `results.json`.

Both runner logs have exactly 33 starts and 33 success records, no failed/skipped
status, and `OK (33 tests)`. API26 took 9.945 s; API37 took 10.186 s. The APKs
are from the final production-source build. Results include source/log hashes
and the separate integration JVM count. The prescribed Gradle gates passed.

After building/installing to the selected emulator, the executed command was:

```sh
adb -s emulator-5554 shell am instrument -w -r \
  -e class io.github.mesteriis.rune.keyboard.intelligence.inference.ActiveModelLifecycleInstrumentedTest,io.github.mesteriis.rune.keyboard.intelligence.inference.ScoringLifecycleInstrumentedTest,io.github.mesteriis.rune.keyboard.intelligence.readiness.AndroidModelCandidatesInstrumentedTest \
  io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner
```

API37 used `emulator-5556`. These identify this run's processes, not future targets.
The first class uses the real active-model adapter, resolver, filesystem watches
and operation locks with a synthetic runtime. The other classes use real private
Binder IPC with synthetic numeric engines. This scoped pass does not establish
real-GGUF latency/quality, full IME/editor behavior, physical Fold or battery
acceptance. See `docs/acceptance/2026-09-05-smart-typing-0.3-model-preparation.md`.
