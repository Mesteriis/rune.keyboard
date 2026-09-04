# Rune Text 0.2 ranking milestone

This directory defines the separate model-training milestone opened after the
unmodified Qwen3-0.6B Base quantization failed the frozen Smart Typing product
holdout. It does not change the Android runtime or qualify a release by itself.

The candidate keeps the exact Qwen3-0.6B Base architecture. Training uses LoRA
only as a host-side optimization; adapters must be fused into the base weights
before the existing pinned llama.cpp converter produces one Q4_K_M GGUF. The
phone never loads an adapter, trains, or changes the request limits. Thus a
candidate has the same parameter count and inference graph class as Rune Text
0.1; physical Fold latency, memory, thermal and energy gates still must be run
for its exact final digest.

`download_wikipedia_context.py` fetches three bounded parquet shards from the
pinned Wikimedia Wikipedia `20231101` conversion and verifies their sizes and
SHA-256 digests. `prepare_wikipedia_context.py` extracts public encyclopedic
prefixes, excludes every family in the already revealed Smart Typing corpus,
keeps one deterministic context per word family, and caps every prefix at 256
UTF-8 bytes. The parquet files and extracted text remain under ignored
`build/`; none is packaged in the application. See `WIKIMEDIA_NOTICE.md` for
source attribution and licenses.

`generate_pairwise_data.py` also verifies the pinned FrequencyWords inputs and
creates disjoint train/validation word families. It joins the independently
verified Wikipedia pool only after excluding every family already assigned to
the frequency or product-calibration splits. A mutation that is itself present
in the 50k vocabulary is never used as a negative. There are no personal
messages or user data.

`train_pairwise.py` optimizes the same per-token average log probability used by
the product scorer, starting at the first divergent token and adding no EOS.
The reference-free logistic preference loss is combined with a small chosen
continuation NLL term. Validation accuracy and mean margin are recorded before
and after training. The committed config is the candidate run; `--smoke` is a
two-iteration wiring check and its output is permanently marked `smokeOnly`.

Typical local sequence (all outputs stay under ignored `build/`):

```sh
uv venv --python 3.11 build/smart-typing-0.3/model-v02/venv
uv pip sync --python build/smart-typing-0.3/model-v02/venv/bin/python \
  tools/model/rune-text-0.2/requirements-lock.txt

python3 tools/model/rune-text-0.2/download_wikipedia_context.py \
  --output build/smart-typing-0.3/model-v02/wikipedia-20231101

build/smart-typing-0.3/model-v02/venv/bin/python \
  tools/model/rune-text-0.2/prepare_wikipedia_context.py \
  --inputs build/smart-typing-0.3/model-v02/wikipedia-20231101 \
  --frequency-inputs build/smart-typing-0.3/corpus-inputs \
  --output build/smart-typing-0.3/model-v02/wikipedia-context

python3 tools/model/rune-text-0.2/generate_pairwise_data.py \
  --inputs build/smart-typing-0.3/corpus-inputs \
  --calibration-export build/smart-typing-0.3/model-v02/calibration-export \
  --context-pool build/smart-typing-0.3/model-v02/wikipedia-context \
  --output build/smart-typing-0.3/model-v02/data

build/smart-typing-0.3/model-v02/venv/bin/python \
  tools/model/rune-text-0.2/train_pairwise.py \
  --base build/smart-typing-0.3/model-v02/base \
  --data build/smart-typing-0.3/model-v02/data \
  --output build/smart-typing-0.3/model-v02/adapters
```

After validation, fuse with pinned `mlx_lm.fuse`, convert with llama.cpp
`36b10154383b60eb15baac2c7a40d2a5f784faa7`, quantize to Q4_K_M, and record all
fused/source/output hashes. Do not publish or activate the model until a newly
frozen calibration and untouched holdout pass, followed by the exact-digest
API26/API37 and physical Fold matrix.

The checked wrapper rejects smoke adapters and architecture changes:

```sh
python3 tools/model/rune-text-0.2/fuse_candidate.py \
  --python build/smart-typing-0.3/model-v02/venv/bin/python \
  --base build/smart-typing-0.3/model-v02/base \
  --adapter build/smart-typing-0.3/model-v02/adapters \
  --output build/smart-typing-0.3/model-v02/fused-candidate \
  --config tools/model/rune-text-0.2/training-config-candidate-04.json
```

Candidate 04 uses `training-config-candidate-04.json`. It keeps the same base architecture and final
Q4_K_M runtime format while expanding only the offline data, LoRA capacity and validation work. Pass
that file explicitly to context preparation, pair generation and training; the original
`training-config.json` remains frozen for reproduction of the rejected candidate.

Candidate 05 uses `training-config-candidate-05.json` after candidate 04 failed production-candidate
calibration. Its product input is the revealed v3 **calibration** export; v3 holdout rows are never
training pairs. Correct and protected calibration rows teach Original against generated hard
negatives, while typo rows teach the independently authored expected spelling when it is present.
The larger LoRA is fused offline, so the final Qwen3-0.6B/Q4_K_M runtime architecture and request
bounds do not grow. Use a new independent corpus for every candidate-05 qualification attempt.

The final local builder requires the clean pinned llama.cpp submodule. It
records the F16 identity, removes that temporary file and the host build after
successful Q4_K_M conversion, and leaves the candidate explicitly
`releaseQualified=false` and `publishable=false`:

Create a separate converter environment containing the exact versions in
`converter-toolchain-lock.json`. In particular, the converter needs PyTorch as well as the
same Transformers/tokenizers versions that wrote the fused tokenizer. The
builder reads those versions from the interpreter and rejects any mismatch
before conversion.

```sh
python3 tools/model/rune-text-0.2/build_gguf.py \
  --converter-python /absolute/path/to/pinned-converter-python \
  --fused build/smart-typing-0.3/model-v02/fused-candidate \
  --llama runtime-llama/src/main/cpp/llama.cpp \
  --output build/smart-typing-0.3/model-v02/gguf-candidate \
  --config tools/model/rune-text-0.2/training-config-candidate-04.json
```
