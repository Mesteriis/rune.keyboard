# U8: reproducible standalone Compose fixture

The standalone fixture's normal `assembleDebug lintDebug` failed because its
Android variant graph resolved `kotlin-stdlib-common:2.2.10` outside the lock.
Running `--write-locks` on up-to-date tasks did not fix it. Declaring the common
Kotlin metadata component at the existing 2.2.10 pin and regenerating the six
affected lock configurations adds exactly one locked module; all existing
locked module/version lines are retained. This is a test fixture dependency,
not a Rune product dependency.

After the change, offline `assembleDebug lintDebug` passed with configuration
cache disabled, then passed twice with the documented default cache, including
one cache reuse. On API 37, the rebuilt independent editor passed all three
`EditingComposeInstrumentedTest` methods, then passed the post-kill phase of
`EditingProcessDeathInstrumentedTest` with the same editor process surviving the
intentional Rune process kill. As in the prior receipt, the kill phase ends in
the expected instrumentation process crash rather than a JUnit pass. The rebuilt
fixture APK SHA-256 is
`c7171578d7805471a17a4262f9eecf5c24850200ccee6ac489a1d40403adda98`.
API 26, physical Fold and accessibility remain separate acceptance work.
