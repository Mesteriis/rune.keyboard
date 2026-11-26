# Q6 retrieval source boundary audit: Unicode marks and underscore

The earlier boundary audit tested alphanumeric and hyphen neighbors but did not
explicitly count combining marks or underscores. A separate source-bound audit
now checks the character immediately before and after each of the 1,800 frozen
retrieval targets in the pinned, NFC-normalized public Wikipedia shard. It
reconstructs each `prefix + target` occurrence, rejects missing or duplicate
sources and input drift, and records aggregate counts without source text.

All 1,800 rows matched once. None had an underscore or combining mark adjacent
to its target on either side. This supports the earlier results for these two
character classes only; it does not resolve the suspended hyphen case, prove
complete Unicode word segmentation, or qualify a fresh corpus. The previous
historical auditor and its hash-bound receipts were not changed.

The source, source-lock, historical rows and auditor identities are bound in
`build/q6-retrieval-unicode-audit-final1/report.json`. An independent second run
produced an identical report. Three unit tests cover both sides, repeated
matches, missing source and duplicate rows. The first second-run command had a
misspelled script path and failed before executing; the corrected run succeeded.
Full Q6 historical coverage and independent qualification remain open.
