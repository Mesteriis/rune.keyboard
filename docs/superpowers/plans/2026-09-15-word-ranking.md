# Candidate-level context training with harder errors

User approved training to select complete words and adding multi-error typos. Continue performance + SDD in the existing worktree from be476a3. Preserve independent switches, original-first/manual-only policy, CatBoost and tap models, REC2 shape and runtime score.

## Frozen experiment

1. Public data: pinned ru-0007 parquet/frequency; exclude first2155 previously scanned articles and every previously used article ID. Article-hash train/dev/test assignment, exact article/context dedup, at most12 targets perarticle and4 occurrences pertarget/split. Deterministic synthetic edit categories with verified optimal-string-alignment distance exactly1/2/3; no expected-word injection into generator. Quotas train single2000/double2000/triple1000/correct1000; dev400/400/200/200; test600/600/300/300. Reserve text caps250000/100000/100000. Correct rows are controls, excluded from typo ranking fit/accuracy denominators.
2. Export real production alternatives, freeze manifests. Worker never parses held-out data; hash-only receipt integrity is allowed. Reuse previous verified train typo groups as an anchor; previous dev remains dev, never train. Fit only groups with an available expected word, at least2 alternatives, and an actual competing label. Missing targets remain evaluation failures. Report coverage by edit count.
3. Fixed training: initialize exact shipped REC2 48x48, unchanged CatBoost. Pair/list softmax loss over actual `tree + clamp((mean logP including final space+3)*.25,-.5,.5)` divided bytemperature0.1. Distillation KL from original character distributions, coefficient0.1, retains general language behavior. One configuration, Adam resetlr0.0001 decay0.9, batch16groups, seed17092026, epochs6; checkpoints1/2/4/6 plus original. Average losses pergroup to avoid long-word weighting. Train on new+oldtrain groups once each per epoch, shuffled deterministically. No future character context.
4. Dev selection: greatest combined top1 on new typo dev, ties greater old dev combined, then exact original preferred, then earlier epoch. Freeze selected artifact hash before new test. No extra checkpoint selection after test. Promotion gates: fresh overall strict improvement and double/triple combined strict improvement; fresh singles no lower; combined counts on all three revealed old tests no lower. Otherwise retain shipped models and report experiment, coverage and limitations.
5. Host tests, numeric export/parity and scoped/whole review. If promoted: regenerate artifact identity, parity/provenance, run relevant full JVM/Android/lint/privacy gates, measure scorer latency and package. If rejected: no app edits or redundant Android rerun. Public reports include aggregate outcomes, no private dialogs. Same model dimensions do not establish equal phone latency.

- [ ] Frozen data and actual candidates
- [ ] Candidate-level training and dev selection
- [ ] Fresh evaluation and regression gates
- [ ] Review and conditional promotion/validation
