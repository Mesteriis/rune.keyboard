# Typing model accuracy refinement

> Execution: reuse superpowers:subagent-driven-development for bounded model tasks; performance is the primary measurement skill.

User requested improving both existing experimental models. Existing four switches and automatic/original policy remain unchanged. Work on codex/morphology-style starting at1c6a889.

## Design and constraints
Improve data coverage and candidate discrimination, then measure on an independently reserved public article split. Previous revealed holdout is regression evidence only. No private chats in public assets. Train/dev/test selection is frozen before fitting. Keep existing APIs, finite bounded Kotlin inference and off-thread asset loading. Russian only. No runtime ML framework. Preserve current dynamic-tap priors unless independently validated to avoid changing an unrelated feature silently. Publish only models that improve the intended held-out metrics without material latency regression; if a candidate fails, retain the better shipped component and report why.

## Tasks
1. Parent: prepare source-hashed public data from already pinned ru-0007.parquet (separate from v1 ru-0009). Deduplicate contexts, group by source article, train/dev/test split. Export actual production candidates with no gold-label injection. Freeze caps and artifacts, keep raw generation failures.
2. Neural worker: train stronger compact context model on train text, select checkpoint/hyperparameters on dev only. Keep test unavailable for tuning. Report dev/old baseline comparisons, numerical export/parity and exact dimensions. Bound artifact under1MiB. Do not replace bundled assets directly.
3. Parent: enrich edit/context features, compare classifier/pairwise CatBoost on train/dev only with <=128 trees/depth<=6. Select before new test reveal; calibrate blending on dev. Compare separate switches and combined runtime scores. Preserve v1 and measure candidate-coverage ceiling.
4. Integrate selected assets/feature schema/strict codecs in Kotlin; regression tests and host/Kotlin parity. No changes to candidate generation or automatic admission. Keep dynamic touch model independent if context architecture/checkpoint changes behavior without tap evaluation.
5. Scoped and whole-change reviews, full JVM/lint/privacy/boundary and selected Android tests/latency. Record exact metrics/limits, build APK and keep branch.

- [x] Data and split freeze
- [x] Neural training and review
- [x] CatBoost and blend selection
- [x] Fresh test and integration
- [x] Validation, final review and APK

Acceptance note: new fixed synthetic article test improved combined top1 from1209/1477 to1390/1477, while exposed v1 regression changed686/926 to679/926. Accepted as a documented optional/default-off experiment; no claim of uniform improvement or automatic correction qualification. Runtime has independent unchanged tap priors.
