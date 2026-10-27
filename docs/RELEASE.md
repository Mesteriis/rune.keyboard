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
3. Commit the reviewed source and check the repository state before building.
   The app's `preReleaseBuild` now depends on `releaseSourceCheck`: live
   `git status --porcelain=v1 -z --untracked-files=all --ignore-submodules=none`
   must be empty, HEAD must exist and every recursive submodule must be initialized
   at its recorded commit. The check runs on every invocation, including Gradle
   configuration-cache reuse. It prints commit/count/reason metadata without
   filenames and does not alter the checkout. Ignored local signing/SDK/build files
   retain normal Git semantics; this is a VCS checkpoint, not hermetic-build or
   qualification proof. Run:

```sh
./gradlew testDebugUnitTest lint assembleDebug assembleRelease assembleProfile \
  privacyGateRelease privacyGateProfile imeIntelligenceBoundary \
  forbiddenRuntimeDependencies :runtime-llama:nativeSymbolGate :app:apkFootprint

tools/verify-native-runtime.sh app/build/outputs/apk/release/app-release.apk
tools/verify-native-runtime.sh app/build/outputs/apk/release/app-release.apk --require-no-local-paths
```

The privacy gates check permissions, cleartext/backup, logging, source dependency boundaries and the absence of debug recorders from release/profile before and after shrinking. Native checks inspect all four libraries in both packaged ABIs, reject DWARF/static symbol sections and require exact bytes from the runtime's stripped outputs. The app reuses the runtime module's pinned NDK for packaging. CI's unsigned build uses `app-release-unsigned.apk` for the APK check.

The separate `--require-no-local-paths` audit also rejects `/Users/` and `/home/`
strings. It currently fails on source-location literals retained in runtime
`.rodata`; stripping debug sections does not remove those literals. This remains
an open U16 release requirement. Do not interpret the ordinary native gate or
the 180,129,837-byte local release candidate as full release acceptance. Fixing
the compiler source-location recipe requires renewed runtime identity and
qualification evidence; do not rewrite packaged strings or qualification pins.
Unstripped build outputs stay local for symbolization and must not be published.

`apkFootprint` selects the single release output from AGP metadata, so signed and
unsigned filenames work without stale-file globs. It records the APK and budget
SHA-256, ZIP payload/unpacked sizes, container overhead and lib/lexicon/experiments/
res/dex/other breakdown. The checked-in limits live in
`tools/apk-footprint-budgets.json`: 183,000,000 bytes for the universal APK and
185,000,000 unpacked, plus component and native-ABI limits. Native limits are
5,000,000 bytes for arm64-v8a and 5,500,000 for x86_64; no separate ARM64-only APK
size is claimed. Change limits only in a reviewed commit with a CHANGELOG entry,
a fresh measured basis and an explanation of growth. The task never raises them.
The report at `app/build/reports/apk-footprint/release.json` contains `passed=false`
and fixed violation codes on budget failure. Structural errors exit nonzero and
remove an older report. CI uploads the report/budget file even on a failed check.

4. Run the GitHub Actions API 26/API 37 instrumentation matrix for the release commit. Inspect actual job conclusions before claiming it passed.
5. Exercise changed UI and typing flows on a disposable emulator and/or an explicitly selected test device. A signed release smoke test should cover launch, onboarding, offline input and settings. Never clear a personal device's data to resolve a signature mismatch.
6. Model, dictionary, retrieval or runtime changes require the corresponding separate qualification in `docs/acceptance/`. A UI-only release does not establish a new model qualification.

## Publish

Commit reviewed source and docs, push `main`, then create an annotated version tag on the verified commit. Copy the **signed** APK to an external staging directory as `rune-keyboard-<version>.apk` and compute SHA-256. Verify its signature with Android Build Tools `apksigner verify --verbose --print-certs`.

Create the GitHub release from that tag, attach the APK and checksum file, and describe new behavior, validation and limitations. Confirm the remote release assets match the local sizes/hashes. The signed APK is `app/build/outputs/apk/release/app-release.apk`; an unsigned/debug APK is not a replacement.

The upstream release and a development debug build use different signing keys. Android deliberately rejects an in-place replacement between them. Users must make an explicit choice about removing a previous debug installation and its local data.

## F-Droid

Update and submit the [build recipe and metadata](FDROID.md). Official inclusion requires maintainer acceptance and an independent build; creating a GitHub release does not automatically publish to F-Droid.

### Prepared source distributions

The Git checkpoint requires a real repository and rejects missing Git metadata,
uninitialized modules and dirty prepared trees. F-Droid source preparation removes
tracked wrappers and scandelete files. Existing historical recipes use source
commits from before this gate. A future recipe needs a verified lifecycle for
checking clean source before preparation and binding permitted preparation effects;
that integration has not been established. Do not infer source-export/F-Droid
build-server acceptance from a clean normal checkout build.
