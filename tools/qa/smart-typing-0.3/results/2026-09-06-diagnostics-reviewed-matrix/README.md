# Reviewed diagnostics integration and first complete152 matrices

Exact reviewed app APK `6a7d0d179b5c0446d88991cb14359ca63f97ce570e1ec09e2692667399f721e1`.
Base full-suite test APK `8cac96cae9a02b20a90fc93f0912b0de291d261dbca1b0f5bffd2026f2914d0a`.

| Target | Actual cases | Failures | Assumptions | Duration |
| --- | ---: | ---: | ---: | ---: |
| API26 first full152 | 148 PASS | 1 | 3 optional-model | 1196.409s |
| API37 first full152 | 149 PASS | 0 | 3 optional-model | 1123.269s |

All five strengthened diagnostic settings/real-editor cases pass on each API.
API26 failed before preview phase1 touched its target: the test looked up b/B
immediately after a settings-triggered input-view replacement. The subsequent
reviewed test-only delta waits for that exact target to become visible. It preserves
actual target geometry/policy assertions and the complete1000ms preview observation.
Both isolated changed-case runs pass (API26 18.439s; API37 17.875s). This is not a
claim that API37's full152 used the changed test APK. The API26 complete rerun is
archived separately after completion. Initial failures are retained unchanged.

The prescribed full local gate command passes (300 Gradle tasks). All actual debug,
release and profile source/packaging checks pass. Focused final JVM scope passes
147/147; XML records are included. API37 current JNI scope passes6/6. Whole-project
postcommit JVM verification remains separate; no new commit is claimed here.

`base-input-receipt.json` binds3902 source/input files and all APKs; changed-source
copies are from that frozen build snapshot. `preview-target-wait/` binds its single
source delta and changed test APK `6f79d6284941893e5d32cf63db249212f2233691b60e2114e6fe5b4ed246def5`.
No product source or app APK changes in that delta. APK binaries remain local in
ignored build storage. Per-case counts exclude standalone numeric sendStatus(0)
bundles without class/test identifiers and retain assumptions as non-passes.

Earlier lint/recreation/protected-popup failures remain in their original archives;
passing reviewed results here do not erase them. This archive does not approve0.3,
close current-model quality, or qualify the physical phone.
