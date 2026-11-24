# U9: reuse consecutive category identifiers

The strict catalog parser now reuses the previously validated category ID when
the next row has identical ID bytes. Changed IDs are still validated, and rows
may still interleave categories. Tests cover interleaving, changed/prefix IDs,
invalid uppercase IDs and reconstruction of the complete packaged catalog.
The input format and asset bytes do not change.

The same predeclared API 26 preview procedure used in the preceding receipt ran
on three new task-owned AVDs, four fresh palettes each, with no retries or
tracing. Handler and populated-window draw-start values, in milliseconds:

| AVD | Handler | Draw start |
| --- | --- | --- |
| 0 | 42.03, 14.55, 7.80, 17.79 | 49.24, 18.63, 12.60, 19.20 |
| 1 | 21.71, 5.57, 7.72, 8.32 | 25.71, 9.35, 12.01, 18.33 |
| 2 | 20.40, 6.82, 7.93, 3.38 | 27.81, 10.26, 16.02, 17.11 |

All 12 observations satisfy the 50 ms preview gate, with only 0.76 ms margin
on the slowest draw start. This unpaired, small series cannot establish a causal
speedup or a reliable tail bound. It measures preview click-to-draw start, not
touch delivery, GPU presentation, cold IME startup, release performance or
Fold. Eight API 26 native emoji font/panel/key tests passed after timing on the
first AVD. All three task-owned AVDs were stopped and deleted.

The full JVM suite passed 1,372 tests with no skips; 15 emoji source tests,
debug lint and the IME/scoring boundary also passed. Raw measurements, APK
hashes, validation logs and cleanup receipts are under
`build/review-u9-id-reuse-20261028/`. The result JSON SHA-256 is
`a18703f50e615ba7544082515aa2b2050e324de5d61c2a9bd4e4c45336a679d4`.
No physical device was used and no replay was run. U9 remains open for the
broader startup, PSS, presented-frame, Fold and manual accessibility checks.
