# A2: Android score parity for successive bounded prefixes

An exact-model Android instrumentation test sends three disclosed synthetic
prefixes matching the existing host cache probe and `ModelPrefixWindow` unit
expectations: initial overflow, one-word extension with a stable cut, and a
later shifted cut. One warm `LlamaLocalModelRuntime` processes all three;
for each request a newly loaded runtime supplies the cold comparison. The two
candidate IDs, token counts and finite score sums are compared within the host
probe's tolerance of 0.002 per scored token. The test verifies the exact model
size and SHA-256 before use and emits numeric metrics only.

On isolated ARM64 emulators API 26 and API 37 (16 KiB pages), the targeted test
passed on both: three requests, six candidate comparisons and maximum score
delta **0.0** on each. The current test APK SHA-256 is
`1bec6d07b2adebd816abebeea8ecba0a81d87ca2a736c35f2cd864a92c30497e`;
the unchanged model SHA-256 is
`7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
Raw numeric logs are in ignored `build/a2-android-runtime-20261103/`; task-owned
emulators and their isolated ADB server were stopped and deleted. No phone was
used. Rebuilding after a comment-only source correction produced the identical
test APK.

The public runtime exposes no cache-hit counter. These results prove numerical
warm/cold agreement for the chosen requests on those emulators, not actual KV
reuse, full controller integration, independent long-context quality, release
performance or Fold latency. The feature remains off. The older host-native
probe separately observed retained-token counts, but is not Android evidence.

All six synthetic English prefix/candidate contexts used by these probes are
registered in the control ledger. The source-bound verifier checks both host
and Android inputs and does not turn them into a fresh holdout. This adds no
single-word family exclusion. The `VerifiedModelOnly` opt-in now selects two
exact-model tests; the ordinary no-model CI selection remains excluded from
both. A2 remains open for its independent quality, actual Android cache reuse
and physical-device acceptance requirements.

Additional validation: eight `ModelPrefixWindowTest` JVM cases and 25 corpus
preparation tests passed; both registration tests and `--check` passed from a
staged source archive without `build/`. The isolated historical text and
279,056-segment checks also passed with the new control entry. These local
checks do not represent a hosted CI run.
