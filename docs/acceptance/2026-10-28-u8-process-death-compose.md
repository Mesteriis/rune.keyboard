# U8: IME process death with an independent Compose editor

The previous same-package process-death probe could not retain its editor. This
test uses the separately installed, network-free Compose QA application instead.
On API 37, Rune typed `old`, pasted `foreign` through the real editing panel,
and waited while the host killed only Rune's process. The separate editor PID
remained unchanged. Android hid the IME; the second phase reopened it through
the same field, verified the editor PID, text and caret, then typed `teh teh `.
The final text was `oldforeignteh the `: the adjacent foreign boundary stayed
literal and correction resumed after the user's own space. The six editor
payload-read counters did not increase during Rune's subsequent typing.

The first instrumentation phase intentionally ends with `Process crashed`
because the host kills that process; it is not a passing JUnit phase. The
second phase reports `OK (1 test)` and checks that the new Rune PID differs.
The explicit `runeEditingDeathFixture=true` opt-in and emulator hardware check
restrict the fixture to disposable emulators. Both phases must be invoked
individually; the first deliberately fails if the host does not kill it.
The QA editor and clipboard contain only synthetic data. This does not cover
API 26, a physical device, process death with right-side text, or manual
accessibility. No phone was used.

The independent editor APK matched the previously recorded U8 Compose artifact
(`50d0cbc99152696931c77d895bba55f12edda66fdb3d8534805e58dbbf659126`). A fresh
offline build of that standalone project failed on a Kotlin dependency-lock
resolution error, so this run used the hash-matched existing artifact; it is not
a fresh Compose build. The Rune debug APK hash was
`111afa4e09889499ea35318bcb2c4fd6b56892e15b44e101f02a382ff3cc1e40`, and test
APK `780a21e0e28c035b1b39b9a19c356aaa54cd875d79264d20da6e3ba1bbdd9f2f`.
The two raw phase logs are in `build/review-u8-process-death-20261028/`.
