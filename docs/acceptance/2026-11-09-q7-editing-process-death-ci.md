# Q7: independent editor process-death route

Android CI now runs both left- and right-context process-death scenarios after
the ordinary debug APKs and independent Compose editor fixture are installed.
The host runner requires exactly one verified task-owned emulator, checks the
installed packages and the preparation proof, and confirms the live Rune and
editor PIDs before signaling the verified Rune PID through the debuggable app's
own `run-as` context. It checks that the independent editor process survives.
The prepare phase must show its expected intentional instrumentation crash;
the separately invoked recovery phase must produce exact start/pass events and
`OK (1 test)`. API 26 requires an enabled sample Latin keyboard and explicitly
rebinds Rune; API 37 does not claim that the IME remains visible automatically.
The first failed scope stops the later scope and cannot produce a passing
receipt. CI retains the existing earlier-failure exit status and uploads the
new logs and receipt.

On isolated ARM64 API 26 and API 37 emulators, both final left/right scopes
passed with the same independent editor PID surviving each targeted Rune
process death. Both APIs used freshly built Rune debug/test and standalone
Compose APKs; API 26 used the explicit fallback/rebind. Each recovery test
verified exact synthetic editor text and that Rune added no payload reads.
The host tool's six tests pass, including skipped recovery, wrong device/PID,
missing fixture, permission failure, stale/invalid proof and wrong crash
transcript. The workflow-shell tests verify that the new failure status is not
hidden. The temporary source, APKs, logs and emulators were removed.

An earlier host-tool version used `am force-stop`. Both API 26 scopes passed,
but API 37 left-context recovery failed because the test could not find Rune's
`t` key. `force-stop` also changes the package stopped state, so that attempt
does not reproduce the original targeted process-death procedure and is not a
pass or proof of the failure's cause. The final targeted-PID implementation
passed both APIs. The complete modified CI workflow and hosted x86_64 have not
been run; physical Fold, real editor diversity and manual TalkBack remain open.
