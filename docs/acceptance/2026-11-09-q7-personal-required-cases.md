# Q7: required personal-admission instrumentation cases

The personal-admission Android CI scope previously required four executed
cases from the expected class, but did not require their method identities.
A report replacing one of the four admission scenarios with an unrelated
method could therefore satisfy that floor.

The report validator now requires all four current personal-admission methods
to pass. Additional methods in the same class remain allowed. The regression
test demonstrates that replacing or skipping each required method is refused;
before the change the replacement probes failed because they were accepted.
The complete suite-runner unit module passes 14 tests. An existing local API 26
JUnit report from the earlier run also passes the new identity check with four
executed cases and zero failures or skips.

No Android test was rerun for this change. The retained report is evidence for
its earlier run, not for the current source or API 37. The latest hosted CI
run remains the failed run at `2c1ff975`; current hosted execution is open.

At source `87a58e9c`, a fresh isolated ARM64 API 26 emulator with software
navigation ran the actual personal-admission class using the `q3-personal`
fixture. Gradle exited zero, and the current report validator accepted the
single fresh JUnit report: four tests, zero failures, errors or skips. The
temporary checkout, build outputs, emulator and isolated ADB server were
removed. This targeted run does not replace the interrupted complete Android
suite, API 37, a hosted x86_64 run or physical-device acceptance.
