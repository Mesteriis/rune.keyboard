# Subtree frequency bound experiment — not adopted

Baseline: 3459033462f90eb6fb4048e9e96f92bbcf501a52. This isolated trial derived
two-byte subtree minimum ranks in the validated loader and added frequency to
the exact global frontier bound. Zero-context patch and hashed raw evidence are
retained here; the patch is NOT present in production.

Correctness: 596 JVM tests passed after correcting a cap fixture to equal
frequencies (the original sequential ranks now legitimately certified early).
All prescribed local product gates passed. The complete 773-request oracle had
257 complete / 479 incomplete / 37 policy results, zero violations. All 905
previously complete calibration results were preserved exactly. Correct-candidate
complete retrieval changed EN184→196, RU366→407, ES314→346. No holdout or model ran.

API26: the same 60 development queries, two warmups and five measured passes
per strategy; both asset/search instrumentation tests passed before and after.
Previous app/test APK hashes match `../2026-09-03/android-tested-apks.json`.
Top-seven CPU p50/p95/max ms changed 5.871/14.528/21.202 →
6.308/15.182/90.671; exhaustive control p50/p95 changed 4.255/5.832 →
4.282/6.007. The last maximum is a single observation, not a stable latency bound.
Baseline was collected while host build work could overlap; these measurements
do not establish causality or physical energy behavior. Nonetheless they provide
no evidence of a CPU saving to justify the extra 7,558,460 dictionary bytes plus
32,776 scratch bytes. API37/physical follow-up was not run for this rejected trial.

Decision: retain the unchanged exact search and investigate repeated prefix DP
replay first. Rank bounds may be reconsidered only with a measured benefit and
memory justification. This is not a final candidate-quality or battery result.
