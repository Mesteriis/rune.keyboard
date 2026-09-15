# Public typing experiments

Two independent, opt-in controls reorder existing **manual alternatives** in Russian. CatBoost scores spelling evidence; a small character network adds a bounded context score. Original text stays first, and automatic-correction admission is unchanged. Both controls default off and are covered by the existing “disable additional features” action and configured/effective diagnostic flags. No network or Android ML framework is used.

## Refined models

- **CatBoostRanker 1.2.8**: PairLogitPairwise, 128 symmetric trees, depth 5, 22,036 bytes. RET2 freezes 95 numeric features: the previous 22 features plus edit type, common prefix/suffix, bigram/trigram overlap, word lengths, Russian endings and preceding prepositions. These are spelling/context clues, not a morphological parser. Kotlin compares float32 borders and accumulates exported leaves.
- **Ranking context**: 48-character window, 48 tanh units, 34 next-character classes; REC2, 320,216 bytes. Candidate scoring includes a terminal space and at most 32 candidate characters. This is a character model, not a general language model.
- **Tap priors**: the previous 24×24 REC1 `ru-context.bin` remains byte-for-byte unchanged, 81,848 bytes. It has its own readiness state. Ranking context failure does not disable available tap priors; tap failure does not disable ranking context.
- Fixed selected blend: `0.8*tanh(treeRaw/4) + clip((meanCharacterLogP+3)*0.25, -0.5, 0.5)`. Gain 1 was selected from 0, 0.25, 0.5, 1 using dev only. Existing personal/touch adjustments remain independently capped at ±0.2 and were not fabricated as training labels.
- Strict version/dimension/size/finite-weight codecs and exact SHA-256 resource identities fail closed independently. Loading runs off the UI thread. Context is bounded and obtained through existing acknowledged editor ownership.

## Data and selection

Pinned public Wikimedia Russian shard `ru-0007.parquet`, separate from the previous `ru-0009` source. The source and frequency-file identities are verified against `tools/model/rune-text-0.2/source-lock.json`. No private chats are used. Articles are deterministically assigned to train/dev/test by salted article-ID hash, with duplicate article texts and exact row contexts removed. Vocabulary may recur across article splits; this is an article-generalization test, not an unseen-word benchmark.

| Split | Characters | Synthetic typo rows |
| --- | ---: | ---: |
| Train | 2,000,000 | 5,000 |
| Dev | 250,000 | 1,000 |
| Test | 250,000 | 1,500 |

Corruptions: one deletion, repeated letter, adjacent transposition or horizontal keyboard-neighbor substitution. Targets are lowercase public-vocabulary words, 5–12 characters. Actual production candidates are exported without passing context or expected labels to the generator. The ranker fits 4,624 train groups with both a correct candidate and a competing alternative. Candidate omissions remain failures in the reported evaluation.

Three fixed CatBoost variants were compared on dev; pairwise won. Two neural sizes were trained for six epochs with checkpoints 2/4/6; 48×48 epoch 6 was selected on dev candidate accuracy. The test set was opened after model identities and blend were frozen. A subsequent input-validation hardening rerun reproduced the exact CatBoost binary; it did not select another model. Source hashes and raw receipts are retained under ignored `build/typing-refinement`.

## Results and limitations

Fresh test: **1,477 rows with generated alternatives**, expected spelling available in **1,416** (95.87% coverage ceiling).

| Scorer | Previous correct top-1 | Refined correct top-1 |
| --- | ---: | ---: |
| CatBoost | 1,208 / 1,477 (81.79%) | 1,383 / 1,477 (93.64%) |
| Context alone | 602 / 1,477 (40.76%) | 842 / 1,477 (57.01%) |
| Combined | 1,209 / 1,477 (81.86%) | 1,390 / 1,477 (94.11%) |

Generator first: 1,239 / 1,477 (83.89%). Context alone is still worse than spelling ranking. Neural next-character cross-entropy on 250,000 reserved characters improved from 2.4605 to 2.0885 nats.

**Known regression:** on the already-exposed previous 926-row holdout, CatBoost changed from 680 to 666 correct and the combined score from 686 (74.08%) to 679 (73.33%). Context alone changed from 303 to 313. The refined pair improves the new one-error distribution but is not uniformly better; it remains an optional experiment. The old ranker and its metadata remain in `baseline/` for reproducible comparison.

These percentages rank alternatives on synthetic Wikipedia spelling errors. They do not measure real-chat accuracy, correct-input false-correction rate, all personalized UI bonuses, automatic edits or touch accuracy. Correct-input/original preservation is an integration invariant, not a learned benchmark result. Android timings and checks are recorded separately in `docs/typing-model-refinement.md`.

## Reproduction

Use two ignored host virtualenvs: Python 3.11 with `requirements.txt` for CatBoost/NumPy evaluation; Apple Silicon Python with `requirements-neural.txt` for PyArrow/MLX training. These packages are host-only. Start with fresh ignored output directories; do not overwrite a frozen selection to retune on test results.

1. Run `prepare_refinement.py --parquet PATH_TO_PINNED_RU_0007 --frequency PATH_TO_PINNED_RU_50K --output build/typing-refinement/data` using the neural environment. Concatenate train/dev/test `*-rows.jsonl`, in that order, into `build/typing-refinement/data/all-rows.jsonl`.
2. Run `tools/morphology/evaluate.py export --rows build/typing-refinement/data/all-rows.jsonl --output build/typing-refinement/candidates-v2` with JDK 17 and the existing Kotlin compiler dependencies. Then run `split_observations.py --data build/typing-refinement/data --export build/typing-refinement/candidates-v2 --output build/typing-refinement/verified-observations`.
3. Run `neural_refinement.py` with the neural environment, then `neural_refinement.py --evaluate-dev` with the NumPy environment. It only trains/chooses on train/dev.
4. Run `rank_refinement.py --train build/typing-refinement/verified-observations/train.jsonl --dev build/typing-refinement/verified-observations/dev.jsonl --output build/typing-refinement/ranker`, then `select_refinement.py`. Inputs require public source identities, manifest/receipt hashes, row alignment and partition checks.
5. Run `evaluate_refinement.py` once. It evaluates frozen models on fresh test plus the explicitly exposed old regression set; the latter requires the existing source-bound `build/morphology-public-export-v3` receipt. It does not refit or select models.
6. Review metrics and retained regressions, then run `promote_refinement.py` to copy the already-selected artifacts, generate identities/parity and public provenance. It requires the evaluated selection hash and supported runtime dimensions/blend. Run host tests, Kotlin parity, Android integration/latency and repository gates before packaging.

All scripts above except the explicitly qualified morphology exporter are in `tools/typing_experiments/`. Example checks:

```sh
PYTHONDONTWRITEBYTECODE=1 build/morphology-venv/bin/python -m unittest discover -s tools/typing_experiments -v
./gradlew :app:testDebugUnitTest :app:lintDebug :app:imeIntelligenceBoundary :app:forbiddenRuntimeDependencies :app:privacyGateRelease
```

Legacy `train.py` now emits only ignored `build/typing-experiments` artifacts and generated fixture proposals. It cannot overwrite the refined APK models or Kotlin source. Legacy tests compare the frozen baseline artifact to its retained CatBoost reference.

## Provenance and license

Public `wikimedia/wikipedia`, snapshot `20231101`, revision `a634f78b1c435397c07001e175fa74cc4ad5e775`; contributors are the original authors. Source metadata declares CC-BY-SA-3.0 and GFDL-1.3; derived weights are distributed under CC-BY-SA-3.0. See the packaged `NOTICE.md` and license. Changes include text extraction, synthetic spelling perturbations, model fitting and numeric export. APK provenance contains aggregate metrics and public hashes only.
