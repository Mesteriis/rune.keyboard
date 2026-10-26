# Contextual ranker Android integration

The owner authorized continued autonomous autocorrection development, Android testing and commits. Integration is in progress; this record does not claim that the offline model is enabled or installed.

## Feature data and extraction

The first integration step ports the exact 38 grammatical and 12 pair-count features into Kotlin, with independent mapped, checksum-validated public-data indices. All validation runs before worker-side publication. Lookups search bounded blocks of 32 front-coded keys, retain no user query cache and make no source/admission decision.

`tools/typing_experiments/contextual_assets.py` exports the full frozen tables and dictionary query space, rather than a test-vocabulary substitute:

| Input | Records | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| Frozen Wikipedia table | 500,000 | 14,912,091 | `e16f45a1c97c58d900efbffab498441389d7d0823f1d9ab4512b6085daae812b` |
| Frozen conversational training table | 63,320 | 2,083,526 | `2fb480d5264ab5e6120695822bf4c7b6ddc839582a3bac7dd1b83299e27f77e6` |
| Dictionary query spellings | 3,142,432 | 39,593,067 | `2e58a4d702f415de6579434247e3256909dc7546cfd77d64f878a4695a6d3a2b` |

Counts preserve the same stored-table word/prefix masses as training, including a negative gain when a candidate pair is absent but the original pair exists. Dictionary projection retains the full-analysis ambiguity count independently of distinct compact grammar codes. Query spellings include the pinned analyzer's е/ё alternatives. Secondary case normalization and the vocative are represented. An initial export rejected the previously unrepresented vocative; its exit 1/log is preserved, and the corrected full export exited 0. No incomplete asset was published.

Small public test fixtures compare Kotlin outputs with the Python training extractors, using the pinned dictionary and frozen full-table denominators. All 49 constructed cases match for 38 + 12 features at double precision (tolerance 1e-12) and with exactly equal float32 bits. Coverage includes ambiguity, е/ё, missing-pair gains, Unicode boundaries, decomposed input, tabs, noun case, infinitives, personal-pronoun agreement and short predicates. Fixture attribution is in `app/src/test/resources/context-feature-parity/README.md`.

## Checks completed for this step

- `PYTHONPATH=tools/typing_experiments python3 -m unittest test_contextual_assets test_grammar_context_features test_word_context_features -v`: 14 passed, exit 0.
- `./gradlew :app:testDebugUnitTest --tests '*ContextFeatureParityTest' --tests '*PackedContextIndexTest'`: five tests passed, exit 0. Parser tests cover cross-block lookup, kind/hash mismatches, truncation, invalid offsets, unordered/duplicate keys and payload rejection with valid recomputed checksums.
- `./gradlew :app:testDebugUnitTest`: 1,088 tests across 112 suites, zero failures/errors/skips, exit 0.
- Initial parser/fixture test mistakes were corrected before the final runs: a changed opaque payload byte is not structural corruption; and an asserted ё-spelling must be present in the fixture. Initial failing logs remain under the ignored run root; no failed check is counted as a pass.

Full generated assets, export receipts and command logs are retained in ignored `build/contextual-runtime-20261026/`. Generated full assets are not yet packaged. Model loading, runtime policy/controller integration, full replay, Android timing/Undo acceptance and device installation remain pending. Existing product behavior and model assets are unchanged at this step.
