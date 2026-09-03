# Rune Text 0.2 candidate evidence — 2026-09-04

The exact Q4_K_M candidate in `candidate-report.json` is rejected. It reached
at least 99% precision on the authored calibration rows, but that result did
not transfer to the previously revealed disjoint development rows. The latter
are diagnostic after reveal and are not a new release holdout.

No model was activated, packaged, published or declared device-qualified. The
next candidate must train on a pinned public multilingual sentence corpus, then
freeze a new family/template-disjoint calibration and untouched holdout before
any model scoring. API 26, API 37 and physical Fold latency, memory, thermal and
energy gates remain separate.
