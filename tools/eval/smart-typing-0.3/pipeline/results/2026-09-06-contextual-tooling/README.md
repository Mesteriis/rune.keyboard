# Contextual evaluator v2 verification — 2026-09-06

The evaluator now uses the production total-log-probability policy: Original
advantage greater than 0.5 and rival advantage at least 4.0. It preserves explicit
suggestions and rejects malformed numeric contracts. The host probe calls the
actual Kotlin policy; 79 fixed synthetic cases matched. All 51 Python pipeline
tests passed. Prescribed lint/build/privacy/dependency/native-symbol gates passed
(236 tasks). Independent source review found no outstanding findings.

Version 2 receipts bind the rule, parameters, production/evaluator sources,
toolchain verification, corpus/export, model and runner. Old version 1 receipts
are rejected. If a run receipt is absent, existing score or completion artifacts
are refused before receipt creation or scorer entry. Six orphan-cache regressions
failed before the admission guard; exact-v2 resume preserves existing bytes.

`results.json` records source identities and archive hashes. `parity-*` files are
copies of the actual verification inputs/outputs and receipt, whose commands refer
to the original local build directory. The compiled host jar is not distributed
here. Reproduce with `contextual_quality.py verify-policy --output NEW_BUILD_DIR
--java JAVA_17 --gradle-cache GRADLE_CACHE`, then run Python unittest discovery
for `tools/eval/smart-typing-0.3/pipeline`.

These are tooling and arithmetic checks. No real-model scoring, fresh corpus
freeze or held-out quality qualification was performed in this slice.
