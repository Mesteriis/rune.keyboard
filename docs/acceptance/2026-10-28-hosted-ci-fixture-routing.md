# Hosted CI: Android fixture routing and API 26 cleanup

The latest published `main` workflow run 40680972358 at `2c1ff975` failed
both Android emulator jobs and the replay job; its build, Python profiles and
MLX job passed. The replay stopped with `PINNED_KOTLIN_CACHE` before the
comparison. The logs do not identify which pinned JAR was missing or ambiguous.
The Android logs include API 26 `clearPrimaryClip` failures, incompatible
fixture ownership arguments, a separate-package lifecycle requirement, and
other editor/typing failures. These are not all explained by this change.

The Android CI runner now separates the general suite from the personal-store
suite (`q3-personal`), export-navigation (`q8-editor`), API 26 picker
(`q4-counters`), and two isolated qualification-package tests. It also runs the
native runtime suite. Each invocation retains its own log and fresh JUnit XML;
old XML is moved aside before a run. A zero Gradle exit cannot pass without a
fresh, nonempty, valid report and the expected minimum cases. All suites run
even if an earlier one fails, and the aggregate then fails. The API 26-only
picker is intentionally not scheduled on API 37, matching its SDK restriction.

Three Android test fixtures now use an empty synthetic clipboard item on API
26–27, where `clearPrimaryClip` does not exist. The picker test invokes the
system Save control's accessibility action instead of a potentially stale tap
coordinate. On an owned API 26 emulator, the original picker attempt reproduced
the hosted failure; the revised method passed twice and verified the numeric
file and cleanup. Preview and WebView clipboard suites passed five tests;
the separate Compose fixture was not run in this slice. Explicitly routed
personal, export-navigation, qualification-lifecycle and qualification-safety
tests passed 4, 1, 1 and 1 cases. AndroidJUnitRunner listing with `notClass`
excluded all four special classes and retained 352 general cases. This proves
the runner filter, not a full Gradle CI run or API 37 acceptance.

Routing unit tests cover scope assignments, continuation after failure, stale,
empty, skipped and malformed reports; five pass. The current local JVM suite
passed 1,390 tests without failures or skips, and lint/IME/scoring boundaries
passed. The local current-product replay matched all 2,160 and 12,000 frozen
rows. The hosted failure predates these local checks, and GitHub has not run
this routing change. Full emulator CI, API 37, hosted replay and the remaining
reported editor failures still require investigation. Raw hosted and local logs
are under `build/review-hosted-ci-audit/`; the owned emulator was stopped and
the physical Fold was not touched.
