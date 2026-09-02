# Optional Android public-runtime benchmark

This manual benchmark scores fixed public synthetic English, Russian and Spanish continuations through `LlamaLocalModelRuntime`. It never generates text or reads editor/session data. It is separate from the existing one-test `VerifiedModelOnly` qualification and from the six ordinary no-model Android tests.

The model must already exist as `qualification-model.gguf` in the instrumentation app's private files directory. The test fails unless its canonical parent, size **396704416 bytes**, and SHA-256 **7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4** match before runtime construction or load. This workflow contains no download or model staging command. The checksum reads the whole model before load, so the load measurement is **not a cold filesystem measurement**.

## Explicit profiles and build variant

Every configuration combines one language with 2, 4 or 8 candidates. Candidate ID zero is the unchanged synthetic original; larger sets contain the smaller set in the same order. All nine configurations get one warmup request first. Measured rounds each visit all nine configurations, starting at `(round * 4) mod 9`; order and fixtures are shared across profiles. Counts are balanced per configuration. A full run gives each configuration each within-round position two or three times; neither profile is a randomized population sample.

- `pilot`: 3 measured requests per configuration (27 total), 600-second whole-test deadline.
- `full`: 20 measured requests per configuration (180 total), 1800-second whole-test deadline.

Both then run three separate admission/cancellation attempts and one recovery request. Pilot is the first device step. Full is a separate explicit decision; the harness does not escalate or adapt repetitions after reading timings. The pilot's p95 is simply its maximum among three observations. These are descriptive sample statistics, with no percentile precision, battery budget or product latency gate implied.

`runeRuntimeTestBuildType` accepts only `debug` or `release` and defaults to `debug`. It selects the library's standard Android test build type; it does not change native flags. The benchmark reads its build variant from test manifest metadata populated by the same Gradle property, rather than trusting a runtime label argument. Debug native timing is diagnostic. Meaningful release baseline evidence requires a release test APK and byte-identical ARM64 native entries in the actual app release APK.

After review/integration, the release build command is:

```sh
./gradlew -PruneRuntimeTestBuildType=release :runtime-llama:assembleReleaseAndroidTest :app:assembleRelease
```

Task availability, manifest merge, APK packaging, installation, the six default no-model tests, and the unchanged one-test qualification are integration checks; standalone Kotlin compilation does not establish them. The APK native match is checked before a benchmark is accepted:

```sh
python3 tools/test-native-scoring/runtime-benchmark/native_proof.py \
  --build release \
  --test-apk runtime-llama/build/outputs/apk/androidTest/release/runtime-llama-release-androidTest.apk \
  --app-release-apk app/build/outputs/apk/release/app-release-unsigned.apk \
  --output build/smart-typing-0.3/fold-release-native-proof.json
```

This compares both `librune_llama.so` and `libc++_shared.so` ARM64 entries, records APK digests, and rejects missing/duplicate/mismatched entries. The Android test independently hashes its installed APK entries; aggregation compares those hashes against this proof. SHA-256 is encoded as eight unsigned, big-endian 32-bit decimal chunks, so records contain no path or textual hash payload. The parent must retain proof from the APKs actually installed. The test explicitly requires a 64-bit ARM64 process; it is not a generic emulator benchmark. `--build debug` creates diagnostic provenance without claiming an app-release match.

With reviewed APKs already installed and the verified private model in place, the explicit pilot command is:

```sh
python3 tools/test-native-scoring/runtime-benchmark/run.py \
  --profile pilot \
  --proof build/smart-typing-0.3/fold-release-native-proof.json \
  --rows build/smart-typing-0.3/fold-release-pilot.csv \
  --summary build/smart-typing-0.3/fold-release-pilot-summary.json
```

Full uses the same explicit command with `--profile full` and separate output names. A missing or unknown profile fails. The runner invokes `adb -d shell am instrument` with the separate `RuntimeBenchmarkOnly` filter, the explicit profile, the build code and both native hashes from the proof. The test rejects build/native mismatches before loading. No command is launched by importing the runner. It performs no build, installation or model transfer. It applies a host timeout of the profile deadline plus 60 seconds; on host timeout it makes a bounded best-effort force-stop of only the dedicated instrumentation app. Both instrumentation and timeout cleanup explicitly use `adb -d` to select the USB device even while an emulator is connected. Exactly one authorized USB target must be attached; the runner does not discover, store or print serials. Do not save unrestricted instrumentation stdout: the collector keeps only numeric benchmark records and requires `OK (1 test)`, the instrumentation completion code, and the exact record schedule. Framework/native diagnostics are discarded, not echoed. Use fresh output names: proof/capture/summary commands reject existing output files. Failed/incomplete runs produce no accepted rows/summary; they are failures, not silently skipped measurements.

The original qualification filter remains unchanged and still selects one test; for this USB Fold workflow the command has the same explicit USB selector:

```sh
adb -d shell am instrument -w -r \
  -e annotation io.github.mesteriis.rune.runtime.llama.VerifiedModelOnly \
  io.github.mesteriis.rune.runtime.llama.test/androidx.test.runner.AndroidJUnitRunner
```

Default Gradle instrumentation excludes both optional annotations. For manual no-model instrumentation use:

```sh
adb -d shell am instrument -w -r \
  -e notAnnotation io.github.mesteriis.rune.runtime.llama.VerifiedModelOnly,io.github.mesteriis.rune.runtime.llama.RuntimeBenchmarkOnly \
  io.github.mesteriis.rune.runtime.llama.test/androidx.test.runner.AndroidJUnitRunner
```

## Numeric schema version 1

Every CSV row has exactly 18 signed decimal integer fields. Ordinary rows use:

| Index | Field | Meaning |
|---|---|---|
| 0 | version | 1 |
| 1 | kind | 0 start, 1 warmup, 2 measured score, 3 lifecycle, 4 cancellation attempt, 5 recovery, 6 successful end, 7 failure, 8 native SHA |
| 2 | profile | 0 pilot, 1 full |
| 3 | sequence | Consecutive record number starting at zero |
| 4 | config | Score: language × 3 + count index; lifecycle: 0 construct, 1 load, 2 unload, 3 close; cancellation: attempt 0..2; otherwise -1 |
| 5 | iteration | Measured round 0..2 or 0..19; warmup 0; otherwise -1 |
| 6 | outcome | 0 success, cancellation 1 cancelled / 2 completion race; failure uses a fixed numeric code |
| 7 | wall_ns | Public call elapsed realtime nanoseconds |
| 8 | process_cpu_ms | Process-wide CPU delta in milliseconds (coarse resolution; may exceed wall duration with multiple threads) |
| 9 | scored_tokens | Sum of public result scoredTokenCount values; cancellation failure has zero |
| 10 | scored_candidates | Public score count; cancellation failure has zero |
| 11 | native_duration_ms | Public result duration/loadMillis; -1 when unavailable/not applicable |
| 12..15 | memory | PSS, RSS, allocated native heap, used Java heap, all bytes; -1 means unavailable |
| 16..17 | auxiliary | Start: API level and build (0 debug / 1 release). Cancellation: signal-to-result-end ns (-1 if completion predates signal), then observed-admission-to-signal ns. Other ordinary records: zero |

Languages are 0 EN, 1 RU, 2 ES. Count indices are 0→2, 1→4, 2→8. For kind 8, config identifies library 0 (`librune_llama.so`) or 1 (`libc++_shared.so`), and fields 8..15 are the eight SHA-256 chunks. The remaining fields have their fixed reserved values. Hash rows are not memory/CPU observations.

Wall/CPU start inside a bounded harness worker immediately before calling the public runtime and stop immediately after it returns; they include public runtime admission, its executor, tokenization and native scoring as an indivisible operation. They exclude harness thread creation, record emission, memory snapshots and result-validation work. Native duration is only the public API's existing duration; it does not identify internal stages. All request snapshots are taken after the call and are not atomic across counters. PSS comes from `Debug.MemoryInfo`, RSS from this process's `/proc/self/status`, native heap from `Debug.getNativeHeapAllocatedSize`, Java heap from `Runtime.totalMemory - freeMemory`. They are footprint snapshots, not allocation deltas, peaks, leak measurements or GC attribution. No forced GC and no `art.gc.bytes-allocated` counter is used.

Start samples memory before runtime construction. Lifecycle rows separate construct, verified-model load, unload and close. End totals include hashing the installed native entries, snapshots, validation, warmups, cancellation and control overhead after the model checksum. Request summaries use only kind 2; warmup/cancellation/recovery are excluded. Each configuration reports p50/p95 (nearest rank), max, request counts and scored token/candidate totals. Lifecycle has one observation per operation; its p50/p95/max are consequently identical. Any missing optional metric suppresses its aggregate and reports available/missing counts; observations are never dropped to manufacture a percentile.

Cancellation uses the existing post-reset admission callback, then a nominal 10-ms wait, sets the independent request flag first, and calls native cancellation second. Admission is not proof that native decode began. Completed requests remain completion races, and returned CANCELLED outcomes are counted separately. Three observations do not establish a cancellation-tail SLA. The recovery request must succeed. Scoring calls have 45-second waits; load 120 seconds; construct/unload/close 30 seconds. Cancellation admits within five seconds, then has a 30-second result wait. On failure the harness requests cancellation and gives five seconds' grace; a stuck call kills only its own dedicated instrumentation process. A separate daemon enforces the profile's whole-test deadline, including cleanup. Timeouts never produce a passing summary.

The test makes no editor-frame, stale-result, scheduler/coalescing, internal tokenizer-stage, battery, thermal or energy claims. It does not implement IME integration. A warm physical-device session still requires a separate scheduling/battery decision after baseline evidence. Run profiles separately without concurrent build/benchmark work and report ambient/device conditions externally without identifiers.

## Host checks and reaggregation

```sh
python3 -m unittest discover -s tools/test-native-scoring/runtime-benchmark -p test_protocol.py
python3 tools/test-native-scoring/runtime-benchmark/protocol.py summary \
  --proof build/smart-typing-0.3/fold-release-native-proof.json \
  --rows build/smart-typing-0.3/fold-release-pilot.csv \
  --summary build/smart-typing-0.3/fold-release-pilot-reaggregated.json
```

Host checks use synthetic numeric records and tiny fake ZIP fixtures. They verify arithmetic, exact schedules/counts, malformed/missing/failure rejection, metric availability, honest cancellation races, native identity, and redacted CLI failures. They execute no JNI or model workload and provide no Android pass.
