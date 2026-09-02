# Rune Smart Typing 0.3 — PR1 acceptance, 2026-09-02

Scope: offline prepared-candidate task suitability for Rune Text 0.1. This
slice adds no composing, correction, punctuation or inference-service behavior
to the application. App version remains 0.2.0. **PR1 suitability gate failed;
the ordered implementation sequence stops here before model-dependent PR2.**
This is completion of the first evaluation slice, not implementation or release
of all Rune Smart Typing 0.3 features.

## Revision and artifact

- Baseline: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`, clean `main` at start.
- Local branch: `feature/smart-typing-03-pr01`; no push or remote PR.
- Native reference commit: `a2110629989fd66c335072c677c8235b6b235d15`.
- Corpus/evaluator commit: `d59d14fa3e608b675bb1c34e8ba13d8a0f5e4979`.
- Model-free CI integration commit: `33c12e1`.
- Upstream llama.cpp: `36b10154383b60eb15baac2c7a40d2a5f784faa7`, clean,
  unchanged gitlink; no tokenizer patch in PR1.
- Model source: Actions artifact `9800688354`, run `33508047561`.
- Verified **inner GGUF**, not its ZIP: 396704416 bytes;
  SHA-256 `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`;
  GGUF v3, qwen3, Q4_K_M (file_type 15), 310 tensors, 28 metadata entries.
- The public `model-rune-text-v0.1.0` release was absent at baseline verification.
  The Actions artifact is qualification input, not a published immutable model.

## Reference implementation

The C++ core performs serial teacher forcing over full `prefix + continuation`
tokenizations, scoring only divergent tokens after their shared token prefix.
It returns raw log-probability sums and counts, clears KV between alternatives,
never appends EOS, never generates text, and abstains when usable conditioning
or divergent tokens are absent. The developer-only JSONL adapter is not linked
into the Android application. Python verifies the exact model before starting it.

The CPU reference uses context 256, logical batch 64, microbatch 1, four threads,
zero GPU layers and disabled flash attention. An independent scalar oracle
exposed microbatch-64 sum differences up to 0.5247. Fresh contexts and disabling
flash attention alone did not remove them. With microbatch 1, all 15 candidate
comparisons matched exactly (maximum absolute sum delta 0), including a batch
boundary and a completely masked first batch. Exact 192/64/256 token-limit
acceptance and overflow rejection were checked separately; the 256-token case
is not itself a scalar-oracle comparison.

Before/after-tokenization and decode cancellation exist. **Cancellation inside
tokenizer is not implemented or qualified by PR1.** It remains conditional PR2.
These host measurements do not establish Android/Fold latency or memory use.

## Corpus and freeze discipline

The synthetic corpus has 13,200 rows: each RU/EN/ES split has 1,000 typo,
1,000 correct/protected and 200 punctuation probes. Original is always candidate
0. Word families and templates are assigned to separate splits before error
generation. All spelling candidates obey the bounded edit neighborhood.

Rows are clustered around authored word families and context templates;
700 correct-word rows per language/split perturb 100 lexical contexts. The
reported Wilson intervals describe row counts and do not provide independent
natural-typing confidence guarantees. Prepared-candidate recall is an oracle
containment check; it does not qualify the future lexicon/candidate generator.
Protected-token abstention uses authored policy annotations, not a product
detector. Punctuation is suggestion-only and its unambiguous metric covers
initial subordinate-clause comma placement.

Pre-holdout review found missing explicit accent/yo ambiguity alternatives in
corpus version 1. Its partial calibration was stopped and discarded from
qualification. It was retained locally for audit. No holdout was scored, no
configuration was frozen, and model scores were not used to choose the repair.
Version 2 is fixed at canonical SHA-256
`2b3874adabbb60370360087f208d6e9cf2ef308e4955af57114ef2a687c7fd96`.
All 6,600 calibration responses were completed before freezing configuration
`cc5cf738022b02cf6843f10677e7a2f2d0634abd42427756a23ad2a90bd5928c`.
All 6,600 holdout responses were then completed without changing thresholds,
candidate sets, ranking or labels. Both P2 review findings are addressed;
whole-branch code review found no remaining consequential issue.

## Quality decision

**FAIL for RU, EN and ES.** Required per-language holdout thresholds are at
least 300 automatic replacements, precision >=99%, and correct/protected
false-change <=0.5%. Thresholds were not retuned after holdout inspection.

| Language | AutoReplace | Correct / auto | Precision | Correct/protected false change | Correct typo coverage | Gate failure |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| RU | 172 | 162/172 | 94.19% | 5/1000 = 0.50% | 162/1000 = 16.20% | Count and precision |
| EN | 7 | 7/7 | 100.00% | 0/1000 = 0.00% | 7/1000 = 0.70% | Count |
| ES | 243 | 239/243 | 98.35% | 3/1000 = 0.30% | 239/1000 = 23.90% | Count and precision |

The 100% EN precision is seven observations, with a descriptive Wilson 95%
interval of 64.57–100%; it is not a useful automatic-correction qualification.
RU and ES precision intervals are 89.63–96.81% and 95.84–99.36% respectively.
All languages meet the stipulated combined false-change point threshold;
RU correct-only false change is separately reported as 5/700 = 0.71%.

Holdout spelling abstention is RU 91.40%, EN 99.65%, ES 87.85%. Prepared
candidate containment is 1000/1000 per language by construction. Unambiguous
punctuation suggestion top-1 is RU 59/100, EN 100/100, ES 50/100; another 100
ambiguous punctuation rows per language are excluded from single-answer
accuracy. Punctuation is never automatically applied by this harness.

All **13,200 responses are present**, with zero runtime errors and zero missing
scores. The holdout has 36/33/33 zero-span abstentions for RU/EN/ES; they remain
in the denominators. The report command exited **2**, its documented quality
failure result, after both scoring processes exited successfully.

The complete [machine report](../../tools/eval/smart-typing-0.3/results/2026-09-02/suitability.json),
[readable report](../../tools/eval/smart-typing-0.3/results/2026-09-02/suitability.md),
numeric cache, immutable config and provenance are checked in under
`tools/eval/smart-typing-0.3/results/2026-09-02/`. They include exact counts,
coverage, abstention, candidate containment, per-cohort false changes, all
Wilson intervals, raw top-1, family counts and false-positive sample IDs.
An independent [quality review](../../tools/eval/smart-typing-0.3/results/2026-09-02/quality-review.md)
verified the identities, complete response order, calibration-only freeze,
report regeneration and a separate raw-score calculation. No findings remain.
The documented offline reproduction command was executed and both generated
report files compared byte for byte with the archive successfully.

## Stop decision and remaining slices

No unrestricted generation, tokenizer/JNI scoring extension, inference service
or model-assisted IME feature is introduced after this failed gate. PR2–PR10
have not been implemented. Composing, candidate strip/Undo, lexicons and
mechanical punctuation can be developed independently, but are not claimed
complete by this PR1 report. The previously identified NO_PERSONALIZED_LEARNING
capitalization/double-space issue belongs to the pending PR4 slice and remains
open; this evaluation makes no new product privacy claim.

A separate fine-tuning milestone should first define independently reviewed,
licensed multilingual ranking examples and a new untouched holdout, preserving
word-family/context separation. Train/compare the constrained ranking task,
freeze calibration again, and repeat all quality gates on the exact quantized
digest. These results must not be used to retune thresholds on this holdout.
Production candidate-generation quality, tokenizer cancellation, Android/Fold
performance and immutable artifact qualification remain separate requirements.
No fine-tuning, model publication or additional model-dependent work was started.

## Gates

| Gate | Status | Evidence / limitation |
| --- | --- | --- |
| Baseline JVM | PASS | 222/222, no failures/errors/skips |
| Post-commit JVM | PASS | Fresh `testDebugUnitTest --rerun-tasks` after all three code/CI commits: 222/222 each |
| Lint/build/privacy/dependency/native | PASS | Full prescribed Gradle command, 232 tasks, 23 executed |
| Native unit test | PASS | CTest 1/1: math, UTF-8 and request bounds |
| Exact-model scalar oracle | PASS | 15 comparisons, max sum delta 0; additional cancellation-reset and bounds assertions |
| Python/corpus final checks | PASS | 24 tests, full 13,200-row validation; repeated generation byte-identical |
| Model-free CI commands on host | PASS | SDK CMake 3.31.6, native build and CTest 1/1; GitHub/Linux job not run |
| Prepared-candidate quality | FAIL | Complete v2 run; all three languages fail the agreed row gate |
| Deterministic pipeline quality | NOT RUN | Product generator/ranker not implemented in PR1 |
| Model-assisted product pipeline | NOT RUN | IME not connected in PR1 |
| API 26 baseline CI | PASS | Exact baseline run 33579534128 |
| API 37 baseline CI | PASS | Exact baseline run 33579534128 |
| API 26 / API 37 new-feature CI | BLOCKED | No new-feature code or authorized remote PR/push |
| Physical Fold / performance | BLOCKED | Not measured in this slice |
| Immutable model publication | BLOCKED | Missing release; requires exact-digest Fold qualification |
| Version 0.3 release | BLOCKED | Quality failed; product integration, device and publication gates incomplete |

Baseline CI: <https://github.com/Mesteriis/rune.keyboard/actions/runs/33579534128>.
Local test logs and the full model remain under ignored `build/smart-typing-0.3/`.
Reproduction commands and corpus limitations are in
`tools/eval/smart-typing-0.3/README.md` and `NATIVE.md`.
