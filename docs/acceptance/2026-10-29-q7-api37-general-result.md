# Q7 API 37 general instrumentation result

The previously started general instrumentation run on the task-owned API 37
emulator finished with **352 tests and 6 failures**. The instrumentation
reported `INSTRUMENTATION_CODE: -1`; the host ADB process exit code alone must
not be treated as a test pass. The run used the previously built test APK and
predates the editor-test correction documented in
[q7-editor-boundary-api37](2026-10-29-q7-editor-boundary-api37.md).

One failure was the editor-boundary test addressed in that receipt. The other
five were three flick and two theme tests, each reporting the composing fixture
label instead of the expected edited text. Their individual reruns passed as
documented in [q7-api37-compose-isolation](2026-10-29-q7-api37-compose-isolation.md),
but isolation does not establish the cause of the suite failures. The complete
raw instrumentation output remains in the ignored local
`build/q7-api37-general-20261029.log`. The task-owned emulator was identified
and removed after the run ended. A fresh full API 37 run on current code, the
suite-only failure investigation, and hosted CI remain outstanding.
