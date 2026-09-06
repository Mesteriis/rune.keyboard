# Production candidate calibration export

This host-only tool runs the current production `CandidateGenerator` and
`PackedCandidateLexicon`, including membership, protection, language routing,
weighted edit features and the shared 8192-state/64-terminal limits. It uses
the existing frozen packed lexicons, whose complete bytes/structure are checked
by the production loader before execution. No model or Android editor is used.

The exact existing corpus files are hash-checked and validated. Only the 6,000
calibration spelling rows reach the generator; its input contains a numeric
row index, language and typed token. Prepared candidate sets, expected answers,
labels and context never reach generation. It exports original plus up to seven
actual alternatives and features. `--maximum-alternatives` fixes the requested
limit (1–7, default7) before execution using the production constructor. The
receipt records that limit; it cannot be lowered after a search exhausts its budget. Missing expected words stay missing. Partial
search results keep their AutoReplace veto. Results are not confidence estimates
or an AutoReplace policy.

Run from the repository with Python 3.11+, JDK17 and the existing hash-pinned Kotlin compiler
cache. Index/rank arguments identify pre-existing caches with the frozen bytes;
replace the example paths if the cache layout differs. No download occurs.

The default corpus remains the original evaluation directory. A later frozen
corpus must be selected explicitly with the same `--corpus <directory>` on
calibration export, deterministic fitting, generated-candidate scoring,
combined fitting, ranker-control export, and every product-holdout command.
Receipts bind the selected relative directory and manifest digest so artifacts
from two corpora cannot be combined. For a candidate other than the original
Rune Text 0.1 artifact, generated scoring also requires its exact
`--expected-model-sha256` and `--expected-model-bytes`; product and contextual
holdout scoring inherit the digest from the frozen model config and require the
exact byte count. The evaluator rejects malformed identities before launching
the native runner.

```sh
python3 tools/eval/smart-typing-0.3/pipeline/export_calibration.py \
  --output build/smart-typing-0.3/pipeline-calibration-01 \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --rank-dir build/smart-typing-0.3/packed-lexicon-reader-prototype/rank-assets \
  --java java --gradle-cache "$HOME/.gradle/caches/modules-2/files-2.1"
python3 -m unittest discover -s tools/eval/smart-typing-0.3/pipeline -p 'test_*.py'
```

The output must be a fresh directory under repository `build/`. It contains
public synthetic inputs and candidate text, compiled harness, raw protocol,
JSONL candidates, summary and provenance. Source and asset hashes are rechecked
after execution. Failed stages preserve evidence and do not produce successful
provenance. Compilation uses two host processors/768 MiB and a 120-second timeout;
generation uses the same process limits and a 600-second timeout. Neither time
nor memory setting is an Android performance measurement.

`summary.json` describes candidate recall and retrieval completion only. It
reports row and unique-token counts because the original prepared corpus has
candidate-set-sensitivity repeats that become identical generator inputs. Those
rows must not be described as independent typing observations. No confidence
threshold, quality PASS, Wilson precision interval or AutoReplace count follows
from this export. The calibrated decision layer and final holdout report remain
separate work. This tool has no holdout execution option; adding that phase must
require a frozen calibration configuration and preserve the earlier model report.

The output text is permitted only because these are checked-in public authored
fixtures. This developer harness is not packaged in the APK and is never an IME
logging/export path.

## Deterministic calibration and generated-candidate model scores

`calibrate_deterministic.py` consumes a verified production export and fits a
bounded integer policy grid on calibration only. The decision function receives
only generated features and retrieval veto, never corpus labels. It ranks by
quarter-unit edit cost, integer `ceil(log2(frequencyRank))`, repetition, fallback
and length difference. A replacement must beat both the original's calibrated
OOV penalty and the next returned alternative by a positive margin. Missing or
incomplete retrieval abstains. The chosen minimum word length is also calibrated.

The fixed grid has10800 parameter combinations per language and width. Selection
uses `--minimum-precision-percent 95|97|99` (historical default 99, Rune 0.3
default 95) and requires <=0.5% false changes among all
correct/protected rows. Among admissible combinations it maximizes correct
replacements, then minimizes errors, then prefers larger margin/minimum length
and smaller original penalty. Remaining ties keep the declared grid order.
Corpus `noAuto` annotations are evaluation errors for replacements, not runtime
vetoes. Reports retain all2000 rows/language and count repeated inputs explicitly.
Wilson intervals are descriptive for these correlated authored rows.

```sh
python3 tools/eval/smart-typing-0.3/pipeline/calibrate_deterministic.py \
  --compiled-export build/smart-typing-0.3/production-width-4-02/export \
  --output build/smart-typing-0.3/deterministic-calibration-four-fresh
```

The output is a new directory with immutable config/report files. Configuration
hashes bind the exact grid, generator receipt, corpus and evaluator sources.
This provisional calibration does not authorize AutoReplace. Kotlin integration
and the final combined pipeline require their own frozen configuration and
holdout gate. No holdout option is provided here.

`score_generated.py` replaces every prepared candidate panel with the actual
original + generated alternatives. Only IDs, prefix and those candidates reach
the CLI. Original-only sets are omitted because the product does not submit them;
incomplete sets with alternatives remain available for suggestion evaluation.
The space goes into the owned prefix, matching the current controller boundary.
Authored annotations and expected answers never reach the model. A new score
cache identity binds the actual requests, executable and exact model digest;
the earlier failed prepared-candidate holdout stays untouched.

```sh
python3 -u tools/eval/smart-typing-0.3/pipeline/score_generated.py \
  --compiled-export build/smart-typing-0.3/production-width-4-02/export \
  --output build/smart-typing-0.3/generated-model-calibration-four-fresh \
  --runner build/smart-typing-0.3/native/rune-score \
  --model build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf
```

Use `--limit 3` for a smoke run; the identical full command resumes the validated
cache. Only `complete.json` plus a fully validated cache proves completion.
`run-input.json`, a process log, or a partial cache alone does not. Scores contain
IDs/numbers only. Model errors remain explicit and cannot authorize replacement.
These host measurements are not device latency or battery results.

## Combined calibration and Kotlin parity

`calibrate_combined.py` fits deterministic features plus the difference between
candidate and original average log probabilities. It searches 43200 combinations
per language using the same explicit precision profile and false-change constraint and adds
model weights 1/2/4/8. The preselected deterministic policy handles absent or
failed scoring. All rows remain in the report. Model-ready calibration assumes
results are available at the boundary; it does not measure device availability.

```sh
python3 tools/eval/smart-typing-0.3/pipeline/calibrate_combined.py \
  --compiled-export build/smart-typing-0.3/production-width-4-02/export \
  --scoring build/smart-typing-0.3/generated-model-calibration-4-01 \
  --deterministic-config build/smart-typing-0.3/deterministic-calibration-4-01/config.json \
  --output build/smart-typing-0.3/combined-calibration-fresh
```

`export_ranker_controls.py` accepts those same first three arguments, plus
`--combined-config` and a fresh `--output`. It produces a hash-bound numeric-only
control set for `CandidateRankerTest`: 6000 inputs with expected deterministic
and combined decisions. No typed words, expected spellings or annotation labels
enter the Kotlin fixture. Kotlin validates bounded finite scores and candidate
IDs, normalizes in the same operation order, and applies both rival margins.
The controller now uses the same six fixed language/mode coefficient sets for
suggestion order and selected state. The active language is captured with the
local request; the callback cannot infer or change it from a winning candidate.
The production coordinator requests exactly three alternatives before search,
then submits original plus those actual alternatives to the model. Original
remains visible and preferred below the calibrated margin. Partial retrieval may
order suggestions but never supplies a preferred correction. Full numeric oracle
parity covers the product policy constants as well as the arithmetic kernel.
This is suggestion integration only: calibration carries no editor-write
authority. AutoReplace/Undo and the frozen final pipeline holdout remain open.

## Frozen product spelling holdout

The product holdout is a separate one-way pipeline. It requires the immutable
combined and deterministic calibration configs plus the exact calibration
generator receipt. `export_product_holdout.py` rejects changed production
generator sources, lexicon assets, candidate width, corpus or config linkage,
then runs the production generator on the 6,000 spelling holdout rows. It has no
fit or threshold-search function. The historical deterministic config source
map remains protected by its canonical config digest; executable ranker sources
are checked against the later combined config that consumed that fallback.

```sh
python3 tools/eval/smart-typing-0.3/pipeline/export_product_holdout.py \
  --output build/smart-typing-0.3/product-holdout-export \
  --combined-config tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-combined-calibration/config.json \
  --deterministic-config tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-deterministic-calibration/width-4-config.json \
  --calibration-export build/smart-typing-0.3/production-width-4-02/export \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --rank-dir build/smart-typing-0.3/packed-lexicon-reader-prototype/rank-assets \
  --java /path/to/jdk17/bin/java \
  --gradle-cache /path/to/.gradle/caches/modules-2/files-2.1

python3 -u tools/eval/smart-typing-0.3/pipeline/score_product_holdout.py \
  --holdout-export build/smart-typing-0.3/product-holdout-export \
  --output build/smart-typing-0.3/product-holdout-scores \
  --combined-config tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-combined-calibration/config.json \
  --runner build/smart-typing-0.3/native/rune-score \
  --model build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf

python3 tools/eval/smart-typing-0.3/pipeline/evaluate_product_holdout.py \
  --holdout-export build/smart-typing-0.3/product-holdout-export \
  --scoring build/smart-typing-0.3/product-holdout-scores \
  --combined-config tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-combined-calibration/config.json \
  --deterministic-config tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-deterministic-calibration/width-4-config.json \
  --calibration-export build/smart-typing-0.3/production-width-4-02/export \
  --output build/smart-typing-0.3/product-holdout-report
```

Scoring is resumable and stores only public corpus IDs plus numeric results.
`evaluate_product_holdout.py` applies the frozen policies once and reports exact
counts, candidate recall, coverage, abstention, precision and false-change with
Wilson 95% row-descriptive intervals. `--minimum-precision-percent 95|97|99`
records the selected release profile (historical default 99; Rune 0.3 default
95). A report may authorize production only if every language has at least 300
replacements, reaches the selected precision profile, has at most
0.5% false changes among all correct/protected rows, and Original in every set.
Host ideal availability does not qualify model latency, energy, physical-device
availability or the real Binder boundary.

## Explicit contextual v5 source-boundary evaluation

`contextual_quality.py` keeps its default `legacy-full` corpus loader and the
schema-2 production-policy receipt checks. The punctuation-only v5 path requires
`export --corpus-format contextual-v5 --corpus <directory>`. It calls
`qualification-v5-contextual/corpus_contract.load_corpus` for complete admission:
pinned inputs, all 40 exclusions, toolchain/implementation identity, exact schema,
quotas and deterministic selector replay. Every current schema-2 export must
retain its repository-relative `corpusDirectory`, exact `corpusManifest` digest
and `holdoutScored:false`. `load_export` repeats the selected full legacy/v5
corpus admission and compares corpus rows, Kotlin input bytes and parsed Kotlin
output with the export receipt. Removing v5 markers cannot bypass corpus
validation through a legacy path with missing provenance. The historical a/b corpus manifests retain their earlier
loader identity and are rejected by the hardened loader. Current c/d use manifest
`dbce48cfc68d36a52a1f7c60d96d612dc568012d409dd1015e5685c386461660`.

Use the corpus's recorded Python 3.11.14 interpreter and pyarrow environment
described in the v5 README. A source-corpus directory contains all 1,200 rows;
export includes both splits without executing a model. Actual Kotlin
`ContextualPunctuationEngine` supplies its seven variants and sentence casing.
Rows excluded by that engine remain in the export with no variants, receive no
model request and remain in every applicable report denominator. Synthetic
protocol checks do not replace the strict corpus loader.

Before model execution, run the existing `verify-policy` command with an absolute
JDK17 path and the pinned Kotlin compiler cache, and review the resulting
synthetic Kotlin/Python parity receipt. The calibration → freeze → holdout flow
uses the existing exact total-log-probability policy: Original advantage strictly
greater than 0.5 and rival advantage at least 4.0. These constants are not fitted
by this tool. `freeze --policy-verification <directory>` requires the current
parity receipt and complete calibration responses; holdout scoring requires its
frozen config. Editing this consumer's source invalidates earlier schema-2 policy
receipts, which must remain as historical evidence. No compatibility exception
admits a receipt from the former average-log-probability evaluator.

Every v5 export, score-input/completion receipt, frozen config and holdout report
binds `corpusFormat: contextual-v5`, `corpusVersion: 5`,
`labelSemantics: observed_wikipedia_boundary` and the hashes of the v5 loader,
generator and both locks. Existing export/config links bind the exact corpus
manifest, actual requests, backend and score bytes through the pipeline. Missing,
changed or mixed v5/legacy semantics are rejected. V5 does not fabricate spelling
rows, `ambiguous`, `unambiguous` or `expectedCandidate` labels.

V5 reports source-boundary agreement of the final suggested decision, suggestion
coverage/abstention, insertion rate at observed spaces, production exclusions,
runtime errors and missing responses. Each language includes all 200 split rows
and four reference-boundary strata of 50. Rates carry their numerators,
denominators and Wilson 95% row-descriptive intervals; empty applicable strata
have null rates/intervals. `decisionCounts` also exposes semicolon, question and
exclamation suggestions, although those boundaries have no source strata.

Original/abstention counts as a source-space agreement, including when caused by
production exclusion or runtime error. Those causes remain explicit counts and
rates with complete denominators; an error never becomes a suggestion. Coverage,
abstention, exclusion and error rates use all rows in the language/stratum.
Insertion at observed spaces uses all observed-space rows, including exclusions
and errors. Missing responses appear in standalone diagnostics; a final report
requires a complete validated score cache for every submitted row. Automatic
replacements remain zero.

These are stratified observed-source diagnostics. Source punctuation is not a
unique semantic answer from a bounded prefix and one following word, and a source
space is not an ambiguity label. Equal quotas do not estimate chat prevalence;
article/observation exclusions do not establish semantic independence or absence
from unknown pretraining. V5 configs/reports explicitly record
`qualityGateEstablished: false` and `semanticCorrectnessEvaluated: false`. No
numeric contextual gate, semantic precision claim, spelling qualification or
device-performance claim follows from this path. Root owns corpus review,
protocol freeze and authorization of subsequent real scoring.
