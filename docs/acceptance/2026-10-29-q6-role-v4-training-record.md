# Q6 role-v4 historical training record

The surviving ignored `build/right-context-training-v4-20261027/` directory
contains a training plan, selected groups, vectors, an experimental model and a
frozen-model record. The model, plan, groups, vectors and selection bytes each
match the corresponding hash in that frozen record; the plan and frozen record
also agree on all 11 feature-source identities. The frozen record declares
8,286 groups, 118,635 candidate rows, 178 features and `qualified=false`.
The separate training-only diagnostic reports the same group and candidate
counts and a scalar/CatBoost maximum absolute difference of approximately
`5.38e-8`. These are recorded training-set facts, not independent quality or
precision metrics.

The initial training log records a `FileExistsError`; the retained retry log
contains vectorization progress and a model-frozen marker. The log, diagnostic
and frozen-record hashes are respectively
`e8a84d84eb50e6bb516670bac66bedd6f83f888129f41a9dc261217025478687`,
`6ec90295864b24c860bcd6f1fd294b800f932f9354f3822f1f6725d9e60cd734`,
`90dfa2f20d2193bb1b86059c462ba50835c6b281b5033dbb0374a13d2e3aaa3c` and
`f98ebe251ae5a62a3fb47b163988dcf7e378cd2e78ea19dd6604f17edbdfe9b0`.
These retained records are evidence of the recorded run, not a fresh independent
reproduction or proof of runtime use.

The corpus manifest names the restored role feature source with hash
`2442a38501946f6fcaad293a99b11d0ad785123efb1fe207b03beb5332a841d0`;
the training plan and frozen-model record instead name the later version
`181fff1a36ee769db22269d54de9a00efb58155520d5fa3d793ef217dfcdfadc`.
A tracked archival copy matches the latter. Thus restoring the earlier source
closes its corpus-manifest identity gap, but does not establish that the model
was trained with that earlier version. The original artifacts remain local;
no model was promoted or installed by this audit.

A later local numeric replay loaded the retained CatBoost JSON and saved vectors
without fitting a model. The binary model, vectors and group file were verified
against the frozen record first; the scalar scorer source also matched its
historical source hash. All 8,286 group boundaries, 118,635 candidate rows and
one-hot targets were verified. Recomputed training cohort counts exactly match
the stored diagnostic. Across 604 candidates in the first 32 groups, the
exported binary scalar scores differed from CatBoost JSON scores by at most
`5.37608273454282e-8`, exactly matching the stored diagnostic maximum. The
JSON model SHA-256 is
`d8a3e1af7f463c8196b5ac6c60805f7f01220616a66d7b939aa7df139672cfef`;
the scorer source SHA-256 is
`e5317839f8c3c02ca711236ca0b5aefa37df0e6bb0c1de017bd366939294f7c6`.
The first replay attempt completed the numeric loop but failed when serializing
a NumPy boolean; the corrected second invocation produced the stated result.
This checks retained training vectors and outputs, not historical feature
regeneration, all scalar outputs, unseen examples or independent qualification.

The comparison was subsequently extended from the first 604 candidates to all
118,635 retained training vectors. Every CatBoost JSON prediction was compared
with the exported binary scalar scorer: zero nonfinite outputs, maximum absolute
difference `5.600035679620419e-8`, below the predefined `1e-5` bound. The
binary, vectors and groups matched the frozen record before and after the run;
the scorer matched its recorded source hash. The JSON and scorer hashes match
the earlier comparison. The numeric receipt SHA-256 is
`14b8c3be7d9a690851e385288fa2e1397bae5f3da1d0c4e825449fcb4d8788d4` and the
log SHA-256 is `20960df38f25ef4991c0728232ad42bfdd22e32837dc71c73c6b7416d647c5f5`.
This extends score parity only on the retained training vectors; it does not
establish feature reconstruction or independent model qualification.

The historical feature pipeline was then run again against all saved training
groups, without fitting or changing the model. Before and after the replay, the
11 plan-bound sources, 25 installed assets, two count inputs, morphology
receipt, plan, groups and saved vectors matched their recorded identities. All
8,286 groups and 118,635 candidate vectors were regenerated with 178 features;
all `float32` values compared equal to the stored vectors, with zero nonfinite
values and zero maximum absolute difference. Numeric equality does not prove
bitwise identity of different representations of zero. The aggregate receipt
SHA-256 is `1d1d644e87139b5d8ee757a7d0608648b8d9b3461426f30cad64e51bf7842292`
and the log SHA-256 is
`e6c0ee62dc5c96368dd90af8b3912cc04e56adbca19059df11b57f6ca28c10a0`.
This verifies reconstruction for the retained training groups and dependencies,
not unseen data, historical run attestation or model qualification.

The feature replay is retained as
`tools/typing_experiments/replay_historical_role_v4_features.py` (SHA-256
`d0c48edccee0d6d5abb78a714dcff5d07fb5a27eec1402713df1dfef67ec5bce`).
From the repository root, with the historical local inputs and the scientific
Python environment available, run:

```sh
python tools/typing_experiments/replay_historical_role_v4_features.py --output build/role-v4-feature-replay.json
```

Two full invocations produced identical numeric receipts with the hash above
and no mismatched rows. An existing output path
and optimized Python (`-O`, which disables assertions) each refused before
writing. The retained local groups and count files are required; this is not a
portable no-build test or an independent qualification.
