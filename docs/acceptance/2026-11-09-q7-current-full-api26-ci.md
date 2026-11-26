# Q7: current complete local API 26 Android CI shell

At clean source `7ad41aea`, the Android emulator script extracted from the
current CI workflow completed with exit code 0 on a disposable isolated ARM64
API 26 emulator. The emulator used 2 GiB RAM (2,054,364 KiB reported by the
kernel), software navigation, software GPU and zero animation scales. Gradle's
worker limit was set to two; the workflow commands and suite routing were
otherwise retained. This is a local ARM64 execution, not a hosted x86_64
GitHub Actions result or a Fold test.

The general suite's fresh JUnit report contains 366 cases, 48 skipped and no
failures or errors: 318 executed. The report gate accepted all required
identities, including all nine editing-panel scenarios. The other nine
separately routed scopes passed with fresh reports and zero skips: personal 4,
case rejection 2, confirmed words 3, Compose editor 3, export navigation 1,
real document picker 1, qualification lifecycle 1, qualification safety 1 and
native runtime 6.

Four synthetic write/reload restart phases passed; independent editor-process
death and recovery passed for left and right context; five voice-fixture
scopes passed, including the API 26 next-keyboard picker. All four receipts
and the full shell returned success. The 48 general-suite skips remain skips,
including model-dependent tests; none is claimed as executed. This result and
the API 37 repeat do not establish hosted CI, physical Fold acceptance or the
cause of the earlier API 37 starting-window failure.

The isolated ADB server, temporary checkout, emulator, APKs and build outputs
were removed after inspection. The unrelated connected physical device was not
used. Original failed-run logs remain available for the separate investigation.
