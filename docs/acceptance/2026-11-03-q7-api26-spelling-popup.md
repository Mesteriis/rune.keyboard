# Q7 API 26 spelling-popup recovery in the test driver

On a fresh isolated API 26 ARM64 AVD, the original debug test APK reproduced
the full-suite editor failure on the fifth isolated run: the same test failed
at the same `resumeQa`/`awaitQaActivity` stack. The saved screenshot and
accessibility hierarchy again show Android's spelling-suggestion popup over the
seeded `leftright` field. Four previous isolated runs passed. The failed raw
instrumentation log has SHA-256
`6e3e4faa1cb20d823957af65ae6d2fef48405de58b434a691240e5d1f7aaf676`.

The test driver now checks for the exact Android `suggestionContainer` only
when waiting for the keyboard fails. If found, it presses Back, requires that
popup to disappear, and requires the keyboard to become accessible before
returning; the original test still checks editor identity, keyboard state and
final text. Other failures still follow the existing rebind path. This changes
Android instrumentation support only, not production keyboard behavior.

The debug app and test APKs built successfully. All 29 subsequent isolated runs
of the affected test passed. In the last run, emulator logcat confirms the
identified suggestion window was dismissed, then the same test completed with
zero failures. That test log SHA-256 is
`9b6793e7e5c719cdcefcbda4c516f46025f524ebe8cd258e178034b93e439ac0`;
the captured logcat SHA-256 is
`251d80ef164c41e21c4b4d90416210ba1c91f9b9eb54ee78c999805716e393a1`.
The seven-test adjacent editor-action and boundary sequence also passed, no
skips; its log SHA-256 is
`424776f957773c1fad496d03692c067926b4d308c2293449a3c491d5387049b0`.
The raw logs and images are retained under ignored `build/q7-overlay-*` paths.

The popup is intermittently supplied by Android spell checking; there is no
fully deterministic standalone popup fixture in this change. The earlier full
API 26 CI shell remains a failure, and neither a new complete shell run nor
hosted CI is claimed. Q7 remains open.
