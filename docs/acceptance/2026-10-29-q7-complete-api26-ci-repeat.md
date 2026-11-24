# Q7 complete local API 26 CI shell repeat

The current CI shell ran to completion on a fresh isolated API 26 ARM64 AVD
with `qemu.hw.mainkeys=0`. Its exit code was 1, preserving the general-suite
failure. The general XML reports 352 tests, one failure, zero errors and 48
skips. The failure is the editor accessibility/system-menu observation and
separate passing reproductions documented in
[q7-api26-editor-overlay](2026-10-29-q7-api26-editor-overlay.md); passing isolated
runs do not repair or erase the full-suite failure.

All eight routed suites passed with fresh results and no skips: personal (4),
case rejection (2), confirmed words (3), export navigation (1), API 26 export
picker (1), qualification lifecycle (1), qualification safety (1), and native
runtime (6). After the ordinary debug APK rebuild, all four synthetic restart
write/reload phases passed. The failure collector reported captures present.
The runner marks the failed general scope `freshResultVerified=false`; its
retained XML and failure are recorded here, not claimed as a successful gate.

The boundary receipt SHA-256 is
`591a0a4ae98ef0c24e450fcd8c462432f467036476ba9f2ef5dda71c9d1b51f7`,
the restart receipt is
`e0eb05f5760e9fc9a3635bd3e0c3009ea3b641897a0b5054474c50f4c132f59d`,
and the capture receipt is
`c5c8612c7497de643110825237f59abe715c41d3ff7034617a9bbcbcd744e46d`.
Raw outputs were copied to ignored `build/q7-ci-api26-failed-20261029/`; the
specific AVD and isolated ADB server were removed after collection. No physical
phone was used. The general Gradle task took 46m50s locally; hosted CI uses a
different x86_64 environment and its result and job time remain unverified.
Q7 remains open.
