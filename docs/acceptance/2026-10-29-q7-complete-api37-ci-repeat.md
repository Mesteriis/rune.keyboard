# Q7 complete local API 37 CI shell repeat

The CI workflow's Android script completed with exit code 0 on a fresh,
task-owned isolated API 37 ARM64 emulator launched with the workflow's
`-prop qemu.hw.mainkeys=0` software-navigation option. The local script was
extracted from the workflow and the matrix API substituted; this is not a
hosted CI run. The product and workflow under test were at `c73fb990`.

The boundary receipt reports general: 353 tests, 0 failures, 0 errors, 48
skips. Each separately routed suite passed with no skips: personal 4,
case-rejection 2, confirmed-words 3, export-navigation 1,
qualification-lifecycle 1, qualification-safety 1, and native-runtime 6.
The previously failing insets and flick methods completed without a failure in
this general run. The ordinary APK rebuild completed and all four synthetic
restart write/reload scopes passed. The failure-artifact collector exited
successfully and reported no captures, consistent with the successful run.

Ignored local receipt SHA-256 values:

- boundary suites: `c0416f3e011f77e02cdfd69ee77015f6c5b572d217e0846d1871383eef4add80`
- synthetic restart: `e0eb05f5760e9fc9a3635bd3e0c3009ea3b641897a0b5054474c50f4c132f59d`
- failure capture: `478b0b9e5fd51cd17b3ce6643d82a7fac0ab07d574adec20e5f7ec0f6721de31`

The preceding repeat without the required software-navigation setting failed
two tests and is retained separately; this result does not erase that failure.
This local API 37 run does not establish hosted CI, API 26, physical Fold or
manual accessibility acceptance. Q7 remains open for hosted CI evidence.
