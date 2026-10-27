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

Build from the Rune repository using its checked-in wrapper and configured SDK:

```sh
./gradlew -p tools/qa/compose-editor assembleDebug lintDebug
```

Install that debug APK, Rune debug and Rune's androidTest APK on a disposable
emulator. Run EditingComposeInstrumentedTest with instrumentation argument
runeComposeQa=true. It checks emulator hardware before changing IME/settings,
uses real Rune keys and prepares public clipboard sentinels in test code.
Without explicit opt-in these three cases are skipped, not acceptance passes;
without the fixture an opted-in run fails. The test driver does not install apps
or switch to a different device. Physical Fold acceptance is separate.

The fixture publishes only numeric length/selection and six InputConnection
payload-read counters through qa_compose_stats. It uses Compose's documented
InterceptPlatformTextInput hook with a stable remembered interceptor and returns
the original connection through a counting wrapper. It does not replace the
editor, fake responses, synthesize selection acknowledgements or export text.
Clipboard operations remain the editor's native implementations. Tests observe
fixed public text through accessibility, not through the IME connection.

References: [platform input interception](https://developer.android.com/reference/kotlin/androidx/compose/ui/platform/PlatformTextInputInterceptor),
[compiler setup](https://developer.android.com/develop/ui/compose/setup-compose-dependencies-and-compiler).
