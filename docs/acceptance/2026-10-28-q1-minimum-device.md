# Q1: setup screen startup on a 2 GiB emulator

The unreleased profile build at source
`d170c5b1971d3194c6cd707397ee2985d35d4e82` was built with
`:app:assembleProfile :app:privacyGateProfile --offline`; both tasks passed.
The profile APK SHA-256 is
`e9833778b4b9529f414c0a9fb45a57abea65c69726c83914189a604fdf4070ba`.
Its installed APK was read back and matched. The separate profile application
ID uses release shrinking and is not the owner's debug installation.

The task-owned Android 8.0/API 26 ARM64 emulator had 2 GiB configured RAM
(`MemTotal` 2,054,364 KiB). It was newly created, its screen was awake, and
package speed compilation returned success. One unreported launch warmed the
filesystem and compilation caches. For each of five included samples the
profile process was force-stopped and confirmed absent; `am start -W` then
launched Rune's `SetupActivity`. All starts returned `Status: ok` and the
requested activity. PSS was sampled with `dumpsys meminfo` approximately five
seconds after each start.

| Sample | Activity TotalTime, ms | Total PSS, KiB |
| --- | ---: | ---: |
| 1 | 126 | 15,249 |
| 2 | 117 | 15,282 |
| 3 | 110 | 15,517 |
| 4 | 111 | 15,295 |
| 5 | 115 | 15,346 |
| Median | 115 | 15,295 |
| Range | 110–126 | 15,249–15,517 |

This is process-cold, warm-filesystem startup of the setup screen, not the
first appearance of the IME or a storage-cold measurement. The emulator did not
contain a downloaded model or imported personal data. The independently measured
IME resource startup and PSS on API 26 are documented in the
[U17 receipt](2026-10-27-u17-profile-startup.md); those measurements use a
different candidate build and protocol. Neither sample represents a population
percentile or a performance guarantee on physical low-memory devices.

Raw `am start -W` and `dumpsys meminfo` output is retained in
`build/review-q1-min-device/`. The task-owned emulator was stopped after the
measurements. This closes the explicit minimum-device README measurement slice,
not Q1's remaining release, F-Droid and distribution requirements.
