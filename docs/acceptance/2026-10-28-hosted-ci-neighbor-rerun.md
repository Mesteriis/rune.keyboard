# Hosted CI: neighbor recovery rerun

The published API 26 CI job failed two real-IME neighbor correction scenarios
and the packaged recovery test. A targeted rerun on a disposable ARM64 API 26
emulator with no second task emulator running passed both live-IME scenarios
and both packaged recovery/worker tests: 4/4. The packaged test recorded 100/100
complete recovery samples, baseline p95 5.456 ms and recovery p95 4.685 ms.
The source and app APK were unchanged. Raw runner output is retained at
`build/review-hosted-editor/neighbor-api26-solo.log`.

A separate API 37 targeted invocation also passed 4/4; another emulator was
running during part of that invocation, so its timing is not a clean performance
measurement. Its transcript is `neighbor-api37.log` in the same directory.

The original hosted failures are real and their cause remains unproven. These
reruns do not establish stability under hosted CI load, prove a fix, or close
Q7; the hosted workflow still needs a fresh run.
