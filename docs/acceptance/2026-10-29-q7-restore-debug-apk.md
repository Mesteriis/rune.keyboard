# Q7 restore ordinary debug APK before synthetic restart

The exact API 37 CI shell run on a task-owned isolated emulator completed the
boundary runner successfully: general XML recorded 353 tests, zero failures or
errors and 48 skipped; the seven additional suites all passed their fresh-result
checks. The complete shell run nevertheless exited 1 in synthetic restart
setup. No synthetic failure screenshots were captured because the failure was in
host setup before instrumentation.

The qualification suites build the `.qualification` application ID into the
same debug APK output paths. After those suites, the restart runner installed
the APK at that path and could not enable the ordinary package's IME. Read-only
inspection of the emulator confirmed the ordinary package was absent and the
qualification IME present. The initial failing helper reduced the ADB error to
`RESTART_ADB_FAILURE`, without retaining stderr.

The workflow now rebuilds both ordinary debug APKs before the restart runner.
It retains an earlier boundary failure, reports a rebuild failure, skips the
restart on rebuild failure, and still executes the EXIT artifact collector.
The shell regression test exercises successful and failed rebuilds, boundary,
restart and collector exit precedence and ordering.

After the failed complete run, the ordinary APK rebuild exited 0 and a fresh
restart invocation on the same isolated emulator passed all four write/reload
scopes with no skips (case rejection and confirmed words). This validates the
repair in separate actual stages, not a fresh end-to-end run or hosted CI.
Physical Fold was not accessed. Q7 remains open pending the complete current
workflow and hosted results.
