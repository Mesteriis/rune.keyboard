# Q7 local emulator navigation mismatch

The local repeat of the API 37 CI shell after the APK restoration fix used a
new `rune-ci-boundary` AVD. Its general suite reported a failure in
`ImeInsetsInstrumentedTest.bottomRowStaysAboveNavigationAndClickableAfterReopenAndRotation`:
`Fixture must have a navigation exclusion`. The failure PNG and hierarchy were
preserved under ignored local `build/q7-insets-failure-20261029/`; the image
shows the QA field and keyboard without a software navigation bar.

This local emulator was started without `-prop qemu.hw.mainkeys=0`; its AVD
configuration has `hw.mainKeys=yes`, and the running emulator's
`qemu.hw.mainkeys` property was empty. The actual CI emulator options explicitly
include `-prop qemu.hw.mainkeys=0` for this test. Therefore this run does not
reproduce the workflow's device setup; it cannot establish an insets product
regression or a successful end-to-end CI run. The earlier full boundary run
using the explicit property had a passing general suite. Complete this current
run, retain its results, and repeat on an emulator with the workflow's software
navigation setting before drawing conclusions.

The same run also failed
`KeyFlickImeInstrumentedTest.allThemesAndLanguagesCommitSecondaryCharactersWithoutTheBaseLetter`:
the expected `1@?` remained `1@`. Its preserved failure hierarchy reports the
period key at `[248,580][276,636]` on a 320×640 display. The test sends its
swipe from the key centre to centre plus 80% of its height: the computed end is
below the 640-pixel screen. The captured screen also shows the key at the lower
edge with no software navigation bar. These observations explain why this
particular input cannot be treated as a clean in-bounds gesture, but do not
prove the product gesture path correct. Repeat on the properly configured
emulator and investigate if it still fails.
