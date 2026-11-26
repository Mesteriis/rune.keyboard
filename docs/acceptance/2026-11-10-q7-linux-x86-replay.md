# Q7: current full product replay on Linux x86_64 under emulation

At source `959d61e247e77954bd43afae929535b364c96238`, the actual
`tools/ci/product_replay_ci.py` command ran in a disposable Ubuntu 24.04
linux/amd64 container emulated on a macOS ARM64 host. The container was limited
to two CPUs and 4 GiB; networking was disabled during replay. OpenJDK
17.0.21.0.3, five SHA-256-verified Kotlin JARs and the Android 37 compile stub
were supplied in the disposable environment. The base Ubuntu image digest and
all source, asset and toolchain bindings are recorded in the
[compact evidence](2026-11-10-q7-linux-x86-replay-evidence.json). The image's
package installation and decoder/toolchain distribution were not independently
attested.

Both required profiles passed with exit 0:

| Profile | Rows | Two passes identical | Behavioral baseline differences | Tolerated diagnostic score values |
| --- | ---: | --- | ---: | ---: |
| Current multilingual | 2,160 | yes | 0 | 462 |
| Historical multilingual | 12,000 | yes | 0 | 2,296 |

The score differences are within the pre-existing absolute tolerance and only
on allowed numeric diagnostic score fields. Product decisions, editor text,
commands, candidates and Undo remain exact. The two passes are compared exactly,
including scores. Actual projection hashes and original receipt hashes are in
the evidence. The current and historical runs took 76.27 and 163.68 seconds in
this CPU-limited emulation, including compiler times of 45.62 and 46.29 seconds;
these are local observations, not a hosted runner duration estimate.

The current replay's serialized `fullTokenGeneration` and
`actualRequestGeneration` fields were also counted for sub-cap
`STATES_EXHAUSTED` neighbor-recovery signatures in each pass: none were found.
This does not prove the source of the earlier intermittent Linux mismatch or
exclude deadline failures under other scheduling conditions. This is not a
hosted GitHub Actions run, Android instrumentation, device qualification or
independent model quality evidence. Those requirements remain open. The
container, task-owned image, copied toolchains, checkout and raw observations
were removed after extracting the bounded evidence; owner diagnostic backups
were not touched.
