# Release

Rune 0.1 ships as a signed APK installed by hand — no store, no update channel, no ADB required
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
./gradlew clean testDebugUnitTest lint assembleDebug assembleRelease privacyGateRelease
```

The signed artifact lands at `app/build/outputs/apk/release/app-release.apk`.

## Verify before shipping

1. `privacyGateRelease` passes — it fails the build if the merged manifest declares any permission
   or if any source file logs (`Log.*` / `android.util.Log`).
2. Work through `docs/ACCEPTANCE.md` on a physical device, including the fold and settings sections.
3. Install the release APK on a clean device and complete onboarding without ADB:
   open Rune → enable → select → the status card reads **Active**.
4. Turn on airplane mode and type a message in all three languages.

## Install

```bash
adb install -r app/build/outputs/apk/release/app-release.apk
```

For a device without ADB, transfer the APK and install it from the file manager; Android will ask
to allow installs from that source.
