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

## Full-data extraction and unified scorer

After the feature-port commit, a host JVM harness compiled the actual Kotlin index/extractor sources and opened all three full generated assets. Every one of 67,143 candidate vectors in 5,564 complete groups from the frozen grammatical holdout matched all 50 Python feature values, with exactly matching float32 bits and maximum double error `1.1102230246251565e-16`. Host index validation took about 484 ms; this is not Android startup or latency evidence.

`ContextualRanker` now assembles 95 existing features + 6 Wikipedia + 6 conversational + the frozen character score + 38 grammatical features. Its 146-feature model decoder is explicitly selected; all older model loaders still require the existing 95-feature schema. Wrong-sized or non-finite score vectors fail closed. The final score is `0.8 * tanh(tree / 4)`; the character score is not added again.

A separate harness compiled the current product model classes and scored the same 67,143 actual candidates, including the original-token option, using the full indices and frozen model `4d7bf2a9477b588046a1187c11e206bd1ca6f73180e8abf3b21c84f024a783f0`. All scores matched the frozen Python computation within `2.220446049250313e-16` (required tolerance `1e-8`). The harness inputs contain candidate attributes and reference numeric scores, not expected spelling labels used to choose candidates. Source/JAR/asset hashes and command logs are retained in the run root.

`./gradlew :app:testDebugUnitTest` after scorer integration: **1,090 passed, zero failures/errors/skips**, exit 0. The two new scorer tests cover explicit dimensional selection, invalid vectors, unsupported language, missing character resources, and exclusion of an additive character bonus. Loading the model into the process resource owner, automatic policy/controller integration, packaged assets and physical Android acceptance are still pending; no new model is enabled by this step.

## Controller and packaged resource integration

The process owner now maps the three feature indices off the main thread and publishes the unified ranker only after all data/model/policy identities validate. Missing or invalid data leaves the previous path available. `ctx` and `gram` are stored uncompressed for read-only APK mapping. The new automatic path has a separate model/data/threshold fingerprint and an appended diagnostic source, `CONTEXTUAL_RANKER`.

The contextual decision applies after the existing baseline. It compares the original and complete joint pool, uses the frozen score/margin point, and calls the existing source/personal admission before accepting a candidate. An existing replacement can be retained or vetoed, not silently replaced with another word. Boundary execution rechecks contextual readiness/qualification and existing source admission. Original-word, rare-word, protected-input, incomplete-search, session/cursor and personal veto protections remain in force. English/unsupported languages are not qualified for this model.

The observer gained a distinct `contextual-production` mode. Initial verification caught two observer routing omissions: the new mode first incorrectly requested a ready model-service response, then skipped recovery. The resulting failures and 98 apparent prior-correct losses were rejected, not qualified. Production/joint-mode classification was centralized; a five-case regression smoke check passed before the corrected full replay. No model weights or thresholds changed in response.

Corrected controller comparison on all **12,000** frozen inputs:

- **585 additional correct / 6 additional wrong (98.9848%)**, satisfying the owner-approved 95% criterion and minimum volume.
- **Zero** prior-correct losses, correct-word control changes or prefix mutations.
- Exact before-boundary text restoration after Backspace for **all 12,000** inputs in both baseline and contextual modes.

The corrected controller outcome reproduces the frozen offline counts. New policy tests cover acquisition, exact admission refusals, existing replacement retention/veto, explicit baseline abstention, original protection, incomplete/not-ready evidence, missing resources, score/margin refusals and fingerprint drift. Full JVM run: **1,094 tests passed**, zero failures/errors/skips, exit 0. Main and Android-test APK assembly succeeded.

## Physical Fold acceptance

Both AURA and Android MCP chats explicitly confirmed no retained phone workflow. The Android MCP LAN session was unavailable and its local package profile authorized only `dev.androidmcp.fixture`; no profile/permission/companion changes were made. Rune used this thread's independently authorized existing ADB/instrumentation development workflow on the explicitly selected Fold. Local shared reservations and chat coordination were used; each update/instrumentation invocation was explicit and finite.

The installed baseline matched `b348bb37f969032f79278686642756a8d2ee330a7482be437f6fb072c946bf31`. Main/test APK signer sets matched that baseline before update. One main `install -r` retained app data; no uninstall, data clear, downgrade or permission grant was used. Packaged model/policy/index bytes and uncompressed mapping entries were verified before installation. Installed main APK, verified again after testing:

`4f27f441046a86fb61b6cd9c4f4e86bd2436ff2b8c00f612b4843d8ce2eaeb7f`

Two final native instrumentation methods passed:

- `learnedContextualCorrectionsAtTwoPacesPreserveExactUndo`: **20/20** real-touch phrase cases at 50/100 ms pauses; six newly available corrections, two existing correction cases and two unchanged controls at each pace. All **16** spelling corrections had exact Undo. All checks for unexpected editor payload reads passed.
- `repeatedRealTouchInputAndUndoKeepTheRequestedCharacters`, two rounds: **8/8** phrases with **160** exactly matching native DOWN/UP pairs and **4** exact spelling Undo checks. The new policy corrects `ты можешь позвоеить` to `ты можешь позвонить`, including when continuing with `позже`. Earlier corrected words remain corrected after subsequent typing.

The first added forensic run correctly rendered its checked phrases but failed an overbroad new zero-read assertion after an unrelated ordinary boundary deletion. Source inspection identified the sole production `getTextBeforeCursor` call in the pre-existing bounded (64 UTF-16 units), non-sensitive grapheme-deletion fallback outside owned composition. The final forensic test preserves strict zero-read assertions for typing and exact spelling Undo; it does not assert that ordinary deletion outside owned composition has the same contract. No production deletion/Unicode protection was weakened. Initial failing artifacts remain private and are not counted as a passed run.

The native exported journal contains `CONTEXTUAL_RANKER` boundary `AUTO_REPLACE` and editor-accepted entries, confirming that the new path executed on the device. Journal stream entry counts are not presented as unique correction counts. Full touch traces/logs are private and ignored; no screenshots were collected. These functional typing tests and host timings are not Android frame-time, cold-start or general keyboard-latency benchmarks.

### Owner state and release

The three original SharedPreferences files match their fresh pre-update hashes exactly, including a delayed recheck, and the three relevant system IME settings match exactly. No restoration write was needed. Four known `no_backup` personal stores are currently absent and match the earlier verified pre-window snapshot; however, the fresh pre-update capture in this run covered SharedPreferences only. Thus this report does **not** claim a contemporaneous before/after hash check of those four stores. They were not restored from an older snapshot. Future device snapshots must explicitly cover those four `no_backup` paths as well as preferences.

Three exact task-created journal cache directories were privately collected and removed by their generated names. All instrumentation processes ended; the reservation was released, and both coordinating chats were explicitly notified. No further phone commands followed release. The new main APK remains installed.

The packaged provenance preserves the pre-acceptance snapshot taken when the APK was constructed. This external acceptance record and ignored `physical-device-receipt.json` bind the subsequent checks to the exact installed APK; packaged pre-test status is not used as proof of physical qualification. The five previously disclosed grammatical-form errors remain unresolved; passing this aggregate gate does not claim otherwise.

## Final source checks

The staged-source JVM run passed all **1,094 tests**, with zero failures, errors or skipped tests. The test task executed after declaring directly read assets and parity vectors as Gradle inputs, so changes to those data files invalidate the test cache. Root `:app:lintDebug` passed.

The optional archived-source native build did not pass: the archive lacks the root Git/submodule metadata required by the reviewed llama.cpp revision guard. A local pinned submodule clone did not supply the missing root gitlink metadata; the guard was retained. This is not counted as successful native validation. APK assembly in the actual Git checkout and the physical Fold checks above passed. The final build-script change declares JVM test inputs only and does not change the installed application behavior.
