# Q1: prepared-source checkpoint with the four host archives

At source `069e1c41444590187a4fa03ca8f9d078307a58bf`, a fresh local
checkout passed the complete current F-Droid checkpoint: one exact signing
replacement and ten exact deletions, including all four host CI archives.
The ordinary clean-source mode still refuses this prepared tree.

The installed fdroidserver 2.4.5 executed `common.prepare_source` with the clean
source/data guards in `init`, followed by `scanner.scan_source` using the exact
29-entry review overlay. The `build_local` launcher-removal condition was
reproduced separately; `build_local` itself and a full assembly were not run.
SDK acquisition prebuild was omitted because the installed SDK was reused.
Scanner networking was blocked and the existing signature cache reused.
There were zero fatal findings and the two previously documented warnings:
the retained calibration test gzip and upstream llama.cpp Keynote file.

Seven direct probes passed their expected results:

- Complete preparation passes with 11 approved changes; default mode refuses it.
- Runtime qualification metadata verifies in explicit prepared mode.
- Restoring one deleted host archive fails with `EXPECTED_DELETE`.
- An unrelated source edit and a C++ edit each fail with `SOURCE_DELTA`.
- Restoring the controlled edits returns the checkpoint to PASS.

Three actual `:app:releaseSourceCheck` Gradle invocations returned 0, 1, 0.
Both the refusal after an unrelated edit and the restored positive run reused
the configuration cache. The check therefore still reads live Git state on
this current prepared tree. The 25 F-Droid policy tests and five qualification
tests also pass. Original owner payload hashes (13) and paths (98) are preserved.

The [machine receipt](2026-10-28-q1-prepared-archives-evidence.json) binds source,
policies, pinned preparer modules, raw logs and the private reproduction scripts.
Historical release recipes were not changed. This evidence does not establish
a new APK, independent build-server success, source export, binary scan or
distribution acceptance. Q1 remains open for those requirements.
