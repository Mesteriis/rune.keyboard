# Q6: joint row to article attestation component

The new source-attestation component checks each supplied row against an
independently supplied article: article and shard name, native morphology family
and partition, normalized source word and exact prefix, historical selection
hash, source-window hash, whole-selector-segment hash, all supplied dictionary
lemmas, and basic control/typo label consistency. It returns only a count, not
words or held labels. The caller supplies the generator, both morphology
sources and the article; this component does not authenticate those inputs,
verify the typo-generation algorithm, or establish corpus-wide split/registry
independence by itself.

Seventeen focused stdlib tests pass for this component and the existing joint
calibration binding. The new test uses one synthetic article and fake dictionary;
it rejects mismatched article, native family, split, expected word, incomplete
lemma list, selection hash, context, segment and changed article text. This is
not a test on the public Parquet shards. Python test-inventory and whitespace
checks pass; raw output is `build/review-hosted-editor/joint-article-attestation-tests.log`.

The trainer does not call this component yet and continues to reject new
training. Source-file authentication, complete row-to-article traversal,
corpus-wide partition checks and a label-blind binding to the frozen inputs
remain outstanding. No training, model, app or phone state was changed.

A later local smoke used one previously disclosed calibration row and the exact
historical Wikipedia Parquet shard: its SHA-256 was
`588e30523cfed480151b4bd5c1a7d7211dc03971fee399a3db6af3ad04e42c87`, matching
original manifest SHA-256
`27c7084f8c739f608da77f617eca1c5ac552ff16b74da05a1a3c3cc888120e3f`.
The article was read from that shard with PyArrow 25.0.1; native morphology and
pinned dictionary-only Pymorphy analyses were loaded from their real sources.
The old disclosed row does not contain current context/segment/lemma metadata,
so the smoke derives those three fields from the source and dictionary before
checking the row. Attestation passes once and rejects separate context, segment
and selection-hash mutations. The isolated driver and numeric output are
`build/review-hosted-editor/joint-article-real-smoke.py` (SHA-256
`e495bdd957fed4ad51301d89e7d82d48db736989c257a02d011f15558726de80`) and
`joint-article-real-smoke.log`. The emulator suite was running concurrently;
no timing or performance claim is made.

This proves compatibility for that one previously disclosed article, not
independent source selection, complete original-corpus reproduction, held-label
isolation or training eligibility. It does not remove the trainer's refusal.
