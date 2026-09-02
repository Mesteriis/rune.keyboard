# Native scoring qualification

This harness builds the production `tools/eval/smart-typing-0.3/scoring.cpp`, runtime
wire encoder and reviewed tokenizer patch. It uses
`runtime-llama/src/main/cpp/PrepareLlamaSource.cmake` to verify the pristine gitlink
and patch digest, archive upstream into this build directory and patch only that
copy. The generated `rune-llama-provenance.json` records both pins.

## Required offline CI gate

```sh
cmake -S tools/test-native-scoring -B build/test-native-scoring -DCMAKE_BUILD_TYPE=Release
cmake --build build/test-native-scoring --parallel 4
ctest --test-dir build/test-native-scoring --output-on-failure -V
python3 -m unittest discover -s tools/test-native-scoring -p 'test_*.py' -v
```

CMake 3.31.6 or newer, a C/C++17 compiler and the initialized pinned submodule are
required. No model, network access or extra runtime package is needed. The four
required tests cover:

- `scoring-contracts`: the real scoring loop with a deterministic model double;
  independent numeric teacher-forcing oracle, positive divergent spans, serial
  context clearing, 192/64/256 token limits including BOS, decode and tokenization
  cancellation, partial-result discard, failed/nonfinite decode and next-request
  reuse, tokenizer error mapping and numeric JNI wire encoding.
- `scoring-math`: the existing production math, strict UTF-8 and request limits.
- `tokenizer-fixture`: generates a 259-token metadata-only GGUF using the pinned
  C++ GGUF writer. All 256 GPT2 byte encodings, an `a a` BPE merge and two synthetic
  special tokens are included. No weights or user data are present.
- `tokenizer-abort`: **real patched tokenizer**, using that tiny GGUF. Verifies
  fixed and seeded Unicode equivalence with the legacy API, strict invalid-input
  statuses, no partial output, exact buffer sizing, unsupported presets and 80
  concurrent calls with separate per-call callback state. It reaches all eight
  cancellation stages and successfully reuses the same vocabulary after each
  cancellation. Unicode preparation, QWEN2 pre-split and BPE merge cancel on their
  third checkpoint, proving cancellation occurs inside the loops. The fixture
  also asserts that its merge and configured BOS actually occur.

CTest fixture dependencies generate the vocabulary even when selecting only the
tokenizer test. Mandatory tests have 30/60-second process timeouts. The 262144-byte
stress strings prove checkpoint reachability; production byte/token caps remain
unchanged, and these tests do not establish a cancellation latency deadline.

## Optional exact-model qualification

Supply an already available, local copy; no command downloads it:

```sh
cmake -S tools/test-native-scoring -B build/test-native-scoring-model \
  -DCMAKE_BUILD_TYPE=Release \
  -DRUNE_SCORING_MODEL=/absolute/path/rune-text-v1-0.1.0-q4_k_m.gguf
cmake --build build/test-native-scoring-model --parallel 4
ctest --test-dir build/test-native-scoring-model --output-on-failure -V
```

The file must be exactly 396704416 bytes and SHA256
`7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
The size and digest are verified both at configure and before each model test.
Setting a wrong path/artifact fails; leaving the option unset registers no model
tests and produces no model-related skips in ordinary CI.

Three additional tests carry the `exact-model` label:

- The existing `scoring_model_test.cpp` supplies an independent token-at-a-time
  scalar oracle for RU/EN/ES and batch boundaries against the production scorer
  compiled with the patched tokenizer API. It also checks repeated results,
  all-or-nothing zero spans, cancellation reset and token caps. The only adopted
  change to that existing oracle is the reviewed zero-span failure expectation.
- `tokenizer-model-equivalence` verifies 632 complete sequences (16 fixed + 300
  seeded Unicode cases, each with both `add_special` values). Output includes
  every token ID, count and order; its SHA256 must equal the independently
  captured pristine upstream old-API digest
  `d65c09fdad70f012a0ad17a01d9e0a7c1d891136a69c1977633b9152a7fdea00`.
  The token generator is retained from the approved tokenizer prototype without
  fixture changes. The baseline is pinned to upstream commit
  `36b10154383b60eb15baac2c7a40d2a5f784faa7` and the exact model above.
- `tokenizer-model-abort` repeats real cancellation/status/reuse checks with the
  exact model vocabulary. It loads only vocabulary metadata, not weights.

The manual `qualify-exact-model-scoring` workflow downloads only Actions artifact
9800688354. `extract_model.py` selects exactly one matching inner GGUF, verifies
its size and SHA-256, and only then replaces the destination. Missing/expired
artifacts fail; there is no alternative URL or digest fallback. Ordinary CI does
not download this model. Neither workflow publishes a model or qualifies its
typing accuracy, Android latency or battery use.

The reviewed tokenizer patch SHA256 is
`0a043ce8a57b8534ef2f409443d2dd6ecf00042bd9c2b661b31d94618eb4dc95`.
Golden digest provenance: the approved
`build/smart-typing-0.3/tokenizer-abort/REPORT.md` records an independently linked
pristine `libllama.a` with SHA256
`11118676778e8154512e23b92a4a817ab374d56a881cb5cb57a0c9f810b14539` and byte-identical
`original.tokens` / `patched.tokens`. These ignored prototype files are not inputs
to this harness. A changed digest requires separately reviewed upstream/model
provenance and a freshly independent old-API baseline, not merely accepting the
new tokenizer output.

## Android scope

`LlamaRuntimeInstrumentedTest` is a separate mandatory no-model gate. It tests the
public scoring lifecycle and strict input failures, plus the actual private JNI
registration with an isolated test-owned native handle to bypass Kotlin preflight.
Reflection is used only for this input-boundary test: runtime handle ownership and
production method visibility are unchanged. Public API races exercise scoring,
cancel, unload and close, check every worker outcome and require bounded completion.

Host passes do not certify Android packaging, device inference, model ranking
quality, latency, battery/thermal behavior or release acceptance. Run the runtime
instrumentation and native symbol/packaging gates separately.

## Optional Android exact-model test

### Scope

`LlamaRealModelInstrumentedTest` is annotated with `VerifiedModelOnly` and excluded
by the runtime module's default Gradle instrumentation arguments. Ordinary Gradle
and CI instrumentation therefore requires no model and does not report a model
test as skipped or passed. Direct `adb am instrument` does not inherit Gradle's
runner arguments: pass the filter explicitly.

The optional test uses the actual public `LlamaLocalModelRuntime` on Android. Its
only model input is the test application's private
`filesDir/qualification-model.gguf`. Size 396704416 bytes and SHA-256
`7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4` are checked before
runtime creation or load. Missing, incorrectly sized, incorrectly hashed or
out-of-directory symlinked files fail. There is no download, alternate path,
artifact substitution, test assumption or early success return.

### Manual run

First build and install the debug runtime test APK on the intended emulator or
device. The current merged manifest declares both instrumentation package and
target package as `io.github.mesteriis.rune.runtime.llama.test`.

```sh
./gradlew :runtime-llama:assembleDebugAndroidTest
adb install -r runtime-llama/build/outputs/apk/androidTest/debug/runtime-llama-debug-androidTest.apk
```

For multiple connected devices, consistently select the intended one with adb's
device selector in every command. Set `RUNE_SCORING_MODEL` to an existing local
copy whose provenance was checked; no command below downloads it. Transfer it
directly to the private test app directory without an external-storage copy:

```sh
adb shell run-as io.github.mesteriis.rune.runtime.llama.test mkdir -p files
adb shell -T 'run-as io.github.mesteriis.rune.runtime.llama.test sh -c "cat > files/qualification-model.gguf"' < "$RUNE_SCORING_MODEL"
```

Explicit exact-model qualification:

```sh
adb shell am instrument -w -r \
  -e annotation io.github.mesteriis.rune.runtime.llama.VerifiedModelOnly \
  io.github.mesteriis.rune.runtime.llama.test/androidx.test.runner.AndroidJUnitRunner
```

Explicit ordinary no-model runtime tests:

```sh
adb shell am instrument -w -r \
  -e notAnnotation io.github.mesteriis.rune.runtime.llama.VerifiedModelOnly \
  io.github.mesteriis.rune.runtime.llama.test/androidx.test.runner.AndroidJUnitRunner
```

Do not combine the inclusion and exclusion filters. The Gradle default excludes
the optional test; using the manual inclusion command avoids an accidentally
empty intersection of filters.

### Assertions and limits

- Exact model load and positive scoring through the public Android/JNI path.
- Complete RU/EN/ES result IDs and input order, positive token counts, finite
  nonpositive summed log probabilities, and repeated same-backend values within
  0.000001 absolute tolerance. These are runtime contracts, not accuracy claims.
- Typed all-or-nothing zero-span failure, malformed Unicode, byte and token
  bounds, duplicate IDs, and candidate-count rejection with a loaded model.
- Pre-cancelled model load and scoring admission return `CANCELLED` using the
  public token-first cancellation contract; later independent requests succeed.
- One bounded concurrent cancellation attempt signals from the fast admission
  predicate after native reset, waits a real 10 ms, sets the request token and
  then cancels the runtime. Both a typed `CANCELLED` and a fully validated success
  are recorded separately, because completion can win the race. Neither result
  identifies tokenizer or decode stage. This test has no production hooks.
- A request succeeds after the cancellation attempt. Unload yields `NOT_LOADED`;
  reloading the exact model restores scoring. Runtime close is exercised by use.

The concurrent request uses eight candidates, 129 prefix tokens and at most
33 continuation tokens on the pinned model, within 192/64/256 production caps.
One JUnit test has a 120-second safety timeout; worker admission/join waits are
also bounded. This timeout is not a promised inference or cancellation latency.

Only numeric duration/count metrics are emitted in an instrumentation Bundle:
`qualificationDurationMillis`, `successfulRequests`, `scoredCandidates`,
`preCancelledRequests`, `cancellationRaceCancelled` and
`cancellationRaceSucceeded`. No input text, output text or private path is logged
by the harness. `successfulRequests` and `scoredCandidates` include the optional
concurrent request only when it completes successfully.

Exact inside-tokenizer cancellation belongs to the host qualification harness;
the Android test cannot certify that stage without intrusive hooks. Device
ranking quality, keyboard UX, production latency, battery and thermal behavior
remain separate gates.
