# Smart Typing 0.3 final qualification corpus

This directory preserves the source and generator for the historical second
calibration/holdout corpus. It used different immutable Wikipedia parquet
shards from model training. The generator excludes every family present in the
actual training data and in the already revealed evaluation corpus before it
assigns calibration and holdout rows.

Both splits contain, for each of EN, RU, and ES, 1,000 typo rows, 1,000
correct/protected rows, and 200 punctuation rows. Assignment is deterministic
and family-disjoint. The complete corpus is frozen before the candidate model
is scored. Inputs and generated text stay out of the APK.

The source text has the same Wikimedia licenses and attribution described in
[`../../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md`](../../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md).

The corpus has since been revealed and reused. It is historical regression and
reproduction data, not an untouched holdout for a new qualification.

## Exact historical reproduction

Use `reproduce_corpus.py` with Python 3.12 and PyArrow 25.0.1. It projects the
three exact archived sources into their original directory layout, checks all
Wikipedia/frequency/training/prior-corpus identities, runs the original generator
and requires all seven data files **and the manifest** to match the committed
bytes. It repeats source/input checks after execution and writes a receipt only
after success. Output must be fresh and under ignored `build/`.

```sh
python3 tools/eval/smart-typing-0.3/qualification-v2/reproduce_corpus.py \
  --inputs build/smart-typing-0.3/qualification-v2/wikipedia-20231101 \
  --frequency-inputs build/smart-typing-0.3/corpus-inputs \
  --training-data build/smart-typing-0.3/model-v02/data-03 \
  --output build/qualification-v2-reproduced
```

The frozen generator hash is `2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65`;
its evaluator dependency is `ad76b78ba9f00f301465e0f47eb7e96781c44d8bc141a8e1176603bc7f12d5d7`.
The later mixed-script eligibility guard belongs to a different generator hash
(`ed9928d64d80911c0182e03446d710a60abb990cb5fb1cff30730443db773225`).
Both versions are archived; substituting one for the other cannot reproduce the
same source receipt. The active generator includes that later guard: it refuses
to label a language-specific regex fragment inside a mixed-script token as a
correct word. Its historical corpus remains bound to the original generator.
The recovery command leaves the active generator, corpus
and their existing manifests unchanged. It neither trains nor calls a model.

## Original generation recipe

The following historical recipe assumes the original source versions, including
the evaluator. For current-tree exact restoration use the command above.
The pinned parquet inputs are downloaded into ignored `build/` storage. After
the final training-data manifest exists, generate the corpus once:

```sh
python3 tools/model/rune-text-0.2/download_wikipedia_context.py \
  --lock tools/eval/smart-typing-0.3/qualification-v2/source-lock.json \
  --output build/smart-typing-0.3/qualification-v2/wikipedia-20231101

build/smart-typing-0.3/model-v02/venv/bin/python \
  tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py \
  --inputs build/smart-typing-0.3/qualification-v2/wikipedia-20231101 \
  --frequency-inputs build/smart-typing-0.3/corpus-inputs \
  --training-data build/smart-typing-0.3/model-v02/data-03 \
  --output tools/eval/smart-typing-0.3/qualification-v2/corpus
```

Commit the generated files before any call to the scoring CLI. Run the common
evaluator against that directory with `--corpus`; calibration must finish and
freeze its configuration before the first holdout request.
