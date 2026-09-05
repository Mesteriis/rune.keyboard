# Host Debug compiler diagnostic, 2026-09-05

Same frozen CPU scoring source, pinned pristine llama.cpp, exact published Rune
Text GGUF and four-candidate public Russian fixture in both executables. Host
macOS ARM64 only. Four threads; GPU/OpenMP/KleidiAI disabled by evaluation CMake.
Both builds keep Debug assertions/symbols; the changed setting is `-O0` to `-O2`.
Each compile database has 218 records with the expected optimization flag.
The binaries ran sequentially, without concurrent builds/tests.

| Observation | `-O0` | `-O2` |
| --- | ---: | ---: |
| First native score | 2076 ms | 115 ms |
| Three repeated warm scores | 1326, 1329, 1330 ms | 58, 58, 58 ms |
| Whole process wall time | 8437.348 ms | 1344.010 ms |
| Whole process CPU time | 25276.601 ms | 1634.829 ms |

All four score sums/token counts match exactly across builds and repeated calls;
maximum sum delta is zero. Warm median is about 23 times lower. This is **one
fixture in a fixed run order**, not a percentile/quality population, a Fold result
or an energy measurement. CLI native score excludes model/context construction;
whole-process totals include construction/load and shutdown. The exact model
checksum was verified before either run, warming the filesystem cache.

`summary.json` preserves numeric results and executable/compile-database digests.
`manifest.json` binds this result to the unchanged scorer, CLI, host CMake and
diagnostic source at the recorded base commit. Android's current source additionally
uses the tokenizer cancellation patch and JNI boundary; these host timings do not
replace either Android test or byte-identical release-native qualification.

Reproduce with host CMake/Ninja/C/C++ available and the existing exact model:

```sh
cmake -S tools/eval/smart-typing-0.3 \
  -B build/smart-typing-0.3/debug-optimization-audit/before -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  '-DCMAKE_C_FLAGS_DEBUG=-g -O0' '-DCMAKE_CXX_FLAGS_DEBUG=-g -O0'
cmake --build build/smart-typing-0.3/debug-optimization-audit/before --target rune-score --parallel 4
cmake -S tools/eval/smart-typing-0.3 \
  -B build/smart-typing-0.3/debug-optimization-audit/after -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  '-DCMAKE_C_FLAGS_DEBUG=-g -O2' '-DCMAKE_CXX_FLAGS_DEBUG=-g -O2'
cmake --build build/smart-typing-0.3/debug-optimization-audit/after --target rune-score --parallel 4
python3 tools/test-native-scoring/compare_debug_optimization.py \
  --before-dir build/smart-typing-0.3/debug-optimization-audit/before \
  --after-dir build/smart-typing-0.3/debug-optimization-audit/after \
  --model build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf \
  --output build/smart-typing-0.3/debug-optimization-audit/summary.json
```

Use a fresh output path when repeating; the diagnostic rejects an existing report.
No download, Android operation, private text or holdout fitting is involved.
