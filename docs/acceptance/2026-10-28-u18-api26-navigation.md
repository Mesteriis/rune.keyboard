# U18: API 26 button navigation

The task-owned API 26 emulator uses the three-button navigation bar. The live
palette-change test and synthetic screenshot capture passed (`OK (2 tests)`) with
the current debug APK and the prior test APK. An initial run failed both tests
before their bodies: the sample fallback keyboard had crashed at boot and its
error dialog obscured the QA activity. After closing that dialog on the emulator,
both tests passed. Raw logs are retained in `build/review-u18-api26/`.

The first light-palette screenshot showed no navigation icons, although the
background assertion passed. After adding a 500 ms settling interval to the
capture-only test, a separately rebuilt test APK passed (`OK (1 test)`). Visual
inspection of the new dark and light captures shows white navigation icons on a
black bar in both palettes. The initial missing-icons image remains evidence of a
transient observation; this check does not establish that the bar is never
invisible during a transition. The visual observation is not a measured contrast
result. Synthetic editor content was only `h`.

SHA-256: debug APK `111afa4e09889499ea35318bcb2c4fd6b56892e15b44e101f02a382ff3cc1e40`,
prior test APK `720cb3b836af63326b4b4686e0d793068eb348d306685178e34d38eac31aebc6`,
settled capture test APK `fc29b82104601ac073874a137bc8918c2f49fa6e464240db38dc20184310ea39`.
Settled dark and light screenshots hash to
`34e957b2bfc048fd460cd1c07ac1146b21daf08cc135649a021d9ed26eb2bdbb` and
`8912d2ef24a8e9b9872ffea74ed44dab7f360a52aaad48f805edd64c279b7d88`.

This covers the emulator's button mode only. Gesture navigation, API 29 and
35+, Fold displays and manual accessibility remain separate acceptance work.
