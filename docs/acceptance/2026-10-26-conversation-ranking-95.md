# Conversational ranking with a 95% proposal-precision requirement

> Historical experiment report from 2026-10-26. Measurements and separation
> claims below belong to its original inputs and implementation. Current source
> and exclusion checks are recorded in [the fixture audit](2026-10-28-q2-disclosure-tools.md);
> they do not establish fresh qualification or complete Q6 lineage.

The owner explicitly requested lowering required precision to 95% and learning from the disclosed context. This changes the offline candidate-proposal acceptance criterion, not a model probability or a blanket runtime admission rule. Minimum 100 newly correct proposals, zero correct-word control changes, zero prior-correct losses and positive net correct remain required.

## Training and data role change

The earlier follow-on audit's 4,000 contexts / 16,000 rows are now training material. Its 7,314 complete eligible joint candidate groups are appended once to the previously frozen training mix, including all five incorrect proposals; the five failures receive no special oversampling. The resulting model trains on 19,802 groups / 227,616 candidate rows. Architecture and hyperparameters are unchanged: 108 features, 128 trees, depth 5, learning rate .05, seed 25102026. Frozen count/character models are unchanged.

This is an explicit data-role promotion authorized by the owner, superseding the five cases' previous regression-only designation for this run. The previous receipts are preserved. Its 466 correct / five wrong result would meet the revised 95% ratio, but cannot independently qualify a model trained on those rows. The 35 older regression cases remain excluded from training.

The promoted public text comes from Tatoeba's Russian detailed export under [CC BY 2.0 FR](https://tatoeba.org/en/downloads). Local `promoted-attribution.json` retains sentence IDs, contributor names, source links, license and adaptation description. Synthetic corruptions and preference labels are adaptations. No text, counts or newly trained weights from this experiment have been packaged in an APK.

## New evaluation design

Before fitting, the plan and selection reserve 3,000 new calibration contexts / 12,000 rows and 3,000 new holdout contexts / 12,000 rows. Calibration and holdout contain 1,429 and 1,449 distinct target families respectively, with no target-family overlap. Source sentences and left-context/target combinations from all previous evaluations and training are excluded, as are the entire original CC0 sentence set and duplicate normalized sentences. One target per sentence, up to four contexts per family, is selected without model scores.

This remains synthetic corruption of public conversational sentences. Related authors/templates may cross collections; this is neither author-independent validation nor phone-typing evidence.

The score/margin grid and 95% gate are frozen before calibration. Thresholds selected only on calibration are frozen before the holdout is scored. The existing Kotlin replay receives typed input and prefix with no expected labels. Expected words are used offline only. A separately tested gate compares unrounded correct/total proposal counts and preserves the other acceptance guards.

## Results

Model SHA-256: `f9aee2be9aa903af6c53d623d0c62409e5aca36ecb7c9bf49f528c2925053d73`.

Calibration selected minimum score `0.08321242798245636` and margin `0.034241327233921065`: 597 correct / 10 incorrect additional proposals (98.35%), with zero control changes/prior-correct losses. Those thresholds were then frozen unchanged.

The independent new holdout produced **498 correct / 11 incorrect additional proposals (97.84%)**, passing the owner-approved 95% gate. Control changes and prior-correct losses were zero; net correct increased by 498. There were 5,472 eligible joint pools among 12,000 input rows. Raw first-choice ranking improved 4,674 → 5,227, comprising 632 wrong→right and 79 right→wrong changes. Those raw ranking losses are not committed incorrect replacements. The 11 wrong proposals are offline proposals, not observed physical-phone edits.

The earlier 35 regressions, which were still excluded from fitting, recovered 30 expected raw winners (previous experiment: 20). Five raw errors remain; the new frozen point made zero wrong proposals and lost zero prior-correct edits on those 35. They are disclosed regression checks, not independent qualification.

### Five promoted training errors

All five targets remain incorrectly ranked and proposed despite being present in training once:

| Typed | Proposed | Intended |
| --- | --- | --- |
| фотографие | фотографией | фотографию |
| злищься | злишься | злиться |
| научищься | научишься | научиться |
| заплатищь | заплатишь | заплатить |
| виновн | виновен | виновны |

Training on the examples did not establish that the model learned their grammatical distinctions. The frozen architecture still confuses case, number and infinitive/finite forms. Passing the aggregate 95% criterion must not be described as fixing these five errors. These training diagnostics were computed after the new holdout result and did not alter weights or thresholds.

## Validation and limits

- `PYTHONPATH=tools/typing_experiments python3 -m unittest test_conversation_acceptance test_conversation_split_checks test_word_context_features test_typing_quality_slices test_local_spelling_stress -v`: **27 tests passed**, exit 0.
- Preparation, training, Kotlin observer replay, evaluation and final verification each exited 0. The final verifier checked 136 hash bindings and separation of all 19,802 selected training groups from the new calibration/holdout.
- Each new evaluation partition had 12,000 complete, identity-checked observations in each of two observer modes, with exact baseline text restoration. The vectorized scorer verified 32 frozen character-component values per partition against direct inference.
- `git diff --check`: passed.
- No Android build, installation or physical phone acceptance was performed. The new 108-feature model is still offline; the application's existing 95-feature decoder has not been extended. Existing packaged models and runtime policy were unchanged. The 95% setting is recorded in this experiment's acceptance policy, not silently substituted into an unrelated product confidence constant.

Raw source text and all scripts, source attribution, frozen plan, selected groups, model/policy hashes, observations and per-case outcomes are retained under ignored `build/conversation-supervised95-20261026/`; its root is mode 0700. `completion-receipt.json` records the completed run. The prior rejected 99% experiment remains intact.
