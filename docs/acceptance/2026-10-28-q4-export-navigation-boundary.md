# Q4: numeric export belongs to the quality dashboard

The full Q8 integration command uncovered a pre-existing boundary failure:
`DiagnosticsActivity` directly referenced `QualityExportActivity`, causing its
dependency closure to include SAF output and `QualityStore` persistence outside
the exact diagnostics storage/activity. Replacing the controller with its
original bytes in the scanner's source map produces the same three failures;
the Q8 callback change did not introduce them.

The numeric-export button now belongs to `QualityDashboardActivity`. A small
debug-only contributor adds the existing button and launches the same private
export Activity. Release/profile contributors are empty. The diagnostics
management page retains its own log export/delete controls. No scanner exception,
capability allowance, storage implementation, export format or permission changed.

Actual checks:

- The unchanged scoring-boundary scanner passes debug/release/profile, including
  its 17 negative and six positive fixtures. All 69 diagnostics boundary and
  packaging tests pass.
- Debug and instrumentation APK builds and debug lint pass. A real API26 test
  on a fresh task-owned emulator verifies the absence of the numeric button in
  diagnostics, launches export from the quality dashboard and returns to it.
  One test completes, zero skips. It does not choose/write a document or reset
  owner statistics. Existing SAF serialization behavior was not changed.
- The first navigation test opened export successfully but looked for an
  off-screen footer button on return. The final test observes the visible
  dashboard status instead and passes. The failed log is retained.

The tested worktree also contains the separate Q8 controller candidate. The
machine receipt binds that overlay and both APKs; it does not claim a clean
commit-only build. The initial combined release privacy invocation was refused
by the normal dirty-source guard, which remains strict. Clean-source release
checks are a separate integration requirement.

See [receipt](2026-10-28-q4-export-navigation-boundary-evidence.json) and
[user instructions](../quality-metrics-debug-export.md). Q4's two actual weeks
of ordinary owner use remain outstanding. No Fold, owner clipboard, publication
or new model training was involved.
