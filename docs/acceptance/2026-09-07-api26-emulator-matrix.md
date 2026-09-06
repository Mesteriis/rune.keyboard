# API 26 emulator matrix — 2026-09-07

Commit under test: `b336cc1` (`release: qualify Smart Typing 0.3`).

Command:

```sh
ANDROID_SERIAL=emulator-5554 ./gradlew :app:connectedDebugAndroidTest --no-configuration-cache
```

Result: **PASS**. The connected-test JUnit receipt reports 163 tests, 0 failures,
0 errors, 4 skipped, elapsed 1371.002 seconds.

The skipped checks require unavailable environment state: two exact installed-model
checks and one installed-model typing check, plus the physical Fold composing check.
Physical Fold is explicitly outside this emulator-only acceptance scope. The normal
Binder, composing, privacy, diagnostics, lifecycle, punctuation and packed-lexicon
matrix completed on the API 26 emulator.
