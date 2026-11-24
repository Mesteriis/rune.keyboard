# Q6 historical context training feature replay

The retained v1–v8 training vectors were checked against a fresh feature replay
without fitting or promoting any model. Six distinct input sets were recomputed:
831,273 candidate vectors across v1, v2, v3, v4, v5 and v7. All regenerated
`float32` values matched their saved values exactly, with zero nonfinite values.
The v6 groups and vectors have the same recorded and actual hashes as v5; v8
likewise reuses v7. Including those two copies, the eight records cover
1,394,597 vector rows. Reuse is recorded as reuse, not as two extra feature
recomputations.

Each model's plan, groups and vector hashes were checked before and after; its
recorded source hashes, 25 app assets, two frequency inputs and morphology
receipt also matched. This validates the retained training groups and current
replay environment against these records, not the complete transitive history,
independent examples or model quality. All eight models remain unqualified.

The reproducible driver is
`tools/typing_experiments/replay_historical_context_features.py` (SHA-256
`674d1d36e5a1feef9996dcce96fbfb7f041ff074c6cda4226fdafcb2eec0c72b`).
With the historical local inputs and scientific Python environment present,
run from the repository root:

```sh
python tools/typing_experiments/replay_historical_context_features.py --output build/context-feature-replay.json
```

Two complete runs produced byte-identical aggregate receipts (SHA-256
`a87834183430eac30e5612497b090cf400fca009291f0518e2307a93da84ffb9`).
The first preceded a tightening of alias metadata checks; the second used the
retained driver. A focused stdlib test verifies rejection of existing and
outside output paths and optimized Python. This replay requires local `build/`
inputs and is not run by CI; its guard test is wired to CI. Hosted CI has not
run this change.

A separate retained score-comparison driver,
`tools/typing_experiments/replay_historical_context_scores.py` (SHA-256
`45edb884631582fbb434eadd20fda91731a7dd1f1db3cdd3d0677cd1df55a90f`),
compares exported scalar scores with CatBoost JSON on all retained training
vectors and checks saved group labels and training diagnostic counts. It checks
bound inputs before and after and requires fresh output inside `build/`. Its
CLI guard test refuses outside output and optimized Python. The full v1–v8 run completed on 1,394,597 saved candidate vectors across
97,528 groups. All saved group boundaries and one-hot targets were consistent,
and every recomputed training diagnostic count matched its stored value. All
exported scalar scores matched CatBoost JSON within `1e-5`; the largest observed
absolute difference was `5.600035679620419e-8`, with no nonfinite values. The
aggregate receipt SHA-256 is
`97e1fca9d5b1dffa0bdde1662c2aca941a6f06085e83f7c92157ce30382cbb82`.
The v6 and v8 models were scored separately even though they reuse v5 and v7
vectors. The replay requires local historical artifacts and a scientific
environment; this is training-vector parity, not model qualification.

A follow-up identity check verified each actual `groups.jsonl` and
`train-vectors.npz` against its frozen record and compared their hashes, group
counts, row counts and widths. Residual v9 uses exactly the v7 input bytes
(30,512 groups, 428,865 vectors of 202 features), so its retained features are
the same ones already reproduced above. Residual v12, v13 and v14 also share
exactly the same inputs (36,272 groups, 503,679 vectors of 242 features). The
latter identity check does not regenerate those 242-feature vectors or prove
score parity for the three distinct residual models.
