# U15 voice IME switch (partial)

At each input-view start, Rune looks for an enabled IME with an enabled `voice`
subtype. Non-sensitive mode keys then offer a microphone alternate with a named
accessibility action. The command rechecks availability on use, switches to the
voice subtype with the platform API, or shows the system picker if the target is
missing or Android rejects the switch. Password fields never offer or dispatch
the voice command. Recognition is performed by the other IME; Rune adds no
microphone permission or audio handling. System package visibility can affect
which IMEs are discoverable. See Android's [IME subtype API](https://developer.android.com/reference/android/view/inputmethod/InputMethodSubtype)
and [input-method service API](https://developer.android.com/reference/android/inputmethodservice/InputMethodService).

Actual tests on task-owned ARM emulators: on API 26 and API 37, an enabled
system voice IME appeared in Rune's accessibility actions and invoking it
changed the selected input method to that voice service. Disabling that IME on
the emulator made the voice action disappear on both APIs; it was restored
afterward. These tests are gated by the explicit `voice_test_mode` argument and
are skipped in ordinary instrumentation runs without the required device setup.
The API 37 enabled test initially failed when a cold boot started with its voice
IME disabled; after explicitly enabling it, the final test passed. The earlier
failure and the other raw outputs remain in ignored `build/u15-voice-*.log`.
The isolated key-view accessibility suite also passed eight methods on API 37.

The final JVM suite passed 1,362 tests with zero failures, errors or skips;
`lintDebug`, `imeIntelligenceBoundary` and `forbiddenRuntimeDependencies`
passed. Debug APK SHA-256:
`72a49d5a01442f026b1f93614e33749bb8550f9f4be3a83ea8308245263420ca`.
Test APK SHA-256:
`e18b7a6dc4d567786cf1b23d141773408919bafd4d3e5071a752806db2022a8a`.
The clean-source `:app:privacyGateRelease` run on commit `261b35e` passed;
its raw log SHA-256 is `81ecd8285d012245164e31c81da7bc2eb90e03f405ba5aeb06dc89b80a5e6ae5`
and release APK SHA-256 is `068f9c9f75c2239f058dd9e0007527eb5826d35363d5674e62c3be449e1e3864`.
A subsequent API 37 emulator run verified the actual hold/move/release gesture
on the voice popup and the system picker after disabling the voice IME while the
keyboard was already shown. See [gesture and fallback evidence](2026-10-28-u15-voice-gesture.md).
No Fold test or manual TalkBack is claimed. The Fold was left with the
previous build for owner testing; neither emulator test used the phone.
