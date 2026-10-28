# Joint correction diagnostics, original protection and supplemental ranking

> Historical material from 2026-10-25. The original body is retained.
> Its source, model and device claims are not fresh acceptance. Current scope
> and outstanding evidence are in the [review completion map](../plans/2026-10-27-review-completion.md).

The primary model and its thresholds remain unchanged. A separately pinned public-data model can correct long Russian words only after both the baseline and primary model abstain. Known and rare originals, protected words and personal rejections retain their vetoes. A missing or mismatched model, policy or qualification fingerprint disables this additional path.

Diagnostics schema 8 appends JOINT and JOINT_RESCUE sources and precise refusal reasons: rare or valid original, unavailable resource, incomplete search, insufficient score or margin, original preference, and admission veto. Ranking records carry no text payload. Late Space replies retain the original request revision. A protected original cannot trigger a futile external ranking request or late replacement. Explicit manual choices remain available.

For short rare originals, manual suggestion ordering can prefer common nearby words. The protective dictionaries are unchanged and this display preference cannot authorize an automatic replacement. Long-word manual ordering uses the separately validated model only when the primary model abstains.

## Validation

The frozen supplemental model and policy were trained/calibrated on public Wikipedia data only. Independent evaluation uses a fresh disjoint 4,788-row corpus, including 1,000 controls. Replay delivers baseline, recovery and manual pools and uses the controller's actual token after automatic capitalization. The comparison disables only the supplemental model in the baseline.

- 126 additional correct replacements across 107 families; zero new wrong replacements.
- No control changes, lost old correct replacements, changed prefixes or Undo failures.
- Long-word totals: 2,501 correct and 14 wrong replacements; the 14 existing errors remain.
- Previous holdout: 115 additional correct, zero new wrong; 15 existing wrong replacements remain.
- Independent manual cohort, 867 abstained long typos: top-1 444 → 483; top-2 559 → 628.
- Public reproduction produced identical model, calibration scores, training receipt and frozen policy bytes.

These results supersede the initial one-phase replay and an intermediate replay that mishandled capitalized tokens. Neither model nor thresholds were tuned on the independent evaluations or private text. Per-slice legacy `passed` fields in the provenance are inherited broad product gates; the separately stated acquisition and regression gates authorize this narrowly scoped addition, not overall product readiness.

Model/policy hashes, corpus hashes and numerical results are packaged in `app/src/main/assets/smarttyping/experiments/joint-rescue-provenance.json`. Private dogfood captures and replay details remain under ignored `build/` and are excluded from model fitting and tracked fixtures.

## Final build and Fold

- JVM: 1,068 tests, zero failures/errors/skips. Diagnostics Python: 64 tests passed; debug/release/profile packaging checks passed.
- `:app:testDebugUnitTest :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug`: BUILD SUCCESSFUL. Scoring-boundary verification and `git diff --check`: passed.
- Final production source replay: all 4,788 boundary, Undo and hint outputs identical to the evaluated native-equivalent version.
- Physical SM-F966B: initial full run 7/8 passed; the final ordinary-typing test stopped when the UI driver could not resolve the key `т`. No replacement mismatch was reported before that lookup error. An unchanged-build targeted repeat passed all 14 ordinary typing cases (`OK (1 test)`). This retains the initial failure as a test-driver reliability limitation; it is not an 8/8 clean full run.
- The other seven physical tests passed, including four new supplemental replacements with exact Undo, rare-original diagnostic refusal, empty-field Backspace, fast typing, preview and Undo preserving the following word, and diagnostic reopen.
- Installed APK SHA-256 equals the checked build: `cf496475aa0d40c6b20dac75bae13de7023b145d3f3cc033bf3075158ac26bd8`.
- Owner preference fingerprint and four personal-store fingerprints unchanged. Rune explicitly enabled/selected after test teardown; a diagnostic baseline was saved before opening a fresh QA field.

Aggregate evidence: [JSON](2026-10-25-joint-diagnostics-and-rescue-evidence.json).
