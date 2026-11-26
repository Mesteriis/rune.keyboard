# Q1 local F-Droid build after source recovery

On clean source commit `611268b4715e404232913e66079b928ee8577eb5`, fdroidserver
2.4.5 `build_local` completed with an unsigned APK and source tarball. The source
scanner reported zero fatal findings and the existing two warnings for the
calibration gzip and upstream Keynote file. SDK acquisition was omitted; the
installed SDK/CMake and existing dependency cache were used with Gradle offline.
This source checkpoint includes the restored historical source inventory and
corrected residual feature driver, but predates later documentation and the
subsequent residual-score decoder fix.

The unsigned APK is 180,122,901 bytes, SHA-256
`da3ae5e0da8d4d2d2c897e5d08894493478fb9229c66685f2b222f084d6baf9d`.
A separate actual binary scan with the pinned local scanner signatures and
network blocked reported zero fatal findings, one successful dexdump invocation,
173 extracted classes and 471 error signatures. The source archive is
164,634,702 bytes, SHA-256
`3641ef81d8d09dee59ebf1ebd2c51281710535c84f4ab5d294aa8fff3283ff19`.
Its 6,928 members have one root, no absolute or traversal paths, and contain
only regular files or directories. Four relevant source entries, including the
lexical ledger and two replay drivers, matched this commit byte-for-byte.

Logs and artifacts remain under ignored
`build/q1-current-fdroid-after-recovery-20261029/`. This local offline build and
scan do not establish an independent F-Droid build-server run, signed release,
distribution acceptance or the result of later commits. No APK was installed.
