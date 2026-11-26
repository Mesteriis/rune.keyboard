# Q7 API 26 complete local CI repeat after popup handling

The complete extracted CI shell finished with exit code 0 on a fresh isolated
API 26 ARM64 emulator, configured with software navigation. The general suite
reported 352 tests, zero failures/errors and 48 skips. The prior editor-boundary
failure did not recur. The earlier failure and direct reproduction of popup
recovery remain recorded in `2026-10-29-q7-complete-api26-ci-repeat.md` and
`2026-11-03-q7-api26-spelling-popup.md`.

All eight separately routed suites passed with fresh results and no skips:
personal (4), case rejection (2), confirmed words (3), export navigation (1),
API 26 export picker (1), qualification lifecycle (1), qualification safety (1)
and native runtime (6). All four synthetic restart write/reload phases passed.
The failure collector found no captured failures. The general Gradle task took
47m14s on this host; this is not a hosted x86_64 timing measurement.

The boundary receipt SHA-256 is
`b2c2f2523a9903c481e9574af288633c01b535d5f5c3568cc82a7f786fa9e8f6`,
the restart receipt is
`e0eb05f5760e9fc9a3635bd3e0c3009ea3b641897a0b5054474c50f4c132f59d`,
and the capture receipt is
`478b0b9e5fd51cd17b3ce6643d82a7fac0ab07d574adec20e5f7ec0f6721de31`.
The sources used by the app, CI tools and workflow were unchanged between
`bebdc2a9` and the checkout at completion. Raw reports are retained in ignored
`build/q7-ci-api26-fixed-complete-20261103/`. The dedicated AVD and isolated
ADB server were removed after collection; no phone was used. The local result
is not a hosted CI run and does not close Q7's hosted evidence requirements.
