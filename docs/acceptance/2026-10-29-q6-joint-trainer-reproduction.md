# Q6: real historical joint trainer reproduction

The guarded trainer ran on the original pinned public joint corpus and original
train/calibration observation receipts with NumPy 2.2.6 and CatBoost 1.2.8.
It fitted 5,492 training groups and scored 5,480 calibration groups. The
produced RET2 binary and calibration-scores JSON are byte-identical to the
retained original outputs; the short and long policy thresholds and metrics also
match the original policy. The CatBoost JSON model has identical feature,
oblivious-tree and scale/bias sections. Its metadata differs in model GUID and
training-finish time, so its whole-file hash is not identical.

The output policy is explicitly `historical-disclosed-calibration`, with
`independentQualification=false` and `productionQualified=false`. The current
trainer bound and rechecked the original inputs, context, feature code, source
receipt and both registry bytes before policy publication. Exact numeric hashes
and comparisons are in the [receipt](2026-10-29-q6-joint-trainer-reproduction-evidence.json);
raw output and log are under `build/review-q6-joint-trainer-real-20261029/` and
`build/review-hosted-editor/joint-trainer-real.log`.

This is a real reproduction of already disclosed data, not an independent
holdout, fresh natural-text quality assessment or permission to ship a model.
New independent training remains blocked until held-source attestation and
complete registry coverage are established. No packaged asset, app or device
was changed. The earlier emulator used for the full API26 run had been stopped.
