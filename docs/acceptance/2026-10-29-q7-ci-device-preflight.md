# Q7 CI device preflight

The Android workflow now invokes the existing owned-emulator guard before its
first Gradle installation or IME settings mutation. The guard requires exactly
one online ADB device, an emulator serial, QEMU hardware and the expected
`rune-ci-boundary` AVD name. It fails before those actions if a different or
additional device is visible. This is a point-in-time preflight, not continuous
isolation during a Gradle invocation.

The existing guard and restart-runner unit suite passes (three tests). A live
negative probe against the local isolated server refused its TCP-style serial
before executing any device-changing command, as designed. The hosted workflow
and positive preflight on its x86_64 AVD have not been run at this revision.
The local API 37 connected run already underway was launched before this
workflow edit and does not prove the new hosted preflight.

The boundary-suite command also requires the expected AVD name and rechecks the
same single-device identity before every suite. A regression test changes the
guard outcome after the first suite and confirms that the next Gradle command
is not run. All 11 boundary-runner tests pass. These checks do not prevent a
device appearing during an already-running Gradle command; hosted execution of
the changed command remains unverified.

The runner now repeats the same check immediately after each Gradle invocation,
so a changed device set cannot produce an accepted suite receipt. This detects
changes after a command returns; it cannot undo actions or detect a device that
appears and disappears entirely during that command. The regression test injects
a guard failure after one invocation and confirms no later suite runs.
