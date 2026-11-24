# U18: API 36 navigation modes

A task-owned API 36 emulator was tested first with the gestural overlay active,
then with `com.android.internal.systemui.navbar.threebutton` active; overlay
state was read back for each mode. In each mode the live palette/text test and
settled synthetic screenshot capture both passed (`OK (2 tests)` per mode).
The synthetic editor contained `h`. Visual inspection of all four captures
showed the gesture handle and button icons distinguishable against their dark
and light navigation backgrounds. This is not a measured contrast guarantee.

Local logs and captures are in `build/review-u18-api36/`. The gesture and button
logs have SHA-256 `376bda4ad1556d884111f595b2b2120e61695c6b913b6135f56c5818c229ef97`
and `0c9985b0cfc9e317d9c6a154dde2ae4e5c890583019bbd273bf0aa6e853431b6`.
Debug APK SHA-256 was `111afa4e09889499ea35318bcb2c4fd6b56892e15b44e101f02a382ff3cc1e40`;
test APK was `fc29b82104601ac073874a137bc8918c2f49fa6e464240db38dc20184310ea39`.
The temporary emulator was stopped after testing. This does not substitute for
API 29, Fold display configurations or manual accessibility acceptance.
