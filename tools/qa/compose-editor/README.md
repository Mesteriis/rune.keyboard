# Independent Compose editor for Rune QA

This standalone Android project supplies a real state-based BasicTextField for
IME compatibility testing. It is not included in Rune's settings.gradle.kts,
app dependencies, release APK or runtime qualification identity. Only its debug
variant is enabled. It has no network permission; AndroidX Core declares the
app-local signature permission DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION.

Pins define one compatibility sample: AGP 9.2.1, Kotlin/Compose compiler 2.2.10,
Compose Foundation 1.9.3 and Activity 1.10.1. The compiler pin matches Rune's
observed kotlinCompilerClasspath. The standalone version catalog and Gradle lock
file keep its library graph separate. The lint exception applies only to update
suggestions for those intentionally pinned catalog entries. Backup/transfer are
disabled. No network, model, logging or owner-data acquisition is implemented.
The Kotlin common metadata component is declared at the same pinned compiler
version so Gradle's Android variant resolution can be checked against the lock.

Build from the Rune repository using its checked-in wrapper and configured SDK:

```sh
./gradlew -p tools/qa/compose-editor assembleDebug lintDebug
```

Install that debug APK, Rune debug and Rune's androidTest APK on a disposable
emulator. Run EditingComposeInstrumentedTest with instrumentation argument
runeComposeQa=true. It checks emulator hardware before changing IME/settings,
uses real Rune keys and prepares public clipboard sentinels in test code.
Without explicit opt-in these four cases are skipped, not acceptance passes;
without the fixture an opted-in run fails. The test driver does not install apps
or switch to a different device. The private emoji case additionally accepts an
explicit Fold opt-in with failure captures disabled; the other three cases stay
emulator-only because they touch the clipboard. A physical host must preserve and
verify owner settings and diagnostic stores, and remove only its own QA package.

Android CI also runs `tools/ci/android_editing_process_death.py` after restoring
the ordinary debug APKs. It requires one verified disposable emulator and this
installed editor, checks both process identities, and kills only the verified
Rune PID during each synthetic left/right-context preparation. The preparation
crash is intentional; the recovery phase must independently pass. API 26 uses
an enabled sample Latin keyboard to rebind Rune explicitly. No physical device
or owner clipboard is in scope.

The same debug-only fixture also declares a silent input method with a `voice`
subtype for `tools/ci/android_voice_fixture_suites.py`. The fixture implements
no speech recognition, audio capture or network access. On a verified disposable
emulator the host runner checks the unavailable path, enables this exact fixture
for the accessibility and gesture paths, verifies stale-target and next-keyboard
behavior on API 26/37, and restores the previous IME state.
It does not test real speech recognition or a physical phone.

The fixture publishes only numeric length/selection and six InputConnection
payload-read counters through qa_compose_stats. It uses Compose's documented
InterceptPlatformTextInput hook with a stable remembered interceptor and returns
the original connection through a counting wrapper. It does not replace the
editor, fake responses, synthesize selection acknowledgements or export text.
Clipboard operations remain the editor's native implementations. Tests observe
fixed public text through accessibility, not through the IME connection.

References: [platform input interception](https://developer.android.com/reference/kotlin/androidx/compose/ui/platform/PlatformTextInputInterceptor),
[compiler setup](https://developer.android.com/develop/ui/compose/setup-compose-dependencies-and-compiler).

The opt-in `qa_private_input` extra marks the Compose input connection with
`NO_PERSONALIZED_LEARNING`. The emoji case checks that flag, selection, deletion,
continuation and the six payload-read counters. It dispatches the emoji grid's
item-click listener directly; it is not a physical-touch or screen-reader test.
