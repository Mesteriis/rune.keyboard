# API 37 emulator matrix — 2026-09-06

Commit under test: `f7eb7e8cbc11b02346d6ff50432fc6b3ee5c6883`.

Command:

```sh
ANDROID_SERIAL=emulator-5556 ./gradlew :app:connectedDebugAndroidTest --no-configuration-cache
```

Result: **PASS**. The connected-test JUnit receipt reports 163 tests, 0 failures,
0 errors, 4 skipped, elapsed 1307.665 seconds.

The skipped tests are expected unavailable-environment checks: two exact installed-model
checks and two physical Fold checks. The latter are intentionally outside the emulator-only
acceptance scope. This receipt does not qualify API 26 or physical Fold.
