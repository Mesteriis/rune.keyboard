# Contextual v5 corpus tooling review

Overall: **PASS — prior P2 strict-admission finding resolved**. Spec compliance and code quality PASS for the reviewed corpus generator/loader scope. The historical finding and evidence are retained below.

## P2 re-review and fresh receipts

Reviewed the corrected `corpus_contract.py` SHA256 `100bafb1fa324aa4be500c38bd49f7c54c2ca211ca0149be5bd6f30d52e1371e` and `test_corpus.py` SHA256 `5a13446fbde6d5d73752bbfe59c718883a332b606297d45f91c4831bb74d620e`. `generate_corpus.py` remains `b1a0b9fff0115aa081e78beb67587431ad0dd8e673b4431db50e6302823b2bb1`; the locks and extraction/selection recipe are unchanged.

`verify_selection` at `corpus_contract.py:313–339` now loads the exact sibling generator, checks the contract module path, replays its selector from stored article row zero until every quota is filled, and compares the complete canonically ordered row objects and **all** measured counts. `verify_parquet_rows` at lines 342–349 supplies the pinned parquet stream. Full `load_corpus` invokes this replay at line 361 after identity/toolchain/exclusion/schema checks, then repeats input-identity verification. The candidate strings and source spans must therefore be the actual fixed extractor/selector output; internally consistent partial words, alternative selections, or invented rejection counts no longer suffice.

There is no historical implementation-hash exception. Current identity remains mandatory at lines 354–355. The replay import restores `sys.path` in `finally` and rejects resolution to another corpus contract. No scoring, freeze, model, production, legacy-loader or source-pool change is part of this correction.

Independent verification performed for this refresh:

- **20/20 scoped tests PASS**, Python 3.11.14, 17.028 seconds. The new tests prove that the old substring/count checks accept the internally consistent mutations, then require exact replay to reject them. The full-admission regression at `test_corpus.py:282–322` passes rehashed temporary artifacts through `load_corpus`, mocking only source/toolchain acquisition to synthetic fixtures rather than bypassing replay.
- **Full unmocked `load_corpus(run-c)` PASS**, 1,200 rows, with the recorded real Python/pyarrow and all pinned inputs. This replays the actual fixed source selection and all rejection counts. Manifest SHA256: `dbce48cfc68d36a52a1f7c60d96d612dc568012d409dd1015e5685c386461660`.
- **Historical run-a rejected with `MANIFEST_IDENTITY`** in an independent full-load attempt. Run-a/run-b hashes still match their original identities. The author's fresh `selector-replay-validation.json/log` also records rejection of both a/b and current admission of c.
- Independently verified every file digest in `selector-replay-comparison.json`, compared all five c/d files byte-for-byte, and compared the three punctuation files plus attribution across old/new runs: **all unchanged**. Recursive manifest comparison confirms the only a-to-c field change is `identity.implementation.corpus_contract.py`. Old a/b were not patched to claim new provenance.

Read `full-admission-replay-red.log`: both consistent-word and count mutations were accepted by the old full loader and failed the new assertions. Read the retained green and new comparison/validation receipts. Run-c/run-d generation itself was performed by the author with root authorization, not by this reviewer. This refresh performed no code edits, Android/Gradle/device action, scoring, freeze or commit; only review reports were updated.

The original P2 is resolved. Current PASS is strict source-recipe admission, not contextual scoring, semantic precision, unseen product qualification, or an evaluator/policy freeze. All remaining scope limitations at the end of this report still apply.

## Initial review scope and identities

Reviewed `task-contextual-v5-recipe.md`, `task-contextual-v5-implementation.md`, all seven files in `tools/eval/smart-typing-0.3/qualification-v5-contextual/`, relevant frozen-v4 extraction/partition source, and the saved generation/validation receipts. All repository-relative paths below resolve from `/Users/avm/projects/Personal/rune-keyboard`.

| File | Reviewed SHA256 |
| --- | --- |
| `corpus_contract.py` | `b564011b2e68e410618b1d111df2893fc09f330cc885140c11f783468a6e45e4` |
| `generate_corpus.py` | `b1a0b9fff0115aa081e78beb67587431ad0dd8e673b4431db50e6302823b2bb1` |
| `test_corpus.py` | `02cd8bd4a6b4c8f421bcc21970624cdce2f473314316f7984495726ccfb14a49` |
| `source-lock.json` | `b70c04203de82dd1f315f2e66b5c780484352809833adb6068d741c2b2bd1f7c` |
| `exclusion-lock.json` | `7054bae1871a1bf23e6f3875c6f31714cfd65c8066a0ae338f9a0182b5bb8043` |
| `README.md` | `65ed044138101940c86ee019b14a8428188b56a9b14e8e4a185473542bed1d0f` |
| `ATTRIBUTION.md` | `0ad6a828bc8cef7eaea663b39f375b8518814fa5e117d776579675ed9fc09958` |

No source edits, scoring, score-cache reads, freeze, generation runs, device operations, Gradle, commits, or delegation. Ran the authorized scoped Python tests and read-only validation. Two adversarial validation probes used automatically deleted temporary copies of the corpus; original generated artifacts were unchanged. No source excerpts or corpus-row text were printed. Only this report was added.

## Historical P2 — Validate the actual extraction/selection result, not only self-consistent spans and counts

The following finding and reproductions concern the initial `b564011b…` contract, before the correction reviewed above.

Primary locations: `corpus_contract.py:175–177`, `corpus_contract.py:300–329`, and their use by `load_corpus` at lines 338–341.

`verify_article` proves that recorded strings equal substrings at the supplied offsets, but does not prove that the offsets select a complete word emitted by the frozen regex/extractor. `validate_rows` checks the internal offset lengths and casefold transformation, which a shortened substring can also satisfy. `verify_parquet_rows` checks selected article identities/spans and the count of residue-3 articles; it never replays the deterministic per-article minimum/priority selection. The two rejection counters are accepted as any nonnegative integers, without recomputation.

I reproduced both consequences through the **full, unmocked `load_corpus`**, using the recorded interpreter/pyarrow and unchanged pinned sources/exclusions:

1. In one temporary copy, changed all three languages' `priorObservationCandidatesRejected` and `selectedObservationCandidatesRejected` values to zero. The strict loader accepted all 1,200 rows. Actual run receipts report respectively EN 4/43, RU 28/8, ES 15/56.
2. In another temporary copy, selected one English calibration row with a word of at least five letters, removed its final observed letter, decremented `wordEnd`, and updated `currentWord`, Original continuation, selection hash/ID, sorted row order, attribution and file digests consistently. Kept the source article hashes, source text, article identity, partition, boundary and quotas unchanged. The strict loader accepted all 1,200 rows. This is a partial source word that the frozen extractor would not emit, despite satisfying the current substring checks.

The probes establish invalid admission, not an invalid original run-a corpus. They also show why file hashes and a current implementation identity do not suffice: the artifact manifest can be made internally consistent without demonstrating that the named implementation produced its rows/counts. A later trusted freeze receipt can detect changed artifact bytes, but the pre-freeze strict loader must first validate the recipe it claims to admit.

**Required correction:** replay the fixed, score-independent selector while streaming the pinned parquet through the recorded stopping point, using the verified exclusions. Compare the full canonical selected rows and every measured language statistic with the submitted artifact. Alternatively, exact extractor-membership validation must reject partial words, and deterministic selection/count validation must independently establish all remaining recipe outputs. Add regression tests for both probes, including full admission rather than only the lower-level digest helper. Preserve the existing generated bytes/receipts; a validator implementation change must receive honest new provenance rather than being represented as the implementation that generated the old manifest.

## Passing spec checks

- Source and exclusion identities are pinned independently of runtime receipts (`corpus_contract.py:25–26`, `79–85`, `262–271`). I compared the exclusion lock against the recipe's exact SHA/path block: all **40 paths and hashes match**. Baseline full loading verified those inputs and the pinned parquet/source/reference-generator files.
- Article selection uses the unchanged seed 7042026 with residue 3 (`corpus_contract.py:144–146`); the referenced v4 code uses the locked same-seed residue selection before punctuation extraction. Split assignment is independently seeded and deterministic at lines 149–150. Generator ownership at `generate_corpus.py:73–97` admits at most one row per article; selected observation signatures are shared across both splits for each language. The fixed priority, per-cell quota, stored row order and minimum `(selectionHash, observationKey)` match the recipe.
- `generate_corpus.py:13–36` preserves the v4 NFC, alphabet, casing, whitespace, bounded-prefix and selection-hash extraction semantics. The retained leading space after oversized UTF-8-tail truncation is consistent with the reference function; the validator's `rstrip` condition does not silently change those source bytes.
- Prior exclusions cover typed/current/expected/candidate endings and pair chosen/rejected endings, across all pinned prior splits (`corpus_contract.py:102–141`). Normalized-prefix and last-up-to-12-alphabetic-token comparisons match the recipe. New article/context overlap and quotas are checked at lines 227–234. These are exact normalized observation checks, not a semantic independence guarantee.
- V5 admission is separate from legacy spelling/full-corpus loading. It requires exact artifact filenames and manifest/row/source/span schemas, duplicate-key/nonfinite JSON rejection, v5 punctuation scope, Original continuation, no automatic application, UTF-8 bounds, explicit observed-boundary semantics and fixed quotas. The generated schema does not pretend that source punctuation is semantically unambiguous.
- Fresh output scope is enforced before generation (`generate_corpus.py:120–125`), with source/toolchain identities checked again before writing at line 142. The manifest records source/exclusion/implementation identities, runtime identities and attribution; scoring, qualification and freeze flags remain false. The implementation contains no model-scoring or threshold-selection path.

## Initial executed verification and real receipts

- Independently ran the 17 scoped synthetic tests with Python 3.11.14: **17/17 PASS**, 2.747 seconds. No model/runtime dependency was used by these tests.
- Independently compared all five run-a/run-b output files byte-for-byte and checked their digests against `comparison.json`: **PASS**. The common manifest SHA is `59b6e1df6b2eef7beb5e3ed2039bb5b23d2b4eb8816c486fff239b017aa66e53`.
- Independently called full `load_corpus(run-a)` with the recorded Python/pyarrow environment: **PASS, 1,200 rows**. The validator checks 1,200 unique article and observation identities and all 24 cells at 50 rows. This establishes that the original artifacts satisfy the present loader; it does not cure the demonstrated loader gap.
- Read `run-a.log`, `run-b.log`, `strict-validation.json/log`, `comparison.json`, `tests-green.log`, and the retained first-failure receipt. The successful run logs agree on counts and manifest SHA; the earlier failure identifies `PREFIX_OR_BOUNDARY` and no output directory. I did not execute either generation or independently witness their process independence. Their retained receipts plus byte comparison are the available generation provenance.

The current tests do not detect the finding: span tests mutate a field without consistently updating dependent fields, and the count test rejects wrong scans/unknown/negative values but permits arbitrary nonnegative rejection counters (`test_corpus.py:158–168`, `202–218`).

## Remaining scope and claim limits

The corpus is not scored, frozen, or release-qualified. Current Kotlin variant export, observed-boundary-to-candidate mapping, policy parity, calibration/freeze sequencing, and future score-receipt binding remain separate integration work described in the handoff. Their absence is not counted as a defect in this generator/loader slice, but this review does not certify them.

Per-article source provenance and licenses are retained, and documentation correctly limits metrics to observed-source agreement, coverage/abstention and insertion rate at source spaces. Equal quotas do not imply chat prevalence; no semicolon/question/exclamation source strata exist; related articles or unknown pretraining may overlap. The corrected loader's PASS establishes strict fixed-recipe admission with the new identity and receipts described above.
