# Grammatical-context feature comparison

> Historical report retained from its original date. Its measurements and
> qualification claims apply to the original recorded inputs and implementation.
> Current source-presence checks are in [the README source audit](2026-10-28-q2-readme-sources.md);
> they do not establish fresh model, device or complete Q6 acceptance.

The owner requested adding grammatical evidence and retraining after the preceding model passed a 95% proposal-precision requirement but retained five grammatical-form errors. This experiment changes the input representation while preserving the exact 19,802 selected training groups, 227,616 candidate rows, seed and tree hyperparameters of the 108-feature reference.

## Features

`tools/typing_experiments/grammar_context_features.py` appends 38 features, yielding 146 total:

- Dictionary availability/ambiguity and candidate part of speech, case, number and person.
- Soft infinitive cues from impersonal/modal constructions, crossing at most a few selected particles/adverbs/dative pronouns: for example `надо научиться`, `начал немного злиться`, `не могу тебе заплатить`.
- Agreement/conflict with explicit personal pronouns for finite verbs and short predicates.
- Preposition cases, adjective–noun case/number/gender agreement and a limited soft accusative-object valency cue.

The feature extractor accepts only preceding text, original and candidate; no expected target, future right context, corpus identity or source contributor is an input. Context is bounded to 128 characters and eight final Russian words, with punctuation and identifier boundaries retained. Ambiguous dictionary analyses remain alternatives: a supported case is not simultaneously flagged as conflict because another reading exists. OpenCorpora secondary case tags are normalized to their case family. Unknown-word guesses are excluded by the reused dictionary-only adapter. These are learning features, not admission overrides or hard grammar rules.

The pinned dependencies are the existing `tools/morphology/requirements.lock`: pymorphy3 2.0.6, pymorphy3-dicts-ru 2.4.417150.4580142 and dawg2-python 0.9.0. Installed package/dictionary file hashes are preserved in `morphology-receipt.json`. Code/data attribution remains as documented in [dictionary provenance](../../tools/morphology/README.md); linguistic data is OpenCorpora CC BY-SA 3.0. This run adds no Android dependency or packaged dictionary derivative.

## Frozen comparison and separation

The training group IDs and order must match the preceding 108-feature model exactly. This includes the previously authorized promotion of the original 4,000 conversational audit contexts (and the five errors) to training, without extra oversampling. The older 35 regression cases remain excluded. Public conversational text source/attribution remains the preceding experiment's [Tatoeba CC BY 2.0 FR record](2026-10-26-conversation-ranking-95.md).

New selection reserves 3,000 calibration contexts / 12,000 rows and 3,000 holdout contexts / 12,000 rows, with 1,423 and 1,442 target families respectively. Family sets are disjoint between evaluation partitions. Previous training, disclosed evaluations (including both 95% partitions), original CC0 sentences and prediction contexts are excluded before selection. The current Kotlin replay receives typed input/prefix with no target labels. Corpus manifests are frozen before fitting or scoring.

An implementation review before any new evaluation scores found missing normalization of secondary case tags. The initial model and receipts are retained with `initial-before-case-alias-` names. The corrected model uses the same selected training/evaluation rows and hyperparameters. Plan/manifest revisions explicitly record this pre-evaluation correction; no evaluation results selected between models.

The reference 108-feature model and its existing score/margin point are frozen. The grammatical model selects its score/margin point on the new calibration set only, at required precision 95%, minimum 100 newly correct, zero correct-word changes/prior-correct losses and positive net correct. Its point is frozen before scoring the new holdout. A comparison gate additionally requires net correct at least as high as the frozen 108-feature reference on the same holdout. There is no retuning against holdout or the five disclosed errors.

## Results

Final model SHA-256: `4d7bf2a9477b588046a1187c11e206bd1ca6f73180e8abf3b21c84f024a783f0`.

Calibration selected minimum score `-0.10238100540254857` and margin `0.038424043936311734`: 605 correct / 14 wrong additional proposals (97.74%). No control changes or prior-correct losses occurred. These thresholds were frozen unchanged before holdout evaluation.

On the same new 3,000-context / 12,000-row holdout:

| Frozen pipeline | Additional correct | Additional wrong | Proposal precision |
| --- | ---: | ---: | ---: |
| Previous 108-feature model / previous frozen policy | 570 | 8 | 98.62% |
| New 146-feature model / newly frozen calibration policy | **585** | **6** | **98.98%** |

Both preserved all prior-correct edits and correct-word controls in this replay. The new pipeline passes the required 95% gate, minimum volume and comparison gate, adding 15 more correct and two fewer incorrect proposals than the frozen reference on this holdout. These are offline proposals, not observed phone edits. The proposal comparison includes recalibration of the new model; it does not isolate the feature change from the policy change.

For raw ranking, where score/margin thresholds play no role, the old and new models picked the expected first candidate in 5,319 and 5,356 of 5,564 eligible pools. Paired changes were 62 wrong→right and 25 right→wrong, net +37. The current packaged scorer had 4,728 expected first choices. Missing/incomplete pools remain outside this ranking denominator; all 12,000 observer rows completed.

The 35 excluded, disclosed regressions recovered 30 expected first choices, with five raw errors remaining, zero wrong proposals at the frozen point and zero prior-correct losses. These are regression checks, not independent qualification.

### The five training errors remain unresolved

None of the five known targets becomes the first candidate or a correct proposal. The competing proposals remain `фотографией`, `злишься`, `научишься`, `заплатишь`, `виновен`. All intended targets are present in their pools. The new infinitive cue correctly distinguishes the intended and finite forms in the three verb cases, and the accusative cue supports `фотографию`. The available bounded context provides neither subject-predicate agreement nor a decisive grammatical cue for `виновны`.

Their incorrect-winner margins changed from approximately .208→.175, .193→.168, .177→.149, .193→.063 and .098→.092 respectively. Reduced margins are not successful corrections. The learned trees contain 101 splits on 16 distinct new grammar features, so the new inputs are used; that does not establish sufficient learning for the five cases. No further model, feature or threshold changes were selected after these scores.

## Verification and runtime limits

- `PYTHONPATH=tools/typing_experiments build/typing-ranker-v2-venv/bin/python -m unittest test_grammar_context_features test_conversation_acceptance test_conversation_split_checks test_word_context_features test_typing_quality_slices test_local_spelling_stress -v`: **33 passed**, exit 0.
- `PYTHONPATH=tools/morphology build/typing-ranker-v2-venv/bin/python -m unittest test_ranker -v`: **18 passed**, exit 0. Total **51 tests**.
- Seven actual pinned-dictionary construction checks passed, including the secondary locative case.
- The final verifier checked source/model/policy/package/code hashes; exact training-ID/order equality; sentence ID, normalized sentence hash, prediction-context and evaluation-family separation; and complete identity/exact baseline text restoration for 12,000 rows in both modes in each evaluation partition.
- Vectorized character-component parity passed on 32 candidates per evaluated partition. Binary model export matched CatBoost JSON inference on 64 actual 146-feature vectors: maximum raw-score error `1.7829318466056066e-08` (required below `1e-5`).
- Preparation, both training implementations, observer replay, evaluation, regression scoring, export parity and final verification exited 0. `git diff --check` passed.

All scripts, pinned dependency log/receipts, retained initial model, frozen plans/data, per-case outcomes and completion receipt remain under ignored `build/grammar-context-ranking-20261026/` (root mode 0700). No Android build/installation or physical-device testing occurred. Packaged model assets, existing admission/Undo/controller behavior and runtime thresholds are unchanged. The 146-feature model is offline and has not been integrated into the current 95-feature application decoder; this candidate qualification is not product runtime qualification.
