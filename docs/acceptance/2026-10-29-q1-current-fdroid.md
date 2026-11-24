# Q1 current F-Droid source and local build

On 2026-10-29, clean source commit `1b3d8c332d388c5434d786a5ef2a532ec75cb009` was checked with fdroidserver 2.4.5. The source preparation and source scanner completed with **zero fatal findings**. The reviewed data policy contained 31 entries and allowed 11 exact prepared-source changes. Seven positive and negative preparation/policy probes produced the expected exit codes and markers. The scanner ran without network access.

Two source-scan warnings remain: the gzip test calibration fixture `app/src/test/resources/smarttyping/ranker/calibration.tsv.gz` and `runtime-llama/src/main/cpp/llama.cpp/docs/development/llama-star/idea-arch.key`, flagged as a possible executable binary. Neither was a fatal finding; this result does not establish their independent review or a clean final binary scan.

The real `fdroidserver.build.build_local` completed successfully on a separate fresh checkout. A normal `:app:assembleRelease` from the same commit in another clean checkout also succeeded. The resulting unsigned APKs compare byte for byte: 180,122,901 bytes, SHA-256 `5ed8115a4d985029704e0580824054587a0906f59b392bc58d0318187a958f7c`. Both builds used the same host and existing toolchain/dependency cache, with Gradle offline. This is local consistency, not independent reproducible-build evidence.

Two earlier local F-Droid attempts stopped before building because the policy check was pointed first at the main working tree containing ignored build datasets, then at a previously scanned checkout with removed files. The successful run used a fresh clean policy checkout. SDK acquisition was omitted and the installed SDK/CMake reused. No source tarball, final APK binary scan, independent build server, publication, or physical-device test was performed. The next versioned recipe and whole-release/distribution acceptance remain open.

The [structured evidence](2026-10-29-q1-current-fdroid-evidence.json) records probe outcomes and source/tool hashes. This receipt describes the tested commit, not later changes.
