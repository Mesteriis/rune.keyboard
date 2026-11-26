# U15: voice input method visibility and deterministic fixture

On API 37, a separately installed, enabled input method with a voice subtype was
registered by Android but absent from Rune's enabled input-method list. The
accessibility action consequently offered no voice switch; an explicit
visibility assertion reproduced the missing method. Android documents that
input-method listings are subject to package visibility on Android 11 and
later: [InputMethodManager](https://developer.android.com/reference/android/view/inputmethod/InputMethodManager).
Rune now queries the input-method service action, without requesting broad
package visibility or microphone permission. Switching delegates to the user's
enabled voice input method; Rune does not implement speech recognition.

The standalone debug-only Compose QA APK now contains a silent input method
with a voice subtype. It does not capture audio or access the network. Android
CI installs this existing independent fixture and runs three separately verified
scopes on its guarded disposable emulator: no voice method available, selection
via the accessibility action, and selection via the popup gesture. The enabled
scopes assert the exact fixture component, and the host runner restores the
previous IME settings. Skipped instrumentation is not a pass.

On isolated ARM64 API 26 and 37 emulators, all three scopes passed with the
fixture and current manifest, each with an exact successful instrumentation
transcript. Before the manifest fix, API 37 failed the enabled scope and the
separate visibility assertion; API 26 passed the three scopes. The fixture APK
permission inspection found no microphone or network permission. Three voice
host tests and three workflow-shell tests passed.

A clean temporary source snapshot with a registered pinned submodule passed the
release source gate, 1,395 JVM tests with zero failures or skips, lint, debug,
release and profile builds, release/profile privacy gates, runtime boundary and
native-symbol gates, and APK footprint. The merged release manifest contains
the targeted input-method query and neither QUERY_ALL_PACKAGES nor RECORD_AUDIO.
Temporary checkouts and APKs were removed. An earlier dirty-snapshot attempt and
a nested-clone attempt failed the source gates and do not count as passes.

With the updated fixture installed on a separate API 37 ARM64 emulator, the
three existing opted-in Compose editor tests passed individually with exact
instrumentation start/pass events. Both left- and right-context process-death
recovery scopes then passed with the independent editor. This cross-check does
not establish an API 26 or hosted workflow repeat after the fixture change.
The emulator, temporary source, APKs and logs were removed.

A subsequent CI routing follow-up requires two additional individually verified
scopes: disabling the voice target after Rune displays its action must open the
system picker, and the next-keyboard gesture must open the picker on API 26 or
switch/show the picker on API 37. On newly created isolated ARM64 emulators,
all five voice/keyboard scopes passed sequentially on each API. Four host-runner
tests passed, including skipped-result and unsupported-API rejection; the
workflow-shell tests passed. Emulators and temporary build artifacts were removed.
This was the direct fixture runner, not the complete CI workflow.

The complete changed CI workflow and hosted x86_64 execution have not been
verified. This fixture run covers the automated scopes above.

## Real TalkBack Actions on API 37

On a disposable ARM64 API 37 emulator, TalkBack 17.0.0.889642762 focused the
Rune **Symbols** key. The continuous down-then-right gesture opened the
TalkBack menu. Swiping to **Actions** and activating that item exposed
Rune's custom actions. [Google TalkBack menu documentation](https://support.google.com/accessibility/android/answer/6007066?hl=en)

- With all voice IMEs disabled, a swipe reached **Next keyboard** and a
  double-tap activated it. Android selected Gboard.
- With the silent QA voice IME enabled as the sole voice target, the
  same path reached **Voice input**. A double-tap made the exact fixture
  component Android's active IME.

An initial attempt left the system voice IME enabled. The action selected
that available component, so the run was repeated with one voice target.
The fixture verifies selection without speech recognition. Both scenarios
used the public QA editor. The APK SHA-256 digests were
`d1a9fa11fd62bb48cd02dddbff9a4fbfba99ee519a0ab8cc39bf8d68f811fbfd`
for Rune and
`55832a66d85c1d07a5b328f123c620c56930cfabe8af7c676542ee2a23946d94`
for the Compose/voice fixture. The completed event trace SHA-256 was
`cd6bea832048e79710cb699c06c9109d42e50dea3af20c7ec066385cc38a62dd`.
Physical Fold and physical TalkBack acceptance remain open.
