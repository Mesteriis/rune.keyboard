# API 37 emulator matrix — 2026-09-07

Commit under test: `1a5d037` (`docs: record API 26 emulator matrix`), containing
Smart Typing `0.3.0`.

Command:

```sh
ANDROID_SERIAL=emulator-5556 ./gradlew :app:connectedDebugAndroidTest --no-configuration-cache
```

Result: **PASS**. The connected-test run completed 163 tests with 0 failures and
4 skipped checks; Gradle reported `BUILD SUCCESSFUL` in 22 minutes.

The skipped checks require unavailable environment state: two exact installed-model
checks and one installed-model typing check, plus the physical Fold composing check.
Physical Fold is explicitly outside this emulator-only acceptance scope. The normal
Binder, composing, privacy, diagnostics, lifecycle, punctuation and packed-lexicon
matrix completed on the API 37 emulator.
