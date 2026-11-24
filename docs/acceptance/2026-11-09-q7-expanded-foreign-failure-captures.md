# Q7: capture failing expanded-candidate and foreign-edit fixtures

Two classes that failed in the interrupted API 37 general run owned their
driver directly and did not use the existing failure-artifact rule. They now
use that rule, which captures before driver teardown and then restores the
driver state. The foreign-edit class retains its separate clipboard cleanup.
For these emulator-only classes capture is explicitly denied when the device
hardware is not `ranchu` or `goldfish`; the existing opt-out argument remains
effective. Product code and correction behavior are unchanged.

In a temporary copy of `e2fc8dcc` with the three-file test patch, an isolated
ARM64 API 37 emulator ran the actual two classes: five tests, zero failures or
skips. A separate, deliberately failing test APK in that temporary copy
injected one assertion failure into each class. Both failures were observed,
and each produced a valid PNG and XML containing the composing editor before
teardown. A further temporary mutation forced the capture predicate to false;
the deliberate failure still occurred and no remote capture directory was
created. The intentional failing Gradle invocations exited nonzero as expected;
they are negative controls, not passing product tests.

The copy, test APKs, emulator, screenshots and hierarchy files were removed.
This verifies the failure-capture path and its denied predicate, not the cause
of the earlier sequential failures, a full Android suite, physical Fold or
hosted CI acceptance.
