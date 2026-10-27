# F-Droid

The repository records [packaging request #4406](https://gitlab.com/fdroid/rfp/-/work_items/4406). Official inclusion and build-server acceptance have not been established by these local checks. F-Droid maintainers review submissions and build accepted applications independently.

## Packaging

- Application ID: `io.github.mesteriis.rune.keyboard`
- Original code license: MIT; separately licensed assets are listed in [third-party notices](../THIRD_PARTY_NOTICES.md).
- Proposed recipe: [fdroid/io.github.mesteriis.rune.keyboard.yml](../fdroid/io.github.mesteriis.rune.keyboard.yml)
- Localized store metadata: [fastlane/metadata/android](../fastlane/metadata/android)
- Historical source tag: `v0.4.2`, version code `8`, original preparation commit `d332c0e`. The tag was restored locally during review; it has not been pushed by this work. Both historical recipes now use full immutable commit hashes.
- Current review changes remain unreleased. The historical 0.4.2 recipe retains the three exceptions applicable to its original source, without reassigning that version to current HEAD.
- Build: Gradle release, `app` subdirectory, recursive submodules; JDK 17, SDK 37, NDK 29.0.14206865 and CMake 3.31.6.

No signing secrets are required to compile the source. Without the ignored local `keystore.properties`, Gradle produces an unsigned release APK. F-Droid can sign its independently built APK. That signing identity is different from the upstream GitHub release unless reproducible upstream signing is separately configured and verified. Byte-for-byte reproducibility has not yet been established.

## Asset review

The native runtime is built from the pinned llama.cpp source submodule, not shipped as a prebuilt library. The Gradle wrapper is checked in. The dependency repositories are Google Maven, Maven Central and the Gradle plugin portal.

Packed dictionaries, morphology, frequency data and small experimental weights are committed data assets. Their formats, licenses, source revisions, transformations and hashes are documented in [packaged lexicon provenance](../app/src/main/assets/smarttyping/lexicon/provenance/PACKAGED_LEXICONS.md), [morphology](../tools/morphology/README.md) and [typing experiments](../tools/typing_experiments/README.md). They are not executable downloads. The historical 0.4.1/0.4.2 recipes have exact scanner exceptions for their three numeric model data files, with their declared provenance retained. Later review assets are inventoried in the separate review-data policy below; a new versioned release recipe still needs to be prepared. The unused training baseline is removed from the F-Droid build tree. There is no blanket binary scanner exclusion.

The optional large Rune Text model is not bundled. Its download is explicit, pinned to a full source revision and checked by size/SHA-256. Typing works without it. Its source and notices are linked from [Rune Text documentation](../tools/model/rune-text-0.1/README.md).

## Current review data overlay

[review-data-policy.json](../fdroid/review-data-policy.json) binds 24 exact data
files and their declared provenance JSON bytes. Its three actions are:

- Nineteen literal scanignore paths: ten shipped numeric .bin files, eight numeric
  test .bin fixtures and the verified Unicode/CLDR source-data ZIP.
- Four inventory-only .ctx/.gram indexes. fdroidserver 2.4.5 does not flag them;
  adding unused scanignore entries would itself fail its source scan.
- One exact scandelete path for the existing unused training baseline.

Run before F-Droid source preparation, on the original checkout:

```sh
python3 tools/fdroid_data_policy.py
python3 -m unittest discover -s tools -p test_fdroid_data_policy.py -v
```

CI runs this standard-library data check. It refuses changed bytes/provenance
bindings, extra or missing indexed data, symlinks and scanner filename-prefix
collisions. Upstream 2.4.5 resolves literal exceptions then uses prefix matching;
a sibling such as ru-ranker.bin.injected.so can inherit a native suppression.
The additional check rejects that case. It is a data-policy check, not a source
scanner or proof of training authorship. Q6 provenance questions remain open.

Apply the emitted scanignore/scandelete lists to a future build entry with its
own release version/source pin, preserving existing historical entries. The
review overlay was tested against immutable snapshot 4278bca and its pinned
submodule: zero fatal findings and the same two documented warnings. An unrelated
prebuilt native library fails both checks; a prefix-lookalike library fails the
additional guard even when the native scanner returns zero. All scans used
private disposable source copies and pinned package SUSS defaults with network
blocked. See the [data-overlay receipt](acceptance/2026-10-27-q1-fdroid-data.md).
No new distribution recipe, isolated build-server success or public release is
established by this overlay.

## Prepared-source release checkpoint

Normal release builds still require a clean committed Git checkout. F-Droid
2.4.5 prepares a different, precisely defined source state: its signing scrub
changes `app/build.gradle.kts`, build cleanup removes wrapper launchers, and its
scanner removes wrapper JARs and the declared training baseline. The committed
[prepared-source policy](../fdroid/prepared-source-policy.json) binds the original
and resulting bytes of the signing scrub and the original bytes of six deletions.

A future versioned recipe must run both guards in `init`, before preparation,
and explicitly select the prepared-source mode for Gradle:

```yaml
init:
  - cd .. && python3 tools/release_source_check.py && python3 tools/fdroid_data_policy.py
gradleprops:
  - runePreparedSource=fdroidserver-2.4.5
```

Use the current review data overlay with that entry; retain historical recipes.
After source scanning, the equivalent standalone checkpoint is:

```sh
python3 tools/release_source_check.py --prepared-source fdroidserver-2.4.5
```

This mode requires the complete exact delta, not merely a subset of permitted
paths. It checks policy bytes against HEAD, original file hashes against Git
objects, replacement bytes/mode, absent deletion targets, matching recursive
submodule commits and exact unstaged NUL-delimited status in every checkout.
Additional edits, staged changes, untracked files, symlinks and hidden index
flags are refused. It does not stash, restore wrappers, edit Git metadata or
accept an arbitrary dirty checkout. The property selects a reviewed source
transformation; it is not proof that a particular service performed it.

The qualification verifier also requires this global checkpoint before accepting
the two example-wrapper deletions inside llama.cpp. Its separate fixed runtime
check refuses every other submodule delta, even if a future committed preparation
policy describes it. Compiled C/C++ changes still cannot retain the old runtime
build identity. Ordinary qualification verification keeps its clean-submodule
requirement.

The [prepared-source receipt](acceptance/2026-10-27-q1-prepared-source.md) records
27 guard/bridge tests and real local `fdroidserver.build.build_local` execution.
The source scan has zero fatal findings and the two known warnings; qualification
metadata and the prepared checkpoint pass. Full assembly still fails the native
`PrepareLlamaSource.cmake` pristine check on the two removed example wrappers.
That file is part of the runtime fingerprint. Its integration needs renewed
runtime identity/qualification; this mode is not yet a passing distribution recipe.

Refresh the fixed hashes deliberately when the app build script or any listed
original changes. Use the actual pinned fdroidserver signing transformation to
obtain the replacement hash, then repeat preparation/scanning/build validation
in a disposable checkout. Missing Git metadata fails closed; exported source
tarballs without Git are not accepted by this mode. Historical commits without
this checkpoint retain their original build behavior.

## Submission and validation

The 2026-10-27 check with `fdroidserver 2.4.5` passes metadata lint using a captured official category catalogue and its eleven icons. A disposable scan of historical commit `d332c0e` plus its pinned submodule returns zero fatal findings; two warnings remain for a compressed test fixture and a Keynote document in llama.cpp documentation. The unmodified package SUSS defaults were used with network blocked during scanning. A separate scan of review commit `0f24f2e` with the historical exceptions returns eight fatal findings and ten warnings; this is not current-source acceptance. See the [historical source/tag receipt](acceptance/2026-10-27-q1-fdroid-history.md). An isolated F-Droid build-server build has not been run locally.

Copy the proposed YAML into an `fdroiddata` checkout's `metadata/` directory. Run `fdroid rewritemeta`, `fdroid lint`, source scanning and the isolated build using the official build-server environment. A successful local Android Gradle build alone does not prove that the F-Droid build-server recipe passes.

Follow the [official submission guide](https://f-droid.org/docs/Submitting_to_F-Droid_Quick_Start_Guide/) and [inclusion policy](https://f-droid.org/docs/Inclusion_Policy/). The GitHub release is the available distribution while the official submission is reviewed.

Existing build entries use full commit hashes as described in the [official metadata reference](https://f-droid.org/docs/Build_Metadata_Reference/#buildscommit). Local source-scanner exceptions do not establish corpus authorship or resolve the separate Q6 provenance audit.
