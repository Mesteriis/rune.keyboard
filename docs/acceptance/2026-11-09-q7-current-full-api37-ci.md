# Q7: current complete local API 37 Android CI shell

At clean source `8af345ea`, the Android emulator script extracted from the
current CI workflow completed with exit code 0 on a disposable isolated ARM64
API 37 (16 KiB) emulator. The emulator used 4 GiB RAM, software navigation,
software GPU and zero animation scales. Gradle's worker limit was set to two;
the workflow commands and suite routing were otherwise retained. This is a
local ARM64 execution, not a hosted x86_64 GitHub Actions result or a Fold
test.

The general suite's fresh JUnit report contains 366 cases, 48 skipped and no
failures or errors: 318 executed. Its Gradle task took 43 minutes 14 seconds.
The report gate accepted all required identities, including all nine
editing-panel scenarios. The earlier three panel failures did not recur. The
other eight separately routed scopes all passed with fresh reports and zero
skips: personal 4, case rejection 2, confirmed words 3, Compose editor 3,
export navigation 1, qualification lifecycle 1, qualification safety 1 and
native runtime 6. API 26's document-picker-only scope is not scheduled here.

Four synthetic write/reload restart phases passed; independent editor-process
death and recovery passed for left and right context; five voice-fixture
scopes passed. All four receipts and the full shell returned success. The 48
general-suite skips remain skips, including model-dependent tests; none is
claimed as executed. The preceding starting-window failure's cause is still
unresolved, and one successful repeat does not establish that it cannot
recur. Hosted CI, API 26 at this source and physical Fold acceptance remain
open.

The isolated ADB server, temporary checkout, emulator, APKs and build outputs
were removed after inspection. The original failed-run logs remain available
for the separate starting-window investigation.
