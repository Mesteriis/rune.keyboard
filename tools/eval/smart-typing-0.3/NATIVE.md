# Bounded native evaluation reference

From the repository root, with CMake >=3.31.6 and Ninja:

```sh
cmake -S tools/eval/smart-typing-0.3 -B build/smart-typing-0.3/native \
  -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/smart-typing-0.3/native \
  --target rune-score scoring-math-test scoring-model-test -j 4
ctest --test-dir build/smart-typing-0.3/native --output-on-failure
```

The build requires clean pinned llama.cpp sources at
`36b10154383b60eb15baac2c7a40d2a5f784faa7`. It neither modifies nor patches
the submodule. The ordinary CTest target needs no model. The separate
`scoring-model-test MODEL_FILE` executable is an independent token-at-a-time
oracle for an already verified model. Do not add it to ordinary CI with an
unverified or full model download.

`rune-score MODEL_FILE` accepts bounded JSONL requests. The Python evaluator
verifies model size and SHA-256 before invoking it; the standalone binary does
not implement that artifact qualification boundary. See README.md for the
exact model and protocol. No unrestricted generation is exposed.

The reusable core returns raw divergent-span log-probability sums and token
counts. Standalone prefix/continuation tokenization only enforces limits;
scoring uses complete strings and their longest common token prefix. It does
not append EOS. An absent common prefix yields `INSUFFICIENT_CONTEXT`; a zero
divergent span yields zero count, which the evaluator treats as abstention.
Each alternative starts with cleared KV state. This serial reference deliberately
uses one-token CPU microbatches and disables flash attention: wider CPU
microbatches did not match the scalar oracle on the pinned backend.

The caller owns the model and cancellation flag, must outlive the scorer, and
must serialize score calls. This PR checks cancellation around tokenization
and during decoding. Tokenizer-internal cancellation, JNI exception containment,
and the product runtime error-code mapping are conditional PR2 work.

## Third-party components

The executable statically links the existing pinned llama.cpp/ggml (MIT,
copyright 2023–2026 The ggml authors). Its JSON adapter uses the pinned
`vendor/nlohmann/json.hpp`, JSON for Modern C++ 3.12.0 (MIT, copyright
2013–2025 Niels Lohmann). Neither is newly vendored into this directory or
added to the Android APK by this evaluation build. Preserve these notices
when distributing the executable, together with any applicable linked platform
library notices.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

## Runtime integration contract

The runtime compiles this same `scoring.cpp` with `RUNE_TOKENIZER_ABORT=1` against
a clean-pin archive copy plus the reviewed additive tokenizer patch. The evaluator
can still compile the default branch against the pristine submodule; the flag is
private to the runtime target. No second scoring implementation is maintained.

A zero divergent-token span rejects the entire candidate set as `SCORING_FAILED`
(including one candidate, identical full token sequences, or one sequence ending
at the LCP). `INSUFFICIENT_CONTEXT` also maps to `SCORING_FAILED` in the runtime.
No partial scores or ranking are returned. This changes the evaluator's previous
zero-score behavior and requires rerunning its contract/model regression suite in
a separate output tree before PR2 integration; existing quality results are not
requalified by the infrastructure change.
