# F-Droid

Rune is being prepared for inclusion in the official F-Droid repository. The presence of metadata in this repository does not mean that an official listing is already available. F-Droid maintainers review submissions and build accepted applications independently.

## Packaging

- Application ID: `io.github.mesteriis.rune.keyboard`
- Original code license: MIT; separately licensed assets are listed in [third-party notices](../THIRD_PARTY_NOTICES.md).
- Proposed recipe: [fdroid/io.github.mesteriis.rune.keyboard.yml](../fdroid/io.github.mesteriis.rune.keyboard.yml)
- Localized store metadata: [fastlane/metadata/android](../fastlane/metadata/android)
- Source tag: `v0.4.0`, version code `6`.
- Build: Gradle release, `app` subdirectory, recursive submodules; JDK 17, SDK 37, NDK 29.0.14206865 and CMake 3.31.6.

No signing secrets are required to compile the source. Without the ignored local `keystore.properties`, Gradle produces an unsigned release APK. F-Droid can sign its independently built APK. That signing identity is different from the upstream GitHub release unless reproducible upstream signing is separately configured and verified. Byte-for-byte reproducibility has not yet been established.

## Asset review

The native runtime is built from the pinned llama.cpp source submodule, not shipped as a prebuilt library. The Gradle wrapper is checked in. The dependency repositories are Google Maven, Maven Central and the Gradle plugin portal.

Packed dictionaries, morphology, frequency data and small experimental weights are committed data assets. Their formats, licenses, source revisions, transformations and hashes are documented in [packaged lexicon provenance](../app/src/main/assets/smarttyping/lexicon/provenance/PACKAGED_LEXICONS.md), [morphology](../tools/morphology/README.md) and [typing experiments](../tools/typing_experiments/README.md). They are not executable downloads. Maintainers should review these inputs rather than applying a blanket binary scanner exclusion.

The optional large Rune Text model is not bundled. Its download is explicit, pinned to a full source revision and checked by size/SHA-256. Typing works without it. Its source and notices are linked from [Rune Text documentation](../tools/model/rune-text-0.1/README.md).

## Submission and validation

Copy the proposed YAML into an `fdroiddata` checkout's `metadata/` directory. Run `fdroid rewritemeta`, `fdroid lint`, source scanning and the isolated build using the official build-server environment. A successful local Android Gradle build alone does not prove that the F-Droid build-server recipe passes.

Follow the [official submission guide](https://f-droid.org/docs/Submitting_to_F-Droid_Quick_Start_Guide/) and [inclusion policy](https://f-droid.org/docs/Inclusion_Policy/). The GitHub release is the available distribution while the official submission is reviewed.
