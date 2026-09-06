# Short-frequency changed-policy evaluator preparation

2026-09-06. Preparation only against production HEAD `909145f`; no production edits, corpus export, corpus row inspection, native model execution, Gradle, device work or commits. Root retains ownership of unrelated physicalFold test work.

## Source handoff

Added `tools/eval/smart-typing-0.3/pipeline/short_policy_evaluation.py` and `test_short_policy_evaluation.py`. The adapter imports a private module instance of the existing evaluator; original `final_product_replay.py` remains byte unchanged (`88d72471eb76384ce7cd063e311b49d1394ea7588cace3381f58d3cc9beea745`). It reuses export, scoring, cache validation, full request delivery, source binding, metrics and integer gates. A small split-specific replay/report function is necessary because the old report function requires both caches and merges reporting with replay. No runtime source rewriting.

The exact frozen buildcopy generator is `build/smart-typing-0.3/retrieval-probe-20260906/short-frequency-01/sources/app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/CandidateGenerator.kt`, SHA `8799e9068983c5796518be0335bf5333e07930975aa13442e19ed28b6ce378a2`. The production original is pinned to `61eb889e1d327f9933e4c189227c93baf2f89b4f08bad41db538d9bfdf354370`; the exact patch is pinned to `f1d97cbbf169a2a3ebcefda85b4f5d811b8c0715ba17175598bf51aac9b9920f`. Only that generator path is substituted in the original 41-source controller closure. The original and variant, patch, base evaluator and adapter bytes enter every protocol receipt; these files also enter the original source binding and therefore the source freeze and request cache identity.

Experiment identity is `revealed-data-short-frequency-candidate-policy-acceptance-v1`, with `policyChanged: true`, unchanged coefficients/no threshold fitting, width three and 8192/64 controls. CURRENT admission is explicitly hypothetical for this experiment. Receipts deny production promotion; reports deny unseen qualification. The old unchanged-policy-freeze receipt is replaced, not reused as a new-policy claim.

## Stage contract

1. `export`: original complete 12000-row controller export, exact source closure substitution, no model calls.
2. `score-calibration`: fresh complete native request scoring using the original strict scorer and identities.
3. `calibration-report`: ready and unavailable controller replay, complete 6000-row split, original precision/false-change/volume/Original/Undo metrics. No holdout scoring, replay or metric computation. The exported row file is filtered by split before evaluation; the original export binds both splits.
4. `freeze-policy`: requires and binds the calibration report, evidence/delivery/replay artifacts and complete calibration cache. It freezes unchanged coefficients for this changed candidate policy. Calibration stages reject pre-existing policy freeze or holdout score directories.
5. `score-holdout`: original scorer first validates the changed-policy freeze, including calibration report provenance.
6. `replay-report`: holdout-only ready and unavailable replay/report with all 6000 rows; calibration evidence remains separate and bound. Reports preserve all abstentions and errors in full denominators.

Suggested execution after root review (not run):

```sh
python3 tools/eval/smart-typing-0.3/pipeline/short_policy_evaluation.py export --root build/smart-typing-0.3/short-policy-evaluation-20260906
python3 tools/eval/smart-typing-0.3/pipeline/short_policy_evaluation.py score-calibration --root build/smart-typing-0.3/short-policy-evaluation-20260906
python3 tools/eval/smart-typing-0.3/pipeline/short_policy_evaluation.py calibration-report --root build/smart-typing-0.3/short-policy-evaluation-20260906
python3 tools/eval/smart-typing-0.3/pipeline/short_policy_evaluation.py freeze-policy --root build/smart-typing-0.3/short-policy-evaluation-20260906
python3 tools/eval/smart-typing-0.3/pipeline/short_policy_evaluation.py score-holdout --root build/smart-typing-0.3/short-policy-evaluation-20260906
python3 tools/eval/smart-typing-0.3/pipeline/short_policy_evaluation.py replay-report --root build/smart-typing-0.3/short-policy-evaluation-20260906
```

Root must review calibration before deliberately invoking freeze/holdout. The wrapper prevents out-of-order execution but does not manufacture a scientific policy-selection decision. Actual controller execution and strict Kotlin request-admission checks remain to be validated after export. Changed-subset comparison and the five known-loss outcomes are intentionally a separate source-bound post-evaluation join owned by root; this adapter does not claim that reporting is complete.

## Verification performed

```sh
python3 -m unittest discover -s tools/eval/smart-typing-0.3/pipeline -p 'test_short_policy_evaluation.py' -v
python3 -m unittest discover -s tools/eval/smart-typing-0.3/pipeline -p 'test_final_product_replay.py' -v
```

New suite: 9 passed. Original suite: 12 passed, 1 opt-in Kotlin export/admission fixture skipped because no actual export is authorized yet. New fixtures reject variant/original/patch/base-source drift, missing/duplicate generator closure, source/request/payload/config cache mismatches, missing/duplicate/reordered scores, missing calibration report, calibration after freeze/holdout, report/adapter/artifact drift and incomplete split denominators.

Compile-only used `compile_inputs` then `base.compile_harness`, with Homebrew Java 17 and the original pinned Kotlin jar/Android stub lookup; no Gradle invocation. Exact argv, all 41 source hashes, jar identity, compiler output and final-adapter re-verification are retained under `build/smart-typing-0.3/short-policy-evaluation-preparation-20260906/`. `compile-receipt.json` records the exact command and the then-current adapter bytes. A later receipt `final-adapter-reverification.json` binds final adapter bytes and rechecks the unchanged compiled source closure and jar. Compilation succeeded; jar SHA `aecc98ac28d80519cbf765415edddb03c32ca975f235c2442992936f7e8c5507`. No compilation failure occurred.

Final adapter SHA `e7b0554ccbb64da1f0a65af16287ce0411dada9af4467ec31d2e7c9ab28379dd`; fixture SHA `803878b8125b75b795a13430f44f120c25b4c079e0647f76225bd703b70c33b4`. Preparation does not qualify the policy or complete physical/release gates.

## Review correction before any export/scoring

The initial calibration-report admission checked declared hashes but accepted an incomplete artifact inventory. Root review identified this as insufficient proof of controller evaluation. Admission now requires exactly seven delivery/replay/log/evidence artifacts, both ordered complete 6000-row ready/unavailable outputs, re-derived row evidence and summaries/gates, and delivery files recomputed from the admitted exact calibration cache. No holdout outputs or metrics are involved.

The same adapter unittest command now passes 10 tests, including missing/empty inventory, false completeness, removed ready/unavailable rows, changed summary, changed evidence and artifact drift negatives. The dedicated admission fixture mocks evaluation internals to exercise validation paths; the unchanged base suite separately verifies actual metric calculations.

Final reviewed adapter SHA `e0dddb9b67e76beba3aa203202d74c8baf8cfb940621d342862dc9ff475cdd36`; fixture SHA `1a675630ed9f4548e4f2de1840b7de992d825596e96aaa39b25cee2fec071be0`. These supersede the earlier preparation hashes. `review-fix-adapter-reverification.json` binds these adapter bytes to the unchanged 41-source compilation and jar; Kotlin did not change, so no redundant compilation was run.
