# Smart Typing 0.3 fourth independent qualification corpus

This directory defines the untouched calibration/holdout corpus for candidate 05. Qualification v3
is revealed and its calibration rows contributed production hard negatives to candidate 05 training,
so it cannot qualify that model. V4 uses three previously unused immutable Wikipedia parquet shards.
The generator excludes every family in candidate 05 training, the original prepared corpus, and all
qualification v2/v3 rows before assigning calibration and holdout.

Each split contains, per EN/RU/ES, 1,000 typo rows, 1,000 correct/protected rows and 200 punctuation
rows. Assignment is deterministic and family-disjoint. Corpus bytes and the conservative Wilson
selection rule are committed before any candidate 05 score is requested. Inputs and generated text
never enter the APK.

The source text uses the Wikimedia licenses and attribution described in
[`../../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md`](../../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md).

```sh
python3 tools/model/rune-text-0.2/download_wikipedia_context.py \
  --lock tools/eval/smart-typing-0.3/qualification-v4/source-lock.json \
  --output build/smart-typing-0.3/qualification-v4/wikipedia-20231101

build/smart-typing-0.3/model-v02/venv/bin/python \
  tools/eval/smart-typing-0.3/qualification-v4/generate_corpus.py \
  --inputs build/smart-typing-0.3/qualification-v4/wikipedia-20231101 \
  --frequency-inputs build/smart-typing-0.3/corpus-inputs \
  --training-data build/smart-typing-0.3/model-v02/data-05 \
  --excluded-corpus tools/eval/smart-typing-0.3 \
  --excluded-corpus tools/eval/smart-typing-0.3/qualification-v2/corpus \
  --excluded-corpus tools/eval/smart-typing-0.3/qualification-v3/corpus \
  --output tools/eval/smart-typing-0.3/qualification-v4/corpus
```

Commit the generated corpus before scoring. Complete calibration and freeze the conservative
configuration before the first holdout request. A failure stops model-dependent product work for this
candidate; revealed v2/v3/v4 holdout rows must never be used for tuning.
