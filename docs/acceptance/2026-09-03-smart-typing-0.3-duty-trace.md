# Smart Typing 0.3 — synthetic CPU duty traces, 2026-09-03

Baseline: `6fb5880efa7815189cfb559675eaecc5775d2b57`. This slice adds nine
ordinary-CI regression traces of the actual `LatestScoringWorker`, with injected
wall/process-CPU clocks and a synthetic engine. No production behavior changes.

Protocol: `tools/qa/smart-typing-0.3/duty-traces/PROTOCOL.md`. Public synthetic
inputs cover RU/EN/ES × 2/4/8 candidates, unchanged full input identity,
rapid replacement, warm completion, denied demand, deadline cancellation,
queue expiry, idle credit recovery, failed load, pressure, rearm and exhaustion.
Whole-worker completion, debt and lease-release assertions are mandatory.
Costs are fixed simulation inputs derived from the earlier Fold baseline, not
new measurements. No calibration/holdout data or threshold changes are involved.

Each trace submits 11 requests: 6 enter the engine; 4 are denied, including one
expired pending request; 3 admitted operations cancel; 2 return OK; 1 returns
LOAD_FAILED; 1 pending request is replaced. These categories overlap. Of the
nine first warm completion probes, only five finish within the hypothetical
1000 ms boundary. Every exhaustion probe leaves -7450 units of debt. The
100 CPU-ms/25 wall-ms cancellation tail is injected, not observed on Android.

The first passing harness used NO_MODEL for the failed-load phase. Final source
uses LOAD_FAILED; the initial XML remains archived and is not evidence for this
corrected branch. Inputs, timing, constants and event ordering did not change.
Report validation exposed an empty-element truthiness bug allowing an embedded
JUnit failure, and an incorrect expected-debt calculation that forgot refill
is capped before CPU debit. Both were corrected; the negative parser control
is archived. Independent arithmetic gives `(8000-8400)*15 + 25*2 - 100*15 = -7450`.
No duty profile was changed to improve results.

Validation: fresh complete JVM **564/564 PASS**, no failures/errors/skips;
Python report contracts **7/7 PASS**; exact report extraction from final XML
PASS; prescribed lint/build/privacy/dependency/native gates **PASS**, 238 tasks,
27 executed. New CI steps perform the same report validation and retain outputs.
Remote GitHub execution remains unrun because no push is authorized.

Evidence: `tools/qa/smart-typing-0.3/results/2026-09-03-model-duty-trace/`.
Source identities, first/final JUnit XML, numeric results, report and check logs
are retained. XML hostname is redacted; raw XML hashes remain in provenance.
Final report is reproducible from the archived normalized XML.

This completes the virtual-clock CI part only. It does not prove real process
CPU/wall cost, Binder trace behavior, idle-unload timing, usable results while
actually typing, model quality, physical energy or the full device trace gate.
No new API26/API37/Fold runtime tests were required for this test-only change;
their earlier results remain scoped to their earlier source checkpoint. PR7
consumer/ranking and PR9 contextual integration, quality and release gates
remain open. No version bump, remote PR or model publication.
