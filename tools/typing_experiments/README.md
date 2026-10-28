# Public typing experiments

This directory retains historical experiments and current source/test commands.
Source-presence acceptance is separate from model qualification; outstanding
lineage and fresh-data work remain in the [review map](../../docs/plans/2026-10-27-review-completion.md).

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

## Historical refinement results and limitations

The following counts belong to the original refinement run. The bundled ranker
was later selected by the augmented/abstaining procedure; this table does not
qualify that later asset or the current application. The original reserved test
is now disclosed regression data.

Original reserved test: **1,477 rows with generated alternatives**, expected spelling available in **1,416** (95.87% coverage ceiling).

| Scorer | Previous correct top-1 | Refined correct top-1 |
| --- | ---: | ---: |
| CatBoost | 1,208 / 1,477 (81.79%) | 1,383 / 1,477 (93.64%) |
| Context alone | 602 / 1,477 (40.76%) | 842 / 1,477 (57.01%) |
| Combined | 1,209 / 1,477 (81.86%) | 1,390 / 1,477 (94.11%) |

Generator first: 1,239 / 1,477 (83.89%). Context alone is still worse than spelling ranking. Neural next-character cross-entropy on 250,000 reserved characters improved from 2.4605 to 2.0885 nats.

**Known regression:** on the already-exposed previous 926-row holdout, CatBoost changed from 680 to 666 correct and the combined score from 686 (74.08%) to 679 (73.33%). Context alone changed from 303 to 313. The refined pair improves the new one-error distribution but is not uniformly better; it remains an optional experiment. The old ranker and its metadata remain in `baseline/` for reproducible comparison.

These percentages rank alternatives on synthetic Wikipedia spelling errors. They do not measure real-chat accuracy, correct-input false-correction rate, all personalized UI bonuses, automatic edits or touch accuracy. Correct-input/original preservation is an integration invariant, not a learned benchmark result. Android timings and checks are recorded separately in `docs/typing-model-refinement.md`.

## Reproduction

Historical model reproduction requires the original pinned inputs and recorded
runtimes: the original CatBoost/NumPy environment and the separate Apple Silicon
PyArrow/MLX environment. Host requirements are in `requirements.txt` and
`requirements-neural.txt`. For current source tests, [CI](../../.github/workflows/ci.yml)
uses Python 3.12 with separate stdlib, scientific and MLX jobs; scientific tests
also require the verified historical-data preparation shown there. Start with
fresh ignored output directories. Revealed tests cannot become fresh
qualification data through rerunning the following historical commands.

1. Run `prepare_refinement.py --parquet PATH_TO_PINNED_RU_0007 --frequency PATH_TO_PINNED_RU_50K --output build/typing-refinement/data` using the neural environment. Concatenate train/dev/test `*-rows.jsonl`, in that order, into `build/typing-refinement/data/all-rows.jsonl`.
2. Run `tools/morphology/evaluate.py export --rows build/typing-refinement/data/all-rows.jsonl --output build/typing-refinement/candidates-v2` with JDK 17 and the existing Kotlin compiler dependencies. Then run `split_observations.py --data build/typing-refinement/data --export build/typing-refinement/candidates-v2 --output build/typing-refinement/verified-observations`.
3. Run `neural_refinement.py` with the neural environment, then `neural_refinement.py --evaluate-dev` with the NumPy environment. It only trains/chooses on train/dev.
4. Run `rank_refinement.py --train build/typing-refinement/verified-observations/train.jsonl --dev build/typing-refinement/verified-observations/dev.jsonl --output build/typing-refinement/ranker`, then `select_refinement.py`. Inputs require public source identities, manifest/receipt hashes, row alignment and partition checks.
5. Run `evaluate_refinement.py` once. It evaluates frozen models on fresh test plus the explicitly exposed old regression set; the latter requires the existing source-bound `build/morphology-public-export-v3` receipt. It does not refit or select models.
6. Review metrics and retained regressions, then run `promote_refinement.py` to copy the already-selected artifacts, generate identities/parity and public provenance. It requires the evaluated selection hash and supported runtime dimensions/blend. Run host tests, Kotlin parity, Android integration/latency and repository gates before packaging.

All scripts above except the explicitly qualified morphology exporter are in `tools/typing_experiments/`. Example checks:

```sh
python3 tools/ci/python_tools_tests.py --check
python3 tools/ci/python_tools_tests.py --profile stdlib --output build/python-tools-readme-stdlib
./gradlew :app:testDebugUnitTest :app:lintDebug :app:imeIntelligenceBoundary :app:forbiddenRuntimeDependencies :app:privacyGateRelease
```

Legacy `train.py` now emits only ignored `build/typing-experiments` artifacts and generated fixture proposals. It cannot overwrite the refined APK models or Kotlin source. Legacy tests compare the frozen baseline artifact to its retained CatBoost reference.

## Provenance and license

Public `wikimedia/wikipedia`, snapshot `20231101`, revision `a634f78b1c435397c07001e175fa74cc4ad5e775`; contributors are the original authors. Source metadata declares CC-BY-SA-3.0 and GFDL-1.3; derived weights are distributed under CC-BY-SA-3.0. See the packaged `NOTICE.md` and license. Changes include text extraction, synthetic spelling perturbations, model fitting and numeric export. APK provenance contains aggregate metrics and public hashes only.

## Additional-epoch follow-up

A further twelve epochs were evaluated with dev-only checkpoint selection and a newly reserved article test. The selected +2 checkpoint did not pass the predeclared fresh-improvement/regression gates; bundled models are unchanged. See [experiment results](../../docs/typing-extra-epochs.md) for counts, limitations and reproduction.

## Candidate-level training follow-up

A fixed six-epoch listwise candidate-selection experiment added exact one/two/three-edit public examples and correct-input controls. Dev improved slightly, but the frozen independent test failed promotion gates; bundled models remain unchanged. The main observed limit was missing gold candidates, especially for three-edit examples. See [candidate-training report](../../docs/typing-word-ranking.md) for exact counts, objective, source separation, tests and reproduction.


### Product quality slices

`typing_quality_slices.py` reports word-length, context and unit-edit slices from
labelled corpus rows and the existing final-product Kotlin replay. It validates
row/input identity and actual editor output, separates retrieved candidates from
applied corrections, records control changes, casing-only changes and exact Undo,
and never fits thresholds or emits promotion authority. Prefix formatting follows
the existing replay contract (one separator after a nonempty prefix).

```sh
python3 tools/typing_experiments/typing_quality_slices.py \
  --rows build/run/rows.jsonl \
  --observations build/run/observations.jsonl \
  --output build/run/quality-slices.json
```

The output must be fresh. Revealed regression data remains descriptive; it cannot
be renamed to an independent qualification set. `manualRetrievedTypos` counts a
target in the diagnostic manual pool, not automatic admission or visibility in
the strip. `spellingPrecision` excludes casing-only changes, which remain counted
separately alongside the literal surface-change metrics.

### Joint short-word and conservative long-word autocorrection (2026-10-25)

`ru-joint-ranker.bin` compares the original and the complete public candidate pool using the existing 95 RET2 features and frozen ranking context. Short acquisition, long acquisition and retention have separate thresholds. Retention can only keep the admitted baseline word or retain the original. Sources `JOINT_SHORT` and `JOINT_LONG` require their own dictionary/model/policy fingerprints; missing resources retain the existing qualified paths. Search runs in the existing cancellable candidate worker. No user text is used in training.

Evidence, rejected policies and the explicit abstention tradeoff: [acceptance](../../docs/acceptance/2026-10-25-joint-short-correction.md). Packaged hashes and aggregate results: `app/src/main/assets/smarttyping/experiments/joint-correction-provenance.json`.

The public source files must match the pinned HF revision and LFS hashes in the source lock before building corpora. `prepare_joint_correction.py` freezes lemma-disjoint train/calibration/holdout; `prepare_joint_followup.py` excludes all previous selected families/articles, with `--exclude-corpus` for a revealed follow-up. Never reuse a revealed holdout to choose thresholds. The final follow-up reused the **original** conservative acquisition threshold and the already-frozen retention threshold, with no new fitting. The prior 98.8% acquisition result remains a failure.

Use the same pinned Python/CatBoost/NumPy environment as the existing ranker tools. The JVM replay also requires JDK 17, the locked Kotlin jars and `ANDROID_HOME`:

```sh
python tools/typing_experiments/replay_joint_correction.py \
  --rows build/joint-correction-20261025/corpus/train.jsonl \
  --output build/joint-train-export --mode joint-export
python tools/typing_experiments/replay_joint_correction.py \
  --rows build/joint-correction-20261025/corpus/calibration.jsonl \
  --output build/joint-calibration-export --mode joint-export
python tools/typing_experiments/train_joint_correction.py \
  build/joint-correction-20261025/corpus build/joint-train-export \
  build/joint-calibration-export build/joint-ranker-reproduction
```

`calibrate_joint_source.py` reproduces the initial full-source arbitration. `calibrate_joint_followup.py` fits acquisition and retention on a fresh calibration only. `joint-ready` takes a six/eight-field TSV: ranker path, ranker SHA-256, short score/margin, long acquisition score/margin, optional retention score/margin. This developer mode explicitly admits the candidate source for an evaluation; it does **not** modify release qualification.

To verify the actual packaged qualification and thresholds without a developer override:

```sh
python tools/typing_experiments/replay_joint_correction.py \
  --rows build/joint-correction-20261025/followup-corpus-v3/holdout.jsonl \
  --output build/joint-production-reproduction --mode joint-production
```

`evaluate_joint_product.py` checks actual editor output, controls, prefix ownership and exact Undo. `evaluate_joint_followup.py` additionally requires independent acquisition precision of at least 99%, at least 100 new correct long replacements, and all existing long-product gates. A high precision among retained old corrections cannot mask a failing new-acquisition source. Replay writes untouched primary logs, compiler/runtime commands, source/input/output hashes and process exit codes; expected words and cohort labels never enter Kotlin.

### Separately qualified joint supplemental model

`train_joint_rescue.py --source-root <pinned-joint-inputs> --output <fresh-build-directory>` trains the supplemental RET2 model from four hash-pinned public inputs. Use the documented Python environment with CatBoost 1.2.8 and NumPy 2.2.6. `calibrate_joint_rescue.py --source-root <pinned-joint-inputs> --work-root <fresh-build-directory>` freezes the additional-path policy from calibration only. Both refuse overwriting output. The model, calibration scores, training receipt and frozen policy were reproduced byte for byte before qualification.

Final-product replay mode `joint-primary-only` is the ablation baseline; `joint-production` applies the independently pinned supplemental qualification. `joint-rescue-ready` is a developer evaluation mode, not production authorization. The harness delivers baseline then recovery and separate manual pools for the actual controller token, including automatic capitalization.

## Local authored stress audit

`local_spelling_stress.py` freezes deterministic everyday-word edits and correct-word/name/short-form controls before replay. It does not train or qualify policies. Run `prepare` once into a new output directory:

```sh
python3 tools/typing_experiments/local_spelling_stress.py prepare --output build/local-stress/corpus
```

Pass its label-free `inputs.tsv` to the existing `final_product_replay.run_harness` in `joint-production` mode using a harness compiled from current sources. Keep source/JAR hashes and raw observer output. Expected spelling and edit-family labels remain in `rows.jsonl`, outside the Kotlin product observer. Then report:

```sh
python3 tools/typing_experiments/local_spelling_stress.py report \
  --rows build/local-stress/corpus/rows.jsonl \
  --observations build/local-stress/observations.jsonl \
  --output build/local-stress/report.json
PYTHONPATH=tools/typing_experiments python3 -m unittest test_typing_quality_slices test_local_spelling_stress
```

The report validates observation identity/order, editor change flags and prefix preservation; counts exact Undo failures; separates spelling substitutions from canonical-case changes; and records actual search completion when no admission callback occurred. A missing callback is not a fabricated policy refusal. Synthetic edits that form valid dictionary words are shown separately: a retained word is not automatically a product bug.

The developer replay emits `hostStageNanos` for baseline/recovery/joint/manual retrieval, controller candidate ranking/admission, and the Space boundary. Timers use `System.nanoTime`; observer-only score exports and serialization are excluded. These are sequential desktop JVM samples including warmup and later GC effects, not UI latency, startup timing, isolated model inference, or Android deadline evidence. Manual expansion is enabled by this observer; the user setting still defaults off. See [the local audit](../../docs/acceptance/2026-10-26-local-spelling-stress.md) for measured results and limits.

## Whole-word context feature probes

`word_context_features.py` contains experimental numeric features for public word-pair counts and a decomposition helper for the frozen tree/character scorer. Counts are validated, missing evidence is explicit, and punctuation/identifier suffixes are not erased. It is not connected to product automatic correction. Run `PYTHONPATH=tools/typing_experiments python3 -m unittest test_word_context_features` for its boundary/count tests.

Two locally frozen experiments added word-pair features and then learned the character contribution inside the tree. Both failed automatic-promotion requirements; their new feature counts are not accepted by the current application model codec. See [context-ranking results and paired regressions](../../docs/acceptance/2026-10-26-context-feature-ranking.md) for data separation, source locks, authored controls and the distinction between raw ranking, offline proposals and committed edits.

## Supervised conversational ranking audit

`conversation_split_checks.py` rejects disclosed regression rows and sentence or left-context/target overlap between partitions. Run `PYTHONPATH=tools/typing_experiments python3 -m unittest test_conversation_split_checks` for its normalization, duplicate-context, sentence-identity and iterator tests. This checks prediction-context separation; it does not establish author independence.

A separate experiment directly trained a unified ranker on public conversational candidate groups and preserved prior failures as regression-only fixtures. Its independently frozen follow-on audit produced 466 correct and five incorrect additional proposals (98.94%, below the required 99%); it is rejected for promotion and is not integrated into the application's model decoder. See [the supervised conversation audit](../../docs/acceptance/2026-10-26-supervised-conversation-ranking.md) for source licenses, frozen selection, gains/losses, remaining grammatical-form errors and runtime limitations. Do not reuse the disclosed fixtures as training or independent qualification data.

`conversation_acceptance.py` evaluates an explicit required precision ratio with unchanged minimum volume, correct-word controls, prior-correct retention and net-improvement guards. It does not turn the ratio into a per-word confidence score. Its tests include the 95% boundary and the preceding 466/471 result at both 95% and 99%. The owner-authorized follow-up promotes the disclosed conversational audit to training and reserves new calibration/test contexts; see [the 95% training record](../../docs/acceptance/2026-10-26-conversation-ranking-95.md).

`grammar_context_features.py` adds 38 soft grammatical features through an injected dictionary-only lexicon: candidate part of speech/case/number/person, infinitive constructions, explicit-pronoun agreement, preposition case, adjective agreement and limited verb valency. It preserves ambiguous analyses, normalizes secondary dictionary cases and stops context evidence at punctuation/identifier boundaries. It neither parses a full sentence nor grants automatic correction admission. `PYTHONPATH=tools/typing_experiments python3 -m unittest test_grammar_context_features` tests these boundaries without external dependencies. The training adapter uses the existing hash-pinned `tools/morphology/requirements.lock`; see [the grammar feature comparison](../../docs/acceptance/2026-10-26-grammar-context-ranking.md).


## Compact-source preservation status (2026-10-28 review)

The compact abstaining/augmented ranker, disclosed-error margin refreeze,
rare-word extractor/packer, compact evaluator and both cascade policy revisions
are now versioned with their existing tests. The selected augmented script and
rare-word packer match the exact SHA-256 values in packaged metadata.
See [the scoped source acceptance](../../docs/acceptance/2026-10-28-q2-compact-sources.md).
This establishes source availability and bounded test coverage. Historical
commands still require their pinned data/export receipts; it does not establish
a new training run, independent holdout or model promotion.


## Joint/neighbor source preservation (2026-10-28 review)

Current joint/neighbor source scripts and their eight test modules are versioned.
The joint trainer/calibrator and three preparation snapshots have matching
historical source identities. The frozen neighbor tool is reconstructed with its
exact original SHA-256; its earlier corpus-builder source remains unrecovered. See [the source and gap record](../../docs/acceptance/2026-10-28-q2-joint-neighbor-sources.md).
These historical builders still require their pinned inputs and consumed-data
exclusions; source preservation does not grant fresh qualification or promotion.


## Historical holdout tools retained (2026-10-28 review)

The v6-v12 label-isolated replay tools, v7-v12 preparers and shared helpers are
versioned with their original tests and cross-version source/routing checks.
See [the source acceptance](../../docs/acceptance/2026-10-28-q2-holdout-sources.md).
These already disclosed corpora remain historical regression data. A filename
containing fresh or independent does not establish a fresh qualification set.
Use explicit pinned inputs and an explicit --java path for replay; complete
consumed-data and historical dependency closure remain required.


## Disclosed diagnostics and source fixtures (2026-10-28 review)

The descriptive slice/stress helpers and explicit offline proposal-ratio gate
are versioned with their original tests. Retained 35-row CC0 regressions and five
detailed-source proposal references have [source and exclusion acceptance](../../docs/acceptance/2026-10-28-q2-disclosure-tools.md).
Run `python3 tools/typing_experiments/audit_disclosed_fixtures.py` for tracked-byte
and known-exclusion checks; add `--historical-root .` only when the original
hash-pinned local public source inputs are present. Neither mode scores models
or certifies fresh qualification. The documented five-case training exception
remains scoped to the recorded original corpus.


## README source checks

Run `python3 tools/check_readme_sources.py` for the main and experiment README
local links, literal project paths, Python scripts and named unittest modules.
The [acceptance record](../../docs/acceptance/2026-10-28-q2-readme-sources.md)
distinguishes tracked source paths from generated Gradle artifacts. This check
does not execute training/build commands, follow remote links or prove complete
transitive model/data lineage.
