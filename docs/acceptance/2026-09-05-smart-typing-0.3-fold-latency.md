# Smart Typing 0.3 Fold latency investigation — 2026-09-05

## Build-mode correction, 2026-09-05

The September 5 device measurements below used **unoptimized Debug native code**.
The inspected ggml C kernels, llama C++ and JNI compile commands had no `-O` flag;
release uses `-O2 -g -DNDEBUG`. The earlier conclusion that these timings prove
the model itself unsuitable was incorrect. They establish a failure of the tested
build. They do not establish the latency or CPU cost of the current optimized runtime.

There is already a separately verified September 2 release-native baseline:
four-candidate full-profile p95 was EN 468.050 ms, RU 1075.744 ms and ES 766.963 ms
(20 observations per configuration). The exact test/app native byte proof and raw
records are archived in `tools/test-native-scoring/runtime-benchmark/results/2026-09-02-fold/`.
Those fixtures and runtime revisions differ, so they cannot be used to calculate
a speedup for the September 5 changes. They still require reduced request cost
and frequency; they do not qualify typing-time battery use.

Debug now enables `-O2` across the entire native dependency tree while preserving
symbols/assertions. A forced compiler guard rejects unoptimized C/C++ translation
units, including a later `-O0` override. Measurements now expose public score wall
time, include lazy context construction in native score time, and label whether
the app is debuggable. Explicit model-identity failures fail the optional test;
they no longer appear as skipped measurements. Digest verification warms the file
cache before load, so load results are not cold-filesystem measurements.

The same public fixture was then compared on host ARM64 with identical source and
Debug assertions, changing only `-O0` to `-O2`. Three warm scores changed from
1326/1329/1330 ms to 58/58/58 ms, with zero score-sum delta. First native score
changed from 2076 to 115 ms. This one-fixture diagnostic confirms a substantial
compiler effect on the host, not a Fold speedup or percentile/battery acceptance.
Numeric results, source/binary identities and reproduction commands are retained
in `tools/test-native-scoring/results/2026-09-05-debug-optimization/`.

Subsequent reconnection produced optimized physical cold/warm, service-duty and
cover-screen Backspace/AutoReplace evidence. Runtime qualification now opens
under the unchanged limits; see
`docs/acceptance/2026-09-05-smart-typing-0.3-fold-qualified.md`. Full physical
activation/release, inner-screen and unplugged energy acceptance remain separate.
Neither changing the model nor retaining it was justified by the faulty
unoptimized build comparison alone.

## Historical unoptimized Debug observations

The exact published Rune Text 0.1 GGUF (`7a97111c…dd9c4`, 396704416 bytes) was measured on the
physical Fold with the public synthetic request `Пекарь готовит ` and four bounded candidates.
The instrumentation verifies the complete model SHA-256 before loading and records content-free
timings only.

| Runtime path (unoptimized Debug) | Load wall | Reported native score | Process CPU | Result for this build |
| --- | ---: | ---: | ---: | --- |
| Original, full prefix per candidate | 0.874 s | 11.638 s | not captured | FAIL |
| Original, repeated thermal run | 1.322 s | 13.621 s | 51.795 s | FAIL |
| Shared prefix once per set | 1.120 s | 4.869 s | 18.569 s | FAIL |
| Persistent context plus incremental KV, cold score | 1.397 s | 5.855 s | 21.698 s | FAIL |
| Persistent context plus incremental KV, warm score | included above | 4.480 s | 16.994 s | FAIL |

Shared-prefix and incremental-KV results match the independent token-at-a-time scalar oracle with
zero sum-log-probability delta. The cache retains token IDs/KV in the private model process only,
clears on cancellation failure, session unbind, memory pressure, idle unload, model replacement or
process death, and never reads editor text.

Two rejected experiments establish practical bounds. Eight scoring threads increased wall time to
37.628 s and CPU to 192.869 s on the Fold. A 64-token microbatch left warm wall time at 4.376 s and
changed calibrated scores by up to 0.407125 in the exact-model oracle, so it was not adopted.

The production watchdog remains 3 seconds and 8 CPU-seconds per minute. The tested
unoptimized warm request exceeds both limits. The earlier assertion that this also
rules out the optimized model/backend is superseded by the build-mode correction above.
Boundary handling still must not wait for a model result.

Backspace ownership was corrected independently: deleting a pending Rune-owned space now reopens
the complete preceding Rune-owned word and requests candidates for that word. A word whose left
boundary predates the bounded session context is not claimed. This preserves the no-readback rule.

An activation stall was observed after the persistent-context change. Allocation
during model load held a scoring context alongside the self-test context; whether
this caused the stall was not established by memory or stack evidence. Lazy
scoring-context construction removes that overlap. Local native/JVM gates cover
the change; physical activation and timing remain required.

An experimental candidate-lane batch reduced the same host request from 206 ms warm to 43 ms and
completed the archived calibration/known-holdout diagnostics at p95 66/70 ms. It was rejected:
the scalar oracle delta reached 0.544792, and a calibration-only point-95 fit scored the already
seen holdout at EN 370/398 (92.96%), RU 509/547 (93.05%) and ES 501/534 (93.82%). These figures are
diagnostic, not a new qualification; the holdout was previously revealed. The
point-95 calibration fit also differs from the earlier scalar fit, so the quality
difference cannot be attributed solely to batching arithmetic. Product inference is
therefore closed for the current model/backend pair even though the exact scalar quality profile
passes the selected point-95 gate. Local deterministic candidates remain available.

Any replacement model must be trained and frozen independently of this
known holdout. Its end-to-end budget includes the measured four-candidate local generation p95 of
51.968 ms. Qualification requires a fresh calibration/holdout and a physical Fold p95 that finishes
before the word boundary; preloading may then remove first-request model load but cannot substitute
for warm inference meeting that budget.

A host-only 262,144-feature hashed linear ranker was also tested against 196,400 pinned public
pairwise rows. It trained in 34.47 s and would require roughly 1 MiB of float weights, but the
point-95 calibration admitted only one replacement per language. On the already seen holdout it
admitted EN 4, RU 2 and ES 0 replacements. This fails coverage by orders of magnitude and is not a
shipping candidate. That prototype also used different training/evaluation feature
sets and an unnormalized single-epoch fit; it does not rule out linear rankers as
a class. A replacement's data and thresholds still require a fresh unseen holdout.
