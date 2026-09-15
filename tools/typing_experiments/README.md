# Public typing experiments

These opt-in models reorder existing **manual alternatives** and supply letter priors for the separately controlled tap experiment. They do not authorize automatic correction. Initial language: Russian. No network or Android ML framework is used.

## Models and limits

- Learned ranking: actually trained CatBoost 1.2.8 reference, exported as 80 bounded symmetric numeric trees (7,756 bytes). Kotlin evaluates the same float32 borders and leaves. The host also trains a pairwise linear comparison.
- Compact context: a trained character MLP with a 24-character window, 24 tanh hidden units and 34 output classes (space plus 33 Russian letters), 81,848 bytes. It scores at most 32 candidate characters. A previous word can affect both candidate scores and next letters. This small character model has no broad language understanding.
- Ranking features: capped unit distance, logarithmic frequency rank, absolute length difference, edit cost, fallback bit, shared two-letter suffix, and 16 deterministic context/candidate suffix buckets. Personal and touch signals are **not** fabricated training labels: their existing adjustments are each independently capped at ±0.2.
- Fixed blend: `0.8*tanh(treeRaw/4) + clip((meanCharacterLogP+3)*0.25, -0.5, 0.5)`. This strength was fixed before the combined holdout evaluation and was not tuned on holdout. The two settings remain independent.
- Codecs reject malformed dimensions, oversized assets, non-finite or excessive weights, missing and trailing bytes. The Android owner verifies exact SHA-256 identities and loads off the UI thread. Missing resources yield zero adjustments and empty priors. Resource completion callbacks are cancellable.

## Reproduction

Use an ignored Python 3.11 virtualenv with `requirements.txt`. Packages are host-only.

```sh
build/morphology-venv/bin/python -m pip install -r tools/typing_experiments/requirements.txt
build/morphology-venv/bin/python tools/typing_experiments/train.py
build/morphology-venv/bin/python -m unittest discover -s tools/typing_experiments -v
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home ./gradlew :app:testDebugUnitTest --tests '*ExperimentModelsTest'
```

The training command accepts **no private corpus path**. It consumes the repository's frozen qualification-v2 Russian public rows and the source-bound `build/morphology-public-export-v3` export. If that export is missing, use `tools/morphology/evaluate.py export --output build/morphology-public-export-v3` first. Training checks source corpus identities, exported row/observation identities, row alignment, and relevant candidate-generator/lexicon source identities. It does not claim unrelated integration/settings sources are frozen. A changed candidate generator fails closed; regenerate the public export intentionally.

Existing calibration and holdout families, templates and IDs are disjoint. Rows are ordered by SHA-256 ID, with seeded training shuffles. `build/typing-experiments/split-freeze.json` is written before fitting. Holdout text never enters training. Public weights, runtime hashes and parity fixtures are generated together. Raw reports, CatBoost reference model and logs stay in ignored build output. `provenance.json` packages aggregate results and public provenance only.

## Results and limitations

On 926 held-out **synthetically corrupted Wikipedia spelling rows with generated alternatives**, expected spelling was present in 739. Top-1 correct counts: generator first 500 (54.00%), linear 633 (68.36%), CatBoost 680 (73.43%), compact context alone 303 (32.72%), fixed CatBoost + context 686 (74.08%). Missing expected alternatives count as failures. The context model alone is worse at spelling ranking; it is a bounded auxiliary. These are standalone fixed-score comparisons, not measured gains for all existing UI bonuses or real chats. Original preservation and automatic policy remain owned by the integration.

Neural holdout cross-entropy: 2.3803 nats; next-character accuracy: 30.64% over 151,562 characters, including spaces. Uniform cross-entropy is 3.5264 nats. This is not on-device performance or dynamic tap accuracy. No real touch supervision, private chats, production-quality guarantee or Android latency measurement is claimed.

## Provenance and license

Source: public `wikimedia/wikipedia`, `20231101` snapshot, revision `a634f78b1c435397c07001e175fa74cc4ad5e775`, Russian `ru-0009.parquet` identity and corpus generation metadata in `tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json` and `source-lock.json`. Wikipedia contributors are the source authors. Corpus source declares CC-BY-SA-3.0 and GFDL-1.3; derived model weights are distributed under CC-BY-SA-3.0. See the packaged `NOTICE.md` and existing CC-BY-SA-3.0 notice. Changes: deterministic public text extraction, synthetic spelling perturbations, model fitting and compact numeric export. No personal messages are included.
