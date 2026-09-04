# Rune Smart Typing 0.3 — prepared-candidate suitability

This offline developer harness evaluates whether **Rune Text 0.1 can rank prepared continuations**. It makes no IME, candidate-generation, correction-engine, device-latency or production-quality claim. The runner returns numeric scores only. No generation endpoint, network inference or personal messages are used.

## Corpus and interpretation

**Corpus version 2** contains **13,200 rows**. Version 1 was superseded before holdout after a label/probe review; its scores must not be reused with this manifest. Each language (RU/EN/ES) has separate calibration and holdout cohorts with exactly:

- 1,000 controlled typo probes from at least 100 authored word families;
- 1,000 no-change probes: **700 candidate-set perturbations of 100 correct-word contexts**, plus 300 protected-token probes;
- 200 punctuation-boundary probes: 100 initial-subordinate-clause comma suggestions and 100 deliberately underdetermined fragments.

These are **clustered synthetic stress probes, not 13,200 independent sentences**. Correct-word panels deliberately repeat the word/context while changing competing candidates. Typo panels repeat each authored word across distinct error mechanisms. There are 20 topical spelling frames per language/split, an additional sentence-initial context, and 40 punctuation frames. Metadata records both `family` and `template`; explicit lexical and template identifiers do not overlap between splits. The English curated `the` example adds one calibration family. Protected identifiers and token formats also have repeated structure.

A row-level Wilson 95% interval is reported descriptively. It is **not** a valid independent-sample confidence guarantee for natural typing, and a 300-row automatic-replacement count is not 300 independent lexical families. Family counts and automatic-replacement families are reported alongside row denominators. A future production evaluation needs independently authored contexts, a representative typo distribution, production-generated candidates and cluster-aware uncertainty.

`seeds.json` contains original synthetic vocabulary/context pairs authored for this evaluation, never user communications. The generator adds adjacency, deletion, insertion, transposition, repetition, vowel/consonant errors, Spanish diacritics, varied lengths and sentence positions. The original continuation is always candidate 0; alternatives are deterministically shuffled. Authored nearby real words and inflections in `nearby-words.json` provide hard competitors. Every spelling candidate must be within case-folded OSA edit distance 2 of the typed original, or distance 1 for originals shorter than five characters; an adjacent transposition counts as one edit. Candidate sets contain only admissible alternatives and need not contain four entries. The expected correction records the authored source word, not a model-selected answer.

The mandatory `автокрекция`, `арфография`, `сообшение`, `teh`, `recieve`, `adress`, `mensage`, `correcion` and `pinguino` examples are curated calibration probes. They do not select thresholds or examples based on model success. Explicit authored contrast pairs test English optional borrowed-word accents (`resume`/`résumé`, `cafe`/`café`; separate holdout pairs) and Russian е/ё (`все`/`всё`, `берет`/`берёт`; separate holdout pairs), alongside Spanish ambiguous accents. Every orthographic-policy row includes its recorded alternative, preserves original 0 and has no-auto protection. The ordinary valid word `небо` is separately categorized as `protected_correct_word`; no artificial `нёбо` variant is created. These are conservative preservation probes, not forced error labels. All generated source words of length <=3 abstain from automatic correction; the curated `teh` case has an explicit intended source. The semantic original is preserved on all correct/protected probes.

`position=middle/end` records the authored typing scenario; no following text is sent to the model. Sentence-initial cases have a preceding complete sentence and capitalized original/candidates. Punctuation candidates preserve `currentWord`; only `. ` may uppercase its initial character. **Punctuation is suggestion-only.** Its unambiguous metric currently covers commas after initial subordinate clauses, not four-way punctuation mastery. Ambiguous fragments have a preservation baseline label and are excluded from single-answer suggestion accuracy.

The no-auto policy is an **authored `noAuto` annotation**, not evidence that a production protection detector exists. Protected probes cover names, surnames, brands including Rune/AIGate/HomeAssistant/ESPHome/PostgreSQL, kubectl and shell commands, camelCase/snake_case/kebab-case, IPv4/IPv6, reserved-domain URLs/email/hostnames, semver, UUID, synthetic paths, Python/C++/Kotlin identifiers, mixed-language tokens, ALL_CAPS and digits. Metrics report unprotected correct words separately so protected-policy abstention does not hide false changes.

## Source provenance and licensing

Authored fixtures and evaluation code are original project additions; no repository-wide `LICENSE` is present at this revision, so this directory does not assert a broader redistribution license for project-authored material.

A **collision veto only** uses Dave's [FrequencyWords](https://github.com/hermitdave/FrequencyWords/tree/525f9b560de45753a5ea01069454e72e9aa541c6), pinned commit `525f9b560de45753a5ea01069454e72e9aa541c6`, `content/2018/{ru,en,es}/{language}_50k.txt`. Upstream identifies the content as **CC-BY-SA-4.0**, with OpenSubtitles2018 as source; upstream generator code is MIT. Full source lists are not committed. Exact URLs and SHA-256 values are preserved in `manifest.json`. No frequencies or sentences from those lists appear in the corpus.

A surface form present in the veto list is not automatically a valid word: subtitle lists include errors. Conversely, absence is **not proof of an error**. The filter supplements authored contexts and a conservative collision list; it is not a spell-check oracle or exhaustive human linguistic review. Curated acceptance misspellings explicitly bypass the frequency veto. Known valid-word changes and optional accents must not become unambiguous error labels. A finding that invalidates a frozen label requires a new corpus version and evaluation, not silently repairing holdout after inspection.

To reproduce generation, fetch the three exact URLs in `manifest.json` into `build/smart-typing-0.3/corpus-inputs/{ru,en,es}_50k.txt`. `generate_corpus.py` checks all hashes before reading them. Keep upstream license/attribution with any redistributed source lists or adaptations. The generator reads no model output or score cache.

```sh
python3 tools/eval/smart-typing-0.3/generate_corpus.py
python3 tools/eval/smart-typing-0.3/evaluate.py validate
python3 -m unittest discover -s tools/eval/smart-typing-0.3 -p 'test_*.py' -v
```

`schema.json` describes fixture fields, including `corpusVersion:2` and independent `expectedSpelling` metadata for typo containment checks. The stdlib validator additionally checks counts, original-at-zero, duplicate observations, labels, protected policy, exact punctuation word preservation and explicit family/template leakage. `manifest.json` binds corpus files, generator and authored seeds. It deliberately does not claim automatic detection of every shared semantic stem or synonymous frame.

## Native reference and scoring protocol

See [NATIVE.md](NATIVE.md) for native build, numerical verification and runner procedures. The reference configuration is CPU-only, four CPU threads, `n_ctx=256`, `n_batch=64`, **`n_ubatch=1`**, flash attention disabled and no GPU layers. The native numerical oracle found CPU microbatch-64 log-probability deltas up to 0.5247 versus scalar scoring; the reference microbatch-1 configuration matched the tested scalar oracle exactly. This setting favors reproducible suitability measurements over speed. It is not an Android latency qualification.

The pinned model must have size `396704416` and SHA-256 `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`. Scoring rejects any other model before launching the runner. The CLI invocation is `rune-score MODEL_FILE`; one persistent process accepts JSONL on stdin:

```json
{"id":"sample-id","prefix":"Please check the","candidates":[" adress"," address"]}
```

Each response is either `{id,scores:[{id,sumLogProbability,scoredTokenCount}],durationMillis}` or `{id,error}`. Candidate IDs are exact array indices, count is bounded at 256, numerical values must be finite, sums cannot be positive, and zero-token scores must have zero sum. Returned natural-language text, arbitrary errors, duplicate/missing candidate IDs and extra fields are rejected. Error strings are a fixed native-code allowlist. The process's stderr is not retained in score caches.

PR1 has checks before and after tokenization; cancellation **inside** the pinned tokenizer remains the conditional PR2 work and is not claimed here.

## Calibration, holdout and resume

Python 3.10+ and the standard library suffice. From the repository root:

```sh
python3 tools/eval/smart-typing-0.3/evaluate.py score \
  --runner build/smart-typing-0.3/native/rune-score \
  --model build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf \
  --cache build/smart-typing-0.3/scores.jsonl --split calibration
python3 tools/eval/smart-typing-0.3/evaluate.py calibrate \
  --cache build/smart-typing-0.3/scores.jsonl \
  --out build/smart-typing-0.3/calibration.json
python3 tools/eval/smart-typing-0.3/evaluate.py score \
  --runner build/smart-typing-0.3/native/rune-score \
  --model build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf \
  --cache build/smart-typing-0.3/scores.jsonl --split holdout \
  --config build/smart-typing-0.3/calibration.json
python3 tools/eval/smart-typing-0.3/evaluate.py report \
  --cache build/smart-typing-0.3/scores.jsonl \
  --config build/smart-typing-0.3/calibration.json \
  --out build/smart-typing-0.3/suitability.json
```

`report` writes JSON plus a sibling Markdown report and exits **2 for a failed row gate**, 0 for a passed row gate, 1 for integrity/execution errors. It always records `productionQualified:false`.

Averages are `sumLogProbability / scoredTokenCount`. Confidence is softmax of average scores: it is a normalized ranking feature, **not an empirical probability of correctness**. The fixed calibration grid selects margin/confidence thresholds using calibration-only labels and scores. `calibrate --minimum-precision-percent 95|97|99` freezes the selected user-visible profile (default 99 for historical reproduction); Rune 0.3 selects 95 by default. Calibration requires the chosen Wilson 95% precision lower bound and the 0.5% combined correct/protected false-change upper bound, with deterministic conservative tie-breaking. If no point qualifies, it selects abstention. Ties, missing/error scores and zero-token scores abstain. Rejected rows stay in metric denominators.

The frozen config contains model/runner hashes, calibration-only corpus and score hashes, thresholds and its own hash. It is created exclusively (`open x`), must exist and match completed calibration before holdout scoring, and cannot be created after any holdout row enters the cache. Reports recompute the fixed calibration rule to detect modified configurations. Do not tune the grid, corpus or thresholds against holdout.

Caches contain a model/runner/corpus identity header followed by IDs and numerical score/error results only. Resume validates identity and all completed responses, then skips completed IDs. A runner failure/timeout stops the current invocation and preserves completed rows. `--limit N` allows a bounded smoke run; it does not change identities. `--timeout` is a finite positive per-request deadline, including first-request model startup. A partial final cache line is rejected unless the operator explicitly supplies `--repair-incomplete-tail`; repair validates all complete records and discards only the unterminated tail. Completed error responses remain errors, not retries silently selected for success.

Holdout's descriptive row gate is per-language: >=300 automatic replacements, precision at the frozen 95/97/99 profile, combined correct/protected false-change <=0.5%, and all requested scores present. Reports include coverage, exact denominators, Wilson row intervals, raw top-1, error/missing counts, typo families, automatic-replacement families and false-positive IDs. `abstentionAllSpelling` is the number of spelling rows without an automatic replacement divided by all spelling rows, including policy-protected, error, zero-token and missing-score rows. `preparedOracleCandidateRecall` is the number of typo rows containing their independent `expectedSpelling` divided by all typo rows. The correct word is injected into every valid prepared fixture, so 100% containment is a corpus invariant—not production candidate-generator recall or model-ranking recall. Empty denominators are reported as undefined (`null`). A failure stops model-dependent work; it does not justify unrestricted generation or performance-selected examples.
