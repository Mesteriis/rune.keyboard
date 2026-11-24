# Q6 selector diagnostic: word-row overlap reporting

The source-bound text diagnostic accepted optional word rows but its aggregate
status used only the text-specific historical counts. Synthetic rows with a
historical lexical overlap or a control-article overlap therefore returned
`BLOCKED_COVERAGE` instead of `BLOCKED_OVERLAP`. Publication remained
forbidden; the full exposure subreport already contained those overlaps.

The diagnostic now includes the combined text-and-row exposure counts and
runs the existing spelling preflight on nonempty word rows. The resulting
`wordRowPreflight` includes control contexts and surfaces, family and source
identity overlap and row identity errors; the status reports an overlap or
identity blocker when present. Aggregate overlap counts are diagnostic
signals across axes, not unique rows. The file wrapper also binds the new
preflight helper and its direct helper files. An empty word-row input is
reported as `null`. Source and label attestation, registry completeness and
publication remain separate and unproven.

The two word-row-only lexical/control cases failed against the previous
implementation and passed after the fix. The initial test fixture omitted a
required language and failed schema validation; an intermediate implementation
also failed due to a local variable collision, which was corrected before the
final run. The complete focused suite passed 16 tests, including protected
context, row-identity, bound-file and helper-drift cases; the underlying corpus-preparation
suite passed 25 tests. Both suites passed from a staged source archive without
`build/`, which was removed after testing. The historical full-text run was not
repeated because its source shard is currently absent. No model, corpus,
registry or APK was changed.
