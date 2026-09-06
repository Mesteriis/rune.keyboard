# Smart Typing 0.3 — exact-model emulator runtime receipt

Run date: 2026-09-06.  This receipt verifies the bounded public Android JNI
runtime on the two supported emulator API levels.  It is correctness evidence;
it does not claim keyboard quality, physical-device latency, battery or Fold
acceptance.

## Immutable model identity

| Field | Value |
| --- | --- |
| Hub revision | `alexm37/rune-text-v1@c057e37928624d3c3c4bd526d3515f7202395920` |
| File | `rune-text-v1-0.1.0-q4_k_m.gguf` |
| Bytes | `396704416` |
| SHA-256 | `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4` |
| Source revision | `6b9b89a34f2d3729685f48a3542b194588938d9f` |

The local download was verified by byte count and SHA-256 before either test.
The file was copied through `run-as` directly into the private test-app files
directory; it was not read from shared storage.  The test emits numeric counters
only and retains no entered text.

## Host exact-model native qualification

```text
cmake -S tools/test-native-scoring -B build/test-native-scoring-model \
  -DCMAKE_BUILD_TYPE=Release -DRUNE_SCORING_MODEL=<verified-gguf>
cmake --build build/test-native-scoring-model --parallel 4
ctest --test-dir build/test-native-scoring-model --output-on-failure -V
```

Result: **7/7 PASS**.  This includes scalar teacher-forcing agreement with
maximum sum-log-probability delta `0`, 632 pristine-tokenizer equivalence
sequences, strict UTF-8 and all eight in-tokenizer cancellation checkpoints.

## Android public-runtime qualification

`LlamaRealModelInstrumentedTest.verifiedModelScoresAndRecoversThroughThePublicAndroidRuntime`
was selected explicitly with the `VerifiedModelOnly` annotation after installing
the current debug Android test APK.

| Target | Result | Duration | Successful requests | Scored candidates | Pre-cancelled | Cancellation race |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Emulator API 26 (`emulator-5554`) | PASS | 705 ms | 9 | 27 | 2 | cancelled: 1, succeeded: 0 |
| Emulator API 37 (`emulator-5556`) | PASS | 631 ms | 9 | 27 | 2 | cancelled: 1, succeeded: 0 |

Both runs verify load, finite bounded scoring, validation failures, cancellation,
post-cancellation reuse and unload/reload through the public Android runtime.
They are not a model-assisted spelling-quality evaluation and do not establish a
latency budget.
