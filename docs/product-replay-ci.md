# Current-product replay

`tools/eval/smart-typing-0.3/pipeline/current_product_replay.py` runs the current
local spelling cascade through the actual Kotlin controller, without a native
model, scorer executable, optional Python model packages or platform-specific
JDK library inventory. Supply an explicit JDK 17 executable; the compiler jars
are selected by the pinned SHA-256 values in the existing toolchain manifest.
Use Python 3.11 or newer. Run Gradle first to populate the Kotlin 2.2.10 cache and install the Android
compile SDK. Both Linux and macOS use their own JDK executable; no Homebrew path
is a default.

```sh
./gradlew testDebugUnitTest
python3 tools/ci/generate_product_replay_v1.py --check
python3 tools/ci/register_product_replay_v1.py --check
python3 tools/eval/smart-typing-0.3/pipeline/current_product_replay.py \
  --java "$JAVA_HOME/bin/java" \
  --rows tools/ci/product-replay-v1/inputs.jsonl \
  --output build/current-product-replay
```

Output must be a fresh directory under `build/`. The driver selects only `id`,
`split`, `language`, `prefix` and `typed` from each input row. Controller IDs are opaque ordinals because historical IDs may contain cohort
names; their mapping to original IDs stays in host-only `input-identities.jsonl`.
Expected-label, alternative and cohort fields never enter the Kotlin process. Input
identities must be unique and EN/RU/ES scope explicit. The v1 CI inputs are disclosed regression data, not independent fresh
qualification. Their CC BY-SA source attribution and adaptation details are in
`tools/ci/product-replay-v1/NOTICE.md`. Older historical spelling inputs remain
supported with their original attribution and license scope.

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
times are recorded separately. Failure leaves a failed receipt and raw output; the original child exit code
or timeout is retained separately from the driver’s failure exit. It is never
converted to a successful replay.

The successful `projection.jsonl` is canonical UTF-8 JSONL. To compare with an
explicit frozen baseline, pass `--baseline path/to/baseline.jsonl`. The command
fails on drift and writes `baseline-comparison.json` with one-based row numbers,
row identities and JSON pointer paths for every changed field. It never updates
the baseline. The same comparator is independently callable:

```sh
python3 tools/eval/smart-typing-0.3/pipeline/replay_projection.py \
  --baseline baseline.jsonl --candidate candidate.jsonl --report diff.json
```

Plain JSONL and `.jsonl.gz` baselines have the same canonical projection.
Decoding is bounded to 1 MiB per line and 256 MiB uncompressed per file.
The comparator exits 0 for equality, 1 for differences and 2 for invalid input or
an existing/unwritable report. CLI raw replay outputs are private by default;
they can contain supplied corpus text. A baseline update requires its own
reviewed commit and acceptance link.

This is the portable runner/comparator foundation for Q7. The permanent licensed label-free CI inputs and surface/context Q6 exclusions
are versioned; unknown canonical families still keep Q6 coverage incomplete.
The newly captured committed baseline,
threshold-mutation failure, expanded tools test jobs and measured Ubuntu CI run
remain separate acceptance work. The existing pipeline test discovery includes
the runner/comparator unit tests. A host-only run does not establish Ubuntu
runtime budgets or a remotely executed CI job.
