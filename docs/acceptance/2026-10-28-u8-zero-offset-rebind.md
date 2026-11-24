# U8: zero-offset service rebind with foreign text on the right

On the API 26 Rune emulator, the real remote QA editor receives `foreign` by
Paste; Home moves the caret to offset zero. The test switches away from Rune and
back, verifies that the framework created a different service instance, and
checks that typing `abc teh ` produces `abc the foreign`. No additional Rune
payload reads occur after the rebind. This is a service rebind, not process
death or a physical-device test.

The isolated instrumentation method passed after rebuilding the debug and test
APKs (`OK (1 test)`). An earlier full nine-method run failed: after three passes,
the new rebind timed out and the fallback Google keyboard's application-error
dialog obscured the QA activity, causing five subsequent setup failures. The
full suite is not accepted from that run. The dialog was dismissed only on the
emulator. The earlier isolated run also exposed the test teardown calling
`clearPrimaryClip` on API 26; teardown now replaces the synthetic clip with an
empty clip there and always restores the driver in a `finally` block.

The complete nine-method API 26 suite subsequently passed (`OK (9 tests)`,
128.133 seconds) after selecting the emulator's installed
`com.example.android.softkeyboard/.SoftKeyboard` as the enabled fallback before
the run. The driver restored that fallback after each method. This is an
environment-specific correction, not a claim that the failing Gboard fallback
was repaired. The raw local output is
`build/review-u8-20261028/api26-suite.log`, SHA-256
`8ac4f931ddf56ae92d964b25c50c3e8e8c0717eb6bc54daed093c22f6c947a3c`.
The installed debug APK SHA-256 was
`111afa4e09889499ea35318bcb2c4fd6b56892e15b44e101f02a382ff3cc1e40`;
the test APK was
`720cb3b836af63326b4b4686e0d793068eb348d306685178e34d38eac31aebc6`.
Both device-side hashes matched the host files. The test source SHA-256 is
`b3c4e0da34949e0638d4daaafbcddf76a557767b0f78076c821a615d11ec4689`.

On the API 37 emulator, the same two APK hashes were installed and verified
on-device. The zero-offset method passed independently, then the complete suite
passed (`OK (9 tests)`, 95.398 seconds) with the emulator's Google Latin IME as
fallback. The full raw output is `build/review-u8-20261028/api37-suite.log`,
SHA-256 `ba346ad86bd1a8057aa50be38f5b54581b58c2906e5223a448527ee87731ea63`.
This does not establish reliability of that fallback on API 26.

U8 remains open for process death, Fold and manual accessibility. No physical
phone was used.
