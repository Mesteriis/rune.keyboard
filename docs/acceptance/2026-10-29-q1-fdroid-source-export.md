# Q1: local F-Droid source export and final binary scan

On clean source commit `00936a6a58726037c8d924f9f90a211320941f7a`, fdroidserver 2.4.5 `build_local` completed with source tarball creation and final binary scanning enabled. The actual source scanner reported zero fatal findings and the same two warnings as the earlier receipt: the gzip calibration fixture and the upstream Keynote file. The SDK-acquisition prebuild was omitted; the installed SDK/CMake and existing dependency cache were reused, with Gradle offline.

The generated unsigned APK is 180,122,901 bytes with SHA-256 `183b9808136ca3897842e6cb935928b62548969de4d47167dd48e90261efdbc4`. A second explicit binary scan with network blocked and the same F-Droid version returned zero problems; `dexdump` succeeded once, 173 scanner class-name matches were found, and 471 error signatures were loaded. This number is not the complete class count.

The generated source tarball SHA-256 is `5777647d0ee4a6cb8f4688ee3ae932a76b954cc1ea0e3b83f41e7ae8d6fcfbbb`. A structural inspection found 6,692 members under one root: 5,946 regular files and 746 directories, with no symlinks or VCS metadata. The retained exclusion ledger is included. This verifies archive presence and basic structure, not a full independent reproducibility or distribution audit.

The earlier `1b3d8c33` local APK has a different whole-file hash. Comparing ZIP members found the same names and only `META-INF/version-control-info.textproto` changed in CRC/size; this comparison is not an independent build or proof of binary reproducibility. Both builds shared a host, caches and toolchain. Raw build and scan logs are under `build/review-hosted-editor/q1-full-fdroid-20261029.log` and `build/q1-fdroid-binary-scan-current-20261029.log`.

The build-server run, independently reproduced source export, signed-release checks and distribution acceptance remain open. The APK is a local test artifact and was not installed or published.
