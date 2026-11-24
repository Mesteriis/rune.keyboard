# Q6: early RU unknown surfaces in the control registry

The existing lexical registry marks 171, 222 and 261 distinct unsupported
target surfaces from the disclosed qualification-v2, compact-v3 and compact-v4
RU spelling corpora. Rechecking the retained, hash-verified row files found
all 654 exact surfaces once each. Before this change, the control registry
already contained nine corresponding RU surface keys, leaving 645 without an
exact-surface entry. Its incomplete-coverage gate already refused unqualified
collection; this change does not imply those inputs had previously passed that
gate or that global coverage is complete.

The control registry now contains a source-bound regression entry with all 654
surface keys: 645 newly excluded and nine already present elsewhere. Its
existing regression anchor supplies the required context-key fields; the new
entry's purpose is conservative exact-surface exclusion, not new labelled
examples. The registration script verifies the original v2 manifest and rows,
the retained v3/v4 archive/manifests, all three lexical parents and their
unsupported-surface counts. It hashes the source inputs and parent entries,
refuses missing or changed parents and does not infer lemmas or intended senses.
No corpus, lexical entry, model or APK was changed.

A dry run in a separate checkout and the actual atomic registration produced
byte-identical registry files. The dry run confirmed every prior control entry
and top-level field was preserved. The new check is wired into CI and the
stdlib inventory. Fifty-two local tests across the new guard, both ledgers,
early importer, archive checker and v6 target checker passed. A real previously
unlisted v2 surface now triggers `CONTROL_SURFACE_OVERLAP`; without the new
entry the existing incomplete-coverage gate still refuses the sample. Removing
a lexical-parent surface is rejected. Product replay disclosure checks, the
v6 target check and inventory validation also passed. The initial new test
expected the old guard to accept incomplete coverage and failed; it was
corrected to assert the actual refusal. A preceding test-file creation attempt
used the wrong relative path and failed before writing the file.

This closes an exact-surface gap only. Unknown canonical families, broader
corpus/source exposure, per-row licensing, available-v6 reconstruction and
independent qualification remain open. Hosted CI and Fold were not run. The
temporary dry-run checkout was removed.
