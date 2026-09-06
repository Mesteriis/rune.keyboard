# Smart Typing 0.3 final qualification corpus

This directory defines the source and generator for the second, untouched
calibration/holdout corpus. It uses different immutable Wikipedia parquet
shards from model training. The generator excludes every family present in the
actual training data and in the already revealed evaluation corpus before it
assigns calibration and holdout rows.

Both splits contain, for each of EN, RU, and ES, 1,000 typo rows, 1,000
correct/protected rows, and 200 punctuation rows. Assignment is deterministic
and family-disjoint. The complete corpus is frozen before the candidate model
is scored. Inputs and generated text stay out of the APK.

The source text has the same Wikimedia licenses and attribution described in
[`../../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md`](../../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md).

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
