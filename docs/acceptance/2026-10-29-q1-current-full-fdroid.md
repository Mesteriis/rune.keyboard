# Q1 current local F-Droid source and binary check

On clean source commit `a5059ca3176dff16fb1d00c7a8525976040e33cc`, the actual
fdroidserver 2.4.5 `build_local` completed with source-tarball creation and final
binary scanning enabled. The source scanner returned zero fatal findings and
retained the two previously disclosed warnings for the calibration gzip and
upstream Keynote file. The SDK acquisition prebuild was omitted; installed
SDK/CMake and the existing dependency cache were reused with Gradle offline.
The pinned source-scan signature cache was used with network blocked.

The unsigned local APK is 180,122,901 bytes and SHA-256
`d0d84f26fa113c6c05287318cfb505826278b8e50715aabc4c00044c8af85b6f`.
The source archive SHA-256 is
`d7815296245931b4153598af1bef2602137881e6af28482419c3c21761edd002`.
A structural inspection found 6,852 members under one root, all regular files
or directories, with no absolute or traversal paths. Logs and artifacts remain
under `build/q1-current-fdroid-full-20261029/`.

This is a local check on the stated commit, not a new versioned recipe, a signed
release, a build-server result or distribution acceptance. The later subtitle
screening commit and later documentation are not in this source snapshot. No
APK was installed or published by this build. Independent build-server and
release acceptance remain open.

At source commit `f6a6c3b7`, a fresh local fdroidserver 2.4.5 `build_local`
completed with source-tarball creation and binary scanning enabled. The source
scanner returned zero fatal findings and the same two warnings; the binary
scanner returned zero findings with 471 error signatures. Scanner network
access was blocked, Gradle ran offline, and the installed pinned SDK/CMake was
reused; the SDK-acquisition prebuild was omitted. The unsigned APK was
180,122,901 bytes, SHA-256
`e9f98a999392cdb13faa85b0c1de178bb209659f7968091ec9b298dcff452f0a`.

The source archive SHA-256 was
`bca578ec5bdd498f143d36dd8ae4fa20ac1077deef8abc2391b7f7ad615ab776`.
It contained 7,096 members under one root, all regular files or directories,
with no absolute/traversal paths; the exclusion ledger was present. The
temporary checkout, package environment, copied cache, archive and APK were
removed. This was not an independent build-server run, signed release,
distribution acceptance or device test.
