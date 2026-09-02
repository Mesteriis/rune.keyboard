# PR1 archived quality-evidence review — 2026-09-02

Scope: the completed evidence under `tools/eval/smart-typing-0.3/results/2026-09-02/`, checked against the corpus, frozen evaluator/native sources and the existing local model/runner. This supplements `final-review.md`; it closes that review's pending quality-report verification. No model execution, corpus/config/threshold edit, alternative threshold search, full test rerun or commit was performed. This review report is the only repository file written by this follow-up.

## Decision

**The prepared-candidate suitability gate legitimately FAILS. No new report-integrity or numerical-denominator finding was established. Model-dependent implementation must stop under the agreed PR1 rule.** No language meets the 300 automatic-replacement minimum; Russian and Spanish also fail the 99% precision requirement. English's 7/7 does not establish adequate coverage or pass the gate.

| Holdout language | Correct / automatic replacements | Precision | False changes / correct-and-protected rows | Zero-span abstentions | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| RU | 162 / 172 | 94.1860% | 5 / 1000 = 0.5% | 36 | FAIL: count and precision |
| EN | 7 / 7 | 100% | 0 / 1000 = 0% | 33 | FAIL: count |
| ES | 239 / 243 | 98.3539% | 3 / 1000 = 0.3% | 33 | FAIL: count and precision |

Every language/split has 2,200 responses: 1,000 typo, 1,000 correct/protected and 200 punctuation rows. Spelling abstention uses 2,000 rows: holdout RU 1828/2000, EN 1993/2000 and ES 1757/2000. Zero-span counts above cover the whole language/split and are deliberately rejected by ranking; they are not missing responses or runtime errors. All six language/split panels have zero runtime errors and zero missing responses. Russian correct-only false change is separately exposed as 5/700, rather than hidden behind the combined gate denominator.

## Independently verified evidence

- All **eight** files named by the archive manifest match their SHA-256 values. The score-cache file hash is `83c0d412804701d105bd14c73c894a7cb1ddf6eab6f5b930511d5bed464a2c02`.
- All **six** native source hashes match `reference-provenance.json`. Evaluator and generator hashes also match it, and those two files have no diff from corpus/evaluator commit `d59d14fa3e608b675bb1c34e8ba13d8a0f5e4979`.
- The loaded corpus hash is `2b3874adabbb60370360087f208d6e9cf2ef308e4955af57114ef2a687c7fd96`, matching the cache and provenance.
- Independently rehashed the existing local runner: `f28ddb5658561bc41b1fd84188c0ed11c77d5f5ec8f415b411824c72b69c9cc4`. This matches the cache, calibration and provenance. It was not executed.
- Independently rechecked the existing inner GGUF: **396704416 bytes**, SHA-256 `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`. This matches the evaluator's required artifact, cache, calibration and provenance. No model is included in the archive.
- Parsed and validated all **13,200 unique responses** against the corpus and numerical protocol, with no unknown/duplicate IDs or missing responses. Cache order contains exactly **6,600 calibration records followed by 6,600 holdout records**.
- Recomputed calibration using the unchanged evaluator and archived numerical evidence. The result exactly equals `calibration.json`, including frozen configuration hash `cc5cf738022b02cf6843f10677e7a2f2d0634abd42427756a23ad2a90bd5928c`. Thresholds are RU `(margin=2, confidence=.95)`, EN `(8, .99)`, ES `(4, .95)`.
- Recomputed the report in memory. Its JSON object exactly equals archived `suitability.json`; the Markdown string is byte-equivalent to archived `suitability.md`. `allScoresPresent=true`, `preparedCandidateRowGatePass=false`, `productionQualified=false`. By the inspected CLI's exit mapping, this result yields exit **2**, not an integrity/execution failure. Historical scoring exit codes were integrator-observed, not re-executed by this review.
- Independently tallied automatic decisions from raw score means, rank margins, softmax confidence and policy flags without calling `features()`, `automatic()` or `language_metrics()`. This second calculation reproduces automatic/correct/false-change counts, abstention denominators, zero-span counts and gate decisions for all six panels. The summary table above uses those independently matched holdout counts.

## Freeze discipline and remaining limits

There is no evidence of threshold retuning: the archived thresholds exactly match the fixed calibration-only selection rule in the unchanged committed evaluator, and calibration records precede holdout records. This review did not search alternative configurations or use holdout failures to propose a data/threshold repair. The archive establishes reproducibility of the recorded calculations; it is not a separately authenticated wall-clock execution audit.

The existing limitations remain explicit: clustered synthetic stress rows, prepared oracle candidates, authored protection labels and descriptive row-level Wilson intervals do not qualify a production typing pipeline. These limitations cannot turn the measured FAIL into a PASS. Fine-tuning, changed data or changed model qualification would require a separate milestone/evaluation, rather than continuing model-dependent PR2–PR10 under this failed baseline.

Remote branch CI, product pipeline behavior, physical Fold/performance and immutable model publication remain separate unverified gates. Their prior statuses are not upgraded by this report. No additional evidence risk blocks accepting this result as a reproducible PR1 suitability failure.
