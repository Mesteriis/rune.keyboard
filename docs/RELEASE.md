# Release

Rune 0.2 ships as one signed APK installed by hand — no store and no ADB required
on the target device.

## One-time: create a signing key

The keystore and its passwords never enter the repository (`*.jks`, `*.keystore` and
`keystore.properties` are git-ignored).

```bash
keytool -genkeypair -v -keystore rune-release.jks -alias rune \
  -keyalg RSA -keysize 4096 -validity 10000
```

Then copy the template and fill in the values you just chose:

```bash
cp keystore.properties.example keystore.properties
```

| Key | Meaning |
|---|---|
| `storeFile` | Keystore path, relative to the repository root |
| `storePassword` | Keystore password |
| `keyAlias` | Key alias (`rune` above) |
| `keyPassword` | Key password |

Without `keystore.properties` the release build still succeeds; it just produces an unsigned APK,
which is what CI does.

## Build

```bash
./gradlew clean testDebugUnitTest lint assembleDebug assembleRelease assembleProfile \
  privacyGateRelease privacyGateProfile imeIntelligenceBoundary \
  forbiddenRuntimeDependencies :runtime-llama:nativeSymbolGate
```

With local signing configured, the signed artifact lands at
`app/build/outputs/apk/release/app-release.apk`. Without `keystore.properties`, Gradle and CI
produce `app/build/outputs/apk/release/app-release-unsigned.apk`; this is a build artifact, not an
installable release. CI also publishes the installable debug build as `rune-debug.apk` and the
unsigned release output as `rune-release-unsigned.apk`, plus `lint-results` and
`unit-test-results`.

## Verify before shipping

1. `privacyGateRelease` passes — merged release/profile manifests contain exactly
   `android.permission.INTERNET`, cleartext and backup are disabled, and Rune-owned code does not log.
2. `tools/verify-native-runtime.sh app/build/outputs/apk/release/app-release-unsigned.apk`
   confirms exactly `arm64-v8a + x86_64`, `JNI_OnLoad`, the allowed native dependencies and no Rune JNI logging/network symbols.
3. The embedded model size/SHA match the immutable `model-rune-text-v0.1.0` asset and its
   two-run reproducibility/Fold qualification evidence.
4. Work through `docs/ACCEPTANCE.md` on a physical device, including model delivery/runtime, fold and settings.
5. Install the release APK on a clean device and complete onboarding without ADB:
   open Rune → enable → select → the status card reads **Active**.
6. Turn on airplane mode and type a message in all three languages.

## Install

```bash
adb install -r app/build/outputs/apk/release/app-release.apk
```

For a device without ADB, transfer the APK and install it from the file manager; Android will ask
to allow installs from that source.

For RC testing, install `rune-debug.apk` from CI or a locally signed release. Do not try to install
`rune-release-unsigned.apk`.
