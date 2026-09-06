# Final controller spelling replay — 2026-09-06

This is the completed fixed-policy reproduction on the already revealed corpus, using the actual current TypingSessionController, packaged generators/assets and an independent host editor. It is not new unseen qualification or physical-phone timing evidence. Product source matches c0b0280; later 27c3df2 changes only a QA navigation fixture.

Both splits contain 6,000 spelling rows: each language has 1,000 typo, 700 correct and 300 protected rows. Each split is replayed with model-ready and model-unavailable delivery, preserving all 24,000 observations. The fixed default HIGH_CONFIDENCE policy uses the user-approved 95% point gate; no threshold fitting or corpus edits occurred.

| Language | Correct / automatic spelling changes | Precision | Wilson 95% | False changes / negatives | Typo coverage | Candidate recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EN | 293/304 | 96.3816% | 93.6379–97.9677% | 0/1000 | 304/1000 | 925/1000 |
| ES | 396/408 | 97.0588% | 94.9301–98.3097% | 0/1000 | 408/1000 | 892/1000 |
| RU | 341/358 | 95.2514% | 92.5276–97.0144% | 1/1000 | 357/1000 | 917/1000 |

The point precision, minimum 300 spelling replacements per language, ordinary/aggregate false-change and immediate restoration checks pass. No-model ordinary spelling automatic changes remain zero because deterministic automatic buckets are unqualified. One ES canonical edit is separate; mechanical changed rows are zero in this spelling corpus. Punctuation suitability is reported separately. Detailed counts, cohorts, abstention and Wilson intervals are retained in report.json.

The frozen all-row Original check remains FAIL: 1,901/2,000 on each holdout language. The independent result-audit.md establishes that all 5,703 owned nonempty candidate sets contain Original; the 297 remaining observations are no-word states (294 null composition and three boundary-only find-dot states) preserving exact input. The separate state-based applicability annotation passed independent spec/quality review (original-applicability-review.md); the archived frozen report is never rewritten and no protected rows are removed from any denominator.

All 2,983 calibration and 2,973 holdout requests have exact retained responses. There are 9 calibration and 14 holdout SCORING_FAILED outcomes, zero retries, zero missing responses and zero live payload refusals. These native failures route to unavailable behavior and preserve text. The 33 previously unmatched fragment payloads now have current exact-request evidence.

The immutable GGUF is 396,704,416 bytes, SHA-256 7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4. Runner SHA-256 is bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553. Source, compiler, runtime, assets, request and policy identities are bound in source-freeze.json, export-receipt.json and scoring receipts.

archive-manifest.json records both archived and original byte hashes. Files larger than 500,000 bytes use deterministic gzip; decompression restores the exact bytes referenced by upstream receipts. The compiled host JAR, model and native executable remain local and are not copied here. The original prepared-candidate suitability failure remains a separate experiment. This report does not approve release or main merge.
