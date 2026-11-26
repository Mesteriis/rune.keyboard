# API 26 general instrumentation run and system crash overlay

The locally installed debug and test APKs ran the 351-case general Android
instrumentation selection on a disposable ARM64 API 26 emulator with the
`q4-counters` fixture argument and the four CI-special classes excluded. The
raw AndroidJUnitRunner reported five failures; 48 assumption-skip status events
were also emitted. This direct runner invocation is not the complete routed
Gradle/hosted CI workflow.

At the first failure the foreground window belonged to Android rather than Rune.
An independent window query identified an `Application Error` dialog for Google
Search, and emulator logcat recorded that process crashing after exceeding its
100-job scheduler limit. Five mechanical punctuation cases failed while the
system overlay was present. The overlay was dismissed on the disposable emulator;
all five cases passed in a separate direct rerun (5/5). This is evidence of a
system overlay interfering with those cases, not proof that every timing or UI
failure has the same cause. The original full run remains failed and is not
relabelled as a pass. The emulator was stopped; no physical device was modified.

Raw logs are `build/review-hosted-editor/full-general-api26.log`,
`full-general-api26-system-errors.log` and `full-api26-overlay-retry.log`.
The short historical-source audits and Python profiles ran concurrently for
part of the suite; this is not an isolated performance measurement. API 37,
the complete routed scopes and a new hosted workflow remain outstanding.
