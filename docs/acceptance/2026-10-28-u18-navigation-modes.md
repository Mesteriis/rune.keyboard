# U18 navigation modes: API 37 emulator evidence

On the API 37 emulator, switched the Android navigation overlay between gesture
and three-button modes and verified the active overlay in each case. In each mode,
`KeyboardThemesInstrumentedTest#paletteChangesRebuildImeAndKeepItsText` passed
(one test each): it exercises palette changes, retained editor text, requested
navigation icon appearance and a sampled navigation backdrop. The production
APK was the same as in the adjacent palette evidence. Those two tests used the
previous test APK recorded there.

A separate capture method, added to the test class in this change, passed once
per mode with the same production APK and a rebuilt test APK. The synthetic QA
editor contained only `h`. Visual inspection of the four captured screenshots
found the gesture handle and the three-button icons distinguishable against the
navigation backgrounds for both dark and light palettes. This is a visual
observation, not a measured contrast guarantee. Captures and raw instrumentation
logs are in ignored `build/u18-navigation-modes/`; they are not distributed.

The app APK SHA-256 was
`a5880c41ce5320f9c12c372e8c6cdead6f86ada1ffa7d8e83cdd4a97cb86fdba`;
the capture test APK SHA-256 was
`fd1c94c3e8c14a4cc8586f3caa5e70e052714e5572cae09367bd8b898bcbeea0`.
The emulator's original gesture mode was restored after the runs. These checks
do not establish behavior on Fold, other API versions or navigation variants,
nor replace manual accessibility and screen-specific acceptance.
