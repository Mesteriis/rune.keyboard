# U18: light palette store screenshot

`fastlane/metadata/android/en-US/images/phoneScreenshots/01-light-palette.png`
is an unedited 1080 × 2340 screenshot of the real SetupActivity home preview on
the API 37 emulator. The test sets the light keyboard palette, verifies the
rendered preview is light, then captures the screen. The field contains no user
text. The screen shows the embedded interactive preview, not a docked IME or a
physical Fold. `captureLightPaletteOnHomeScreen` passed (`OK (1 test)`), and the
test driver's teardown restores the emulator's preferences.

SHA-256: screenshot `93f44bc7f6801fdc148e2b8b28ee2912ad4e813fe88a8b0e8082636091cbbe51`,
debug APK `111afa4e09889499ea35318bcb2c4fd6b56892e15b44e101f02a382ff3cc1e40`,
test APK `f63ff00f7aaa8c2b869b0a5b8ed0e6e23e4f8cfb598576f8fa09fc2785a40574`.
The raw test log is retained locally at `build/review-u18-store/capture.log`.
This adds one English distribution screenshot; broader distribution acceptance,
Fold and manual accessibility checks remain open. No store was published.
