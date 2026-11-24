# U15 voice popup and stale-target fallback on API 37

On a task-owned API 37 emulator with its system voice IME enabled, the test held
Rune's `?123`, found the actual in-process voice popup cell, injected MOVE to its
bounds and released. The selected system IME changed to the voice service:
`OK (1 test)`. This verifies the touch path, not just the accessibility action.

A second test held a reference to the shown mode key, disabled the voice IME,
then invoked the already exposed accessibility action. The system chooser
appeared with Rune and another keyboard as entries, and the test restored the
voice IME: `OK (1 test)`. Two earlier attempts failed because the assertion
looked for a lowercase title containing `keyboard`; the actual chooser listed
its choices without that title. The diagnostic attempt recorded the visible
entries. Those failures and both final logs remain under ignored `build/`.

Tests require explicit `voice_test_mode` instrumentation arguments and are
skipped without their disposable-device setup. The emulator was stopped.
Production debug APK SHA-256:
`72a49d5a01442f026b1f93614e33749bb8550f9f4be3a83ea8308245263420ca`.
Final test APK SHA-256:
`76d4550d1b6803dbd6174373e2ea0b1936c588bfb95c9a57e78676d014abc2f3`.
These checks do not establish behavior on Fold, API 26 gesture/picker, manual
TalkBack, or the next-keyboard alternate. The owner's Fold was not used.

## API 26 follow-up

On a task-owned API 26 emulator, the same actual voice-cell hold/move/release
selected the enabled system voice IME, and disabling that IME after the mode key
was shown caused the chooser to list Rune and Gboard. A third actual popup
gesture selected the next-keyboard cell and opened the system chooser. Each
final invocation reported `OK (1 test)`; the voice IME was restored and the
emulator stopped. The final test APK SHA-256 for this follow-up is
`e2c46385b963f85d2d00a80b0b595f6ab4978b364166e5cd49ca2236fa9cd490`;
the production debug APK is unchanged. Raw logs remain in ignored `build/`.
These checks do not cover Fold or a manual TalkBack session.

## API 37 next-keyboard gesture

With Rune and another keyboard enabled on the task-owned API 37 emulator, an
actual hold/move/release on the `Next keyboard` popup cell was followed by
either a change of selected IME or the system chooser listing Rune and Gboard;
the test requires one of these outcomes and passed twice (`OK (1 test)` each).
The retained instrumentation summaries do not distinguish which branch occurred,
so no particular branch is claimed. The final test APK SHA-256 was
`f1b5d93faa1d353c06d2b9756c139ab3d50988186a117c21e05b11244466db05`;
the production APK was unchanged. The test is argument-gated to a disposable
emulator and the emulator was stopped. Fold and TalkBack remain outstanding.
