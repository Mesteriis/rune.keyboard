# Smart Typing 0.3 third independent qualification corpus

This directory defines the source and generator for a new untouched calibration/holdout corpus after
candidate-03 failed the revealed v2 RU/ES false-change gate. It uses three previously unused immutable
Wikipedia parquet shards. The generator excludes every family in model training, the original prepared
evaluation corpus, and qualification-v2 before it assigns v3 calibration and holdout rows.

Each split contains, per EN/RU/ES, 1,000 typo rows, 1,000 correct/protected rows and 200 punctuation
rows. Assignment is deterministic and family-disjoint. Corpus bytes and the conservative Wilson
selection rule are committed before any v3 model score is requested. Inputs and generated text never
enter the APK.

The source text uses the Wikimedia licenses and attribution described in
[`../../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md`](../../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md).

```sh
python3 tools/model/rune-text-0.2/download_wikipedia_context.py \
  --lock tools/eval/smart-typing-0.3/qualification-v3/source-lock.json \
  --output build/smart-typing-0.3/qualification-v3/wikipedia-20231101

build/smart-typing-0.3/model-v02/venv/bin/python \
  tools/eval/smart-typing-0.3/qualification-v3/generate_corpus.py \
  --inputs build/smart-typing-0.3/qualification-v3/wikipedia-20231101 \
  --frequency-inputs build/smart-typing-0.3/corpus-inputs \
  --training-data build/smart-typing-0.3/model-v02/data-03 \
  --excluded-corpus tools/eval/smart-typing-0.3 \
  --excluded-corpus tools/eval/smart-typing-0.3/qualification-v2/corpus \
  --output tools/eval/smart-typing-0.3/qualification-v3/corpus
```

Commit the generated corpus before scoring. Complete calibration and freeze the v2 conservative
configuration before the first holdout request. A failure stops model-dependent product work for this
candidate; revealed v2 or v3 holdout rows must never be used for tuning.
