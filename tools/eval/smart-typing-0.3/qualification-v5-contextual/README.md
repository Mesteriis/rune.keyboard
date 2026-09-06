# Contextual punctuation v5 source-observation corpus

This tool selects a new, unscored Wikipedia pool for contextual punctuation evaluation. It does not load a model, inspect score caches, fit thresholds, establish a quality gate, or qualify spelling. Generation remains separate from root-owned review, corpus freeze and scoring.

The source and exclusion locks pin three cached Wikipedia shards and all 40 recorded prior context inputs. The source lock records the old v4 lock/generator identities. SHA256(`7042026:<language>:<article_id>`) first eight bytes, interpreted big-endian, modulo four must equal three. V4 used two with the same seed on these shards. Training used other shards; residue numbers with different seeds do not establish disjointness.

Each language contributes 200 calibration and 200 holdout rows, with 50 observed spaces, commas, colons and periods per split. Article split is SHA256(`contextual-v5-split:<language>:<article_id>`) first byte modulo two, zero for calibration. The fixed extraction seed is 5062026. Selection follows stored parquet order, takes at most one row per `(language, article_id)`, fills colon/period/comma/space cells in that order, and takes the smallest observation hash within the article/cell. Quota exhaustion fails. No source pool is selected based on scores.

Prior corpus, training/validation and Wikipedia pair-pool prefixes are excluded after NFC/casefold/whitespace normalization. The last up to 12 alphabetic tokens of prefix plus each observed/candidate continuation are also excluded; selected v5 observations use the same signature. This catches exact and suffix observations across changed IDs/boundaries, not semantic paraphrases or unknown pretraining overlap.

The frozen extraction recipe may retain leading whitespace after an oversized UTF-8 tail is cut at its first whitespace boundary. Those exact prefix bytes are preserved, including in source-span attribution; only exclusion signatures normalize whitespace. The validator checks the exact recorded transformation and does not trim the prefix again.

## Generate and verify

Run from the repository root. The cached model venv interpreter symlink is currently broken; this available interpreter can use its pyarrow package:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=build/smart-typing-0.3/model-v02/venv/lib/python3.11/site-packages \
/Users/avm/.pyenv/versions/3.11.14/bin/python3.11 \
  tools/eval/smart-typing-0.3/qualification-v5-contextual/generate_corpus.py \
  --output build/smart-typing-0.3/contextual-v5-20260906/run-c
```

A second independent generation may target fresh `run-d`. The CLI permits only fresh direct children of `build/smart-typing-0.3/contextual-v5-20260906/`. It emits counts and manifest SHA only. Corpus text stays in the output files. Compare all five output files byte-for-byte; counts alone do not prove reproducibility. Existing output directories must never be overwritten.

The strict integration entry point is `corpus_contract.load_corpus(directory) -> (rows, manifest)`, imported with this directory on Python's module path. It requires the recorded Python/pyarrow toolchain, pinned source/exclusion inputs and unchanged implementation. It validates digests, exact v5 row/manifest schemas, fixed quotas, article and observation uniqueness, prior exclusions, Original continuation, labels and transformations. It then streams the pinned parquet through the actual fixed generator selector, independently stopping at quota completion, and compares every selected row and every measured scan/rejection count. This proves whole-word extraction, priority/minimum selection and the claimed exclusions rather than accepting self-consistent substrings or arbitrary nonnegative counters. It returns v5 rows with `observedBoundary`, not legacy `expectedCandidate` or semantic ambiguity labels. Import and call this explicitly from any future v5 evaluation adapter; do not weaken the existing spelling/full-corpus loaders.

The historical run-a/run-b manifests bind the earlier loader and are preserved with their original receipts. The hardened loader rejects them at implementation identity admission. Fresh run-c/run-d bind the hardened source; their three punctuation files and attribution must remain byte-identical to run-a/run-b. There is no historical implementation exception.

`read_artifacts` is the lower-level digest/attribution layer and is not complete evaluation admission. `validate_rows` validates in-memory rows against an explicit exclusion set. `load_corpus` performs the full source and toolchain checks. Python and pyarrow runtime files, implementation files, input hashes and measured scan/exclusion counts are recorded in the output manifest. There are no wall-clock timestamps or output-directory names in corpus bytes.

Synthetic tests require only the standard library:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tools/eval/smart-typing-0.3/qualification-v5-contextual -p 'test_*.py'
```

The tests use public synthetic strings and temporary artifacts, never a model or real score cache. They cover source normalization/spans/casing, disjoint partitions, prior-observation exclusions, selection ownership, exact 1,200-row quotas, tampered schema/labels/spans/identities/files/counts and malformed JSON. Full-admission regressions rebuild artifact digests and attribution around shortened source words or zeroed rejection counts; replay still rejects them. Only parquet I/O and runtime/input identities are substituted for these synthetic fixtures; the real loader, selector, exclusions, artifact reader and validation execute.

## Schema and provenance

The output comprises `punctuation-en.jsonl`, `punctuation-ru.jsonl`, `punctuation-es.jsonl`, `attribution.jsonl`, and `manifest.json`. Each row has `corpusVersion: 5`, task `punctuation`, `labelSemantics: observed_wikipedia_boundary`, `noAuto: true`, a lowercase `currentWord`, exact `originalContinuation`, `observedBoundary`, deterministic ID and selection hash, and full extraction attribution. Unknown fields, including `ambiguous`, are rejected.

Source attribution contains article ID, URL, title, source shard path, zero-based parquet row, raw/NFC article SHA, exact offsets in NFC Unicode code points, the pre-truncation prefix window, observed separator and observed word. Transformations state NFC normalization, bounded UTF-8 prefix truncation, whitespace changes and casefolding. The future production variant exporter supplies its existing seven variants and sentence-start casing; this corpus does not inject alternative words.

Manifest fields `modelScoringPerformed`, `qualityQualified`, and `frozen` are deliberately false. They describe this generator's actions. Root can bind the reviewed corpus manifest SHA in a separate freeze receipt without editing these bytes or claiming that generation scored or qualified anything. Preserve all old corpus and quality reports.

## Metric scope

Report agreement with the **observed source boundary**, suggestion coverage/abstention, insertion rate at observed spaces, runtime errors and production exclusions, by language and reference boundary. Keep complete corpus denominators; do not remove rows following model disagreement, abstention or failure.

Observed Wikipedia punctuation is not a unique semantic correctness label from a bounded prefix and one following word. An observed space does not prove ambiguity; observed punctuation does not prove lack of ambiguity. Do not call these data semantic precision or ambiguity-suppression evidence without blind adjudication. Equal boundary quotas are a stratified diagnostic, not natural chat prevalence. Related articles may still share information; one row per article does not prove statistical independence.

This recipe has no source-label strata for semicolons, question marks or exclamation marks, although the actual production candidate set may propose them. Describe this limitation when counting those proposals against source references. No contextual quality threshold is invented. This corpus cannot qualify ordinary spelling, and no claim excludes overlap with unknown base-model pretraining or unrecorded external use.

See [ATTRIBUTION.md](ATTRIBUTION.md) for source and license provenance.
