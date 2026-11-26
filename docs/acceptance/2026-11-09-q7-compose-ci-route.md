# Q7: independent Compose editor routed into Android CI

The general Android suite discovers three `EditingComposeInstrumentedTest`
cases but skips them without the explicitly opted-in independent fixture. The
CI boundary plan now includes a separate `compose-editor` scope with
`runeComposeQa=true`. Its report must contain exactly the three expected method
identities; a missing, foreign, failed or skipped case prevents a passing
boundary receipt. The general-suite skips remain visible and are not counted
as successes.

After checking the disposable emulator identity, CI builds the existing
standalone Compose QA APK, checks that identity again and installs the fixture
using the explicitly returned emulator serial. Fixture build, device guard or
installation failure stops the shell before the boundary runner. The Compose
project remains separate from Rune's product dependency graph and APK.

On isolated ARM64 API 26 and API 37 emulators with the current product source,
the standalone fixture and Rune debug/test APKs were built in a temporary
checkout. Each API ran the opted-in Compose class: three tests, zero failures,
errors or skips, and the new exact-identity report parser accepted the fresh
XML. The cases cover native selection/cut/paste, vertical boundaries and
post-paste autocorrection recovery, including the six payload-read counters.
This was a targeted invocation of the routed test class, not a full execution
of the modified CI workflow.

The Android boundary routing suite passed 15 host tests, including missing
identity and skipped-case probes. The workflow-shell suite passed three tests,
including failures of fixture build, device guard and installation. The
synthetic restart and failure-artifact helper suites passed three and two tests,
respectively. Temporary checkouts, APKs and both emulators were removed.
Hosted x86_64 CI, physical Fold and manual TalkBack remain unverified.
