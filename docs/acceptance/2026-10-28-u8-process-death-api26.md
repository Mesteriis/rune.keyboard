# U8: process death with independent Compose editor on API 26

The API 37 process-death fixture was repeated on API 26 with the freshly built
independent Compose APK. The host killed Rune's process while instrumentation
was active; the separate editor PID and `oldforeign` text survived. The test
verified a different Rune PID and the same editor PID, then checked
`oldforeignteh the ` and no additional Rune payload reads during subsequent
typing. The post-kill phase reports `OK (1 test)`; the prepare phase's process
crash is the intentional host kill, not a JUnit pass.

The first attempt failed before setup because the sample fallback IME's crash
dialog covered the QA app. After dismissing it, two post-kill attempts retained
the editor and text but timed out waiting for Rune's hidden input window; neither
is accepted as a typing pass. On API 26 the final test explicitly switches to
the emulator's sample fallback IME and back to Rune *inside the new test
process* before typing. It checks that Rune is selected and measures payload
reads only after that switch, since the fallback can read the editor. Thus this
proves process death plus explicit IME rebind, not automatic window recovery.

The final test APK SHA-256 is
`1145ba0a9a0ef454f9bc7c97c57aa5a6fd99052dd65152d13d290a1d382107cd`;
Rune debug APK `111afa4e09889499ea35318bcb2c4fd6b56892e15b44e101f02a382ff3cc1e40`;
Compose APK `c7171578d7805471a17a4262f9eecf5c24850200ccee6ac489a1d40403adda98`.
The final post-kill log SHA-256 is
`017ff4f99e76670c3b8cbd7054d4c4a3dd5be1d80769055d7222e7060b4e7d05`;
all attempts are retained locally in `build/review-u8-process-death-api26-20261028/`.
Right-context process death, Fold and manual accessibility remain separate.
