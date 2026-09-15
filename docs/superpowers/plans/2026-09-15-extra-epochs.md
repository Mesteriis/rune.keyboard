# Additional context-model epochs

User requested further improvement through additional training. Continue performance + subagent-driven-development workflow in the existing isolated worktree, starting at79868bd.

1. Freeze experiment before fitting: continue the shipped REC2 48×48 weights for twelve additional epochs on the exact prior public train text, Adam restarted (previous optimizer state is unavailable), learning rate0.0005 with0.9 decay per extra epoch; checkpoints+2,+4,+8,+12. Keep the original model as a candidate. No CatBoost/tap/feature/runtime architecture changes.
2. Prepare a fresh public test from the same hash-pinned parquet, excluding all first1920 articles previously scanned and all prior used article IDs; reserve1500 synthetic single-error rows and250000characters. Export actual production candidates without labels/context. Never use this test for training or selecting checkpoints.
3. Select using existing verified dev only: combined score with unchanged CatBoost, ties prefer lower character cross-entropy; exact tied original preferred. Freeze chosen hash before fresh evaluation. Repeated previously exposed tests are regression gates, not validation or model-selection inputs.
4. Promote only if selected candidate improves dev, improves fresh combined top1 by at least one row, and does not lower combined correct counts on either previously exposed test. Otherwise retain existing APK/model and report actual experiment results. No further checkpoint selection after test reveal.
5. Verify numerical parity, host regression tests and review. If promoted, regenerate public provenance/fixtures, run JVM/Android/lint/privacy gates and package. Existing independent switches and logs remain unchanged. Same dimensions imply same operation count, not a claim of measured equal phone latency.

- [x] Training and frozen dev selection
- [x] New test and regression evaluation
- [x] Review, any accepted promotion and validation

Outcome: experiment completed; extra2 failed the predeclared acceptance gates. All application/runtime/asset files retained.19hosttests pass; whole-change review approved.
