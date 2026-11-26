# Q6: isolate the suspended-source historical verifier

The suspended-source registration at `f5546368` binds five then-current helper
files. A later edit to one of those files makes the direct historical check
reject the ledger binding even when the archived disclosure itself is intact.
The five exact helper versions are now retained in one text archive; their
bytes are verified against both historical registry entries before use.

CI runs the unchanged six historical registration tests and `--check` in a
temporary source tree with those verified helpers. The live checkout and the
original entries are not rewritten. A separate test uses the current preflight
and current ledgers to verify that the disclosed word still blocks a candidate
in another article and context; removing the two new historical entries removes
the matching surface signals. Historical reproducibility therefore does not
replace the current admission check.

In a source archive without `build/`, an extra newline was appended to each of
the five live helpers. The old direct verifier then failed with the expected
registry-drift error. The isolated verifier passed all six original tests and
the historical check, and the current preflight test also passed. The temporary
archive was removed. The isolated runner's five tests pass on Python 3.12 and
3.14: they cover changed or duplicate archive data, registry binding mismatch,
failure propagation, unchanged live helpers and refusal of a symlink escaping
the temporary tree. The symlink negative test failed before the fix. The six
historical tests, check and live gate passed on both Python versions; the
previous historical text-boundary runner tests also passed.

The snapshot is checked against the recorded helper hashes, not a signature.
Only this one registration is isolated. Other historical entries may bind
other live helpers and require separate verification or migration; future
ledger-schema changes may also require an explicit historical projection.
Neither this change nor these checks establish complete registry coverage,
independent qualification, hosted CI or device acceptance.
