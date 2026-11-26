# Q5: check Undo observations against editor text

The historical chat reporter counts Undo using the observer's
`restoredBeforeBoundaryExactly` flag. For Space boundaries it did not verify
that flag against `beforeBoundary.text` and `afterBackspace.text`: a changed
control with an incorrect post-Backspace text and a `true` flag was reported
as having zero Undo failures. This is a report-integrity gap, not evidence
that the prior observer emitted a wrong flag or that Rune's Undo failed.

`chat_corpus_report_v2.py` preserves the historical reporter and adds an
independent equality check for every supplied observation. It refuses missing,
malformed or contradictory snapshots and flags before creating its report;
real failed Undo is retained as a failure. Its report binds input and helper
bytes and remains descriptive, with no independent qualification claim. The
documented command now uses v2; v1 remains available for historical receipt
reproduction.

Five focused tests pass, including the counterexample accepted by v1, a real
failure, missing fields and CLI refusal without output. Both committed public
replay baselines, 2,160 plus 12,000 observations, have complete text snapshots
and consistent Undo flags under the new check. Those are regression inputs,
not the previously reported 34,330-row chat run; its discarded raw observations
were not rechecked here. Eight original quality-slice tests, 18 local-stress
tests and the staged 183-module stdlib inventory check also pass. The first
inventory check, before the new test file was staged, correctly rejected that
untracked file as stale; it is not a passing check.

No model, policy or Android code was changed. Source-label quality, clustered
natural-chat qualification, phrase/revision coverage and Fold acceptance
remain open.
