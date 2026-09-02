# Rune Text 0.1 suitability evidence — 2026-09-02

**FAIL. Stop model-dependent development under the agreed PR1 gate.**
This is a synthetic prepared-candidate result, not a release or product quality
qualification. See `suitability.md` for all metrics and limitations.

`scores.jsonl` contains the full 13,200 numerical responses and an identity
header. It contains no input text, generated text, private editor data or model
weights. `calibration.json` was frozen after all calibration responses and
before the first holdout request. `manifest.json` binds these evidence files;
`reference-provenance.json` records the exact GGUF, source and runner identities,
toolchain and reference settings. `verification.json` records the completed
local code gates and separates baseline CI from unrun external/device gates.

Recompute the full report from the repository root without a model:

```sh
python3 tools/eval/smart-typing-0.3/evaluate.py report \
  --cache tools/eval/smart-typing-0.3/results/2026-09-02/scores.jsonl \
  --config tools/eval/smart-typing-0.3/results/2026-09-02/calibration.json \
  --out build/smart-typing-0.3/reproduced-report.json
```

Expected exit code is **2**, indicating the measured quality-gate failure.
Exit 1 indicates an integrity or execution error. Recomputed JSON and Markdown
must equal `suitability.json` and `suitability.md` byte for byte. The command
recomputes calibration from calibration-only evidence and verifies the freeze.

The source corpus/manifest are version 2. A partial version-1 calibration was
superseded before any holdout scoring because review found missing authored
accent/yo ambiguity contrasts; its model scores were not consulted to repair
the corpus. This archive contains only the fresh complete version-2 run.

The 36/33/33 rejected holdout scores are zero-divergent-span abstentions, not
missing requests or runtime errors. All remain in metric denominators. The
native reference intentionally uses scalar CPU microbatches; timings are host
evaluation timings and do not establish Android/Fold latency budgets.
