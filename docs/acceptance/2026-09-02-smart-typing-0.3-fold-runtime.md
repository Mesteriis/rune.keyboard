# Smart Typing 0.3 — initial physical Fold runtime evidence

Date: 2026-09-02. Device: USB-connected Samsung SM-F966B, API36. This report covers only the dedicated runtime instrumentation package. User Rune installation and data were not replaced or cleared.

## Debug correctness checkpoint

The runtime source is unchanged from `585f380691baabb7bec25ae5bd25067880d54158`; integration checkout before the test was `84e47273b02e3b1726601f2e76b8023dda8a8218`.

- Test APK SHA-256: `0333b569278649452397ff421b987bfdb4eb014d3092833bc73dd109d4ef2a93`.
- ARM64 `librune_llama.so` SHA-256: `f0d25e382e192b768ea98c0ac48070ec8bc664233da3906e16007f9cb8220beb`.
- ARM64 `libc++_shared.so` SHA-256: `c4c2fe5cbcb1fba0003a31fc7ab29a9bb12df6cc187ec45a806462540e83d93b`.
- Exact model: 396704416 bytes; SHA-256 `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`, checked inside the instrumentation before loading.
- Ordinary no-model JNI contracts: **6/6 PASS**, 0.079 s.
- `VerifiedModelOnly`: **1/1 PASS**, 76.599 s total; nine successful scoring requests, 27 candidate scores, two pre-cancelled requests, one cancelled admission race, successful subsequent request and unload/reload.

Evidence: `build/smart-typing-0.3/fold-runtime-install.log`, `fold-runtime-contracts.log`, `fold-runtime-exact-model.log`. The exact model was placed only in the dedicated test package's private qualification file. No editor text was read or used.

## Performance and release limits

This APK uses Debug native compilation. Inspected compile commands for representative ggml/llama code have no optimization flag; the existing release `RelWithDebInfo` uses `-O2 -DNDEBUG`. The 76.599-second qualification includes digest verification, load and reload and is **not per-request latency**. It must not be used as a product latency or energy result.

Release-native pilot and full-profile results are recorded below. Acceptance requires actual test/app native identity matching and separate 2/4/8-candidate measurements. USB power and thermal context must accompany physical samples; CPU and memory observations alone do not measure battery energy.

| Gate | Status at this checkpoint |
| --- | --- |
| Physical runtime ordinary/verified-model correctness | PASS for the APK and digest above |
| Physical release-native performance | Baseline measured; product/battery acceptance OPEN |
| Cover/inner live IME editor/lifecycle/Undo/process-death matrix | UNRUN |
| Full physical Fold acceptance | OPEN |
| Model quality / immutable publication | Prior quality FAIL / publication not performed |

API26/API37 emulator evidence remains separate. No version bump or model publication follows from this checkpoint.

## Release-native pilot

The reviewed test APK was built with `runeRuntimeTestBuildType=release`; both ARM64 native entries match the actual app release APK. Merged test manifest metadata is release. Ordinary contracts passed 6/6 (0.030 s), and the unchanged qualification filter passed 1/1 (3.465 s). These totals remain correctness evidence.

The fixed pilot passed 27 measured requests plus nine warmups, three cancellation attempts and one recovery request. No model, scheduling, thread-count or workload parameter was changed after observing the result.

| Language | Candidates | Observed p50 ms | Observed p95/max ms | Process CPU p95 ms |
| --- | --- | --- | --- | --- |
| EN | 2 | 124.798 | 125.449 | 409 |
| EN | 4 | 239.113 | 263.953 | 908 |
| EN | 8 | 512.926 | 663.198 | 2299 |
| RU | 2 | 286.169 | 360.873 | 1257 |
| RU | 4 | 514.640 | 682.152 | 2389 |
| RU | 8 | 993.263 | 1565.291 | 5703 |
| ES | 2 | 179.233 | 270.194 | 938 |
| ES | 4 | 362.731 | 568.115 | 1988 |
| ES | 8 | 717.951 | 720.537 | 2530 |

Each cell has only three measurements; its p95 is its observed maximum, not an estimated population tail. All three cancellation attempts returned CANCELLED; maximum signal-to-return was 13.103 ms, followed by successful recovery. Total interval was 19.440 s wall / 61.893 s process CPU, including non-measured setup/control work. Multiple inference threads can accumulate more CPU time than elapsed wall time.

The phone was USB-powered, battery temperature 36.0 C and thermal status 1 before the pilot. The follow-up observation was delayed by 109.290 s after summary creation: 36.3 C, thermal status 1. It is not an immediate post-load thermal observation and cannot establish peak temperature or energy.

Evidence: `fold-release-native-proof.json`, `fold-release-pilot.csv`, `fold-release-pilot-summary.json`, and `fold-release-pilot-context-{before,after}.json` in `build/smart-typing-0.3/`. No user text is present.

Decision before further measurement: execute one unchanged fixed full profile (20 measurements per configuration), with immediate context capture in the same runner. The pilot shows material CPU/latency cost, so model scoring on every key is not an acceptable scheduling assumption. Product scheduling, quality and battery acceptance remain open.


## Fixed full release-native baseline

The unchanged full profile completed **180 measured requests**, nine warmups, three cancellations and one recovery. All result identities/counts/finite-score checks passed. Each cell has 20 observations; percentiles are descriptive nearest-rank statistics.

| Language | Candidates | p50 ms | p95 ms | max ms | Process CPU p95 ms |
| --- | --- | --- | --- | --- | --- |
| EN | 2 | 243.752 | 256.852 | 263.209 | 862 |
| EN | 4 | 460.864 | 468.050 | 509.248 | 1666 |
| EN | 8 | 981.304 | 1003.985 | 1007.281 | 3634 |
| RU | 2 | 508.106 | 599.097 | 666.487 | 2138 |
| RU | 4 | 944.807 | 1075.744 | 1088.725 | 3937 |
| RU | 8 | 2027.731 | 2062.163 | 2074.235 | 7656 |
| ES | 2 | 348.981 | 368.663 | 424.829 | 1272 |
| ES | 4 | 722.933 | 766.963 | 785.499 | 2702 |
| ES | 8 | 1401.246 | 1431.023 | 1545.204 | 5263 |

Total interval: **160.063 s wall / 546.950 s process CPU**. Maximum measured post-request PSS was 438.910 MiB (whole dedicated test process). Verified/warm-filesystem load was 360.049 ms; unload 100.849 ms; close 0.283 ms. Post-close PSS was about 58.236 MiB, which is a snapshot rather than secure erasure or leak evidence.

All three cancellation attempts returned CANCELLED; maximum signal-to-return was 19.258 ms, followed by successful recovery. These are admission races, not proof of a particular tokenizer/decode stage or an IME stale-result measurement.

Before/after: USB powered, battery 36.2 → 37.7 C, thermal status 1 → 2. The final context was captured 0.419 seconds after summary writing. Battery percentage rose while charging, so no energy inference is valid. Full-run scoring was materially slower than the pilot; thermal state is a relevant concurrent observation, not an isolated causal experiment. Ambient conditions and Fold posture were not controlled for this runtime-only test.

Decision: correctness and bounded cancellation PASS for this test APK/model. Frequent background scoring remains **unqualified**: the sustained four-thread cost is incompatible with assuming one inference per keystroke. Product request frequency, CPU duty budget, deterministic admission filters and model/runtime efficiency must be addressed before battery acceptance. No numerical energy budget is claimed. No more repetitions of this unchanged baseline are needed now.

The compact raw CSVs, summaries, native proof, numeric power/thermal context and SHA manifest are archived in `tools/test-native-scoring/runtime-benchmark/results/2026-09-02-fold/`. Runtime source remains unchanged; only the optional benchmark/build-selection/tooling was added. Physical cover/inner typing, editor behavior, lifecycle/frame/stale events and battery qualification remain open.
