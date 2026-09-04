# Candidate 03 prepared-candidate holdout

Result: **FAIL**. All 13,200 corpus rows have one identity-bound score record and
`report.json` was emitted before the evaluator returned exit code 2. The frozen
calibration configuration was not changed after holdout scoring began.

EN passes the row gate. RU and ES exceed the maximum 0.5% false-change rate:
RU is 8/1,000 (0.8%) and ES is 7/1,000 (0.7%). Their precision remains above
99%, and each language has more than 300 automatic replacements. The product
candidate pipeline, contextual model scoring and release promotion were not run
for this model after the failure.

`report.md` is retained exactly as emitted. Its `Rune Text 0.1` heading is a
known legacy presentation string and does not identify this run. The exact model
identity is SHA-256 `7a61cd75e672533beba48480f972688baf281f3d0867e11ca63aee5a17228f65`
in `report.json`, `frozen-config.json`, the score-cache header and
`provenance.json`.

The GGUF and native runner are not included. `scores.jsonl.gz` uses deterministic
gzip metadata and expands to the cache digest recorded in `provenance.json`.
