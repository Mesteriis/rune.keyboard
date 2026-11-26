# Q7 API 37 general instrumentation rerun

A fresh task-owned API 37 emulator ran the same direct general instrumentation
scope as the previous failed run: the `q4-counters` fixture and four separately
routed classes excluded. AndroidJUnitRunner reported 352 tests, 48 assumption
skips, no failures and `OK (352 tests)`: **304 tests executed**, not 352. The
run took 2,610 seconds. The raw log is
`build/q7-api37-general-rerun-20261029.log`; the runner's `-1` final code alone
is not a proof of success.

The app and test APK were rebuilt before the run, including the editor-boundary
test fix. This run predates the later search-completion diagnostics change and
the new expanded-suggestion test; it cannot prove those later changes. It also
does not replace the separate scopes, Gradle-connected report gate or a hosted
CI rerun. The previous failed general run and the suite-only failures remain
disclosed in their receipts. The emulator was identified by AVD name, then
removed after the later targeted API 37 test completed. No physical phone was
used. Q7 remains open.
