# Local morphology experiment — 2026-09-15

Host-only proposal comparison; no Android policy or neural weight changes.
The actual production candidate generator uses the shared width constant and
all 12 packaged trie/length/rank/case assets. A pinned OpenCorpora-derived
morphological graph adds bounded context evidence. A public n-gram profile is
trained only on calibration references; no coefficients are fitted on holdout.

## Public RU qualification-v2 reproduction

Each split contains 1000 typo and 1000 negative-control rows. On holdout:

| Proposal policy | Correct changes | False changes | Precision |
|---|---:|---:|---:|
| Current local/common-confusion |364|0|100.00%|
| + morphology |393|1|99.75%|
| + morphology/public context frequencies |395|1|99.75%|

On calibration the respective counts were 358/3,391/6,452/6. Calibration includes
texts used to train public frequencies and is not validation of that profile.
The existing corpus is revealed data; these results do not establish unseen
accuracy or full editor behavior. Mechanical and canonical-case edits are not
part of the compared proposals. Existing qualification remains unchanged.

Public report SHA-256: `3fbb2ab36e4e711e7034b6ad26ef67f764dd004a5397ba876d9b82f0b615497c`.
The ignored report and receipts bind sources, actual consumed inputs, model data,
compiler dependencies and dictionary files. Source changes invalidate replay.

## Host timing

On 4000 rows: generator p95 1.32ms; morphology p95 0.25ms;
morphology with public frequencies p95 0.27ms. Dictionary initialization including
a forced public-word lookup took 14.68ms. Ranking distributions include fast
eligibility abstentions. They are not Android keystroke latency or energy claims.

## Verification

- New-module unittest discovery: 53 tests, PASS.
- Existing typing diagnostics analyzer: 19 tests, PASS.
- Actual Kotlin public export: 4000 rows, PASS.
- Additional private source-bound runs completed; private data and their learned
  profile are not repository artifacts.
- Reviewed and fixed consumed-path receipt binding, production candidate width,
  evaluated original retention, lazy dictionary timing, and helper-source hashes.
- Android instrumentation not run: this patch adds only host-side tools/docs.

See `tools/morphology/README.md` for reproducible setup, data boundaries, commands
and experimental limitations. A separate calibration/qualification and Android
integration remains necessary before enabling new automatic replacements.
