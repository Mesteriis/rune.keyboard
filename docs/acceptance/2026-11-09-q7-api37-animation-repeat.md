# Q7: API 37 boundary repeat with CI animation settings

At clean source `721e31b3`, an isolated ARM64 API 37 (16 KiB) emulator ran
the boundary suites with the CI software-navigation and GPU options, 4 GiB
RAM, and all three global animation scales explicitly set and read back as
zero. A visible navigation inset and the isolated ADB device identity were
checked. Debug assembly, test assembly and installation succeeded.

The boundary runner exited zero and accepted a fresh JUnit report for each
scope. The general report has 354 cases, 48 skipped, zero failures or errors:
306 executed. Seven separate scopes ran 18 tests without skips or failures:
personal (4), case rejection (2), confirmed words (3), export navigation (1),
qualification lifecycle (1), qualification safety (1) and native runtime (6).
The API 26-only picker was not scheduled. After ordinary debug APK restoration,
all four synthetic case-rejection and confirmed-word write/reload restart
phases passed. The temporary checkout, outputs, emulator and isolated ADB
server were removed; only the aggregate counts above were retained.

An earlier run with animations not explicitly disabled was interrupted after
11 failures; all were subsequently repeated successfully after reinstalling
the same APKs, as recorded in the previous receipt. The present clean run had
no reported failures, but a new emulator and elapsed time also differ: this
comparison does not establish animations as the cause. Per-case JUnit results
from this run were not retained, so the aggregate report does not independently
prove the status of any specific case beyond the runner's required-case gate.
It does not establish a hosted x86_64 run, complete workflow shell, physical
Fold acceptance, or the outcomes of the 48 skipped general cases.
