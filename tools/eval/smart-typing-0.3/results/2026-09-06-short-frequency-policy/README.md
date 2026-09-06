# Frozen short-frequency candidate-policy evidence

This archive records the completed **revealed-data** experiment `revealed-data-short-frequency-candidate-policy-acceptance-v1`. Status: **QUALIFIED NUMERIC ONLY** under the agreed ≥95% point precision, ≤0.5% correct/protected false changes and ≥300 automatic spelling changes per language. It does **not** approve production adoption or unseen qualification. Coefficients, thresholds, model, width three and 8192-state/64-terminal limits were unchanged; no fitting followed final results.

| Split | EN correct/automatic | RU correct/automatic | ES correct/automatic | Negative false changes EN/RU/ES |
| --- | --- | --- | --- | --- |
| Calibration | 345/347 | 354/357 | 430/434 | 0/1000, 0/1000, 0/1000 |
| Holdout | 294/306 (96.0784%) | 341/358 (95.2514%) | 396/408 (97.0588%) | 0/1000, 1/1000, 0/1000 |

Every split contains 6000 rows: 2000 per language, each 1000 typo, 700 correct and 300 protected. Both ready and unavailable controller replay cover every row. Actual fresh response counts are 2983 calibration and 2973 holdout. Holdout model errors are EN2/RU10/ES3, retained in the full denominators; delivery refusals are zero. Unavailable ordinary spelling automatic changes are zero. Exact Undo passes all 2000 rows per language in both modes/splits.

The frozen raw Original gate remains FAIL: calibration1902/2000 and holdout1901/2000 per language, with raw allPass=false. The existing separate ownership annotation accounts for every row: calibration1902 owned+98 no-word, holdout1901 owned+99 no-word; 2000/2000 contract passes in each language/mode. This is full state accounting, not a dropped denominator or rewritten raw result.

Individual regressions are retained. Holdout introduces `ipe→ice` (target `pipe`) and `ipk→ink` (authored ambiguous `noAuto=true`, so target text alone does not make it safe). It also correctly changes `pioe→pipe` and newly abstains on `inb`, previously incorrectly changed to `in`. EN precision decreases from293/304 to294/306 while remaining above95%. There are125 changed ordered holdout requests, all short, with27 target gains and12 losses. Calibration has115 changed ordered requests,39 target gains/five losses; `teh` correctly becomes `the` and `Rofo` newly abstains. The detailed reviews retain all known losses and before/after evidence.

The long-word named retrieval blockers `автокрекция` and `correcion` remain unchanged. This archive does not complete that milestone, physical latency/interaction gates, or release gates. No phone work or unrelated mutable service source is included.

## Layout and provenance

- `run/`: exact export, source/policy freezes, compile log, stage receipts/reports/logs, requests/responses, deliveries, input rows, controller evidence and both comparison joins.
- `bound/`: exact bound repository files, including the41 compiled Kotlin source closure, separate original and variant generator, exact two-line patch, frozen adapter/base evaluator, policies/configuration, evaluation corpus inputs, packaged lexicons and toolchain manifest. The original production generator is retained separately from the compiled buildcopy variant.
- `tools/`: focused adapter/base evaluator and ownership annotation tests plus the existing annotation tool.
- `reviews/`: probe, scoped policy, preparation, calibration and holdout reviews.
- `baseline/`: the exact original controller evidence required by the comparison joins. It was not rescored or mutated.
- `manifest.json`: exact original paths, original/decoded hashes and sizes, archive hashes and sizes, source closure, freezes and excluded executable/model/toolchain identities.
- `archive.py`: writer and standalone `--verify` entry point. Writer command and final verification are recorded in the accompanying task archive report.

Large text (≥32768 bytes) is encoded using gzip level9 with mtime0 and no filename field. To recover original bytes, decompress the listed gzip entry to its manifest source-relative location; smaller files retain exact bytes. Existing bound `.gz` files are preserved as identity-encoded source bytes. Every entry's archived and decoded SHA256 is verified. The manifest excludes itself from its own entry list; its external SHA is recorded in the task report.

GGUF, APK, JAR and native executable/runtime binaries are omitted. Their exact hashes and byte lengths remain in `excludedBoundArtifacts` and original receipts, including the compiled controller jar. These external tools/models are required for replay; this archive is an evidence package, not a bundled executable environment. Original receipts retain original path identities: do not rewrite them to pretend they were produced in the archive directory. There are no mutable phone-fix files in the41-source closure.

Verify without model, Java, Gradle, devices or repository source imports:

```sh
python3 tools/eval/smart-typing-0.3/results/2026-09-06-short-frequency-policy/archive.py --verify tools/eval/smart-typing-0.3/results/2026-09-06-short-frequency-policy
```
