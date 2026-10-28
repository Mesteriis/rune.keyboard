# Current-product replay

`tools/eval/smart-typing-0.3/pipeline/current_product_replay.py` runs the current
local spelling cascade through the actual Kotlin controller, without a native
model, scorer executable, optional Python model packages or platform-specific
JDK library inventory. Supply an explicit JDK 17 executable; the compiler jars
are selected by the pinned SHA-256 values in the existing toolchain manifest.
Run Gradle first to populate the Kotlin 2.2.10 cache and install the Android
compile SDK. Both Linux and macOS use their own JDK executable; no Homebrew path
is a default.

```sh
./gradlew testDebugUnitTest
python3 tools/eval/smart-typing-0.3/pipeline/current_product_replay.py \
  --java "$JAVA_HOME/bin/java" \
  --rows tools/eval/smart-typing-0.3/spelling-en.jsonl \
  --rows tools/eval/smart-typing-0.3/spelling-ru.jsonl \
  --rows tools/eval/smart-typing-0.3/spelling-es.jsonl \
  --rows tools/eval/smart-typing-0.3/protected-tokens.jsonl \
  --output build/current-product-replay
```

Output must be a fresh directory under `build/`. The driver selects only `id`,
`split`, `language`, `prefix` and `typed` from each input row. Controller IDs are opaque ordinals because historical IDs may contain cohort
names; their mapping to original IDs stays in host-only `input-identities.jsonl`.
Expected-label, alternative and cohort fields never enter the Kotlin process. Input
identities must be unique and EN/RU/ES scope explicit. These existing historical
fixtures are regression inputs, not independent fresh qualification. Their
attribution and licensing remain as described in the source corpus README;
this tool does not grant a new license to authored fixture content.

`current-product` selects the existing full noun-case production chain, including
its contextual and infinitive stages and the earlier local/joint/rescue/word
context paths. Default settings and current qualification gates still apply.
External model requests receive the existing unavailable response; no model
scores or replacement policies are fabricated. The legacy
`tools/typing_experiments/replay_joint_correction.py` is versioned with explicit
`--java` and all production stage names for historical RU receipts.

The driver compiles once and runs two separate JVM processes. Every observation
must complete and preserve the exact submitted row identity and payload.
`determinism.json` compares all fields except exactly the top-level
`fullTokenGenerationNanos` and `hostStageNanos`. Unknown timing-like fields,
source/refusal values, candidate order, scores, editor text, commands, boundary
and Backspace states remain compared. Boolean and numeric type changes differ.
Duplicate JSON keys, incomplete/empty/truncated observations and invalid numbers
cannot pass as deterministic output.

Files, selected production/observer sources, the Android personalization source,
all packaged assets, input files, exact compiler jars, JDK executable and Android
stub are SHA-256 bound before and after execution. Compilation and replay wall
times are recorded separately. Failure leaves a failed receipt and raw output;
it is never converted to a successful replay.

The successful `projection.jsonl` is canonical UTF-8 JSONL. To compare with an
explicit frozen baseline, pass `--baseline path/to/baseline.jsonl`. The command
fails on drift and writes `baseline-comparison.json` with one-based row numbers,
row identities and JSON pointer paths for every changed field. It never updates
the baseline. The same comparator is independently callable:

```sh
python3 tools/eval/smart-typing-0.3/pipeline/replay_projection.py \
  --baseline baseline.jsonl --candidate candidate.jsonl --report diff.json
```

The comparator exits 0 for equality, 1 for differences and 2 for invalid input or
an existing/unwritable report. CLI raw replay outputs are private by default;
they can contain supplied corpus text. A baseline update requires its own
reviewed commit and acceptance link.

This is the portable runner/comparator foundation for Q7. The permanent licensed
label-free CI inputs and Q6 exclusions, newly captured committed baseline,
threshold-mutation failure, expanded tools test jobs and measured Ubuntu CI run
remain separate acceptance work. The existing pipeline test discovery includes
the runner/comparator unit tests. A host-only run does not establish Ubuntu
runtime budgets or a remotely executed CI job.
