# Release

Public releases contain a signed release APK, SHA-256 checksums and release notes for an immutable source tag. Never upload signing keys or local configuration.

## Signing

The private `rune-release.jks` and `keystore.properties` files are ignored by Git. Keep a secure backup of both: future updates must use the same key. They are not CI artifacts.

For an independent distribution, create your own key interactively:

```sh
keytool -genkeypair -keystore rune-release.jks -alias rune \
  -keyalg RSA -keysize 4096 -validity 10000
cp keystore.properties.example keystore.properties
```

Fill `storeFile`, `storePassword`, `keyAlias` and `keyPassword` locally. Restrict both files to the owner (`chmod 600`). Never paste passwords into shell commands or public logs. Without that file, the release build produces an unsigned APK for independent signing.

## Version and checks

1. Increase `versionName` and `versionCode` in `app/build.gradle.kts`.
2. Update `CHANGELOG.md`, the F-Droid recipe and Fastlane changelogs named with the version code.
3. Run:

```sh
./gradlew testDebugUnitTest lint assembleDebug assembleRelease assembleProfile \
  privacyGateRelease privacyGateProfile imeIntelligenceBoundary \
  forbiddenRuntimeDependencies :runtime-llama:nativeSymbolGate

tools/verify-native-runtime.sh app/build/outputs/apk/release/app-release.apk
```

The privacy gates check permissions, cleartext/backup, logging, source dependency boundaries and the absence of debug recorders from release/profile before and after shrinking. Native checks cover both packaged ABIs. CI's unsigned build uses `app-release-unsigned.apk` for the APK check.

4. Run the GitHub Actions API 26/API 37 instrumentation matrix for the release commit. Inspect actual job conclusions before claiming it passed.
5. Exercise changed UI and typing flows on a disposable emulator and/or an explicitly selected test device. A signed release smoke test should cover launch, onboarding, offline input and settings. Never clear a personal device's data to resolve a signature mismatch.
6. Model, dictionary, retrieval or runtime changes require the corresponding separate qualification in `docs/acceptance/`. A UI-only release does not establish a new model qualification.

## Publish

Commit reviewed source and docs, push `main`, then create an annotated version tag on the verified commit. Copy the **signed** APK to an external staging directory as `rune-keyboard-<version>.apk` and compute SHA-256. Verify its signature with Android Build Tools `apksigner verify --verbose --print-certs`.

Create the GitHub release from that tag, attach the APK and checksum file, and describe new behavior, validation and limitations. Confirm the remote release assets match the local sizes/hashes. The signed APK is `app/build/outputs/apk/release/app-release.apk`; an unsigned/debug APK is not a replacement.

The upstream release and a development debug build use different signing keys. Android deliberately rejects an in-place replacement between them. Users must make an explicit choice about removing a previous debug installation and its local data.

## F-Droid

Update and submit the [build recipe and metadata](FDROID.md). Official inclusion requires maintainer acceptance and an independent build; creating a GitHub release does not automatically publish to F-Droid.
