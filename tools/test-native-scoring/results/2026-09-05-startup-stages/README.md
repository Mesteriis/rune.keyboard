# Host startup stages, 2026-09-05

Exact Rune Text GGUF, three independent model/context lifetimes and four calls
per lifetime to the fixed public Russian fixture in `startup_benchmark.cpp`.
Each call scores four candidates. All 48 candidate sums/counts matched the first
result exactly. Exit status was zero; stderr was empty. A failed run invalidates
all previously emitted rows. This optional diagnostic is not a timing CI gate.

macOS ARM64, Release `-O3 -DNDEBUG`, four CPU threads, Metal/OpenMP/KleidiAI off,
CPU Accelerate/BLAS enabled by this host build. The tokenizer cancellation patch
and shared scoring core are the same sources as the native contract tests.
The filesystem cache was warmed by exact-digest verification. No emulator,
concurrent project test or build was running during this final diagnostic.

| Stage | Wall ms, each lifetime | Process CPU ms, each lifetime |
| --- | --- | --- |
| Model load | 582.624, 572.012, 592.790 | 580.381, 563.213, 581.216 |
| Scorer/context construction | 3.906, 3.794, 4.116 | 3.906, 3.795, 4.064 |
| First score | 88.082, 85.069, 86.991 | 320.897, 309.257, 315.007 |
| Three warm scores per lifetime | 54.080–57.501 across 9 calls | 193.396–203.625 across 9 calls |

Weights dominate this host's startup; eagerly creating a scoring context would
save only about four milliseconds here. The first score has a separate warm-up
cost. These small samples do not establish population percentiles, cold-storage
latency, Android performance, battery consumption or model suitability. They
motivate overlapping weights with typing and avoiding repeated cancelled loads,
without changing the model/scoring math or widening device duty limits.

`stages.csv` has no header: `cycle,stage,wall_us,cpu_us`. Cycle -1 covers the one
backend lifetime. Stage IDs: 0 backend init, 1 weights load, 2 scorer create,
3 first score, 4/5/6 repeated scores, 7 scorer free, 8 weights free, 9 backend
free. `report.json` preserves all 26 rows in named groups, exact source/model/
binary/compile-database hashes and upstream/patch provenance. The compile database
itself stays in the local build directory. `native-contracts.log` records **7/7
PASS**, including exact-model oracle, tokenizer equivalence and tokenizer abort.

Reproduce with a locally supplied exact GGUF; nothing is downloaded:

```sh
cmake -S tools/test-native-scoring -B build/test-native-scoring-model \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DRUNE_SCORING_MODEL="$PWD/build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf"
cmake --build build/test-native-scoring-model --target startup-benchmark --parallel 4
cmake \
  -DMODEL="$PWD/build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf" \
  -DPROGRAM="$PWD/build/test-native-scoring-model/startup-benchmark" \
  -P tools/test-native-scoring/RunModelTest.cmake > build/startup-stages.csv
```

Check the command's exit code before consuming the CSV. Keep the host idle during
measurement. This run used CMake 4.4 with the macOS 26.5 SDK; Android uses its
separately pinned SDK/NDK and build variants.
