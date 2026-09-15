# Candidate retrieval for manual suggestions

## Spec and goal

The user authorized improving candidate retrieval after the word-ranking experiment
found the expected word absent in 593 of 1500 typo queries. Implement and measure a
bounded optional expansion before learned manual ranking. Existing corpus results
are diagnostic/regression evidence; reserve a new public article cohort for a final
check. No claim of improved accuracy without comparing actual generated candidates.

## Global Constraints

- Work in the existing codex/morphology-style worktree; preserve unrelated changes.
- Existing three-candidate generation and automatic admission must retain their
  behavior. Additional candidates are manual suggestions only and may never enter
  automatic/model replacement admission or the certified distance-one set.
- All new runtime behavior has a default-off settings toggle, global disable support,
  configured/effective diagnostic state, and editor/language eligibility checks.
- Original remains separately selectable. Cancellation, stale reply rejection,
  reader failure handling, and finite state/terminal/text bounds remain enforced.
- No new private chat processing, network runtime dependencies, or model weight changes.
- Preserve raw check output and exit codes in ignored build/typing-retrieval.

### Task 1: Implement bounded optional manual retrieval

Inspect the generator, packed search, worker/coordinator, manual display projection,
settings and diagnostics. Add an optional manual candidate pool of at most seven
verified distinct alternatives. Start with the existing radius-two packed search
at width seven. If implemented, radius-three search is limited to Russian unknown
words of at least seven scalar characters, stays within a separately explicit
8192-state/64-terminal budget, and is manual only. Keep the baseline generation
and all automatic decisions separate from this optional pool. Avoid duplicate
search where the baseline already yields the requested pool. Report the exact
entry point so the host observer and Android benchmark can call production code.

Add settings persistence/UI/global disable/diagnostics and lifecycle invalidation.
Add regression tests for off/on pools, manual selection, unchanged automatic
behavior, language/editor eligibility, settings toggles, cancellation, bounds,
valid/protected tokens, and stale results. Run focused JVM tests, self-review,
commit only task-owned files, and write an implementation report.

### Task 2: Compare retrieval and integration

Controller-owned: build a reproducible host comparison against the baseline using
the actual production entry point, and retained shipped CatBoost/context weights.
Report coverage and top-one/top-three suggestions by typo count, correct-word
controls, completion/budget counts, and host latency separately from Android.
Use already exposed data for diagnostic selection. Freeze the chosen configuration
before the new final public article cohort is evaluated. Reject an expansion that
has no useful coverage gain or disproportionate latency; document the decision.
Run relevant JVM, Android integration/latency, lint, privacy and boundary checks.
Document measured results and limitations, package the APK if runtime work is kept.

### Task 3: Review and finish

Review Task 1 for spec and code quality, then review the full current task change
including evaluation and evidence. Resolve material findings, archive review
artifacts, and report actual outcomes. No merge, push, or physical phone install.
